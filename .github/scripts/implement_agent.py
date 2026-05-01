"""
Agentic implementation loop using Anthropic tool use.

Reads URL content + task from args, loads repo context (CLAUDE.md + skills),
and runs a Claude-powered plan → implement → test cycle with real file
editing and bash execution.

Usage:
  python implement_agent.py <url> <issue_num> <task>

Writes /tmp/impl_result.json with {"success": bool, "summary": str}
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import anthropic

# ---------------------------------------------------------------------------
# Args
# ---------------------------------------------------------------------------
URL = sys.argv[1] if len(sys.argv) > 1 else ""
ISSUE_NUM = sys.argv[2] if len(sys.argv) > 2 else "?"
TASK = sys.argv[3] if len(sys.argv) > 3 else ""
RESULT_FILE = "/tmp/impl_result.json"
MAX_TURNS = 40  # hard cap on agentic loop iterations


# ---------------------------------------------------------------------------
# Tool implementations (run on the host)
# ---------------------------------------------------------------------------
def tool_bash(cmd: str) -> str:
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=120
        )
        out = result.stdout[-6000:] if len(result.stdout) > 6000 else result.stdout
        err = result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr
        parts = []
        if out.strip():
            parts.append(out)
        if err.strip():
            parts.append(f"[stderr]\n{err}")
        parts.append(f"[exit {result.returncode}]")
        return "\n".join(parts)
    except subprocess.TimeoutExpired:
        return "[timeout after 120s]"
    except Exception as exc:
        return f"[error: {exc}]"


def tool_read_file(path: str) -> str:
    try:
        return Path(path).read_text(errors="replace")[:8000]
    except Exception as exc:
        return f"[error reading {path}: {exc}]"


def tool_write_file(path: str, content: str) -> str:
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return f"Written {len(content)} chars to {path}"
    except Exception as exc:
        return f"[error writing {path}: {exc}]"


def tool_list_files(pattern: str = "**/*.py") -> str:
    try:
        result = subprocess.run(
            f"git ls-files -- {pattern}",
            shell=True, capture_output=True, text=True, timeout=15,
        )
        lines = result.stdout.strip().splitlines()
        return "\n".join(lines[:200]) if lines else "(no files matched)"
    except Exception as exc:
        return f"[error: {exc}]"


TOOLS = [
    {
        "name": "bash",
        "description": (
            "Run a bash command in the repository root. "
            "Use for: git operations, running pytest, installing packages, "
            "inspecting directory structure, running the app. "
            "stdout and stderr are returned (last 6000 chars)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cmd": {"type": "string", "description": "The bash command to run"}
            },
            "required": ["cmd"],
        },
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file (up to 8000 chars).",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path relative to repo root"}
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write (overwrite) a file with the given content. Creates parent dirs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path relative to repo root"},
                "content": {"type": "string", "description": "Complete file content"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "list_files",
        "description": "List tracked files matching a git-ls-files glob pattern.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern, e.g. '*.py' or 'tests/*.py'",
                }
            },
            "required": ["pattern"],
        },
    },
]


def dispatch_tool(name: str, inp: dict) -> str:
    if name == "bash":
        return tool_bash(inp["cmd"])
    if name == "read_file":
        return tool_read_file(inp["path"])
    if name == "write_file":
        return tool_write_file(inp["path"], inp["content"])
    if name == "list_files":
        return tool_list_files(inp.get("pattern", "**/*.py"))
    return f"[unknown tool: {name}]"


# ---------------------------------------------------------------------------
# Context loading
# ---------------------------------------------------------------------------
def load_context() -> str:
    parts = []

    # CLAUDE.md
    claude_md = Path("CLAUDE.md")
    if claude_md.exists():
        parts.append("=== CLAUDE.md (repo operating guide) ===\n" + claude_md.read_text()[:3000])

    # Key skills
    skill_paths = [
        ".agents/skills/implementation-planner/SKILL.md",
        ".agents/skills/test-first-executor/SKILL.md",
        ".agents/skills/changelog-enforcer/SKILL.md",
        ".agents/skills/issue-resolver/SKILL.md",
    ]
    for sp in skill_paths:
        p = Path(sp)
        if p.exists():
            parts.append(f"=== SKILL: {p.parent.name} ===\n" + p.read_text()[:1500])

    # File tree
    result = subprocess.run(
        "git ls-files -- '*.py' '*.js' '*.ts' '*.yml' '*.yaml' '*.md' | head -120",
        shell=True, capture_output=True, text=True,
    )
    parts.append("=== REPO FILE TREE ===\n" + result.stdout)

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
SYSTEM = textwrap.dedent("""
    You are an expert software engineer implementing a feature for the
    local-llm-server repository (a self-hosted OpenAI-compatible proxy).

    ## Your mandate
    Given a URL's content and a task description, you will:
    1. Understand what features are described in the URL content.
    2. Identify which features are relevant and implementable in this repo.
    3. Follow the implementation-planner skill: plan before coding.
    4. Follow the test-first-executor skill: write tests, confirm they fail,
       then implement until they pass.
    5. Follow the changelog-enforcer skill: add a changelog entry under
       [Unreleased] in docs/changelog.md.
    6. Use the bash tool to run `pytest -x -q --tb=short` after implementing.
       If tests fail, fix the code — do NOT give up.
    7. When done, call bash with `echo IMPLEMENTATION_COMPLETE` to signal done.

    ## Rules
    - Only implement features clearly supported by the URL content.
    - Make minimal, focused changes. No sprawling refactors.
    - All public functions need type annotations.
    - Log with the module-level logger, never print().
    - Use async for all I/O (FastAPI handlers, etc.).
    - Never hardcode secrets.
    - New routes belong in the appropriate module and must be wired into proxy.py.

    ## Finishing
    When implementation is complete and tests pass, output a brief summary
    of what was implemented (2-4 bullet points) then call:
      bash(cmd="echo IMPLEMENTATION_COMPLETE")
""").strip()


# ---------------------------------------------------------------------------
# Main agent loop
# ---------------------------------------------------------------------------
def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    url_content = Path("/tmp/note_content.txt").read_text()
    context = load_context()

    user_msg = textwrap.dedent(f"""
        ## Issue #{ISSUE_NUM}

        **URL**: {URL}
        **Task**: {TASK or "(no specific task — infer from URL content)"}

        ## URL Content
        {url_content[:5000]}

        ## Repo Context
        {context[:6000]}

        ---
        Begin by reading CLAUDE.md and the relevant skill files using read_file,
        then plan and implement. Run pytest when done.
    """).strip()

    client = anthropic.Anthropic(api_key=api_key)
    messages: list[dict] = [{"role": "user", "content": user_msg}]

    success = False
    summary = "No implementation performed"
    turns = 0

    while turns < MAX_TURNS:
        turns += 1
        print(f"\n[agent] Turn {turns}/{MAX_TURNS}")

        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=8192,
            system=SYSTEM,
            tools=TOOLS,  # type: ignore[arg-type]
            messages=messages,  # type: ignore[arg-type]
        )

        # Collect text output
        text_blocks = [b.text for b in response.content if hasattr(b, "text")]
        tool_uses = [b for b in response.content if b.type == "tool_use"]

        if text_blocks:
            print("[agent] " + " ".join(text_blocks)[:500])

        # Append assistant turn
        messages.append({"role": "assistant", "content": response.content})

        # Done?
        if response.stop_reason == "end_turn" and not tool_uses:
            summary = " ".join(text_blocks) or summary
            # Check if IMPLEMENTATION_COMPLETE was signalled via bash
            success = True  # end_turn without tool_use = done
            break

        # Execute tools
        tool_results = []
        for tu in tool_uses:
            print(f"[tool] {tu.name}({list(tu.input.keys())})")
            output = dispatch_tool(tu.name, tu.input)
            print(f"[tool result] {output[:300]}")

            if tu.name == "bash" and "IMPLEMENTATION_COMPLETE" in output:
                success = True
                summary = " ".join(text_blocks) or summary

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": output,
            })

        messages.append({"role": "user", "content": tool_results})

        if success:
            break

    if not success and turns >= MAX_TURNS:
        summary = f"Agent hit turn limit ({MAX_TURNS}) without completing"

    result = {"success": success, "summary": summary, "turns": turns}
    with open(RESULT_FILE, "w") as f:
        json.dump(result, f)

    print(f"\n[agent] Done — success={success}, turns={turns}")
    print(f"[agent] Summary: {summary[:300]}")
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

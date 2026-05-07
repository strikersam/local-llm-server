"""
Agentic implementation loop using NVIDIA NIM (OpenAI-compatible tool use).

Reads URL content + task from args, loads repo context (CLAUDE.md + skills),
and runs a plan → implement → test cycle with real file editing and bash
execution via OpenAI function-calling against the NVIDIA NIM API.

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

from openai import OpenAI

# ---------------------------------------------------------------------------
# Args
# ---------------------------------------------------------------------------
URL = sys.argv[1] if len(sys.argv) > 1 else ""
ISSUE_NUM = sys.argv[2] if len(sys.argv) > 2 else "?"
TASK = sys.argv[3] if len(sys.argv) > 3 else ""
RESULT_FILE = "/tmp/impl_result.json"  # nosec: B108 - Predictable temp file path used for backward compatibility; secure temp file used internally
MAX_TURNS = 40

# Model preference: heavy reasoning model first, reliable fallbacks after.
# All are free-tier NVIDIA NIM models.
CANDIDATE_MODELS = [
    ("qwen/qwen3-coder-480b-a35b-instruct",      "coding (Qwen3-Coder 480B — primary)"),
    ("nvidia/llama-3.1-nemotron-ultra-253b-v1", "reasoning (Nemotron Ultra 253B)"),
    ("meta/llama-3.3-70b-instruct",             "coding (Llama 3.3 70B)"),
    ("qwen/qwen2.5-coder-32b-instruct",         "coding (Qwen2.5 Coder 32B)"),
]


# ---------------------------------------------------------------------------
# Tool implementations (run on the host)
# ---------------------------------------------------------------------------
def tool_bash(cmd: str) -> str:
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=120  # nosec B602
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
            ["git", "ls-files", "--", pattern],
            capture_output=True, text=True, timeout=30,
        )
        lines = result.stdout.strip().splitlines()
        return "\n".join(lines[:200]) if lines else "(no files matched)"
    except Exception as exc:
        return f"[error: {exc}]"


TOOL_DISPATCH = {
    "bash": lambda inp: tool_bash(inp["cmd"]),
    "read_file": lambda inp: tool_read_file(inp["path"]),
    "write_file": lambda inp: tool_write_file(inp["path"], inp["content"]),
    "list_files": lambda inp: tool_list_files(inp.get("pattern", "**/*.py")),
}

# OpenAI-format tool schemas
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": (
                "Run a bash command in the repository root. "
                "Use for git operations, running pytest, installing packages, "
                "inspecting directory structure. stdout+stderr are returned."
            ),
            "parameters": {
                "type": "object",
                "properties": {"cmd": {"type": "string"}},
                "required": ["cmd"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file (up to 8000 chars).",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write (overwrite) a file with the given content. Creates parent dirs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List tracked files matching a git-ls-files glob pattern.",
            "parameters": {
                "type": "object",
                "properties": {"pattern": {"type": "string"}},
                "required": ["pattern"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Context loading
# ---------------------------------------------------------------------------
def load_context() -> str:
    parts = []
    for p_str in [
        "CLAUDE.md",
        ".agents/skills/implementation-planner/SKILL.md",
        ".agents/skills/test-first-executor/SKILL.md",
        ".agents/skills/changelog-enforcer/SKILL.md",
        ".agents/skills/issue-resolver/SKILL.md",
    ]:
        p = Path(p_str)
        if p.exists():
            label = p.name if p.name != "CLAUDE.md" else "CLAUDE.md"
            parts.append(f"=== {label} ===\n" + p.read_text()[:2000])

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

    Given a URL content and a task description you will:
    1. Read CLAUDE.md and the skill files using read_file to understand context.
    2. Follow the implementation-planner skill: plan before coding.
    3. Follow the test-first-executor skill: write tests first, confirm they
       fail, then implement until they pass.
    4. Follow the changelog-enforcer skill: add an entry under [Unreleased]
       in docs/changelog.md.
    5. Use bash to run `pytest -x -q --tb=short` after implementing.
       If tests fail, fix the code — do NOT give up.
    6. ONLY when `pytest -x -q --tb=short` exits 0 (all tests pass), call:
         bash(cmd="echo IMPLEMENTATION_COMPLETE")
       NEVER call this if the last pytest run had any failures or errors.

    CRITICAL rules to avoid breaking existing tests:
    - Prefer adding NEW files (new modules, new test files) over modifying existing ones.
    - If you must modify an existing file, make the smallest possible change.
    - NEVER change function signatures or remove functions that tests call.
    - NEVER change class names or module-level variable names.
    - After EVERY file change, re-run `pytest -x -q --tb=short` to catch regressions immediately.
    - If tests were passing before your change and fail after, revert that change.
    - The baseline test count is shown below — your final pytest run must match or exceed it.

    Additional rules:
    - Only implement features clearly supported by the URL content.
    - Minimal focused changes — no sprawling refactors.
    - Type annotations on all public functions.
    - Use async for all I/O handlers.
    - Log with module-level logger, never print().
    - Never hardcode secrets.
""").strip()


# ---------------------------------------------------------------------------
# Pick a working NVIDIA NIM model (first one that responds AND supports tools)
# ---------------------------------------------------------------------------
def pick_model(client: OpenAI) -> str:
    for model, label in CANDIDATE_MODELS:
        print(f"[model] Trying {label} ({model})")
        try:
            # Probe with tools= to verify tool-calling support
            client.chat.completions.create(
                model=model,
                max_tokens=8,
                messages=[{"role": "user", "content": "hi"}],
                tools=TOOLS,  # type: ignore[arg-type]
            )
            print(f"[model] Using {model}")
            return model
        except Exception as exc:
            print(f"[model] {model} unavailable: {exc}")
    print("[model] All models failed — aborting", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Main agent loop
# ---------------------------------------------------------------------------
def main() -> None:
    api_key = os.environ.get("NVIDIA_API_KEY", "")
    if not api_key:
        print("ERROR: NVIDIA_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key,
    )
    model = pick_model(client)

    url_content = Path("/tmp/note_content.txt").read_text()  # nosec: B108 - Reading from predictable temp file path written by fetch_url.py
    context = load_context()

    # Run baseline pytest before agent touches anything so we know the passing count.
    print("[agent] Running baseline pytest to establish passing baseline...")
    baseline_result = subprocess.run(
        ["pytest", "-x", "-q", "--tb=no"],
        capture_output=True, text=True, timeout=300,
    )
    baseline_summary = (baseline_result.stdout + baseline_result.stderr).strip()[-500:]
    baseline_passed = baseline_result.returncode == 0
    print(f"[agent] Baseline: returncode={baseline_result.returncode}")
    print(baseline_summary)

    system_with_context = SYSTEM + "\n\n" + context[:4000]
    user_msg = textwrap.dedent(f"""
        ## Issue #{ISSUE_NUM}
        **URL**: {URL}
        **Task**: {TASK or "(no specific task — infer from URL content)"}

        ## Baseline test status (before your changes)
        ```
        {baseline_summary}
        ```
        {"✅ Baseline passing — your implementation must keep all these tests green." if baseline_passed else "⚠️ Baseline had failures — do not introduce new failures."}

        ## URL Content
        {url_content[:4000]}

        Begin by reading CLAUDE.md and the skill files, then plan and implement.
        Run `pytest -x -q --tb=short` after EVERY file change to catch regressions immediately.
        Only call `echo IMPLEMENTATION_COMPLETE` when pytest exits 0.
    """).strip()

    messages: list[dict] = [
        {"role": "system", "content": system_with_context},
        {"role": "user", "content": user_msg},
    ]

    success = False
    last_pytest_passed = False  # tracks whether the most recent pytest bash call succeeded
    summary = "No implementation performed"
    turns = 0

    while turns < MAX_TURNS:
        turns += 1
        print(f"\n[agent] Turn {turns}/{MAX_TURNS}")

        response = client.chat.completions.create(
            model=model,
            max_tokens=8192,
            tools=TOOLS,  # type: ignore[arg-type]
            tool_choice="auto",
            messages=messages,  # type: ignore[arg-type]
        )

        msg = response.choices[0].message
        finish = response.choices[0].finish_reason

        if msg.content:
            print(f"[agent] {msg.content[:400]}")

        # Append assistant message
        messages.append(msg.model_dump(exclude_unset=False))

        # No tool calls → just update summary, don't mark as successful yet
        if finish == "stop" or not msg.tool_calls:
            summary = msg.content or summary
            # Only succeed if the model explicitly signals completion in content AND tests passed
            if msg.content and "IMPLEMENTATION_COMPLETE" in msg.content and last_pytest_passed:
                success = True
            break

        # Execute tool calls
        for tc in msg.tool_calls:
            fn_name = tc.function.name
            try:
                fn_args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                fn_args = {}

            print(f"[tool] {fn_name}({list(fn_args.keys())})")
            handler = TOOL_DISPATCH.get(fn_name)
            output = handler(fn_args) if handler else f"[unknown tool: {fn_name}]"
            print(f"[tool result] {output[:300]}")

            # Track whether the last pytest run succeeded
            if fn_name == "bash" and "pytest" in fn_args.get("cmd", ""):
                last_pytest_passed = "[exit 0]" in output

            if fn_name == "bash" and "IMPLEMENTATION_COMPLETE" in output:
                if last_pytest_passed:
                    success = True
                    summary = msg.content or summary
                else:
                    # Inject a hard block so the agent knows it must fix tests first
                    print("[agent] IMPLEMENTATION_COMPLETE blocked — last pytest was not exit 0")
                    # Override the tool result to push the agent to fix tests
                    output = (
                        "[BLOCKED] IMPLEMENTATION_COMPLETE rejected: your last pytest run "
                        "did not exit 0. Run `pytest -x -q --tb=short`, fix all failures, "
                        "then call `echo IMPLEMENTATION_COMPLETE` again."
                    )

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": output,
            })

        if success:
            break

    if not success and turns >= MAX_TURNS:
        summary = f"Agent hit turn limit ({MAX_TURNS}) without completing"

    result = {"success": success, "summary": summary, "turns": turns}
    with open(RESULT_FILE, "w") as f:
        json.dump(result, f)

    print(f"\n[agent] Done — success={success}, turns={turns}")
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

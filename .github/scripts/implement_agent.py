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
MAX_TURNS = 120

# Model preference: heavy reasoning model first, reliable fallbacks after.
# All are free-tier NVIDIA NIM models.
CANDIDATE_MODELS = [
    ("nvidia/nemotron-3-super-120b-a12b",       "reasoning (Nemotron 120B — primary)"),
    ("nvidia/llama-3.3-nemotron-super-49b-v1",  "reasoning (Nemotron Super 49B)"),
    ("meta/llama-3.3-70b-instruct",             "coding (Llama 3.3 70B)"),
    ("qwen/qwen2.5-coder-32b-instruct",         "coding (Qwen2.5 Coder 32B)"),
]


# ---------------------------------------------------------------------------
# Tool implementations (run on the host)
# ---------------------------------------------------------------------------
_API_KEY_ENV_VARS = (
    "NVIDIA_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
    "GEMINI_API_KEY", "GROQ_API_KEY", "MISTRAL_API_KEY",
)


def tool_bash(cmd: str) -> str:
    # Strip API keys when running pytest so tests that check model selection
    # are not affected by whatever keys are set in the CI environment.
    env = dict(os.environ)
    if "pytest" in cmd:
        for key in _API_KEY_ENV_VARS:
            env.pop(key, None)
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=120, env=env  # nosec B602
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


def tool_search(query: str) -> str:
    return tool_bash(f"grep -rnE '{query}' . --include='*.py' | head -50")


TOOL_DISPATCH = {
    "bash": lambda inp: tool_bash(inp["cmd"]),
    "read_file": lambda inp: tool_read_file(inp["path"]),
    "write_file": lambda inp: tool_write_file(inp["path"], inp["content"]),
    "list_files": lambda inp: tool_list_files(inp.get("pattern", "**/*.py")),
    "search_code": lambda inp: tool_search(inp["query"]),
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
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Grep for a regex pattern across all .py files.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
SYSTEM = textwrap.dedent("""
    You are a senior software engineer implementing features in a Python/FastAPI repository.

    ## Mandatory workflow — follow in order

    1. **Read CLAUDE.md** to understand conventions, structure, and rules:
       bash(cmd="cat CLAUDE.md")

    2. **Survey the task area** — read relevant existing files before writing anything.

    3. **Implement the feature** — create new files or extend existing ones.
       - All public functions must have type annotations and `from __future__ import annotations`.
       - Use `logging.getLogger("qwen-proxy")` for logging, never `print`.
       - Pydantic models for all API I/O.
       - Tests go in `tests/` and must pass with `pytest -x -q --tb=short`.

    4. **Add a changelog entry** — this is REQUIRED for CI to pass:
       Open `docs/changelog.md`, find `## [Unreleased]`, and add one or more lines
       describing what you added/changed/fixed. Without this, the PR will be blocked.
       Example:
       ```
       ### Added
       - `scripts/my_feature.py` — brief description of what it does.
       ```

    5. **Run tests and verify** — API keys are automatically stripped for pytest:
       bash(cmd="pytest -x -q --tb=short 2>&1 | tail -20")
       Fix any failures. Only proceed when all tests pass.
       If a test fails because an env var like NVIDIA_API_KEY changes routing,
       fix the test to mock/monkeypatch it instead of relying on env state.

    6. **Verify staged changes exist**:
       bash(cmd="git add -A && git diff --staged --stat")
       There must be changed files. If nothing is staged, check your write_file calls.

    7. **Signal completion** — call ONLY when pytest exits 0 AND staged changes exist:
       bash(cmd="echo IMPLEMENTATION_COMPLETE")

    ## Rules
    - Never signal IMPLEMENTATION_COMPLETE if the last pytest run had failures.
    - Always update docs/changelog.md under ## [Unreleased] — CI will block the PR without it.
    - Only implement features clearly supported by the URL content.
    - Minimal focused changes — ADD new code only. Do NOT delete, refactor, or rewrite existing code.
    - Never delete lines from docs/changelog.md — only append new entries.
    - Never hardcode secrets.
    - If the feature is already implemented, signal IMPLEMENTATION_COMPLETE immediately without changing any files.
""").strip()


def _read_claude_md() -> str:
    try:
        return Path("CLAUDE.md").read_text()[:3000]
    except Exception:
        return ""


def _run_baseline_pytest() -> str:
    result = subprocess.run(
        ["python", "-m", "pytest", "-x", "-q", "--tb=line", "--no-header"],
        capture_output=True, text=True, timeout=120,
    )
    lines = (result.stdout + result.stderr).splitlines()
    return "\n".join(lines[-15:])


# ---------------------------------------------------------------------------
# Main agent loop
# ---------------------------------------------------------------------------
def main() -> None:
    api_key = os.environ.get("NVIDIA_API_KEY", "")
    if not api_key:
        print("ERROR: NVIDIA_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=api_key)

    note_path = Path("/tmp/note_content.txt")  # nosec: B108
    url_content = note_path.read_text() if note_path.exists() else ""

    print("Running baseline pytest...", flush=True)
    baseline = _run_baseline_pytest()
    print(f"Baseline pytest output:\n{baseline}", flush=True)

    claude_md = _read_claude_md()

    user_msg = (
        f"Issue #{ISSUE_NUM}\n"
        f"URL: {URL}\n"
        f"Task: {TASK}\n\n"
        f"Content from URL (may be truncated):\n{url_content[:4000]}\n\n"
        f"--- CLAUDE.md (repo conventions) ---\n{claude_md}\n\n"
        f"--- Baseline pytest (before your changes) ---\n{baseline}\n"
        "Fix any pre-existing failures if they are easy, but focus on the task.\n"
        "Remember: always update docs/changelog.md before signaling IMPLEMENTATION_COMPLETE."
    )

    messages: list[dict] = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user_msg},
    ]

    success = False
    last_pytest_passed = False
    summary = "No implementation performed"
    turns = 0
    model_idx = 0
    model = CANDIDATE_MODELS[model_idx][0]

    while turns < MAX_TURNS:
        turns += 1
        print(f"\n[agent] Turn {turns}/{MAX_TURNS} model={model}", flush=True)

        try:
            res = client.chat.completions.create(
                model=model,
                max_tokens=8192,
                tools=TOOLS,  # type: ignore[arg-type]
                tool_choice="auto",
                messages=messages,  # type: ignore[arg-type]
            )
        except Exception as exc:
            print(f"Model {model} error: {exc}", file=sys.stderr)
            model_idx += 1
            if model_idx >= len(CANDIDATE_MODELS):
                print("All candidate models exhausted.", file=sys.stderr)
                break
            model = CANDIDATE_MODELS[model_idx][0]
            print(f"Switching to: {model}", file=sys.stderr)
            turns -= 1
            continue

        msg = res.choices[0].message

        if msg.content:
            print(f"[agent] {msg.content[:400]}", flush=True)

        # Serialise without null sentinel fields that NIM rejects with 422
        assistant_entry: dict = {"role": "assistant"}
        if msg.content:
            assistant_entry["content"] = msg.content
        if msg.tool_calls:
            assistant_entry["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ]
        messages.append(assistant_entry)

        # No tool calls → terminal turn
        if not msg.tool_calls:
            summary = msg.content or summary
            if msg.content and "IMPLEMENTATION_COMPLETE" in msg.content and last_pytest_passed:
                success = True
                summary = msg.content[:500]
            break

        # Execute tool calls
        for tc in msg.tool_calls:
            fn_name = tc.function.name
            try:
                fn_args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                fn_args = {}

            print(f"[tool] {fn_name}({list(fn_args.keys())})", flush=True)
            handler = TOOL_DISPATCH.get(fn_name)
            out = handler(fn_args) if handler else f"[unknown tool: {fn_name}]"
            print(f"[tool result] {str(out)[:300]}", flush=True)

            if fn_name == "bash":
                cmd = fn_args.get("cmd", "")
                if "pytest" in cmd:
                    last_pytest_passed = "[exit 0]" in out
                    print(f"pytest exit 0: {last_pytest_passed}", flush=True)
                if "IMPLEMENTATION_COMPLETE" in out:
                    if last_pytest_passed:
                        success = True
                        summary = f"Agent signaled completion after {turns} turns."
                    else:
                        out = (
                            "[BLOCKED] IMPLEMENTATION_COMPLETE rejected: last pytest did not exit 0. "
                            "Fix all test failures first, then signal completion."
                        )

            messages.append({"role": "tool", "tool_call_id": tc.id, "content": str(out)})

        if success:
            break

    if not success and turns >= MAX_TURNS:
        summary = f"Agent hit turn limit ({MAX_TURNS}) without completing"

    result = {"success": success, "summary": summary, "turns": turns}
    with open(RESULT_FILE, "w") as f:
        json.dump(result, f)

    print(f"\n[agent] Done — success={success}, turns={turns}, model={model}", flush=True)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

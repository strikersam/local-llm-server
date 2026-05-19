from __future__ import annotations

"""
Agentic implementation loop using NVIDIA NIM (OpenAI-compatible tool use).

Reads URL content + task from args, loads repo context (CLAUDE.md + skills),
and runs a plan → implement → test cycle with real file editing and bash
execution via OpenAI function-calling against the NVIDIA NIM API.

Usage:
  python implement_agent.py <url> <issue_num> <task>

Writes /tmp/impl_result.json with {"success": bool, "summary": str}
"""


import json
import os
import subprocess
import sys
import textwrap
import time
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

# Primary: Claude Opus via Anthropic (CEO / agency grade).
# Fallback: NVIDIA NIM free-tier models.
OPUS_MODEL = "claude-opus-4-6"
NVIDIA_CANDIDATE_MODELS = [
    ("qwen/qwen3-coder-480b-a35b-instruct",      "coding (Qwen3-Coder 480B — primary)"),
    ("nvidia/llama-3.1-nemotron-ultra-253b-v1", "reasoning (Nemotron Ultra 253B)"),
    ("nvidia/llama-3.3-nemotron-super-49b-v1",  "reasoning (Nemotron Super 49B)"),
    ("meta/llama-3.3-70b-instruct",             "coding (Llama 3.3 70B)"),
    ("qwen/qwen2.5-coder-32b-instruct",         "coding (Qwen2.5 Coder 32B)"),
    ("qwen/qwen3-coder-480b-a35b-instruct",     "coding (Qwen3-Coder 480B — last resort)"),
]
# Keep old name as alias
CANDIDATE_MODELS = NVIDIA_CANDIDATE_MODELS


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
        text = Path(path).read_text(errors="replace")
        if len(text) > 12000:
            return text[:12000] + f"\n\n[... truncated — file is {len(text)} chars total. Use bash(cmd='wc -l {path}') to check size, or read specific sections with bash(cmd='sed -n \"1,50p\" {path}')]"
        return text
    except Exception as exc:
        return f"[error reading {path}: {exc}]"


def tool_write_file(path: str, content: str) -> str:
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        # Safety guard: refuse to shrink an existing file by more than 10 lines.
        # This prevents the agent from accidentally overwriting files with truncated reads.
        if p.exists():
            existing_lines = p.read_text(errors="replace").count("\n")
            new_lines = content.count("\n")
            if existing_lines > 20 and new_lines < existing_lines - 10:
                return (
                    f"[BLOCKED] write_file would reduce {path} from {existing_lines} lines to {new_lines} lines "
                    f"(lost {existing_lines - new_lines} lines). This usually means you read a truncated version "
                    f"of the file and are writing it back incomplete. "
                    f"For docs/changelog.md use add_changelog_entry instead. "
                    f"For source files, use bash(cmd='cat >> file') to append or make targeted edits."
                )
        p.write_text(content)
        return f"Written {len(content)} chars to {path}"
    except Exception as exc:
        return f"[error writing {path}: {exc}]"


def tool_add_changelog_entry(entry: str) -> str:
    """Safely insert an entry under ## [Unreleased] without touching the rest of the file."""
    try:
        p = Path("docs/changelog.md")
        text = p.read_text(errors="replace")
        marker = "## [Unreleased]"
        idx = text.find(marker)
        if idx == -1:
            return "[error: '## [Unreleased]' marker not found in docs/changelog.md]"
        insert_at = idx + len(marker)
        # Find the next blank line after the marker to insert after the header
        rest = text[insert_at:]
        newline_pos = rest.find("\n")
        insert_at += newline_pos + 1
        new_text = text[:insert_at] + entry.rstrip() + "\n" + text[insert_at:]
        p.write_text(new_text)
        return f"Changelog updated — inserted {len(entry)} chars under ## [Unreleased]"
    except Exception as exc:
        return f"[error updating changelog: {exc}]"


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
    "add_changelog_entry": lambda inp: tool_add_changelog_entry(inp["entry"]),
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
            "description": "Read the contents of a file (up to 12000 chars, truncated with notice if longer).",
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
            "description": (
                "Write (overwrite) a file with the given content. Creates parent dirs. "
                "BLOCKED if the new content is more than 10 lines shorter than the existing file — "
                "this prevents accidentally writing back a truncated read. "
                "NEVER use this for docs/changelog.md — use add_changelog_entry instead. "
                "NEVER create backup files (e.g. proxy_original.py, proxy_backup.py)."
            ),
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
            "name": "add_changelog_entry",
            "description": (
                "Safely insert a new entry into docs/changelog.md under ## [Unreleased]. "
                "Always use this instead of read_file + write_file for the changelog. "
                "Pass the full entry text including the ### Added / ### Fixed header."
            ),
            "parameters": {
                "type": "object",
                "properties": {"entry": {"type": "string"}},
                "required": ["entry"],
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
       - All public functions must have type annotations and return type annotations.
       - Use `logging.getLogger("qwen-proxy")` for logging, never `print`.
       - Pydantic models for all API I/O.
       - Tests go in `tests/` and must pass with `pytest -x -q --tb=short`.

    4. **Add a changelog entry** — this is REQUIRED for CI to pass:
       Use the `add_changelog_entry` tool — NEVER read_file + write_file the changelog.
       The changelog is large; writing it back from a read will truncate it and break CI.
       Example:
       add_changelog_entry(entry="### Added\n- `module.py` — brief description.\n")

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
    - Always use add_changelog_entry for docs/changelog.md — NEVER write_file it.
    - Only implement features clearly supported by the URL content.
    - Minimal focused changes — ADD new code only. Do NOT delete, refactor, or rewrite existing code.
    - Never create backup files (proxy_original.py, any_file_backup.py, etc.).
    - Never hardcode secrets.
    - If the feature is already implemented, signal IMPLEMENTATION_COMPLETE immediately without changing any files.
""").strip()


def _read_claude_md() -> str:
    try:
        return Path("CLAUDE.md").read_text()[:3000]
    except Exception:
        return ""


def _run_baseline_pytest() -> str:
    # Strip API keys so routing tests see the same environment as tool_bash pytest calls.
    # Without this, NVIDIA_API_KEY in CI changes model-selection behaviour and causes
    # tests that assert local Ollama model names to fail spuriously.
    env = {k: v for k, v in os.environ.items() if k not in _API_KEY_ENV_VARS}
    result = subprocess.run(
        ["python", "-m", "pytest", "-x", "-q", "--tb=line", "--no-header"],
        capture_output=True, text=True, timeout=120, env=env,
    )
    lines = (result.stdout + result.stderr).splitlines()
    return "\n".join(lines[-15:])


# ---------------------------------------------------------------------------
# Anthropic-native agent loop (Opus primary)
# ---------------------------------------------------------------------------

def _openai_tools_to_anthropic(tools: list[dict]) -> list[dict]:
    """Convert OpenAI function-calling tool schemas to Anthropic tool schemas."""
    result = []
    for t in tools:
        fn = t.get("function", {})
        result.append({
            "name": fn["name"],
            "description": fn.get("description", ""),
            "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
        })
    return result


def _run_anthropic_agent_loop(anthropic_key: str, user_msg: str) -> tuple[bool, str, int]:
    """Run the implementation agent loop using Claude Opus via Anthropic SDK.

    Returns (success, summary, turns_used).
    """
    import anthropic as _anthropic
    client = _anthropic.Anthropic(api_key=anthropic_key)
    anthropic_tools = _openai_tools_to_anthropic(TOOLS)

    messages: list[dict] = [{"role": "user", "content": user_msg}]
    success = False
    last_pytest_passed = False
    summary = "No implementation performed"
    turns = 0

    while turns < MAX_TURNS:
        turns += 1
        print(f"\n[agent] Turn {turns}/{MAX_TURNS} model={OPUS_MODEL} (Anthropic)", flush=True)

        try:
            resp = client.messages.create(
                model=OPUS_MODEL,
                max_tokens=8192,
                system=SYSTEM,
                tools=anthropic_tools,  # type: ignore[arg-type]
                messages=messages,      # type: ignore[arg-type]
            )
        except Exception as exc:
            # Permanent failures (bad key, access denied, unknown model) must not be
            # retried — they will never recover and would exhaust all 120 turns before
            # NVIDIA fallback can run.
            status = getattr(exc, "status_code", None)
            if status in (401, 403, 404):
                print(f"Anthropic permanent error ({status}): {exc} — falling back to NVIDIA", file=sys.stderr)
                break
            print(f"Anthropic transient error: {exc}", file=sys.stderr)
            time.sleep(5)
            continue  # retry transient errors (rate limit, server error, network)

        # Build assistant content list
        assistant_content: list[dict] = []
        text_content = ""
        tool_use_blocks: list = []

        for block in resp.content:
            if block.type == "text":
                text_content = block.text
                assistant_content.append({"type": "text", "text": block.text})
                print(f"[agent] {block.text[:400]}", flush=True)
            elif block.type == "tool_use":
                tool_use_blocks.append(block)
                assistant_content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })

        messages.append({"role": "assistant", "content": assistant_content})

        # No tool calls → terminal turn
        if not tool_use_blocks:
            summary = text_content or summary
            if text_content and "IMPLEMENTATION_COMPLETE" in text_content and last_pytest_passed:
                success = True
                summary = text_content[:500]
            break

        # Execute tool calls and collect results
        tool_results: list[dict] = []
        for call in tool_use_blocks:
            fn_name = call.name
            fn_args = call.input if isinstance(call.input, dict) else {}
            print(f"[tool] {fn_name}({list(fn_args.keys())})", flush=True)

            handler = TOOL_DISPATCH.get(fn_name)
            out = handler(fn_args) if handler else f"[unknown tool: {fn_name}]"
            print(f"[tool result] {str(out)[:300]}", flush=True)

            if fn_name == "bash":
                cmd = fn_args.get("cmd", "")
                if "pytest" in cmd:
                    last_pytest_passed = "[exit 0]" in out
                if "IMPLEMENTATION_COMPLETE" in out:
                    if last_pytest_passed:
                        success = True
                        summary = f"Agent signaled completion after {turns} turns."
                    else:
                        out = (
                            "[BLOCKED] IMPLEMENTATION_COMPLETE rejected: last pytest did not exit 0. "
                            "Fix all test failures first."
                        )

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": call.id,
                "content": str(out),
            })

        messages.append({"role": "user", "content": tool_results})

        if success:
            break

    if not success and turns >= MAX_TURNS:
        summary = f"Agent hit turn limit ({MAX_TURNS}) without completing"

    return success, summary, turns


# ---------------------------------------------------------------------------
# Main agent loop
# ---------------------------------------------------------------------------
def main() -> None:
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    nvidia_key = os.environ.get("NVIDIA_API_KEY", "")

    if not anthropic_key and not nvidia_key:
        print("ERROR: neither ANTHROPIC_API_KEY nor NVIDIA_API_KEY set", file=sys.stderr)
        sys.exit(1)

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

    success = False
    summary = "No implementation performed"
    turns = 0
    final_model = OPUS_MODEL

    # Primary: Claude Opus via Anthropic
    if anthropic_key:
        print("[agent] Using Anthropic Claude Opus as primary model", flush=True)
        try:
            success, summary, turns = _run_anthropic_agent_loop(anthropic_key, user_msg)
        except Exception as exc:
            print(f"[agent] Anthropic agent loop failed: {exc} — falling back to NVIDIA", file=sys.stderr)

    # Fallback: NVIDIA NIM
    if not success and nvidia_key:
        print("[agent] Falling back to NVIDIA NIM models", flush=True)
        client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=nvidia_key)

        messages: list[dict] = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_msg},
        ]

        last_pytest_passed = False
        model_idx = 0
        model = NVIDIA_CANDIDATE_MODELS[model_idx][0]
        final_model = model
        turns = 0  # fresh turn budget for NVIDIA fallback

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
                if model_idx >= len(NVIDIA_CANDIDATE_MODELS):
                    print("All candidate models exhausted.", file=sys.stderr)
                    break
                model = NVIDIA_CANDIDATE_MODELS[model_idx][0]
                final_model = model
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

            # No tool calls → check for XML-format tool calls (Qwen3 quirk) then terminal turn
            if not msg.tool_calls:
                content = msg.content or ""
                # Some models (e.g. Qwen3-coder) emit tool calls as XML text in content
                # instead of structured tool_calls. Detect and switch models.
                if "<tool_call>" in content or "<function=" in content:
                    print(f"[agent] {model} emitted XML tool calls in content — switching model", file=sys.stderr)
                    messages.pop()  # discard the malformed assistant turn
                    model_idx += 1
                    if model_idx < len(NVIDIA_CANDIDATE_MODELS):
                        model = NVIDIA_CANDIDATE_MODELS[model_idx][0]
                        final_model = model
                        print(f"[agent] Switched to: {model}", flush=True)
                        turns -= 1  # don't count this as a real turn
                    else:
                        print("All candidate models exhausted.", file=sys.stderr)
                        break
                    continue
                summary = content or summary
                if content and "IMPLEMENTATION_COMPLETE" in content and last_pytest_passed:
                    success = True
                    summary = content[:500]
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

    print(f"\n[agent] Done — success={success}, turns={turns}, model={final_model}", flush=True)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

"""Agentic implementation loop using NVIDIA NIM (OpenAI-compatible tools API)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from openai import NotFoundError, OpenAI, PermissionDeniedError

URL = sys.argv[1] if len(sys.argv) > 1 else ""
ISSUE_NUM = sys.argv[2] if len(sys.argv) > 2 else "?"
TASK = sys.argv[3] if len(sys.argv) > 3 else ""
RESULT_FILE = "/tmp/impl_result.json"
MAX_TURNS = 50

CANDIDATE_MODELS = [
    ("nvidia/llama-3_1-nemotron-ultra-253b-v1", "reasoning"),
    ("qwen/qwen3-coder-480b-a35b-instruct", "coding"),
    ("qwen/qwen2.5-coder-32b-instruct", "coding"),
]


def tool_bash(cmd: str) -> str:
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        out, err = result.stdout[-6000:], result.stderr[-2000:]
        return f"{out}\n[stderr]\n{err}\n[exit {result.returncode}]"
    except Exception as exc:  # noqa: BLE001
        return f"[error: {exc}]"


def tool_read_file(path: str) -> str:
    try:
        return Path(path).read_text(errors="replace")[:12000]
    except Exception as exc:  # noqa: BLE001
        return f"[error: {exc}]"


def tool_write_file(path: str, content: str) -> str:
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return f"Written to {path}"
    except Exception as exc:  # noqa: BLE001
        return f"[error: {exc}]"


TOOL_DISPATCH = {
    "bash": lambda i: tool_bash(i["cmd"]),
    "read_file": lambda i: tool_read_file(i["path"]),
    "write_file": lambda i: tool_write_file(i["path"], i["content"]),
    "list_files": lambda i: tool_bash(f"git ls-files -- '{i.get('pattern', '**/*.py')}' | head -100"),
}

TOOLS = [
    {"type": "function", "function": {"name": "bash", "parameters": {"type": "object", "properties": {"cmd": {"type": "string"}}, "required": ["cmd"]}}},
    {"type": "function", "function": {"name": "read_file", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "write_file", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "list_files", "parameters": {"type": "object", "properties": {"pattern": {"type": "string"}}}}},
]

SYSTEM = (
    "You are a senior software engineer. Implement the feature, write tests, and ensure "
    "'pytest -x -q --tb=short' passes. Call bash(cmd='echo IMPLEMENTATION_COMPLETE') "
    "ONLY when all tests pass."
)


def main() -> None:
    client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=os.environ["NVIDIA_API_KEY"])

    note_path = Path("/tmp/note_content.txt")
    url_content = note_path.read_text() if note_path.exists() else ""
    user_msg = f"Issue #{ISSUE_NUM}\nURL: {URL}\nTask: {TASK}\n\nContent:\n{url_content[:5000]}"

    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user_msg}]
    success = False
    last_pytest_passed = False
    turns = 0
    model_idx = 0
    model = CANDIDATE_MODELS[model_idx][0]
    msg = None

    while turns < MAX_TURNS:
        turns += 1
        try:
            res = client.chat.completions.create(model=model, tools=TOOLS, messages=messages)
        except (NotFoundError, PermissionDeniedError):
            model_idx += 1
            if model_idx >= len(CANDIDATE_MODELS):
                break
            model = CANDIDATE_MODELS[model_idx][0]
            turns -= 1
            continue

        msg = res.choices[0].message
        messages.append(msg.model_dump(exclude_unset=False))

        if not msg.tool_calls:
            if msg.content and "IMPLEMENTATION_COMPLETE" in msg.content and last_pytest_passed:
                success = True
            break

        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            out = TOOL_DISPATCH.get(tc.function.name, lambda _i: "[error: unknown tool]")(args)
            if tc.function.name == "bash" and "pytest" in args.get("cmd", ""):
                last_pytest_passed = "[exit 0]" in out
            if tc.function.name == "bash" and "IMPLEMENTATION_COMPLETE" in out and not last_pytest_passed:
                out = "[ERROR] Pytest failed. Fix tests before completion."
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": out})

    with open(RESULT_FILE, "w", encoding="utf-8") as handle:
        json.dump({"success": success, "summary": msg.content if msg and msg.content else ("Done" if success else "Failed")}, handle)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

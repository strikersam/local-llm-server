"""
Agentic implementation loop using NVIDIA NIM or Moonshot (OpenAI-compatible tool use).
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

from openai import NotFoundError, OpenAI, PermissionDeniedError, RateLimitError

URL = sys.argv[1] if len(sys.argv) > 1 else ""
ISSUE_NUM = sys.argv[2] if len(sys.argv) > 2 else "?"
TASK = sys.argv[3] if len(sys.argv) > 3 else ""
RESULT_FILE = "/tmp/impl_result.json"
MAX_TURNS = 100

CANDIDATE_MODELS = [
    ("nvidia/nemotron-3-super-120b-a12b", "nvidia"),
    ("qwen/qwen2.5-coder-32b-instruct", "nvidia"),
    ("kimi-k2.6", "moonshot"),
]

PROVIDERS = {
    "nvidia": {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "api_key": os.environ.get("NVIDIA_API_KEY"),
    },
    "moonshot": {
        "base_url": "https://api.moonshot.ai/v1",
        "api_key": os.environ.get("MOONSHOT_API_KEY"),
    }
}

def tool_bash(cmd: str) -> str:
    """
    Execute a shell command and return its stdout, stderr, and exit code formatted into a single string.

    Parameters:
        cmd (str): Shell command to execute.

    Returns:
        str: The command's stdout (truncated to the last 6000 characters), followed by "[stderr]" and the command's stderr (truncated to the last 2000 characters), and ending with "[exit N]" where N is the process exit code. If an exception occurs, returns a string in the format "[error: <exception>]".
    """
    try:
        argv = shlex.split(cmd)
        result = subprocess.run(argv, shell=False, capture_output=True, text=True, timeout=120)
        out, err = result.stdout[-6000:], result.stderr[-2000:]
        return f"{out}\n[stderr]\n{err}\n[exit {result.returncode}]"
    except Exception as exc:
        return f"[error: {exc}]"

def tool_read_file(path: str) -> str:
    """
    Read a text file and return its contents truncated to 12,000 characters.
    
    Parameters:
        path (str): Path to the file to read.
    
    Returns:
        str: The file contents (up to the first 12,000 characters), or a string of the form "[error: <exc>]" if reading fails.
    """
    try:
        return Path(path).read_text(errors="replace")[:12000]
    except Exception as exc:
        return f"[error: {exc}]"

def tool_write_file(path: str, content: str) -> str:
    """
    Write text to the given filesystem path, creating parent directories if needed.
    
    Parameters:
        path (str): Destination file path.
        content (str): Text content to write to the file.
    
    Returns:
        result (str): "Written to <path>" on success, or "[error: <exc>]" containing the exception message on failure.
    """
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return f"Written to {path}"
    except Exception as exc:
        return f"[error: {exc}]"

def tool_search(query: str) -> str:
    """
    Search the repository tree for lines matching a regular-expression query.

    Parameters:
        query (str): Regular expression to search for.

    Returns:
        str: Combined command output containing up to 50 matching lines; includes any stderr and an "[exit N]" exit-code suffix as produced by the underlying command, or an error string beginning with "[error:" on failure.
    """
    try:
        result = subprocess.run(
            ["grep", "-rnE", query, "."],
            shell=False,
            capture_output=True,
            text=True,
            timeout=120
        )
        # Limit to first 50 lines
        lines = result.stdout.splitlines()[:50]
        out = "\n".join(lines)
        err = result.stderr[-2000:] if result.stderr else ""
        return f"{out}\n[stderr]\n{err}\n[exit {result.returncode}]"
    except Exception as exc:
        return f"[error: {exc}]"

def tool_list_files(pattern: str = "**/*") -> str:
    """
    List files in the repository matching a pattern using git ls-files.

    Parameters:
        pattern (str): File pattern to match (default: '**/*').

    Returns:
        str: File listing output with exit code suffix, or error message.
    """
    try:
        result = subprocess.run(
            ["git", "ls-files", "--", pattern],
            shell=False,
            capture_output=True,
            text=True,
            timeout=120
        )
        # Limit to first 200 lines
        lines = result.stdout.splitlines()[:200]
        out = "\n".join(lines)
        err = result.stderr[-2000:] if result.stderr else ""
        return f"{out}\n[stderr]\n{err}\n[exit {result.returncode}]"
    except Exception as exc:
        return f"[error: {exc}]"

TOOL_DISPATCH = {
    "bash": lambda i: tool_bash(i["cmd"]),
    "read_file": lambda i: tool_read_file(i["path"]),
    "write_file": lambda i: tool_write_file(i["path"], i["content"]),
    "list_files": lambda i: tool_list_files(i.get("pattern", "**/*")),
    "search_code": lambda i: tool_search(i["query"]),
}

TOOLS = [
    {"type": "function", "function": {"name": "bash", "parameters": {"type": "object", "properties": {"cmd": {"type": "string"}}, "required": ["cmd"]}}},
    {"type": "function", "function": {"name": "read_file", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "write_file", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "list_files", "parameters": {"type": "object", "properties": {"pattern": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "search_code", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
]

SYSTEM = (
    "You are a senior software engineer. Implement the feature, write tests, and ensure "
    "'pytest -x -q --tb=short' passes. Call bash(cmd='echo IMPLEMENTATION_COMPLETE') "
    "ONLY when all tests pass."
)

def main() -> None:
    """
    Run the agent loop that queries candidate LLM models, executes requested tool calls, and writes a JSON result file.
    
    Iteratively queries models from CANDIDATE_MODELS using provider configs from PROVIDERS, appends model responses to the conversation, executes tool calls via TOOL_DISPATCH, and tracks pytest results from bash outputs. The run is marked successful only when an IMPLEMENTATION_COMPLETE signal is produced after pytest has passed. Writes a JSON summary {"success": ..., "summary": ...} to RESULT_FILE and terminates the process with exit code 0 on success or 1 on failure. Prints status and error messages to stderr as needed.
    """
    note_path = Path("/tmp/note_content.txt")
    url_content = note_path.read_text() if note_path.exists() else ""
    user_msg = f"Issue #{ISSUE_NUM}\nURL: {URL}\nTask: {TASK}\n\nContent:\n{url_content[:5000]}"

    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user_msg}]
    success = False
    last_pytest_passed = False
    turns = 0
    model_idx = 0
    msg = None

    while turns < MAX_TURNS:
        turns += 1
        model, provider_name = CANDIDATE_MODELS[model_idx]
        provider = PROVIDERS[provider_name]

        if not provider["api_key"]:
            print(f"Skipping {model} as {provider_name} API key is missing.", file=sys.stderr)
            model_idx += 1
            if model_idx >= len(CANDIDATE_MODELS):
                break
            turns -= 1
            continue

        client = OpenAI(base_url=provider["base_url"], api_key=provider["api_key"])

        try:
            res = client.chat.completions.create(model=model, tools=TOOLS, messages=messages)
        except (NotFoundError, PermissionDeniedError) as exc:
            print(f"Error with model {model}: {exc}", file=sys.stderr)
            model_idx += 1
            if model_idx >= len(CANDIDATE_MODELS):
                print("All candidate models failed.", file=sys.stderr)
                break
            turns -= 1
            continue
        except RateLimitError as exc:
            wait = 5 * (2 ** (turns % 3))
            print(f"Rate limit hit for {model}. Waiting {wait}s...", file=sys.stderr)
            time.sleep(wait)
            turns -= 1
            continue
        except Exception as exc:
            print(f"Unexpected error: {exc}", file=sys.stderr)
            break

        msg = res.choices[0].message
        messages.append(msg.model_dump(exclude_unset=False))

        if not msg.tool_calls:
            if msg.content and "IMPLEMENTATION_COMPLETE" in msg.content and last_pytest_passed:
                success = True
            break

        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments)
                out = TOOL_DISPATCH.get(tc.function.name, lambda _i: "[error: unknown tool]")(args)
                if tc.function.name == "bash" and "pytest" in args.get("cmd", ""):
                    last_pytest_passed = "[exit 0]" in out
                if tc.function.name == "bash" and "IMPLEMENTATION_COMPLETE" in out:
                    if last_pytest_passed:
                        success = True
                    else:
                        out = "[ERROR] Pytest failed. Fix tests before completion."
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": out})
            except Exception as e:
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": f"[error: {e}]"})

        if success:
            break

    with open(RESULT_FILE, "w", encoding="utf-8") as handle:
        json.dump({"success": success, "summary": msg.content if msg and msg.content else ("Done" if success else "Failed")}, handle)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations

"""
apply_review.py — Apply PR review comments using Claude Opus (primary) or NVIDIA NIM (fallback).

Usage: python3 apply_review.py <pr_number>

Env vars:
  ANTHROPIC_API_KEY     Anthropic API key (Opus primary — preferred)
  NVIDIA_API_KEY        NVIDIA NIM API key (fallback)
  GH_TOKEN              GitHub token for reading/posting PR comments
  GITHUB_REPOSITORY     owner/repo string (set automatically by GitHub Actions)
"""


import json
import logging
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[apply_review] %(message)s")
log = logging.getLogger("apply_review")

NVIDIA_BASE = "https://integrate.api.nvidia.com/v1"
# Primary: Anthropic Claude Opus (CEO / agency grade).
OPUS_MODEL = "claude-opus-4-6"
# Fallback: NVIDIA NIM models.
NVIDIA_CANDIDATE_MODELS = [
    ("nvidia/nemotron-3-super-120b-a12b",      "reasoning (Nemotron 120B)"),
    ("nvidia/llama-3.3-nemotron-super-49b-v1", "reasoning (Nemotron 49B)"),
    ("meta/llama-3.3-70b-instruct",            "coding (Llama 3.3 70B)"),
    ("qwen/qwen2.5-coder-32b-instruct",        "coding (Qwen2.5 32B)"),
]
# Keep old name as alias
CANDIDATE_MODELS = NVIDIA_CANDIDATE_MODELS
MAX_TURNS = 50
_STRIP_KEYS = ("NVIDIA_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
               "GEMINI_API_KEY", "GROQ_API_KEY", "MISTRAL_API_KEY")


# ── GitHub API helpers ────────────────────────────────────────────────────────

def _gh(path: str, token: str) -> list | dict:
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        log.warning(f"GitHub API {path} → {e.code}: {e.read()[:200]}")
        return []


def build_review_context(pr: str, repo: str, token: str) -> str:
    """Aggregate all review feedback for the PR into a single context string."""
    reviews        = _gh(f"/repos/{repo}/pulls/{pr}/reviews", token)
    inline_comments = _gh(f"/repos/{repo}/pulls/{pr}/comments", token)
    issue_comments  = _gh(f"/repos/{repo}/issues/{pr}/comments", token)

    parts: list[str] = []

    # Top-level review bodies (CHANGES_REQUESTED or COMMENTED)
    for r in reviews:
        body  = (r.get("body") or "").strip()
        state = r.get("state", "")
        user  = r.get("user", {}).get("login", "unknown")
        if body and state in ("CHANGES_REQUESTED", "COMMENTED"):
            parts.append(f"=== REVIEW by @{user} [{state}] ===\n{body}")

    # Inline code comments — include ```suggestion blocks verbatim
    for c in inline_comments:
        body = (c.get("body") or "").strip()
        if not body:
            continue
        path = c.get("path", "?")
        line = c.get("line") or c.get("original_line") or "?"
        user = c.get("user", {}).get("login", "unknown")
        note = " (apply the ```suggestion block literally)" if "```suggestion" in body else ""
        parts.append(f"--- @{user} on {path}:{line}{note} ---\n{body}")

    # Bot walkthroughs (CodeRabbit, Copilot, etc.)
    _BOT_PATTERNS = ("coderabbitai", "copilot", "codex", "code-rabbit")
    for c in issue_comments:
        user = (c.get("user", {}).get("login") or "").lower()
        body = (c.get("body") or "").strip()
        if body and any(p in user for p in _BOT_PATTERNS):
            parts.append(f"=== BOT WALKTHROUGH by @{user} ===\n{body[:4000]}")

    return "\n\n".join(parts)


# ── Agentic loop ──────────────────────────────────────────────────────────────

_SYSTEM = """\
You are a senior engineer addressing pull-request review feedback.
You receive the aggregated review comments and must edit the codebase to satisfy them.

Available tools:
  read_file(path)              — read a source file
  write_file(path, content)    — overwrite a file
  bash(cmd)                    — run a shell command (pytest, git diff, etc.)
  done(success, summary)       — call when finished

Guidelines:
1. Read every file mentioned in the review before editing.
2. Apply ALL actionable suggestions — especially ```suggestion blocks, which must be applied exactly.
3. After edits, run `pytest -x -q --tb=short` to verify tests still pass.
4. If a comment is a compliment or question with no required change, note it and move on.
5. Call done(success=True, summary="…") when all changes are applied and tests pass.
6. Call done(success=False, summary="…") only if a comment is contradictory or impossible to satisfy.
"""


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


class ApplyReviewAgent:
    def __init__(self, api_key: str, model: str, review_context: str) -> None:
        self.api_key = api_key
        self.model = model
        self.history: list[dict] = [
            {"role": "system", "content": _SYSTEM},
            {
                "role": "user",
                "content": (
                    "Here are the review comments to address:\n\n"
                    f"{review_context}\n\n"
                    "Start by reading the relevant files, apply the changes, run tests, then call done()."
                ),
            },
        ]
        self.success = False
        self.summary = ""

    # ── Tool implementations ──────────────────────────────────────────────────

    def _read_file(self, path: str) -> str:
        try:
            return Path(path).read_text(errors="replace")[:10000]
        except Exception as e:
            return f"Error: {e}"

    def _write_file(self, path: str, content: str) -> str:
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(content)
            return f"Written {len(content)} chars to {path}"
        except Exception as e:
            return f"Error: {e}"

    def _bash(self, cmd: str) -> str:
        env = {k: v for k, v in os.environ.items() if k not in _STRIP_KEYS}
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=120, env=env,
        )
        return (r.stdout + r.stderr)[-3000:] + f"\n[exit {r.returncode}]"

    def _dispatch(self, name: str, args: dict) -> tuple[str, bool]:
        """Return (result_text, should_stop)."""
        if name == "read_file":
            return self._read_file(args.get("path", "")), False
        if name == "write_file":
            return self._write_file(args.get("path", ""), args.get("content", "")), False
        if name == "bash":
            return self._bash(args.get("cmd", "")), False
        if name == "done":
            self.success = bool(args.get("success", False))
            self.summary = str(args.get("summary", ""))
            return "Acknowledged.", True
        return f"Unknown tool: {name}", False

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self) -> bool:
        """Run using NVIDIA NIM (OpenAI-compatible). Called as fallback."""
        import openai
        client = openai.OpenAI(api_key=self.api_key, base_url=NVIDIA_BASE)

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read a source file",
                    "parameters": {
                        "type": "object",
                        "properties": {"path": {"type": "string", "description": "File path"}},
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Write/overwrite a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string", "description": "Full file content"},
                        },
                        "required": ["path", "content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "bash",
                    "description": "Run a shell command",
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
                    "name": "done",
                    "description": "Signal completion",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean"},
                            "summary": {"type": "string", "description": "What was changed"},
                        },
                        "required": ["success"],
                    },
                },
            },
        ]

        for turn in range(MAX_TURNS):
            log.info(f"Turn {turn + 1}/{MAX_TURNS} model={self.model}")
            try:
                resp = client.chat.completions.create(
                    model=self.model,
                    messages=self.history,
                    tools=tools,
                    max_tokens=4096,
                    temperature=0.2,
                )
            except Exception as e:
                log.warning(f"API error: {e}")
                time.sleep(5)
                continue

            msg = resp.choices[0].message
            self.history.append(msg.model_dump(exclude_none=True))

            if not msg.tool_calls:
                log.info("No tool calls — agent finished without calling done()")
                break

            results: list[dict] = []
            stop = False
            for call in msg.tool_calls:
                try:
                    args = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                log.info(f"  tool={call.function.name} args_keys={list(args.keys())}")
                text, stop_now = self._dispatch(call.function.name, args)
                results.append({"role": "tool", "tool_call_id": call.id, "content": text})
                if stop_now:
                    stop = True

            self.history.extend(results)
            if stop:
                break

        return self.success

    def run_with_anthropic(self, anthropic_key: str) -> bool:
        """Run using Claude Opus via Anthropic SDK (primary path)."""
        import anthropic as _anthropic
        client = _anthropic.Anthropic(api_key=anthropic_key)
        # Convert OpenAI tool schemas to Anthropic format
        tools_list = [
            {"type": "function", "function": {"name": "read_file", "description": "Read a source file",
             "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
            {"type": "function", "function": {"name": "write_file", "description": "Write/overwrite a file",
             "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string", "description": "Full file content"}}, "required": ["path", "content"]}}},
            {"type": "function", "function": {"name": "bash", "description": "Run a shell command",
             "parameters": {"type": "object", "properties": {"cmd": {"type": "string"}}, "required": ["cmd"]}}},
            {"type": "function", "function": {"name": "done", "description": "Signal completion",
             "parameters": {"type": "object", "properties": {"success": {"type": "boolean"}, "summary": {"type": "string"}}, "required": ["success"]}}},
        ]
        anthropic_tools = _openai_tools_to_anthropic(tools_list)

        # Extract system and user messages for Anthropic format
        system_content = ""
        messages: list[dict] = []
        for msg in self.history:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                messages.append({"role": msg["role"], "content": msg["content"]})

        for turn in range(MAX_TURNS):
            log.info(f"Turn {turn + 1}/{MAX_TURNS} model={OPUS_MODEL} (Anthropic)")
            try:
                resp = client.messages.create(
                    model=OPUS_MODEL,
                    max_tokens=4096,
                    system=system_content,
                    tools=anthropic_tools,  # type: ignore[arg-type]
                    messages=messages,      # type: ignore[arg-type]
                )
            except Exception as e:
                # Permanent failures must not be retried — break to NVIDIA fallback.
                status = getattr(e, "status_code", None)
                if status in (401, 403, 404):
                    log.warning(f"Anthropic permanent error ({status}): {e} — falling back to NVIDIA")
                    return False
                log.warning(f"Anthropic transient error: {e}")
                time.sleep(5)
                continue  # retry transient errors (rate limit, server error, network)

            assistant_content: list[dict] = []
            tool_use_blocks: list = []
            for block in resp.content:
                if block.type == "text":
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    tool_use_blocks.append(block)
                    assistant_content.append({"type": "tool_use", "id": block.id, "name": block.name, "input": block.input})

            messages.append({"role": "assistant", "content": assistant_content})

            if not tool_use_blocks:
                break

            tool_results: list[dict] = []
            stop = False
            for call in tool_use_blocks:
                fn_args = call.input if isinstance(call.input, dict) else {}
                log.info(f"  tool={call.name} args_keys={list(fn_args.keys())}")
                text, stop_now = self._dispatch(call.name, fn_args)
                tool_results.append({"type": "tool_result", "tool_use_id": call.id, "content": text})
                if stop_now:
                    stop = True

            messages.append({"role": "user", "content": tool_results})
            if stop:
                break

        return self.success


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: apply_review.py <pr_number>", file=sys.stderr)
        sys.exit(1)

    pr    = sys.argv[1]
    repo  = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GH_TOKEN", "")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    nvidia_key = os.environ.get("NVIDIA_API_KEY", "")

    result_path = Path("/tmp/review_apply_result.json")

    def _skip(reason: str) -> None:
        log.info(reason)
        result_path.write_text(json.dumps({"success": True, "applied": False, "summary": reason}))

    if not anthropic_key and not nvidia_key:
        _skip("Neither ANTHROPIC_API_KEY nor NVIDIA_API_KEY set — skipping review application")
        sys.exit(0)

    log.info(f"Fetching review comments for PR #{pr} in {repo}")
    try:
        context = build_review_context(pr, repo, token)
    except Exception as e:
        log.error(f"Failed to fetch comments: {e}")
        _skip(f"Could not fetch review comments: {e}")
        sys.exit(0)

    if not context.strip():
        _skip("No actionable review comments found")
        sys.exit(0)

    log.info(f"Review context ({len(context)} chars)")

    agent = ApplyReviewAgent("", OPUS_MODEL, context)
    success = False

    # Primary: Claude Opus via Anthropic
    if anthropic_key:
        log.info(f"Trying model {OPUS_MODEL} (Anthropic — primary)")
        try:
            success = agent.run_with_anthropic(anthropic_key)
        except Exception as e:
            log.warning(f"Anthropic Opus failed: {e} — trying NVIDIA fallback")

    # Fallback: NVIDIA NIM
    if not success and nvidia_key:
        for model, desc in NVIDIA_CANDIDATE_MODELS:
            log.info(f"Trying model {model} ({desc}) (NVIDIA NIM — fallback)")
            agent = ApplyReviewAgent(nvidia_key, model, context)
            try:
                success = agent.run()
                if success:
                    break
            except Exception as e:
                log.warning(f"Model {model} failed: {e}")

    summary = agent.summary if agent else ""
    result_path.write_text(json.dumps({"success": success, "applied": True, "summary": summary}))
    log.info(f"Done — success={success} summary={summary[:120]}")
    sys.exit(0)   # always exit 0; caller checks result JSON


if __name__ == "__main__":
    main()

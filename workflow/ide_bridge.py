"""workflow/ide_bridge.py — OpenAI-compatible SSE bridge for IDE clients.

This module makes the CRISPY workflow engine accessible from any IDE that
speaks the OpenAI chat completions protocol (Continue, Cursor, Cline,
Copilot Chat, Aider, etc.) without any custom plugin or extension.

How it works
------------
1. IDE sends a normal ``POST /v1/chat/completions`` with model="crispy-workflow"
   (or to the dedicated ``POST /v1/workflow/chat`` endpoint).
2. The bridge inspects the last user message for a workflow trigger prefix:
     @build  <task>     →  trigger a full CRISPY build workflow
     @workflow <task>   →  same as @build
     /crispy <task>     →  same as @build
     @status [run_id]   →  report status of a workflow run
     @approve <run_id>  →  approve the gate for a run
     @reject <run_id> [reason] → reject the gate for a run
3. If a trigger is detected:
   - A WorkflowRun is created (for @build/@workflow/crispy) or queried.
   - The engine's event log is polled for up to STREAM_TIMEOUT_SECS.
   - Status updates are streamed back as SSE chat tokens so the IDE shows
     a live "typing" reply with run progress.
4. If NO trigger is detected the request is forwarded transparently to the
   normal Ollama/OpenAI-compat handler so the "crispy-workflow" model still
   works as a regular chat model.

Stream format (SSE tokens the IDE sees)
----------------------------------------
  ✅ CRISPY workflow started  ·  run_id: wf_abc123
  Phase: context  ·  status: running
  Phase: research ·  status: done
  ...
  ⏸  AWAITING APPROVAL  —  POST /workflow/wf_abc123/approve to proceed
  (or, after approval:)
  Phase: executing  ·  Slice 1/3: Add workflow models
  ✅ DONE  ·  run: wf_abc123  ·  all slices applied

Environment variables
---------------------
CRISPY_STREAM_TIMEOUT  — seconds to stream before returning a status URL
                         (default 60; set to 0 to return immediately)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from typing import Any, AsyncIterator

from fastapi import Request
from fastapi.responses import JSONResponse, StreamingResponse

log = logging.getLogger("crispy-ide-bridge")

STREAM_TIMEOUT_SECS = float(os.environ.get("CRISPY_STREAM_TIMEOUT", "60"))
_POLL_INTERVAL = 1.5  # seconds between event log polls

# ── Trigger patterns ──────────────────────────────────────────────────────────

_BUILD_RE = re.compile(
    r"""^(?:@build|@workflow|/crispy)\s+(.+)$""",
    re.I | re.S,
)
_STATUS_RE = re.compile(r"^@status(?:\s+(\S+))?$", re.I)
_APPROVE_RE = re.compile(r"^@approve\s+(\S+)$", re.I)
_REJECT_RE = re.compile(r"^@reject\s+(\S+)(?:\s+(.+))?$", re.I | re.S)


def _extract_last_user_message(messages: list[dict[str, Any]]) -> str:
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                return content.strip()
            if isinstance(content, list):
                # Handle multi-part content (vision, etc.)
                for part in reversed(content):
                    if isinstance(part, dict) and part.get("type") == "text":
                        return str(part.get("text", "")).strip()
    return ""


# ── SSE helpers ───────────────────────────────────────────────────────────────

def _sse_chunk(text: str, model: str = "crispy-workflow") -> bytes:
    """Produce one SSE data: line containing a chat completion delta."""
    chunk = {
        "id": f"chatcmpl-crispy-{int(time.time())}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {"role": "assistant", "content": text},
                "finish_reason": None,
            }
        ],
    }
    return b"data: " + json.dumps(chunk).encode("utf-8") + b"\n\n"


def _sse_done(model: str = "crispy-workflow") -> bytes:
    done_chunk = {
        "id": f"chatcmpl-crispy-{int(time.time())}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    return (
        b"data: " + json.dumps(done_chunk).encode("utf-8") + b"\n\n"
        + b"data: [DONE]\n\n"
    )


def _json_response(content: str, model: str = "crispy-workflow") -> JSONResponse:
    """Return a non-streaming OpenAI-compat JSON response."""
    data = {
        "id": f"chatcmpl-crispy-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": len(content) // 4, "total_tokens": len(content) // 4},
    }
    return JSONResponse(content=data)


# ── Build streaming ───────────────────────────────────────────────────────────

async def _stream_workflow_progress(
    engine: Any,
    run_id: str,
    stream: bool,
) -> AsyncIterator[bytes]:
    """Stream live workflow status as SSE tokens.

    Polls the event log every _POLL_INTERVAL seconds and emits tokens for
    each new event.  Terminates when:
      - The run reaches a terminal state (done / failed / cancelled)
      - The run reaches awaiting_approval (emit the approval instruction + stop)
      - STREAM_TIMEOUT_SECS is reached (emit a status URL + stop)
    """
    start = time.monotonic()
    last_pos = 0
    last_status = ""
    emitted_lines: list[str] = []

    def emit(text: str) -> bytes:
        emitted_lines.append(text)
        return _sse_chunk(text)

    yield emit(f"✅ **CRISPY workflow started**\n`run_id: {run_id}`\n\n")

    while True:
        elapsed = time.monotonic() - start
        run = engine.get(run_id)
        if run is None:
            yield emit("❌ Run not found.\n")
            break

        # Emit new events from the event log
        new_events = engine.get_events(run_id, from_position=last_pos, limit=50)
        for ev in new_events:
            last_pos = ev["position"] + 1
            etype = ev["event_type"]
            payload = ev.get("payload", {})

            if etype == "phase_started":
                phase = payload.get("phase", "?")
                yield emit(f"▶ Phase `{phase}` — running…\n")
            elif etype == "phase_complete":
                phase = payload.get("phase", "?")
                art = payload.get("artifact", "")
                yield emit(f"✓ Phase `{phase}` — done  →  `{art}`\n")
            elif etype == "phase_failed":
                phase = payload.get("phase", "?")
                err = payload.get("error", "")[:120]
                yield emit(f"✗ Phase `{phase}` — **FAILED**: {err}\n")
            elif etype == "gate_created":
                gate_id = payload.get("gate_id", "")
                yield emit(
                    f"\n⏸  **AWAITING APPROVAL**\n"
                    f"Review the plan artifact, then approve:\n"
                    f"```\n"
                    f"curl -X POST http://localhost:8000/workflow/{run_id}/approve \\\n"
                    f"  -H 'Authorization: Bearer YOUR_KEY' \\\n"
                    f"  -H 'Content-Type: application/json' \\\n"
                    f"  -d '{{\"approved_by\": \"<your-name>\"}}'\n"
                    f"```\n"
                    f"Or in your IDE: `@approve {run_id}`\n"
                )
            elif etype == "slices_registered":
                count = payload.get("count", "?")
                yield emit(f"\n📦 **{count} slice(s)** registered for execution.\n\n")
            elif etype == "slice_started":
                sid = payload.get("slice_id", "?")
                run_now = engine.get(run_id)
                sl = run_now.slice_by_id(sid) if run_now else None
                title = sl.title if sl else sid
                yield emit(f"▶ Slice `{title}` — executing…\n")
            elif etype == "slice_complete":
                sid = payload.get("slice_id", "?")
                passed = payload.get("check_passed", False)
                status = "✓ applied" if passed else "✗ FAILED"
                run_now = engine.get(run_id)
                sl = run_now.slice_by_id(sid) if run_now else None
                title = sl.title if sl else sid
                yield emit(f"{status}  Slice `{title}`\n")
            elif etype == "slice_failed":
                err = payload.get("error", "")[:120]
                yield emit(f"✗ Slice failed: {err}\n")
            elif etype == "workflow_done":
                yield emit(
                    f"\n🎉 **DONE** — `{run_id}`\n"
                    f"All slices applied and verified.\n"
                    f"View full report: `GET /workflow/{run_id}/artifacts/final-report.md`\n"
                )

        status = run.status
        if status != last_status:
            last_status = status

        # Terminal states — stop streaming
        if status in ("done", "failed", "cancelled"):
            if status == "failed":
                yield emit(f"\n❌ Workflow **FAILED** — `{run_id}`\nCheck events: `GET /workflow/{run_id}/events`\n")
            elif status == "cancelled":
                yield emit(f"\n🚫 Workflow **CANCELLED** — `{run_id}`\n")
            break

        # Gate — stop streaming and prompt for approval
        if status == "awaiting_approval":
            # Events above already emitted the approval instructions
            break

        # Timeout — emit a status URL and stop
        if STREAM_TIMEOUT_SECS > 0 and elapsed > STREAM_TIMEOUT_SECS:
            yield emit(
                f"\n⏱  Stream timeout ({STREAM_TIMEOUT_SECS:.0f}s).\n"
                f"Workflow still running. Poll: `GET /workflow/{run_id}`\n"
            )
            break

        await asyncio.sleep(_POLL_INTERVAL)

    yield _sse_done()


# ── Main handler ──────────────────────────────────────────────────────────────

async def handle_workflow_ide_chat(
    *,
    request: Request,
    engine: Any,
    ollama_base: str,
    email: str,
    department: str,
    key_id: str | None,
    body_override: bytes | None = None,
) -> JSONResponse | StreamingResponse:
    """Handle an OpenAI-compatible chat request from an IDE.

    Intercepts workflow trigger commands; passes all other requests to the
    normal chat completions handler transparently.
    """
    from chat_handlers import handle_openai_chat_completions
    from workflow.models import WorkflowBuildRequest

    body = body_override if body_override is not None else await request.body()

    try:
        payload: dict[str, Any] = json.loads(body) if body else {}
    except Exception:
        payload = {}

    messages = payload.get("messages", [])
    if not isinstance(messages, list):
        messages = []

    last_msg = _extract_last_user_message(messages)
    is_stream = bool(payload.get("stream", False))

    # ── @build / @workflow / /crispy ─────────────────────────────────────────
    m = _BUILD_RE.match(last_msg)
    if m:
        task = m.group(1).strip()
        log.info("IDE bridge: @build trigger from %s: %r", email, task[:80])
        req = WorkflowBuildRequest(
            request=task,
            title=task[:80],
            workspace_root=None,
        )
        run = await engine.create_run(req)
        if is_stream:
            return StreamingResponse(
                _stream_workflow_progress(engine, run.run_id, stream=True),
                media_type="text/event-stream",
                headers={
                    "X-Accel-Buffering": "no",
                    "Cache-Control": "no-cache",
                    "X-Workflow-Run-Id": run.run_id,
                },
            )
        # Non-streaming: return run_id summary immediately
        content = (
            f"✅ CRISPY workflow started\n\n"
            f"**run_id**: `{run.run_id}`\n"
            f"**status**: `{run.status}`\n\n"
            f"Pre-gate phases are running asynchronously.\n"
            f"Poll status: `GET /workflow/{run.run_id}`\n"
            f"When status reaches `awaiting_approval`, send:\n"
            f"`@approve {run.run_id}`"
        )
        return _json_response(content)

    # ── @status ───────────────────────────────────────────────────────────────
    m = _STATUS_RE.match(last_msg)
    if m:
        run_id = (m.group(1) or "").strip()
        if run_id:
            run = engine.get(run_id)
            if run is None:
                content = f"❌ WorkflowRun `{run_id}` not found."
            else:
                phases_text = "\n".join(
                    f"  • `{p.name}`: {p.status}" for p in run.phases
                )
                slices_text = "\n".join(
                    f"  • `{s.title}`: {s.status}" for s in run.slices
                ) or "  (none yet)"
                content = (
                    f"**Workflow** `{run.run_id}` — **{run.status}**\n\n"
                    f"Phases:\n{phases_text}\n\n"
                    f"Slices:\n{slices_text}\n"
                )
        else:
            # List most recent 5 runs
            runs = engine.list_runs(limit=5)
            if not runs:
                content = "No workflow runs found."
            else:
                lines = [f"**Recent CRISPY workflow runs** (newest first):\n"]
                for r in runs:
                    lines.append(f"• `{r.run_id}` — {r.status} — {r.title[:60]}")
                content = "\n".join(lines)
        return _json_response(content) if not is_stream else StreamingResponse(
            _single_token_stream(content),
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
        )

    # ── @approve ──────────────────────────────────────────────────────────────
    m = _APPROVE_RE.match(last_msg)
    if m:
        run_id = m.group(1).strip()
        try:
            updated = engine.approve(run_id, approved_by=email or "ide-user")
            content = (
                f"✅ Approved `{run_id}`\n"
                f"Status: `{updated.status}`\n"
                f"Post-gate execution (slice execute → review → verify → report) has begun.\n"
                f"Use `@status {run_id}` to monitor progress."
            )
        except (KeyError, ValueError) as exc:
            content = f"❌ Could not approve `{run_id}`: {exc}"
        return _json_response(content) if not is_stream else StreamingResponse(
            _single_token_stream(content),
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
        )

    # ── @reject ───────────────────────────────────────────────────────────────
    m = _REJECT_RE.match(last_msg)
    if m:
        run_id = m.group(1).strip()
        reason = (m.group(2) or "Rejected via IDE").strip()
        try:
            updated = engine.reject(run_id, reason=reason, rejected_by=email or "ide-user")
            content = (
                f"🚫 Rejected `{run_id}`\n"
                f"Reason: {reason}\n"
                f"Status: `{updated.status}`"
            )
        except (KeyError, ValueError) as exc:
            content = f"❌ Could not reject `{run_id}`: {exc}"
        return _json_response(content) if not is_stream else StreamingResponse(
            _single_token_stream(content),
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
        )

    # ── No trigger detected — pass through to normal chat handler ────────────
    log.debug("IDE bridge: no trigger in %r — forwarding to normal chat handler", last_msg[:60])
    # Re-create a Request-like object with the body already consumed.
    # We pass body_override so the handler can re-read it.
    # Simplest approach: forward as-is via handle_openai_chat_completions
    # (re-uses the already-read body stored in body_override).
    from starlette.datastructures import MutableHeaders
    # Patch the body back into request scope so handle_openai_chat_completions
    # can call await request.body() again.
    request._body = body  # type: ignore[attr-defined]
    return await handle_openai_chat_completions(
        request=request,
        ollama_base=ollama_base,
        email=email,
        department=department,
        key_id=key_id,
    )


async def _single_token_stream(content: str) -> AsyncIterator[bytes]:
    """Emit a complete response as a single SSE token (for non-build commands)."""
    yield _sse_chunk(content)
    yield _sse_done()

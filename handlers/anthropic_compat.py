"""
Anthropic Messages API compatibility layer.

Accepts POST /v1/messages in Anthropic format, translates to Ollama OpenAI-compat,
and returns Anthropic-format responses — including full SSE streaming.

This enables Claude Code CLI, the Anthropic Python/TS SDK, and any tool that sets
ANTHROPIC_BASE_URL to use your local Ollama models transparently.

Model routing:
  - Reads MODEL_MAP env var to map Anthropic model names → local Ollama names.
  - Falls back to AGENT_EXECUTOR_MODEL if no mapping found.

Auth:
  - Accepts both x-api-key header (Claude Code default) and Authorization: Bearer.
  - Auth is enforced by proxy.py before this handler is called.

Limitations vs real Anthropic API:
  - Images in content blocks are skipped (Ollama text models don't support vision).
  - Computer use / beta features are silently ignored.
  - Caching / prompt caching headers are accepted but not functional.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any, AsyncIterator

import httpx
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from langfuse_obs import emit_chat_observation
from router import get_router, RoutingDecision
from router.health import invalidate_cache as _invalidate_health_cache

log = logging.getLogger("qwen-proxy")


# ─── Fallback-aware HTTP helper ───────────────────────────────────────────────

async def _post_anthropic_with_fallback(
    url: str,
    body: bytes,
    headers: dict[str, str],
    openai_payload: dict[str, Any],
    fallback_models: list[str],
) -> Any:  # returns httpx.Response
    """POST to Ollama; on 5xx retry with each model in *fallback_models*."""
    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
        resp = await client.post(url, content=body, headers=headers)
    if resp.status_code < 500 or not fallback_models:
        return resp

    for fallback in fallback_models:
        log.warning(
            "Anthropic handler: Ollama returned %d — retrying with fallback model %r",
            resp.status_code, fallback,
        )
        _invalidate_health_cache()
        payload = dict(openai_payload)
        payload["model"] = fallback
        retry_body = json.dumps(payload).encode("utf-8")
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
            resp = await client.post(url, content=retry_body, headers=headers)
        if resp.status_code < 500:
            return resp

    return resp


# ─── Legacy shim (kept for any external callers) ───────────────────────────────

def get_local_model(anthropic_model: str) -> str:
    """Return the local Ollama model name for a given Anthropic model name.

    .. deprecated::
        Prefer ``get_router().route(requested_model=...)`` which returns full
        routing metadata. This shim is kept for backwards compatibility.
    """
    decision = get_router().route(requested_model=anthropic_model)
    return decision.resolved_model


# ─── Request translation: Anthropic → OpenAI ──────────────────────────────────

def _system_field_to_string(system: Any) -> str:
    """Convert Anthropic system field (string or list of content blocks) to plain string."""
    if isinstance(system, str):
        return system
    if isinstance(system, list):
        parts: list[str] = []
        for block in system:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "\n".join(parts)
    return ""


def _content_block_to_text(block: dict[str, Any]) -> str:
    """Convert a single Anthropic content block to a plain text string."""
    btype = block.get("type", "")
    if btype == "text":
        return block.get("text", "")
    if btype == "image":
        return "[image — not supported by local model]"
    if btype == "tool_result":
        tool_id = block.get("tool_use_id", "")
        content = block.get("content", "")
        if isinstance(content, list):
            content = " ".join(
                b.get("text", "") for b in content if isinstance(b, dict)
            )
        return f"[Tool result ({tool_id})]: {content}"
    if btype == "tool_use":
        return f"[Called {block.get('name', 'unknown')} with {json.dumps(block.get('input', {}))}]"
    return ""


def _messages_to_openai(
    messages: list[dict[str, Any]],
    system: str | None,
) -> list[dict[str, Any]]:
    """Convert Anthropic messages array + system string to OpenAI messages list."""
    out: list[dict[str, Any]] = []

    if system:
        out.append({"role": "system", "content": system})

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content")

        if isinstance(content, str):
            out.append({"role": role, "content": content})
        elif isinstance(content, list):
            text = "\n".join(_content_block_to_text(b) for b in content if isinstance(b, dict))
            out.append({"role": role, "content": text})
        else:
            out.append({"role": role, "content": str(content or "")})

    return out


def _tools_to_openai(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert Anthropic tool definitions to OpenAI function tool definitions."""
    out: list[dict[str, Any]] = []
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        out.append({
            "type": "function",
            "function": {
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
                "parameters": tool.get("input_schema", {"type": "object", "properties": {}}),
            },
        })
    return out


# ─── Response translation: OpenAI → Anthropic ─────────────────────────────────

def _finish_reason_to_stop_reason(finish: str | None) -> str:
    mapping = {"tool_calls": "tool_use", "length": "max_tokens", "stop": "end_turn"}
    return mapping.get(finish or "stop", "end_turn")


def _openai_choice_to_anthropic_content(choice: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert an OpenAI response choice to Anthropic content block list."""
    blocks: list[dict[str, Any]] = []
    msg = choice.get("message") or {}

    text = msg.get("content") or ""
    if text:
        blocks.append({"type": "text", "text": text})

    for tc in (msg.get("tool_calls") or []):
        if not isinstance(tc, dict):
            continue
        fn = tc.get("function") or {}
        try:
            inp = json.loads(fn.get("arguments", "{}"))
        except (json.JSONDecodeError, TypeError):
            inp = {}
        blocks.append({
            "type": "tool_use",
            "id": tc.get("id", f"toolu_{uuid.uuid4().hex[:16]}"),
            "name": fn.get("name", ""),
            "input": inp,
        })

    return blocks


def _build_anthropic_response(
    data: dict[str, Any],
    anthropic_model: str,
    msg_id: str,
) -> dict[str, Any]:
    choices = data.get("choices") or []
    usage = data.get("usage") or {}

    content_blocks: list[dict[str, Any]] = []
    stop_reason = "end_turn"

    if choices:
        choice = choices[0]
        stop_reason = _finish_reason_to_stop_reason(choice.get("finish_reason"))
        content_blocks = _openai_choice_to_anthropic_content(choice)

    return {
        "id": msg_id,
        "type": "message",
        "role": "assistant",
        "content": content_blocks,
        "model": anthropic_model,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": int(usage.get("prompt_tokens") or 0),
            "output_tokens": int(usage.get("completion_tokens") or 0),
        },
    }


# ─── Anthropic SSE streaming ───────────────────────────────────────────────────

def _sse_event(event_type: str, data: dict[str, Any]) -> bytes:
    return (
        f"event: {event_type}\n"
        f"data: {json.dumps(data, separators=(',', ':'))}\n\n"
    ).encode("utf-8")


async def _stream_anthropic_sse(
    target_url: str,
    forward_headers: dict[str, str],
    forward_body: bytes,
    anthropic_model: str,
    local_model: str,
    msg_id: str,
    email: str,
    department: str,
    key_id: str | None,
    openai_messages: list[dict[str, Any]],
    start_time: float,
    routing_meta: dict[str, Any] | None = None,
) -> AsyncIterator[bytes]:
    """Translate Ollama OpenAI SSE stream → Anthropic SSE stream."""

    # ── Preamble events ────────────────────────────────────────────────────────
    yield _sse_event("message_start", {
        "type": "message_start",
        "message": {
            "id": msg_id,
            "type": "message",
            "role": "assistant",
            "content": [],
            "model": anthropic_model,
            "stop_reason": None,
            "stop_sequence": None,
            "usage": {"input_tokens": 0, "output_tokens": 1},
        },
    })
    yield _sse_event("content_block_start", {
        "type": "content_block_start",
        "index": 0,
        "content_block": {"type": "text", "text": ""},
    })
    yield _sse_event("ping", {"type": "ping"})

    # ── Stream from Ollama ─────────────────────────────────────────────────────
    text_parts: list[str] = []
    input_tokens = 0
    output_tokens = 0
    ttft_ms: int | None = None
    line_buf = bytearray()

    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
        async with client.stream("POST", target_url, content=forward_body, headers=forward_headers) as resp:
            if resp.status_code >= 400:
                error_body = await resp.aread()
                log.error("Ollama returned %d: %s", resp.status_code, error_body[:500])
                yield _sse_event("error", {
                    "type": "error",
                    "error": {"type": "api_error", "message": f"Upstream error {resp.status_code}"},
                })
                return

            async for chunk in resp.aiter_bytes(chunk_size=512):
                line_buf.extend(chunk)
                # Parse complete SSE lines from the buffer
                while True:
                    nl = bytes(line_buf).find(b"\n")
                    if nl == -1:
                        break
                    raw_line = bytes(line_buf[:nl])
                    del line_buf[:nl + 1]

                    if not raw_line.startswith(b"data:"):
                        continue
                    payload_bytes = raw_line[5:].strip()
                    if payload_bytes == b"[DONE]":
                        continue

                    try:
                        obj = json.loads(payload_bytes)
                    except json.JSONDecodeError:
                        continue

                    # Extract usage from final chunk
                    u = obj.get("usage")
                    if isinstance(u, dict):
                        input_tokens = int(u.get("prompt_tokens") or 0)
                        output_tokens = int(u.get("completion_tokens") or 0)

                    # Extract text deltas and emit as Anthropic content_block_delta
                    for ch in (obj.get("choices") or []):
                        delta = ch.get("delta") or {}
                        text = delta.get("content")
                        if isinstance(text, str) and text:
                            if ttft_ms is None:
                                ttft_ms = int((time.perf_counter() - start_time) * 1000)
                            text_parts.append(text)
                            yield _sse_event("content_block_delta", {
                                "type": "content_block_delta",
                                "index": 0,
                                "delta": {"type": "text_delta", "text": text},
                            })

    # ── Epilogue events ────────────────────────────────────────────────────────
    full_text = "".join(text_parts)
    if not output_tokens and full_text:
        output_tokens = max(len(full_text) // 4, 1)

    yield _sse_event("content_block_stop", {"type": "content_block_stop", "index": 0})
    yield _sse_event("message_delta", {
        "type": "message_delta",
        "delta": {"stop_reason": "end_turn", "stop_sequence": None},
        "usage": {"output_tokens": output_tokens},
    })
    yield _sse_event("message_stop", {"type": "message_stop"})

    # ── Langfuse observation ───────────────────────────────────────────────────
    latency_ms = int((time.perf_counter() - start_time) * 1000)
    await _emit_safely(
        email, department, key_id, local_model, openai_messages, full_text,
        input_tokens, output_tokens,
        latency_ms=latency_ms,
        ttft_ms=ttft_ms or 0,
        routing_meta=routing_meta,
    )


# ─── Langfuse emission ─────────────────────────────────────────────────────────

async def _emit_safely(
    email: str,
    department: str,
    key_id: str | None,
    model: str,
    messages: list[dict[str, Any]],
    out_text: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: int = 0,
    ttft_ms: int = 0,
    routing_meta: dict[str, Any] | None = None,
) -> None:
    try:
        await asyncio.to_thread(
            emit_chat_observation,
            email=email,
            department=department,
            key_id=key_id,
            model=model,
            messages=messages,
            output_text=out_text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            ttft_ms=ttft_ms,
            routing_meta=routing_meta,
        )
    except Exception as exc:
        log.warning("Anthropic compat Langfuse emit error: %s", exc)


# ─── Main handler ──────────────────────────────────────────────────────────────

async def handle_anthropic_messages(
    *,
    request: Request,
    ollama_base: str,
    email: str,
    department: str,
    key_id: str | None,
) -> JSONResponse | StreamingResponse:
    """Handle POST /v1/messages — Anthropic Messages API format."""
    start_time = time.perf_counter()
    body_bytes = await request.body()

    try:
        payload: dict[str, Any] = json.loads(body_bytes) if body_bytes else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON body must be an object")

    # ── Field extraction ───────────────────────────────────────────────────────
    anthropic_model = str(payload.get("model") or "claude-3-5-sonnet-20241022")

    system_raw = payload.get("system")
    system_text = _system_field_to_string(system_raw) if system_raw else None

    anthropic_messages: list[dict[str, Any]] = payload.get("messages") or []
    stream = bool(payload.get("stream", False))
    max_tokens = payload.get("max_tokens")
    tools: list[dict[str, Any]] = payload.get("tools") or []

    # ── Route: decide which local model to use ─────────────────────────────────
    # Manual override: client sends X-Model-Override header (works from any IDE).
    override_model = request.headers.get("x-model-override") or None
    openai_messages_for_routing = _messages_to_openai(anthropic_messages, system_text)
    routing = get_router().route(
        requested_model=anthropic_model,
        messages=openai_messages_for_routing,
        system=system_text,
        has_tools=bool(tools),
        stream=stream,
        override_model=override_model,
        endpoint_type="chat",
    )
    local_model = routing.resolved_model
    routing_meta = routing.to_meta()

    # ── Build OpenAI payload ───────────────────────────────────────────────────
    openai_messages = openai_messages_for_routing

    openai_payload: dict[str, Any] = {
        "model": local_model,
        "messages": openai_messages,
        "stream": stream,
    }

    if max_tokens:
        openai_payload["max_tokens"] = max_tokens

    if stream:
        openai_payload["stream_options"] = {"include_usage": True}

    if tools:
        openai_payload["tools"] = _tools_to_openai(tools)

    # Pass through sampling params if present
    for param in ("temperature", "top_p"):
        val = payload.get(param)
        if val is not None:
            openai_payload[param] = val

    forward_body = json.dumps(openai_payload).encode("utf-8")
    target_url = f"{ollama_base}/v1/chat/completions"
    forward_headers = {"Content-Type": "application/json"}
    msg_id = f"msg_{uuid.uuid4().hex[:24]}"

    log.info(
        "→ /v1/messages model=%s → %s [%s/%s] stream=%s tools=%d",
        anthropic_model, local_model,
        routing.mode, routing.selection_source,
        stream, len(tools),
    )

    # ── Streaming response ─────────────────────────────────────────────────────
    if stream:
        return StreamingResponse(
            _stream_anthropic_sse(
                target_url, forward_headers, forward_body,
                anthropic_model, local_model, msg_id,
                email, department, key_id, openai_messages, start_time,
                routing_meta=routing_meta,
            ),
            media_type="text/event-stream",
            headers={
                "X-Accel-Buffering": "no",
                "Cache-Control": "no-cache",
                "anthropic-version": "2023-06-01",
                "X-Routing-Mode": routing.mode,
                "X-Routing-Model": local_model,
            },
        )

    # ── Non-streaming response (with fallback retry on 5xx) ───────────────────
    resp = await _post_anthropic_with_fallback(
        target_url, forward_body, forward_headers,
        openai_payload, routing.fallback_chain,
    )

    latency_ms = int((time.perf_counter() - start_time) * 1000)

    if not resp.headers.get("content-type", "").startswith("application/json"):
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:500])

    data = resp.json()
    anthropic_resp = _build_anthropic_response(data, anthropic_model, msg_id)

    pt = anthropic_resp["usage"]["input_tokens"]
    ct = anthropic_resp["usage"]["output_tokens"]
    out_text = next(
        (b.get("text", "") for b in anthropic_resp["content"] if b.get("type") == "text"),
        "",
    )

    await _emit_safely(
        email, department, key_id, local_model, openai_messages, out_text,
        pt, ct, latency_ms=latency_ms,
        routing_meta=routing_meta,
    )

    return JSONResponse(
        content=anthropic_resp,
        status_code=resp.status_code,
        headers={
            "anthropic-version": "2023-06-01",
            "X-Routing-Mode": routing.mode,
            "X-Routing-Model": local_model,
        },
    )

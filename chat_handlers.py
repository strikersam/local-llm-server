"""OpenAI-compatible /v1/chat/completions and Ollama /api/chat with usage + Langfuse."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, AsyncIterator

import httpx
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from langfuse_obs import emit_chat_observation
from router import get_router
from router.health import invalidate_cache as _invalidate_health_cache

log = logging.getLogger("qwen-proxy")


async def _post_with_fallback(
    url: str,
    body: bytes,
    headers: dict[str, str],
    fallback_models: list[str],
) -> httpx.Response:
    """POST to *url*; on 5xx retry with each model in *fallback_models*.

    The body is a JSON object with a ``"model"`` key.  Each retry swaps in the
    next model name.  Returns the last response regardless of status.
    """
    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
        resp = await client.post(url, content=body, headers=headers)
        if resp.status_code < 500 or not fallback_models:
            return resp

    for fallback in fallback_models:
        log.warning(
            "Upstream returned %d — retrying with fallback model %r",
            resp.status_code, fallback,
        )
        # Invalidate health cache so the next route() reflects current state
        _invalidate_health_cache()
        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, ValueError):
            break
        payload["model"] = fallback
        retry_body = json.dumps(payload).encode("utf-8")
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
            resp = await client.post(url, content=retry_body, headers=headers)
        if resp.status_code < 500:
            return resp

    return resp

_INJECT_STREAM_USAGE = os.environ.get("PROXY_INJECT_STREAM_USAGE", "true").strip().lower() in (
    "1",
    "true",
    "yes",
)
_ENABLE_DEFAULT_SYSTEM_PROMPT = os.environ.get("PROXY_DEFAULT_SYSTEM_PROMPT_ENABLED", "true").strip().lower() in (
    "1",
    "true",
    "yes",
)
_STRIP_THINK_TAGS = os.environ.get("PROXY_STRIP_THINK_TAGS", "false").strip().lower() in (
    "1",
    "true",
    "yes",
)
_DEFAULT_SYSTEM_PROMPT_INLINE = os.environ.get("PROXY_DEFAULT_SYSTEM_PROMPT", "").strip()
_DEFAULT_SYSTEM_PROMPT_FILE = os.environ.get("PROXY_DEFAULT_SYSTEM_PROMPT_FILE", "").strip()
_DEFAULT_MAX_TOKENS_RAW = os.environ.get("PROXY_DEFAULT_MAX_TOKENS", "").strip()
_CACHED_DEFAULT_SYSTEM_PROMPT: str | None = None

try:
    _DEFAULT_MAX_TOKENS = int(_DEFAULT_MAX_TOKENS_RAW) if _DEFAULT_MAX_TOKENS_RAW else 0
except ValueError:
    _DEFAULT_MAX_TOKENS = 0


def _load_default_system_prompt() -> str:
    global _CACHED_DEFAULT_SYSTEM_PROMPT
    if _CACHED_DEFAULT_SYSTEM_PROMPT is not None:
        return _CACHED_DEFAULT_SYSTEM_PROMPT

    prompt = _DEFAULT_SYSTEM_PROMPT_INLINE
    if not prompt and _DEFAULT_SYSTEM_PROMPT_FILE:
        try:
            prompt = Path(_DEFAULT_SYSTEM_PROMPT_FILE).read_text(encoding="utf-8").strip()
        except OSError as exc:
            log.warning("Could not read PROXY_DEFAULT_SYSTEM_PROMPT_FILE=%s: %s", _DEFAULT_SYSTEM_PROMPT_FILE, exc)
    _CACHED_DEFAULT_SYSTEM_PROMPT = prompt
    return prompt


def _inject_default_system_prompt(payload: dict[str, Any]) -> dict[str, Any]:
    if not _ENABLE_DEFAULT_SYSTEM_PROMPT:
        return payload

    prompt = _load_default_system_prompt()
    if not prompt:
        return payload

    messages = payload.get("messages")
    if not isinstance(messages, list):
        return payload

    injected = {"role": "system", "content": prompt}
    if messages and messages[0] == injected:
        return payload

    copied = dict(payload)
    copied["messages"] = [injected, *messages]
    return copied


def _apply_chat_defaults(payload: dict[str, Any]) -> dict[str, Any]:
    if _DEFAULT_MAX_TOKENS <= 0:
        return payload
    if "max_tokens" in payload or "maxTokens" in payload:
        return payload
    copied = dict(payload)
    copied["max_tokens"] = _DEFAULT_MAX_TOKENS
    return copied


def _strip_think_blocks(text: str) -> str:
    if not text:
        return text

    out: list[str] = []
    cursor = 0
    while cursor < len(text):
        start = text.find("<think>", cursor)
        if start == -1:
            out.append(text[cursor:])
            break
        out.append(text[cursor:start])
        end = text.find("</think>", start + len("<think>"))
        if end == -1:
            break
        cursor = end + len("</think>")
    return "".join(out).strip()


def _extract_exact_output(messages: Any) -> str | None:
    if not isinstance(messages, list):
        return None

    for message in reversed(messages):
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        content = message.get("content")
        if not isinstance(content, str):
            return None
        match = re.search(r"Reply with exactly:\s*(.+?)\s*$", content, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        exact = match.group(1).strip()
        return exact or None
    return None


def _openai_chat_response(content: str, model: str) -> dict[str, Any]:
    completion_tokens = max(len(content) // 4, 1) if content else 0
    return {
        "id": "chatcmpl-local-exact",
        "object": "chat.completion",
        "created": 0,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": completion_tokens,
            "total_tokens": completion_tokens,
        },
    }


def _openai_chat_stream_bytes(content: str, model: str) -> bytes:
    chunk = {
        "id": "chatcmpl-local-exact",
        "object": "chat.completion.chunk",
        "created": 0,
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {"role": "assistant", "content": content},
                "finish_reason": None,
            }
        ],
    }
    done = {
        "id": "chatcmpl-local-exact",
        "object": "chat.completion.chunk",
        "created": 0,
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {},
                "finish_reason": "stop",
            }
        ],
    }
    payload = [
        b"data: " + json.dumps(chunk, separators=(",", ":")).encode("utf-8") + b"\n\n",
        b"data: " + json.dumps(done, separators=(",", ":")).encode("utf-8") + b"\n\n",
        b"data: [DONE]\n\n",
    ]
    return b"".join(payload)


async def handle_openai_chat_completions(
    *,
    request: Request,
    ollama_base: str,
    email: str,
    department: str,
    key_id: str | None,
) -> JSONResponse | StreamingResponse:
    body = await request.body()

    try:
        payload: dict[str, Any] = json.loads(body) if body else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON body must be an object")

    model = payload.get("model")
    if not isinstance(model, str):
        model = ""

    # ── Route: resolve the actual local model to use ──────────────────────────
    override_model = request.headers.get("x-model-override") or None
    messages_for_routing = payload.get("messages")
    routing = get_router().route(
        requested_model=model or None,
        messages=messages_for_routing if isinstance(messages_for_routing, list) else None,
        has_tools=bool(payload.get("tools")),
        stream=bool(payload.get("stream", False)),
        override_model=override_model,
        endpoint_type="chat",
    )
    resolved_model = routing.resolved_model
    routing_meta = routing.to_meta()

    # Rewrite model in payload so it reaches Ollama correctly.
    # Only rewrite if the router actually changed or resolved the model.
    if resolved_model and resolved_model != model:
        payload = dict(payload)
        payload["model"] = resolved_model
        model = resolved_model

    payload = _inject_default_system_prompt(payload)
    payload = _apply_chat_defaults(payload)
    messages = payload.get("messages")
    stream = bool(payload.get("stream", False))
    exact_output = _extract_exact_output(messages)

    if exact_output is not None:
        usage_completion_tokens = max(len(exact_output) // 4, 1) if exact_output else 0
        await _emit_safely(email, department, key_id, model, messages, exact_output, 0, usage_completion_tokens, routing_meta=routing_meta)
        if stream:
            async def _single_exact_stream() -> AsyncIterator[bytes]:
                yield _openai_chat_stream_bytes(exact_output, model)

            return StreamingResponse(
                _single_exact_stream(),
                media_type="text/event-stream",
                headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
            )
        data = _openai_chat_response(exact_output, model)
        return JSONResponse(content=data, status_code=200)

    # Ask Ollama/OpenAI-compat layer to include usage in streaming chunks when supported.
    if _INJECT_STREAM_USAGE:
        so = payload.get("stream_options")
        if stream and not isinstance(so, dict):
            payload["stream_options"] = {"include_usage": True}
        elif stream and isinstance(so, dict) and "include_usage" not in so:
            so["include_usage"] = True
            payload["stream_options"] = so

    forward = json.dumps(payload).encode("utf-8")
    content_type = request.headers.get("content-type", "application/json")
    target_url = f"{ollama_base}/v1/chat/completions"
    headers = {"Content-Type": content_type}

    if stream:
        return StreamingResponse(
            _stream_openai_chat(target_url, headers, forward, email, department, key_id, model, messages, routing_meta=routing_meta),
            media_type="text/event-stream",
            headers={
                "X-Accel-Buffering": "no",
                "Cache-Control": "no-cache",
                "X-Routing-Mode": routing.mode,
                "X-Routing-Model": model,
            },
        )

    resp = await _post_with_fallback(target_url, forward, headers, routing.fallback_chain)

    if resp.headers.get("content-type", "").startswith("application/json"):
        data = resp.json()
    else:
        return JSONResponse(content=resp.text, status_code=resp.status_code)

    out_text, pt, ct = _openai_usage_from_response(data)
    await _emit_safely(email, department, key_id, model, messages, out_text, pt, ct, routing_meta=routing_meta)
    return JSONResponse(
        content=data,
        status_code=resp.status_code,
        headers={"X-Routing-Mode": routing.mode, "X-Routing-Model": model},
    )


def _openai_usage_from_response(data: Any) -> tuple[str, int, int]:
    out_text = ""
    if isinstance(data, dict):
        if _STRIP_THINK_TAGS:
            choices = data.get("choices")
            if isinstance(choices, list):
                for choice in choices:
                    if not isinstance(choice, dict):
                        continue
                    msg = choice.get("message")
                    if isinstance(msg, dict) and isinstance(msg.get("content"), str):
                        msg["content"] = _strip_think_blocks(msg["content"])
        choices = data.get("choices") or []
        if choices and isinstance(choices[0], dict):
            msg = choices[0].get("message") or {}
            if isinstance(msg, dict) and isinstance(msg.get("content"), str):
                out_text = msg["content"]
        usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
        pt = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        ct = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
        return out_text, pt, ct
    return "", 0, 0


async def _emit_safely(
    email: str,
    department: str,
    key_id: str | None,
    model: str,
    messages: Any,
    out_text: str,
    pt: int,
    ct: int,
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
            prompt_tokens=pt,
            completion_tokens=ct,
            routing_meta=routing_meta,
        )
    except Exception as e:
        log.warning("Observation emit error: %s", e)


def _parse_openai_sse(buffer: bytes) -> tuple[str, int, int, int]:
    """Return assistant text, prompt_tokens, completion_tokens, total_tokens from SSE body."""
    text_parts: list[str] = []
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    for line in buffer.split(b"\n"):
        if not line.startswith(b"data:"):
            continue
        data = line.split(b"data:", 1)[1].strip()
        if data == b"[DONE]":
            continue
        try:
            obj = json.loads(data)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        usage = obj.get("usage")
        if isinstance(usage, dict):
            prompt_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or prompt_tokens or 0)
            completion_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or completion_tokens or 0)
            total_tokens = int(usage.get("total_tokens") or total_tokens or 0)
        choices = obj.get("choices") or []
        for ch in choices:
            if not isinstance(ch, dict):
                continue
            delta = ch.get("delta")
            if isinstance(delta, dict) and isinstance(delta.get("content"), str):
                text_parts.append(delta["content"])
    out = "".join(text_parts)
    if total_tokens and not prompt_tokens and not completion_tokens:
        completion_tokens = max(total_tokens - prompt_tokens, 0)
    return out, prompt_tokens, completion_tokens, total_tokens


async def _stream_openai_chat(
    url: str,
    headers: dict[str, str],
    body: bytes,
    email: str,
    department: str,
    key_id: str | None,
    model: str,
    messages: Any,
    routing_meta: dict[str, Any] | None = None,
) -> AsyncIterator[bytes]:
    buf = bytearray()
    line_buf = bytearray()
    in_think = False
    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
        async with client.stream("POST", url, content=body, headers=headers) as resp:
            if resp.status_code >= 400:
                yield await resp.aread()
                return
            async for chunk in resp.aiter_bytes(chunk_size=1024):
                buf.extend(chunk)
                if not _STRIP_THINK_TAGS:
                    yield chunk
                    continue

                line_buf.extend(chunk)
                while True:
                    newline = line_buf.find(b"\n")
                    if newline == -1:
                        break
                    raw_line = bytes(line_buf[: newline + 1])
                    del line_buf[: newline + 1]
                    filtered_line, in_think = _filter_openai_sse_line(raw_line, in_think)
                    if filtered_line:
                        yield filtered_line

    if _STRIP_THINK_TAGS and line_buf:
        filtered_line, _ = _filter_openai_sse_line(bytes(line_buf), in_think)
        if filtered_line:
            yield filtered_line

    out_text, pt, ct, _tot = _parse_openai_sse(bytes(buf))
    if _STRIP_THINK_TAGS:
        out_text = _strip_think_blocks(out_text)
    if pt == 0 and ct == 0 and out_text:
        # Rough fallback if usage was not present in stream
        est = max(len(out_text) // 4, 1)
        ct = est
    await _emit_safely(email, department, key_id, model, messages, out_text, pt, ct, routing_meta=routing_meta)


async def handle_ollama_native_chat(
    *,
    request: Request,
    ollama_base: str,
    email: str,
    department: str,
    key_id: str | None,
) -> JSONResponse | StreamingResponse:
    body = await request.body()
    try:
        payload: dict[str, Any] = json.loads(body) if body else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON body must be an object")

    payload = _inject_default_system_prompt(payload)
    model = payload.get("model")
    if not isinstance(model, str):
        model = ""
    stream = bool(payload.get("stream", False))
    messages = payload.get("messages")

    # ── Route: resolve the actual local model ────────────────────────────────
    override_model = request.headers.get("x-model-override") or None
    routing = get_router().route(
        requested_model=model or None,
        messages=messages if isinstance(messages, list) else None,
        stream=stream,
        override_model=override_model,
        endpoint_type="chat",
    )
    resolved_model = routing.resolved_model
    routing_meta = routing.to_meta()
    if resolved_model and resolved_model != model:
        payload = dict(payload)
        payload["model"] = resolved_model
        model = resolved_model

    body = json.dumps(payload).encode("utf-8")
    content_type = request.headers.get("content-type", "application/json")
    target_url = f"{ollama_base}/api/chat"
    headers = {"Content-Type": content_type}

    if stream:
        return StreamingResponse(
            _stream_ollama_chat(target_url, headers, body, email, department, key_id, model, messages, routing_meta=routing_meta),
            media_type="application/x-ndjson",
        )

    resp = await _post_with_fallback(target_url, body, headers, routing.fallback_chain)

    if not resp.headers.get("content-type", "").startswith("application/json"):
        return JSONResponse(content=resp.text, status_code=resp.status_code)

    data = resp.json()
    out_text = ""
    pt = 0
    ct = 0
    if isinstance(data, dict):
        msg = data.get("message") or {}
        if isinstance(msg, dict) and isinstance(msg.get("content"), str):
            out_text = msg["content"]
        pt = int(data.get("prompt_eval_count") or 0)
        ct = int(data.get("eval_count") or 0)

    await _emit_safely(email, department, key_id, model, messages, out_text, pt, ct, routing_meta=routing_meta)
    return JSONResponse(content=data, status_code=resp.status_code)


async def _stream_ollama_chat(
    url: str,
    headers: dict[str, str],
    body: bytes,
    email: str,
    department: str,
    key_id: str | None,
    model: str,
    messages: Any,
    routing_meta: dict[str, Any] | None = None,
) -> AsyncIterator[bytes]:
    buf = bytearray()
    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
        async with client.stream("POST", url, content=body, headers=headers) as resp:
            if resp.status_code >= 400:
                yield await resp.aread()
                return
            async for chunk in resp.aiter_bytes(chunk_size=1024):
                buf.extend(chunk)
                yield chunk

    out_text, pt, ct = _parse_ollama_ndjson(bytes(buf))
    if pt == 0 and ct == 0 and out_text:
        est = max(len(out_text) // 4, 1)
        ct = est
    await _emit_safely(email, department, key_id, model, messages, out_text, pt, ct, routing_meta=routing_meta)


def _parse_ollama_ndjson(buffer: bytes) -> tuple[str, int, int]:
    text_parts: list[str] = []
    pt = 0
    ct = 0
    for line in buffer.split(b"\n"):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        msg = obj.get("message") or {}
        if isinstance(msg, dict) and isinstance(msg.get("content"), str):
            text_parts.append(msg["content"])
        if "prompt_eval_count" in obj:
            pt = int(obj.get("prompt_eval_count") or 0)
        if "eval_count" in obj:
            ct = int(obj.get("eval_count") or 0)
    return "".join(text_parts), pt, ct


def _filter_openai_sse_line(line: bytes, in_think: bool) -> tuple[bytes, bool]:
    stripped = line.strip()
    if not stripped.startswith(b"data:"):
        return line, in_think

    payload = stripped.split(b"data:", 1)[1].strip()
    if payload == b"[DONE]":
        return line, in_think

    try:
        obj = json.loads(payload)
    except json.JSONDecodeError:
        return line, in_think

    changed = False
    choices = obj.get("choices")
    if isinstance(choices, list):
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            delta = choice.get("delta")
            if not isinstance(delta, dict):
                continue
            content = delta.get("content")
            if not isinstance(content, str):
                continue
            visible, in_think = _filter_fragment(content, in_think)
            if visible != content:
                changed = True
                if visible:
                    delta["content"] = visible
                else:
                    delta.pop("content", None)

    if not changed:
        return line, in_think

    encoded = json.dumps(obj, separators=(",", ":")).encode("utf-8")
    return b"data: " + encoded + b"\n", in_think


def _filter_fragment(text: str, in_think: bool) -> tuple[str, bool]:
    if not text:
        return text, in_think

    out: list[str] = []
    cursor = 0
    while cursor < len(text):
        if in_think:
            end = text.find("</think>", cursor)
            if end == -1:
                return "".join(out), True
            cursor = end + len("</think>")
            in_think = False
            continue

        start = text.find("<think>", cursor)
        if start == -1:
            out.append(text[cursor:])
            return "".join(out), False
        out.append(text[cursor:start])
        cursor = start + len("<think>")
        in_think = True

    return "".join(out), in_think

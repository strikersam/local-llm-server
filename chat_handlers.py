"""OpenAI-compatible /v1/chat/completions and Ollama /api/chat with usage + Langfuse."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, AsyncIterator

import httpx
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from langfuse_obs import emit_chat_observation

log = logging.getLogger("qwen-proxy")

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
_DEFAULT_SYSTEM_PROMPT_INLINE = os.environ.get("PROXY_DEFAULT_SYSTEM_PROMPT", "").strip()
_DEFAULT_SYSTEM_PROMPT_FILE = os.environ.get("PROXY_DEFAULT_SYSTEM_PROMPT_FILE", "").strip()
_CACHED_DEFAULT_SYSTEM_PROMPT: str | None = None


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
    payload = _inject_default_system_prompt(payload)
    messages = payload.get("messages")
    stream = bool(payload.get("stream", False))

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
            _stream_openai_chat(target_url, headers, forward, email, department, key_id, model, messages),
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
        )

    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
        resp = await client.post(target_url, content=forward, headers=headers)

    if resp.headers.get("content-type", "").startswith("application/json"):
        data = resp.json()
    else:
        return JSONResponse(content=resp.text, status_code=resp.status_code)

    out_text, pt, ct = _openai_usage_from_response(data)
    await _emit_safely(email, department, key_id, model, messages, out_text, pt, ct)
    return JSONResponse(content=data, status_code=resp.status_code)


def _openai_usage_from_response(data: Any) -> tuple[str, int, int]:
    out_text = ""
    if isinstance(data, dict):
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

    out_text, pt, ct, _tot = _parse_openai_sse(bytes(buf))
    if pt == 0 and ct == 0 and out_text:
        # Rough fallback if usage was not present in stream
        est = max(len(out_text) // 4, 1)
        ct = est
    await _emit_safely(email, department, key_id, model, messages, out_text, pt, ct)


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
    body = json.dumps(payload).encode("utf-8")
    model = payload.get("model")
    if not isinstance(model, str):
        model = ""
    stream = bool(payload.get("stream", False))
    messages = payload.get("messages")

    content_type = request.headers.get("content-type", "application/json")
    target_url = f"{ollama_base}/api/chat"
    headers = {"Content-Type": content_type}

    if stream:
        return StreamingResponse(
            _stream_ollama_chat(target_url, headers, body, email, department, key_id, model, messages),
            media_type="application/x-ndjson",
        )

    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
        resp = await client.post(target_url, content=body, headers=headers)

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

    await _emit_safely(email, department, key_id, model, messages, out_text, pt, ct)
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
    await _emit_safely(email, department, key_id, model, messages, out_text, pt, ct)


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

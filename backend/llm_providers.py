from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

log = logging.getLogger("llm-wiki")


@dataclass(frozen=True)
class LlmProviderConfig:
    """Minimal provider config for OpenAI-compatible chat."""

    type: str
    base_url: str
    api_key: str | None = None
    default_model: str | None = None


def normalize_base_url(base_url: str) -> str:
    return (base_url or "").strip().rstrip("/")


def openai_compat_url(base_url: str, path: str) -> str:
    """Build an OpenAI-compatible URL for a provider base URL.

    Supports base URLs either with or without a trailing /v1.
    """
    base = normalize_base_url(base_url)
    if not path.startswith("/"):
        path = "/" + path
    if base.endswith("/v1"):
        return f"{base}{path}"
    return f"{base}/v1{path}"


def _auth_headers(api_key: str | None) -> dict[str, str]:
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


async def chat_completion_text(
    provider: LlmProviderConfig,
    *,
    messages: list[dict[str, Any]],
    model: str | None,
    temperature: float,
    timeout_sec: float = 120.0,
    retries: int = 2,
    client: httpx.AsyncClient | None = None,
) -> str:
    use_model = (model or provider.default_model or "").strip()
    if not use_model:
        raise ValueError("Missing model (set provider default_model or pass model)")

    payload: dict[str, Any] = {
        "model": use_model,
        "messages": messages,
        "temperature": float(temperature),
        "stream": False,
    }

    url = openai_compat_url(provider.base_url, "/chat/completions")
    headers = _auth_headers(provider.api_key)

    async def _do(c: httpx.AsyncClient) -> str:
        resp = await c.post(url, json=payload, headers=headers)
        if resp.status_code == 404 and provider.type == "ollama":
            # Older Ollama builds may not expose the OpenAI-compatible surface.
            native_url = f"{normalize_base_url(provider.base_url)}/api/chat"
            native_payload: dict[str, Any] = {
                "model": use_model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": float(temperature)},
            }
            native_headers = {"Content-Type": "application/json"}
            if provider.api_key:
                native_headers["Authorization"] = f"Bearer {provider.api_key}"
            native = await c.post(native_url, json=native_payload, headers=native_headers)
            native.raise_for_status()
            data = native.json()
            msg = data.get("message") if isinstance(data, dict) else None
            if isinstance(msg, dict) and isinstance(msg.get("content"), str):
                return msg["content"]
            if isinstance(data, dict) and isinstance(data.get("response"), str):
                return data["response"]
            raise ValueError("Unexpected Ollama /api/chat response shape")
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    if client is not None:
        return await _do(client)

    timeout = httpx.Timeout(timeout_sec, connect=min(10.0, timeout_sec))
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as c:
                return await _do(c)
        except Exception as exc:
            last_exc = exc
            if attempt >= retries:
                break
            log.warning("LLM chat attempt %s/%s failed: %s", attempt + 1, retries + 1, exc)
    assert last_exc is not None
    raise last_exc


async def list_openai_models(
    provider: LlmProviderConfig,
    *,
    timeout_sec: float = 10.0,
    client: httpx.AsyncClient | None = None,
) -> list[str]:
    url = openai_compat_url(provider.base_url, "/models")
    headers = {}
    if provider.api_key:
        headers["Authorization"] = f"Bearer {provider.api_key}"

    async def _do(c: httpx.AsyncClient) -> list[str]:
        resp = await c.get(url, headers=headers)
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        data = resp.json()
        items = data.get("data") if isinstance(data, dict) else None
        if not isinstance(items, list):
            return []
        out: list[str] = []
        for item in items:
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                out.append(item["id"])
        return out

    if client is not None:
        return await _do(client)

    timeout = httpx.Timeout(timeout_sec, connect=min(5.0, timeout_sec))
    async with httpx.AsyncClient(timeout=timeout) as c:
        return await _do(c)

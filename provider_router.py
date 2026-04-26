from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import httpx

log = logging.getLogger("llm-provider-router")


@dataclass(frozen=True)
class ProviderConfig:
    provider_id: str
    type: str
    base_url: str
    api_key: str | None = None
    default_model: str | None = None
    priority: int = 100
    headers: dict[str, str] = field(default_factory=dict)

    @property
    def normalized_base_url(self) -> str:
        return self.base_url.strip().rstrip("/")

    def auth_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", **self.headers}
        if self.api_key and "Authorization" not in headers and "x-api-key" not in {k.lower(): v for k, v in headers.items()}:
            if self.type == "anthropic":
                headers["x-api-key"] = self.api_key
                headers["anthropic-version"] = os.environ.get("ANTHROPIC_VERSION", "2023-06-01")
            else:
                headers["Authorization"] = f"Bearer {self.api_key}"
        return headers


@dataclass(frozen=True)
class ProviderAttempt:
    provider_id: str
    model: str
    status_code: int | None
    error: str | None = None
    latency_ms: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "model": self.model,
            "status_code": self.status_code,
            "error": self.error,
            "latency_ms": self.latency_ms,
        }


@dataclass(frozen=True)
class ProviderResult:
    response: httpx.Response
    provider: ProviderConfig
    model: str
    attempts: list[ProviderAttempt]


class ProviderFallbackError(RuntimeError):
    def __init__(self, attempts: list[ProviderAttempt]) -> None:
        self.attempts = attempts
        summary = "; ".join(
            f"{a.provider_id}/{a.model}: {a.status_code or a.error}" for a in attempts[-5:]
        ) or "no providers attempted"
        super().__init__(f"All configured LLM providers failed ({summary})")


def _openai_url(base_url: str, path: str) -> str:
    base = base_url.strip().rstrip("/")
    parsed = urlparse(base)
    if parsed.path and parsed.path != "/":
        return f"{base}{path}"
    return f"{base}/v1{path}"


def extract_openai_text(data: Any) -> str:
    if not isinstance(data, dict):
        return ""
    choices = data.get("choices") or []
    if not choices or not isinstance(choices[0], dict):
        return ""
    msg = choices[0].get("message") or {}
    if not isinstance(msg, dict):
        return ""
    content = msg.get("content") or msg.get("reasoning_content") or ""
    return content if isinstance(content, str) else ""


class ProviderRouter:
    """Priority-ordered LLM provider fallback with health checks and retries."""

    def __init__(self, providers: list[ProviderConfig]) -> None:
        seen: set[tuple[str, str]] = set()
        unique: list[ProviderConfig] = []
        for provider in sorted(providers, key=lambda p: p.priority):
            key = (provider.provider_id, provider.normalized_base_url)
            if provider.normalized_base_url and key not in seen:
                seen.add(key)
                unique.append(provider)
        self.providers = unique

    @classmethod
    def from_env(cls, primary_provider: ProviderConfig | None = None) -> "ProviderRouter":
        providers: list[ProviderConfig] = []
        if primary_provider:
            providers.append(primary_provider)
        else:
            providers.append(
                ProviderConfig(
                    provider_id="ollama-local",
                    type="ollama",
                    base_url=os.environ.get("OLLAMA_BASE") or os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434",
                    default_model=os.environ.get("OLLAMA_MODEL") or os.environ.get("AGENT_EXECUTOR_MODEL") or "qwen3-coder:30b",
                    priority=0,
                )
            )

        hf_key = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_API_TOKEN")
        if hf_key:
            providers.append(
                ProviderConfig(
                    provider_id="huggingface",
                    type="openai-compatible",
                    base_url=os.environ.get("HF_BASE_URL") or "https://api-inference.huggingface.co",
                    api_key=hf_key,
                    default_model=os.environ.get("HF_MODEL_ID") or "Qwen/Qwen2.5-Coder-7B-Instruct",
                    priority=20,
                )
            )

        openrouter_key = os.environ.get("OPENROUTER_API_KEY")
        if openrouter_key:
            providers.append(
                ProviderConfig(
                    provider_id="openrouter",
                    type="openai-compatible",
                    base_url=os.environ.get("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1",
                    api_key=openrouter_key,
                    default_model=os.environ.get("OPENROUTER_MODEL") or "qwen/qwen3-235b-a22b",
                    priority=30,
                )
            )

        deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
        if deepseek_key:
            providers.append(
                ProviderConfig(
                    provider_id="deepseek",
                    type="openai-compatible",
                    base_url=os.environ.get("DEEPSEEK_BASE_URL") or "https://api.deepseek.com",
                    api_key=deepseek_key,
                    default_model=os.environ.get("DEEPSEEK_MODEL") or "deepseek-chat",
                    priority=40,
                )
            )

        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        if anthropic_key:
            providers.append(
                ProviderConfig(
                    provider_id="anthropic",
                    type="anthropic",
                    base_url=os.environ.get("ANTHROPIC_BASE_URL") or "https://api.anthropic.com",
                    api_key=anthropic_key,
                    default_model=os.environ.get("ANTHROPIC_MODEL") or "claude-sonnet-4-5",
                    priority=50,
                )
            )

        return cls(providers)

    async def health_check(self, provider: ProviderConfig) -> bool:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
                if provider.type == "ollama":
                    resp = await client.get(f"{provider.normalized_base_url}/api/tags")
                elif provider.type == "anthropic":
                    resp = await client.get(
                        f"{provider.normalized_base_url}/v1/models",
                        headers=provider.auth_headers(),
                    )
                else:
                    resp = await client.get(_openai_url(provider.normalized_base_url, "/models"), headers=provider.auth_headers())
            return resp.status_code < 500 and resp.status_code not in (401, 403)
        except Exception as exc:
            log.debug("Provider health check failed for %s: %s", provider.provider_id, exc)
            return False

    async def chat_completion(
        self,
        payload: dict[str, Any],
        *,
        model_fallbacks: list[str] | None = None,
        max_retries: int = 2,
    ) -> ProviderResult:
        attempts: list[ProviderAttempt] = []
        if not self.providers:
            raise ProviderFallbackError(attempts)

        original_model = str(payload.get("model") or "").strip()
        for provider_index, provider in enumerate(self.providers):
            candidate_models = self._candidate_models(provider, original_model, model_fallbacks or [], provider_index == 0)
            for model in candidate_models:
                provider_payload = dict(payload)
                provider_payload["model"] = model
                provider_payload["stream"] = False
                for attempt_number in range(max_retries + 1):
                    started = time.perf_counter()
                    try:
                        response = await self._post_chat(provider, provider_payload)
                        latency_ms = int((time.perf_counter() - started) * 1000)
                        attempts.append(ProviderAttempt(provider.provider_id, model, response.status_code, latency_ms=latency_ms))
                        if self._is_success(response):
                            return ProviderResult(response=response, provider=provider, model=model, attempts=attempts)
                        if not self._should_retry_status(response.status_code):
                            break
                    except Exception as exc:
                        latency_ms = int((time.perf_counter() - started) * 1000)
                        attempts.append(ProviderAttempt(provider.provider_id, model, None, error=str(exc), latency_ms=latency_ms))
                    if attempt_number < max_retries:
                        await asyncio.sleep(min(0.25 * (2**attempt_number), 2.0))
        raise ProviderFallbackError(attempts)

    def _candidate_models(
        self,
        provider: ProviderConfig,
        original_model: str,
        model_fallbacks: list[str],
        is_primary: bool,
    ) -> list[str]:
        values: list[str] = []
        if is_primary and original_model:
            values.append(original_model)
            values.extend(model_fallbacks)
        if provider.default_model:
            values.append(provider.default_model)
        if not values and original_model:
            values.append(original_model)
        deduped: list[str] = []
        for value in values:
            if value and value not in deduped:
                deduped.append(value)
        return deduped

    async def _post_chat(self, provider: ProviderConfig, payload: dict[str, Any]) -> httpx.Response:
        headers = provider.auth_headers()
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
            if provider.type == "anthropic":
                response = await client.post(
                    f"{provider.normalized_base_url}/v1/messages",
                    json=self._anthropic_payload(payload),
                    headers=headers,
                )
                if response.status_code >= 400:
                    return response
                return self._anthropic_to_openai_response(response, str(payload.get("model") or ""))
            url = _openai_url(provider.normalized_base_url, "/chat/completions")
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code == 404 and provider.type == "ollama":
                native = await client.post(
                    f"{provider.normalized_base_url}/api/chat",
                    json={
                        "model": payload.get("model"),
                        "messages": payload.get("messages") or [],
                        "stream": False,
                        "options": {"temperature": payload.get("temperature", 0.3)},
                    },
                    headers={"Content-Type": "application/json"},
                )
                if native.status_code < 400:
                    return self._ollama_native_to_openai_response(native, str(payload.get("model") or ""))
            return response

    @staticmethod
    def _is_success(response: httpx.Response) -> bool:
        return 200 <= response.status_code < 300

    @staticmethod
    def _should_retry_status(status_code: int) -> bool:
        return status_code in (404, 408, 409, 425, 429) or status_code >= 500

    @staticmethod
    def _anthropic_payload(payload: dict[str, Any]) -> dict[str, Any]:
        system_parts: list[str] = []
        messages: list[dict[str, str]] = []
        for msg in payload.get("messages") or []:
            if not isinstance(msg, dict):
                continue
            role = msg.get("role")
            content = msg.get("content")
            if not isinstance(content, str):
                continue
            if role == "system":
                system_parts.append(content)
            elif role in ("user", "assistant"):
                messages.append({"role": role, "content": content})
        return {
            "model": payload.get("model"),
            "messages": messages or [{"role": "user", "content": ""}],
            "system": "\n\n".join(system_parts) if system_parts else None,
            "max_tokens": int(payload.get("max_tokens") or 1024),
            "temperature": float(payload.get("temperature") or 0.3),
        }

    @staticmethod
    def _anthropic_to_openai_response(response: httpx.Response, model: str) -> httpx.Response:
        data = response.json()
        content = "".join(
            block.get("text", "") for block in data.get("content", []) if isinstance(block, dict)
        )
        usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
        body = {
            "id": data.get("id") or "chatcmpl-anthropic-fallback",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
            "usage": {
                "prompt_tokens": int(usage.get("input_tokens") or 0),
                "completion_tokens": int(usage.get("output_tokens") or 0),
                "total_tokens": int(usage.get("input_tokens") or 0) + int(usage.get("output_tokens") or 0),
            },
        }
        return httpx.Response(200, json=body, headers={"content-type": "application/json"})

    @staticmethod
    def _ollama_native_to_openai_response(response: httpx.Response, model: str) -> httpx.Response:
        data = response.json()
        msg = data.get("message") if isinstance(data, dict) else None
        content = msg.get("content", "") if isinstance(msg, dict) else data.get("response", "")
        body = {
            "id": "chatcmpl-ollama-native-fallback",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
            "usage": {
                "prompt_tokens": int(data.get("prompt_eval_count") or 0),
                "completion_tokens": int(data.get("eval_count") or 0),
                "total_tokens": int(data.get("prompt_eval_count") or 0) + int(data.get("eval_count") or 0),
            },
        }
        return httpx.Response(200, json=body, headers={"content-type": "application/json"})

    @staticmethod
    def attempts_header(attempts: list[ProviderAttempt]) -> str:
        compact = [a.as_dict() for a in attempts[-8:]]
        return json.dumps(compact, separators=(",", ":"))
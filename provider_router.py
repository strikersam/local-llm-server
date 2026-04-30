from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import httpx

log = logging.getLogger("llm-provider-router")

# ── Cross-request provider cooldowns ──────────────────────────────────────────
# These are module-level so cooldown state persists across ProviderRouter
# instances within the same process.
_provider_cooldowns: dict[str, float] = {}
_DEFAULT_COOLDOWN_SECONDS: int = int(os.environ.get("PROVIDER_COOLDOWN_SECONDS", "60"))


def mark_provider_failed(provider_id: str, cooldown_seconds: int | None = None) -> None:
    """Put provider_id on cooldown for *cooldown_seconds* (default: PROVIDER_COOLDOWN_SECONDS)."""
    secs = (
        cooldown_seconds if cooldown_seconds is not None else _DEFAULT_COOLDOWN_SECONDS
    )
    _provider_cooldowns[provider_id] = time.time() + secs
    log.warning("Provider %s placed on cooldown for %ds", provider_id, secs)


def is_provider_on_cooldown(provider_id: str) -> bool:
    """Return True if provider_id is currently on cooldown."""
    until = _provider_cooldowns.get(provider_id)
    if until is None:
        return False
    if time.time() >= until:
        _provider_cooldowns.pop(provider_id, None)
        return False
    return True


def get_cooldown_state() -> dict[str, float]:
    """Return a snapshot of active cooldowns {provider_id: expiry_unix_timestamp}."""
    now = time.time()
    return {
        pid: until for pid, until in list(_provider_cooldowns.items()) if until > now
    }


def clear_cooldowns() -> None:
    """Clear all cooldown entries (useful for testing)."""
    _provider_cooldowns.clear()


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
        lower_header_names = {k.lower() for k in headers}
        if (
            self.api_key
            and "authorization" not in lower_header_names
            and "x-api-key" not in lower_header_names
        ):
            if self.type == "anthropic":
                headers["x-api-key"] = self.api_key
                headers["anthropic-version"] = os.environ.get(
                    "ANTHROPIC_VERSION", "2023-06-01"
                )
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
        summary = (
            "; ".join(
                f"{a.provider_id}/{a.model}: {a.status_code or a.error}"
                for a in attempts[-5:]
            )
            or "no providers attempted"
        )
        super().__init__(f"All configured LLM providers failed ({summary})")


class CommercialFallbackRequiredError(RuntimeError):
    def __init__(self, candidates: list[str]) -> None:
        self.candidates = candidates
        summary = ", ".join(candidates[:5]) or "commercial provider"
        super().__init__(
            "Commercial fallback requires user approval before switching providers "
            f"({summary})."
        )


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


_COMMERCIAL_PROVIDER_IDS = {
    "anthropic",
    "anthropic-universal",
    "openai",
    "openrouter",
    "together-ai",
    "zhipu",
    "dashscope",
    "minimax",
    "google-gemini",
    "moonshot",
}
_FREE_CLOUD_PROVIDER_IDS = {
    "huggingface-serverless",
    "huggingface",
    "deepseek",
}
# Nvidia NIM is free-tier — treated as highest-priority free cloud provider
_NVIDIA_PROVIDER_IDS = {"nvidia-nim", "nvidia"}
_KNOWN_COMMERCIAL_HOSTS = (
    "anthropic.com",
    "openai.com",
    "openrouter.ai",
    "together.xyz",
    "bigmodel.cn",
    "aliyuncs.com",
    "minimax.chat",
    "googleapis.com",
    "moonshot.cn",
)
_KNOWN_FREE_HOSTS = (
    "huggingface.co",
    "hf.space",
    "deepseek.com",
)
_KNOWN_NVIDIA_HOSTS = ("integrate.api.nvidia.com",)


def _provider_field(
    provider: ProviderConfig | dict[str, Any], field_name: str, default: Any = ""
) -> Any:
    if isinstance(provider, dict):
        return provider.get(field_name, default)
    return getattr(provider, field_name, default)


def provider_access_tier(provider: ProviderConfig | dict[str, Any]) -> str:
    provider_id = (
        str(_provider_field(provider, "provider_id", "") or "").strip().lower()
    )
    provider_type = str(_provider_field(provider, "type", "") or "").strip().lower()
    base_url = str(_provider_field(provider, "base_url", "") or "").strip().lower()
    hostname = (urlparse(base_url).hostname or "").lower()
    name = str(_provider_field(provider, "name", "") or "").strip().lower()

    if provider_id in _NVIDIA_PROVIDER_IDS or any(
        host in hostname for host in _KNOWN_NVIDIA_HOSTS
    ):
        return "nvidia_nim"
    if provider_id in _COMMERCIAL_PROVIDER_IDS or any(
        host in hostname for host in _KNOWN_COMMERCIAL_HOSTS
    ):
        return "commercial"
    if provider_type.startswith("emergent-"):
        return "commercial"
    if provider_id in _FREE_CLOUD_PROVIDER_IDS or any(
        host in hostname for host in _KNOWN_FREE_HOSTS
    ):
        return "free_cloud"
    if provider_type == "anthropic":
        return "commercial"
    if provider_type == "ollama" and hostname in {
        "localhost",
        "127.0.0.1",
        "ollama",
        "host.docker.internal",
        "::1",
    }:
        return "local"
    if (
        hostname.startswith("192.168.")
        or hostname.startswith("10.")
        or hostname.startswith("172.")
    ):
        return "windows_server"
    if any(token in hostname for token in ("ngrok", "cloudflare", "trycloudflare")):
        return "windows_server"
    if any(token in name for token in ("windows", "remote", "server")):
        return "windows_server"
    if provider_type == "ollama":
        return "windows_server"
    if provider_type == "huggingface":
        return "free_cloud"
    return "windows_server"


def is_commercial_provider(provider: ProviderConfig | dict[str, Any]) -> bool:
    return provider_access_tier(provider) == "commercial"


def provider_sort_key(
    provider: ProviderConfig | dict[str, Any],
) -> tuple[int, int, str]:
    tier_order = {
        # Nvidia NIM comes first — free, no local infra needed
        "nvidia_nim": 0,
        # Local Ollama is second preference when available
        "local": 1,
        "windows_server": 2,
        "free_cloud": 3,
        "commercial": 4,
    }
    priority = int(_provider_field(provider, "priority", 100) or 100)
    provider_id = str(_provider_field(provider, "provider_id", "") or "")
    return (tier_order.get(provider_access_tier(provider), 99), priority, provider_id)


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
    def from_env(
        cls, primary_provider: ProviderConfig | None = None
    ) -> "ProviderRouter":
        providers: list[ProviderConfig] = []

        # ── Nvidia NIM — highest priority, always added when key is present ──
        nvidia_key = (
            os.environ.get("NVIDIA_API_KEY")
            or os.environ.get("NVidiaApiKey")
            or ""
        ).strip()
        if nvidia_key:
            nvidia_base = (
                os.environ.get("NVIDIA_BASE_URL") or "https://integrate.api.nvidia.com/v1"
            ).rstrip("/")
            providers.append(
                ProviderConfig(
                    provider_id="nvidia-nim",
                    type="openai-compatible",
                    base_url=nvidia_base,
                    api_key=nvidia_key,
                    default_model=(
                        os.environ.get("NVIDIA_DEFAULT_MODEL")
                        or "meta/llama-3.3-70b-instruct"
                    ),
                    priority=-10,  # before everything else
                )
            )

        if primary_provider:
            providers.append(primary_provider)
        else:
            providers.append(
                ProviderConfig(
                    provider_id="ollama-local",
                    type="ollama",
                    base_url=os.environ.get("OLLAMA_BASE")
                    or os.environ.get("OLLAMA_BASE_URL")
                    or "http://localhost:11434",
                    default_model=os.environ.get("OLLAMA_MODEL")
                    or os.environ.get("AGENT_EXECUTOR_MODEL")
                    or "qwen3-coder:30b",
                    priority=10,
                )
            )

        windows_base = (
            (os.environ.get("OLLAMA_WINDOWS_SERVER") or "").strip().rstrip("/")
        )
        if windows_base:
            providers.append(
                ProviderConfig(
                    provider_id="ollama-windows-server",
                    type="ollama",
                    base_url=windows_base,
                    default_model=(
                        os.environ.get("OLLAMA_WINDOWS_MODEL")
                        or os.environ.get("OLLAMA_MODEL")
                        or "llama3.2"
                    ),
                    priority=5,
                )
            )

        hf_key = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_API_TOKEN")
        hf_base = os.environ.get("HF_BASE_URL")
        if hf_key and hf_base:
            providers.append(
                ProviderConfig(
                    provider_id="huggingface",
                    type="openai-compatible",
                    base_url=hf_base,
                    api_key=hf_key,
                    default_model=os.environ.get("HF_MODEL_ID")
                    or "Qwen/Qwen2.5-Coder-7B-Instruct",
                    priority=20,
                )
            )

        openrouter_key = os.environ.get("OPENROUTER_API_KEY")
        openrouter_base = os.environ.get("OPENROUTER_BASE_URL")
        if openrouter_key and openrouter_base:
            providers.append(
                ProviderConfig(
                    provider_id="openrouter",
                    type="openai-compatible",
                    base_url=openrouter_base,
                    api_key=openrouter_key,
                    default_model=os.environ.get("OPENROUTER_MODEL")
                    or "qwen/qwen3-235b-a22b",
                    priority=30,
                )
            )

        deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
        deepseek_base = os.environ.get("DEEPSEEK_BASE_URL")
        if deepseek_key and deepseek_base:
            providers.append(
                ProviderConfig(
                    provider_id="deepseek",
                    type="openai-compatible",
                    base_url=deepseek_base,
                    api_key=deepseek_key,
                    default_model=os.environ.get("DEEPSEEK_MODEL") or "deepseek-chat",
                    priority=40,
                )
            )

        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        anthropic_base = os.environ.get("ANTHROPIC_BASE_URL")
        if anthropic_key and anthropic_base:
            providers.append(
                ProviderConfig(
                    provider_id="anthropic",
                    type="anthropic",
                    base_url=anthropic_base,
                    api_key=anthropic_key,
                    default_model=os.environ.get("ANTHROPIC_MODEL")
                    or "claude-sonnet-4-5",
                    priority=50,
                )
            )

        emergent_key = os.environ.get("EMERGENT_LLM_KEY")
        if emergent_key:
            providers.append(
                ProviderConfig(
                    provider_id="anthropic-universal",
                    type="emergent-anthropic",
                    base_url="emergent://anthropic",
                    api_key=emergent_key,
                    default_model=os.environ.get("EMERGENT_ANTHROPIC_MODEL")
                    or "claude-sonnet-4-5-20250929",
                    priority=60,
                )
            )

        return cls(sorted(providers, key=provider_sort_key))

    @classmethod
    def from_provider_records(
        cls,
        provider_records: list[dict[str, Any]],
        *,
        primary_provider_id: str | None = None,
        include_commercial: bool = True,
    ) -> "ProviderRouter":
        providers: list[ProviderConfig] = []
        selected: ProviderConfig | None = None

        for record in provider_records:
            base_url = str(record.get("base_url") or "").strip()
            provider_id = str(record.get("provider_id") or "").strip()
            if not provider_id or not base_url:
                continue
            if not include_commercial and is_commercial_provider(record):
                continue
            cfg = ProviderConfig(
                provider_id=provider_id,
                type=str(record.get("type") or "openai-compatible").strip(),
                base_url=base_url,
                api_key=(str(record.get("api_key") or "").strip() or None),
                default_model=(str(record.get("default_model") or "").strip() or None),
                priority=int(record.get("priority") or 100),
                headers=dict(record.get("headers") or {}),
            )
            if primary_provider_id and provider_id == primary_provider_id:
                selected = cfg
            else:
                providers.append(cfg)

        providers = sorted(providers, key=provider_sort_key)
        if selected is not None:
            providers = [selected, *providers]
        return cls(providers)

    async def health_check(self, provider: ProviderConfig) -> bool:
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(10.0, connect=5.0)
            ) as client:
                if provider.type.startswith("emergent-"):
                    return bool(provider.api_key)
                if provider.type == "ollama":
                    resp = await client.get(f"{provider.normalized_base_url}/api/tags")
                elif provider.type == "anthropic":
                    resp = await client.get(
                        f"{provider.normalized_base_url}/v1/models",
                        headers=provider.auth_headers(),
                    )
                else:
                    resp = await client.get(
                        _openai_url(provider.normalized_base_url, "/models"),
                        headers=provider.auth_headers(),
                    )
            return resp.status_code < 500 and resp.status_code not in (401, 403)
        except Exception as exc:
            log.debug(
                "Provider health check failed for %s: %s", provider.provider_id, exc
            )
            return False

    async def chat_completion(
        self,
        payload: dict[str, Any],
        *,
        model_fallbacks: list[str] | None = None,
        max_retries: int = 2,
        allow_commercial_fallback: bool = True,
    ) -> ProviderResult:
        attempts: list[ProviderAttempt] = []
        deferred_commercial: list[str] = []
        if not self.providers:
            raise ProviderFallbackError(attempts)

        original_model = str(payload.get("model") or "").strip()
        for provider_index, provider in enumerate(self.providers):
            # Skip providers that are currently on cooldown
            if is_provider_on_cooldown(provider.provider_id):
                log.info(
                    "Skipping provider %s (on cooldown, expires %.0fs from now)",
                    provider.provider_id,
                    _provider_cooldowns.get(provider.provider_id, 0) - time.time(),
                )
                continue
            if (
                provider_index > 0
                and is_commercial_provider(provider)
                and not allow_commercial_fallback
            ):
                deferred_commercial.append(provider.provider_id)
                continue
            candidate_models = self._candidate_models(
                provider, original_model, model_fallbacks or [], provider_index == 0
            )
            for model in candidate_models:
                provider_payload = dict(payload)
                provider_payload["model"] = model
                provider_payload["stream"] = False
                for attempt_number in range(max_retries + 1):
                    started = time.perf_counter()
                    try:
                        response = await self._post_chat(provider, provider_payload)
                        latency_ms = int((time.perf_counter() - started) * 1000)
                        attempts.append(
                            ProviderAttempt(
                                provider.provider_id,
                                model,
                                response.status_code,
                                latency_ms=latency_ms,
                            )
                        )
                        if self._is_success(response):
                            return ProviderResult(
                                response=response,
                                provider=provider,
                                model=model,
                                attempts=attempts,
                            )
                        if not self._should_retry_status(response.status_code):
                            break
                    except Exception as exc:
                        latency_ms = int((time.perf_counter() - started) * 1000)
                        attempts.append(
                            ProviderAttempt(
                                provider.provider_id,
                                model,
                                None,
                                error=str(exc),
                                latency_ms=latency_ms,
                            )
                        )
                    if attempt_number < max_retries:
                        await asyncio.sleep(min(0.25 * (2**attempt_number), 2.0))
            # All models for this provider exhausted — put it on cooldown
            mark_provider_failed(provider.provider_id)
        if deferred_commercial and not attempts:
            raise CommercialFallbackRequiredError(deferred_commercial)
        if deferred_commercial:
            raise CommercialFallbackRequiredError(deferred_commercial)
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

    async def _post_chat(
        self, provider: ProviderConfig, payload: dict[str, Any]
    ) -> httpx.Response:
        headers = provider.auth_headers()
        if provider.type.startswith("emergent-"):
            return await self._post_emergent_chat(provider, payload)
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(300.0, connect=10.0)
        ) as client:
            if provider.type == "anthropic":
                response = await client.post(
                    f"{provider.normalized_base_url}/v1/messages",
                    json=self._anthropic_payload(payload),
                    headers=headers,
                )
                if response.status_code >= 400:
                    return response
                return self._anthropic_to_openai_response(
                    response, str(payload.get("model") or "")
                )
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
                    return self._ollama_native_to_openai_response(
                        native, str(payload.get("model") or "")
                    )
            return response

    async def _post_emergent_chat(
        self, provider: ProviderConfig, payload: dict[str, Any]
    ) -> httpx.Response:
        from emergentintegrations.llm.chat import LlmChat, UserMessage

        provider_name = provider.type.replace("emergent-", "", 1)
        session_id = f"{provider.provider_id}-{uuid.uuid4().hex}"
        messages = payload.get("messages") or []
        system_message, user_text = self._emergent_prompt(messages)
        chat = LlmChat(
            api_key=provider.api_key or "",
            session_id=session_id,
            system_message=system_message,
        ).with_model(
            provider_name, str(payload.get("model") or provider.default_model or "")
        )
        response_text = await chat.send_message(UserMessage(text=user_text))
        return httpx.Response(
            200,
            json={
                "id": f"chatcmpl-{uuid.uuid4().hex}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": str(payload.get("model") or provider.default_model or ""),
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": str(response_text)},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                },
            },
        )

    def _emergent_prompt(self, messages: list[dict[str, Any]]) -> tuple[str, str]:
        system_parts: list[str] = []
        transcript: list[str] = []
        for message in messages:
            role = str(message.get("role") or "user")
            content = self._message_content_text(message.get("content"))
            if not content:
                continue
            if role == "system":
                system_parts.append(content)
            else:
                transcript.append(f"{role.upper()}: {content}")

        system_message = "\n\n".join(system_parts) or "You are a helpful assistant."
        user_text = "\n\n".join(transcript) or "USER: Hello"
        return system_message, user_text

    def _message_content_text(self, content: Any) -> str:
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text") or item.get("content") or ""
                    if isinstance(text, str) and text.strip():
                        parts.append(text.strip())
            return "\n".join(parts).strip()
        return ""

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
    def _anthropic_to_openai_response(
        response: httpx.Response, model: str
    ) -> httpx.Response:
        data = response.json()
        content = "".join(
            block.get("text", "")
            for block in data.get("content", [])
            if isinstance(block, dict)
        )
        usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
        body = {
            "id": data.get("id") or "chatcmpl-anthropic-fallback",
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
            "usage": {
                "prompt_tokens": int(usage.get("input_tokens") or 0),
                "completion_tokens": int(usage.get("output_tokens") or 0),
                "total_tokens": int(usage.get("input_tokens") or 0)
                + int(usage.get("output_tokens") or 0),
            },
        }
        return httpx.Response(
            200, json=body, headers={"content-type": "application/json"}
        )

    @staticmethod
    def _ollama_native_to_openai_response(
        response: httpx.Response, model: str
    ) -> httpx.Response:
        data = response.json()
        msg = data.get("message") if isinstance(data, dict) else None
        content = (
            msg.get("content", "")
            if isinstance(msg, dict)
            else data.get("response", "")
        )
        body = {
            "id": "chatcmpl-ollama-native-fallback",
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
            "usage": {
                "prompt_tokens": int(data.get("prompt_eval_count") or 0),
                "completion_tokens": int(data.get("eval_count") or 0),
                "total_tokens": int(data.get("prompt_eval_count") or 0)
                + int(data.get("eval_count") or 0),
            },
        }
        return httpx.Response(
            200, json=body, headers={"content-type": "application/json"}
        )

    @staticmethod
    def attempts_header(attempts: list[ProviderAttempt]) -> str:
        compact = [a.as_dict() for a in attempts[-8:]]
        return json.dumps(compact, separators=(",", ":"))

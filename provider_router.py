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
_DEFAULT_COOLDOWN_SECONDS: int = int(os.environ.get("PROVIDER_COOLDOWN_SECONDS", "30"))
_AUTH_FAILURE_COOLDOWN_SECONDS: int = 300  # bad API key — don't retry for 5 min
_CONN_FAILURE_COOLDOWN_SECONDS: int = 15  # network hiccup — retry sooner


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
    "bedrock",
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
    "groq",
    "groq-cloud",
    "qwen-dashscope",
    "together-free",
    "cerebras",
    "sambanova",
    "mistral",
    "google-gemini-free",
    "cloudflare-ai",
    "opencode-zen",
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
    "api.groq.com",
    "dashscope.aliyuncs.com",
    "api.cerebras.ai",
    "api.sambanova.ai",
    "api.mistral.ai",
    "generativelanguage.googleapis.com",
    "api.cloudflare.com",
)
_KNOWN_NVIDIA_HOSTS = ("integrate.api.nvidia.com",)

# Prefixes that identify AWS Bedrock model IDs / inference profile IDs.
# Requests using these model IDs are routed exclusively to the bedrock provider
# so that other providers (e.g. Nvidia NIM) cannot intercept or fallback-serve them.
_BEDROCK_MODEL_PREFIXES = (
    "us.anthropic.",
    "eu.anthropic.",
    "ap.anthropic.",
    "global.anthropic.",
    "arn:aws:bedrock:",
    "anthropic.claude-",  # direct Bedrock foundation model IDs
)


def _is_bedrock_model_id(model_id: str) -> bool:
    """Return True if model_id is an AWS Bedrock model or inference profile ID."""
    return any(model_id.startswith(p) for p in _BEDROCK_MODEL_PREFIXES)


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
                os.environ.get("NVIDIA_BASE_URL") or "https://integrate.api.nvidia.com"
            ).rstrip("/")
            providers.append(
                ProviderConfig(
                    provider_id="nvidia-nim",
                    type="openai-compatible",
                    base_url=nvidia_base,
                    api_key=nvidia_key,
                    default_model=(
                        os.environ.get("NVIDIA_DEFAULT_MODEL")
                        or "nvidia/nemotron-3-super-120b-a12b"
                    ),
                    priority=-10,  # before everything else
                )
            )

        if primary_provider:
            providers.append(primary_provider)
        else:
            # Include Ollama as a fallback only if explicitly opted in via settings
            include_local_fallback = os.environ.get("INCLUDE_LOCAL_FALLBACK", "false").lower() == "true"
            if include_local_fallback:
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
                        priority=0,  # local Ollama beats windows-server (5) and cloud fallbacks
                    )
                )
        # If we have NVIDIA key and not including local fallback, we skip Ollama

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
        if hf_key:
            hf_base = (
                os.environ.get("HF_BASE_URL") or "https://api-inference.huggingface.co/v1"
            ).rstrip("/")
            providers.append(
                ProviderConfig(
                    provider_id="huggingface",
                    type="openai-compatible",
                    base_url=hf_base,
                    api_key=hf_key,
                    default_model=os.environ.get("HF_MODEL_ID")
                    or "Qwen/Qwen2.5-Coder-7B-Instruct",
                    priority=45,
                )
            )

        zhipu_key = os.environ.get("ZHIPU_API_KEY")
        if zhipu_key:
            providers.append(
                ProviderConfig(
                    provider_id="zhipu",
                    type="openai-compatible",
                    base_url="https://open.bigmodel.cn/api/paas/v4",
                    api_key=zhipu_key,
                    default_model=os.environ.get("ZHIPU_MODEL") or "glm-4-flash",
                    priority=46,
                )
            )

        minimax_key = os.environ.get("MINIMAX_API_KEY")
        if minimax_key:
            minimax_group = os.environ.get("MINIMAX_GROUP_ID", "")
            providers.append(
                ProviderConfig(
                    provider_id="minimax",
                    type="openai-compatible",
                    base_url="https://api.minimax.chat/v1",
                    api_key=minimax_key,
                    default_model=os.environ.get("MINIMAX_MODEL") or "MiniMax-Text-01",
                    priority=47,
                    headers={"GroupId": minimax_group} if minimax_group else {},
                )
            )

        openrouter_key = os.environ.get("OPENROUTER_API_KEY")
        if openrouter_key:
            openrouter_base = (
                os.environ.get("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1"
            ).rstrip("/")
            providers.append(
                ProviderConfig(
                    provider_id="openrouter",
                    type="openai-compatible",
                    base_url=openrouter_base,
                    api_key=openrouter_key,
                    default_model=os.environ.get("OPENROUTER_MODEL")
                    or "qwen/qwen3-235b-a22b:free",
                    priority=40,
                )
            )

        deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
        if deepseek_key:
            deepseek_base = (
                os.environ.get("DEEPSEEK_BASE_URL") or "https://api.deepseek.com"
            ).rstrip("/")
            providers.append(
                ProviderConfig(
                    provider_id="deepseek",
                    type="openai-compatible",
                    base_url=deepseek_base,
                    api_key=deepseek_key,
                    default_model=os.environ.get("DEEPSEEK_MODEL") or "deepseek-chat",
                    priority=20,
                )
            )

        groq_key = os.environ.get("GROQ_API_KEY")
        if groq_key:
            providers.append(
                ProviderConfig(
                    provider_id="groq",
                    type="openai-compatible",
                    base_url="https://api.groq.com/openai/v1",
                    api_key=groq_key,
                    default_model=os.environ.get("GROQ_MODEL") or "llama-3.3-70b-versatile",
                    priority=25,
                )
            )

        qwen_key = os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("QWEN_API_KEY")
        if qwen_key:
            qwen_base = (
                os.environ.get("DASHSCOPE_BASE_URL")
                or "https://dashscope.aliyuncs.com/compatible-mode/v1"
            ).rstrip("/")
            providers.append(
                ProviderConfig(
                    provider_id="qwen-dashscope",
                    type="openai-compatible",
                    base_url=qwen_base,
                    api_key=qwen_key,
                    default_model=os.environ.get("QWEN_MODEL") or "qwen-plus",
                    priority=30,
                )
            )

        cerebras_key = os.environ.get("CEREBRAS_API_KEY")
        if cerebras_key:
            providers.append(
                ProviderConfig(
                    provider_id="cerebras",
                    type="openai-compatible",
                    base_url="https://api.cerebras.ai/v1",
                    api_key=cerebras_key,
                    default_model=os.environ.get("CEREBRAS_MODEL") or "llama-3.3-70b",
                    priority=28,
                )
            )

        sambanova_key = os.environ.get("SAMBANOVA_API_KEY")
        if sambanova_key:
            providers.append(
                ProviderConfig(
                    provider_id="sambanova",
                    type="openai-compatible",
                    base_url="https://api.sambanova.ai/v1",
                    api_key=sambanova_key,
                    default_model=os.environ.get("SAMBANOVA_MODEL") or "Meta-Llama-3.3-70B-Instruct",
                    priority=27,
                )
            )

        together_key = os.environ.get("TOGETHER_API_KEY")
        if together_key:
            together_base = (
                os.environ.get("TOGETHER_BASE_URL") or "https://api.together.xyz/v1"
            ).rstrip("/")
            providers.append(
                ProviderConfig(
                    provider_id="together-free",
                    type="openai-compatible",
                    base_url=together_base,
                    api_key=together_key,
                    default_model=os.environ.get("TOGETHER_MODEL") or "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
                    priority=35,
                )
            )

        mistral_key = os.environ.get("MISTRAL_API_KEY")
        if mistral_key:
            providers.append(
                ProviderConfig(
                    provider_id="mistral",
                    type="openai-compatible",
                    base_url="https://api.mistral.ai/v1",
                    api_key=mistral_key,
                    default_model=os.environ.get("MISTRAL_MODEL") or "mistral-small-latest",
                    priority=38,
                )
            )

        gemini_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            providers.append(
                ProviderConfig(
                    provider_id="google-gemini-free",
                    type="openai-compatible",
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai",
                    api_key=gemini_key,
                    default_model=os.environ.get("GEMINI_MODEL") or "gemini-2.0-flash",
                    priority=39,
                )
            )

        cloudflare_token = os.environ.get("CLOUDFLARE_API_TOKEN")
        cloudflare_account = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
        if cloudflare_token and cloudflare_account:
            providers.append(
                ProviderConfig(
                    provider_id="cloudflare-ai",
                    type="openai-compatible",
                    base_url=f"https://api.cloudflare.com/client/v4/accounts/{cloudflare_account}/ai/v1",
                    api_key=cloudflare_token,
                    default_model=os.environ.get("CLOUDFLARE_MODEL") or "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
                    priority=43,
                )
            )

        zen_key = os.environ.get("OPENCODE_ZEN_API_KEY")
        if zen_key:
            zen_base = (
                os.environ.get("OPENCODE_ZEN_BASE_URL") or "https://gateway.opencode.ai/v1"
            ).rstrip("/")
            providers.append(
                ProviderConfig(
                    provider_id="opencode-zen",
                    type="openai-compatible",
                    base_url=zen_base,
                    api_key=zen_key,
                    default_model=os.environ.get("OPENCODE_ZEN_MODEL") or "zen",
                    priority=5,
                )
            )

        aws_access_key = (
            os.environ.get("AWS_ACCESS_KEY_ID") or os.environ.get("BEDROCK_ACCESS_KEY") or ""
        ).strip()
        aws_secret_key = (
            os.environ.get("AWS_SECRET_ACCESS_KEY") or os.environ.get("BEDROCK_SECRET_KEY") or ""
        ).strip()
        if aws_access_key and aws_secret_key:
            aws_region = (
                os.environ.get("AWS_REGION")
                or os.environ.get("AWS_DEFAULT_REGION")
                or "us-east-1"
            )
            bedrock_model = (
                os.environ.get("BEDROCK_MODEL_ID") or "us.anthropic.claude-opus-4-6-v1"
            )
            providers.append(
                ProviderConfig(
                    provider_id="bedrock",
                    type="bedrock",
                    base_url=f"https://bedrock-runtime.{aws_region}.amazonaws.com",
                    api_key=aws_access_key,
                    default_model=bedrock_model,
                    priority=15,
                    headers={
                        "X-Bedrock-Secret": aws_secret_key,
                        "X-Bedrock-Region": aws_region,
                    },
                )
            )

        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        if anthropic_key:
            anthropic_base = (
                os.environ.get("ANTHROPIC_BASE_URL") or "https://api.anthropic.com"
            ).rstrip("/")
            providers.append(
                ProviderConfig(
                    provider_id="anthropic",
                    type="anthropic",
                    base_url=anthropic_base,
                    api_key=anthropic_key,
                    default_model=os.environ.get("ANTHROPIC_MODEL")
                    or "claude-sonnet-4-6",
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
            if provider.type == "bedrock":
                return bool(provider.api_key and provider.headers.get("X-Bedrock-Secret"))
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

    async def _try_one_provider(
        self,
        provider: ProviderConfig,
        payload: dict[str, Any],
        original_model: str,
        model_fallbacks: list[str],
        is_primary: bool,
        max_retries: int,
        attempts: list[ProviderAttempt],
        provider_timeout_sec: float,
    ) -> ProviderResult | None:
        """Try all models for one provider. Returns ProviderResult on success, None on failure.

        Records attempts in-place and applies a failure-type-aware cooldown on exhaustion.
        """
        last_status: int | None = None
        last_was_conn_error = False
        for model in self._candidate_models(provider, original_model, model_fallbacks, is_primary):
            provider_payload = {**payload, "model": model, "stream": False}
            for attempt_number in range(max_retries + 1):
                started = time.perf_counter()
                try:
                    response = await self._post_chat(
                        provider, provider_payload, provider_timeout_sec
                    )
                    latency_ms = int((time.perf_counter() - started) * 1000)
                    attempts.append(ProviderAttempt(
                        provider.provider_id, model, response.status_code, latency_ms=latency_ms,
                    ))
                    if self._is_success(response):
                        return ProviderResult(
                            response=response, provider=provider, model=model, attempts=list(attempts)
                        )
                    last_status = response.status_code
                    if not self._should_retry_status(response.status_code):
                        break
                except Exception as exc:
                    latency_ms = int((time.perf_counter() - started) * 1000)
                    attempts.append(ProviderAttempt(
                        provider.provider_id, model, None, error=str(exc), latency_ms=latency_ms,
                    ))
                    last_was_conn_error = True
                if attempt_number < max_retries:
                    await asyncio.sleep(min(0.25 * (2**attempt_number), 2.0))
        # Apply failure-type-aware cooldown: auth errors last longer than transient failures.
        if last_status in (401, 403):
            mark_provider_failed(provider.provider_id, _AUTH_FAILURE_COOLDOWN_SECONDS)
        elif last_was_conn_error:
            mark_provider_failed(provider.provider_id, _CONN_FAILURE_COOLDOWN_SECONDS)
        else:
            mark_provider_failed(provider.provider_id)
        return None

    async def chat_completion(
        self,
        payload: dict[str, Any],
        *,
        model_fallbacks: list[str] | None = None,
        max_retries: int = 2,
        allow_commercial_fallback: bool = True,
        provider_timeout_sec: float = 300.0,
    ) -> ProviderResult:
        attempts: list[ProviderAttempt] = []
        deferred_commercial: list[str] = []
        if not self.providers:
            raise ProviderFallbackError(attempts)

        original_model = str(payload.get("model") or "").strip()
        skipped_on_cooldown: list[tuple[ProviderConfig, bool]] = []  # (provider, is_primary)
        # Track the first actually-eligible provider so is_primary works correctly
        # even when earlier providers are skipped (cooldown or model-affinity).
        first_eligible = True
        _bedrock_only = bool(original_model and _is_bedrock_model_id(original_model))

        for provider in self.providers:
            if is_provider_on_cooldown(provider.provider_id):
                log.info(
                    "Skipping provider %s (on cooldown, expires %.0fs from now)",
                    provider.provider_id,
                    _provider_cooldowns.get(provider.provider_id, 0) - time.time(),
                )
                skipped_on_cooldown.append((provider, first_eligible))
                continue
            # Bedrock model IDs (us.anthropic.*, arn:aws:bedrock:*, etc.) must only
            # be routed to the bedrock provider — other providers cannot serve them
            # and would silently fall back to their own default model instead.
            if _bedrock_only and provider.type != "bedrock":
                continue
            if not first_eligible and is_commercial_provider(provider) and not allow_commercial_fallback:
                deferred_commercial.append(provider.provider_id)
                continue
            result = await self._try_one_provider(
                provider, payload, original_model, model_fallbacks or [],
                first_eligible, max_retries, attempts, provider_timeout_sec,
            )
            first_eligible = False
            if result is not None:
                return result

        # ── Last-resort bypass ────────────────────────────────────────────────
        # If all providers were on cooldown (attempts is empty), bypass cooldowns
        # and make a single best-effort attempt per skipped provider.
        # This prevents the misleading "no providers attempted" dead-end that
        # occurs when a previous request put every provider on cooldown.
        if not attempts and skipped_on_cooldown:
            log.warning(
                "All %d providers on cooldown — making last-resort bypass attempt",
                len(skipped_on_cooldown),
            )
            for provider, is_primary in skipped_on_cooldown:
                # Apply the same Bedrock-affinity filter in the bypass path so that
                # a Bedrock model ID is never routed to a non-Bedrock provider even
                # when all providers were on cooldown.
                if _bedrock_only and provider.type != "bedrock":
                    continue
                if is_commercial_provider(provider) and not allow_commercial_fallback:
                    deferred_commercial.append(provider.provider_id)
                    continue
                result = await self._try_one_provider(
                    provider, payload, original_model, model_fallbacks or [],
                    is_primary,
                    0,
                    attempts,
                    provider_timeout_sec,
                )
                if result is not None:
                    return result

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
        self,
        provider: ProviderConfig,
        payload: dict[str, Any],
        timeout_sec: float = 300.0,
    ) -> httpx.Response:
        headers = provider.auth_headers()
        if provider.type == "bedrock":
            return await self._post_bedrock_converse(provider, payload, timeout_sec)
        if provider.type.startswith("emergent-"):
            return await self._post_emergent_chat(provider, payload, timeout_sec)
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_sec, connect=min(10.0, timeout_sec))
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
        self,
        provider: ProviderConfig,
        payload: dict[str, Any],
        timeout_sec: float = 300.0,
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
        response_text = await asyncio.wait_for(
            chat.send_message(UserMessage(text=user_text)),
            timeout=timeout_sec,
        )
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

    async def _post_bedrock_converse(
        self,
        provider: ProviderConfig,
        payload: dict[str, Any],
        timeout_sec: float = 300.0,
    ) -> httpx.Response:
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError(
                "boto3 is required for the Bedrock provider. "
                "Install with: pip install 'boto3>=1.34.0'"
            ) from exc

        aws_secret = provider.headers.get("X-Bedrock-Secret", "")
        aws_region = provider.headers.get("X-Bedrock-Region", "us-east-1")
        model_id = str(payload.get("model") or provider.default_model or "")

        bedrock_payload = self._openai_to_bedrock_converse(payload)

        def _sync_call() -> dict[str, Any]:
            client = boto3.client(
                "bedrock-runtime",
                region_name=aws_region,
                aws_access_key_id=provider.api_key,
                aws_secret_access_key=aws_secret,
            )
            kwargs: dict[str, Any] = {
                "modelId": model_id,
                "messages": bedrock_payload["messages"],
            }
            if bedrock_payload.get("system"):
                kwargs["system"] = bedrock_payload["system"]
            if bedrock_payload.get("inferenceConfig"):
                kwargs["inferenceConfig"] = bedrock_payload["inferenceConfig"]
            return client.converse(**kwargs)  # type: ignore[return-value]

        response_data = await asyncio.wait_for(
            asyncio.to_thread(_sync_call),
            timeout=timeout_sec,
        )
        return self._bedrock_response_to_openai(response_data, model_id)

    @staticmethod
    def _openai_to_bedrock_converse(payload: dict[str, Any]) -> dict[str, Any]:
        """Translate an OpenAI chat/completions payload to Bedrock Converse format."""
        system_parts: list[dict[str, str]] = []
        messages: list[dict[str, Any]] = []
        for msg in payload.get("messages") or []:
            if not isinstance(msg, dict):
                continue
            role = str(msg.get("role") or "user")
            content = msg.get("content")
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                text = " ".join(
                    item.get("text", "")
                    for item in content
                    if isinstance(item, dict) and item.get("type") == "text"
                )
            else:
                text = ""
            if not text:
                continue
            if role == "system":
                system_parts.append({"text": text})
            elif role in ("user", "assistant"):
                messages.append({"role": role, "content": [{"text": text}]})

        inference_config: dict[str, Any] = {}
        if payload.get("max_tokens"):
            inference_config["maxTokens"] = int(payload["max_tokens"])
        if payload.get("temperature") is not None:
            inference_config["temperature"] = float(payload["temperature"])

        return {
            "messages": messages or [{"role": "user", "content": [{"text": "Hello"}]}],
            "system": system_parts,
            "inferenceConfig": inference_config,
        }

    @staticmethod
    def _bedrock_response_to_openai(data: dict[str, Any], model: str) -> httpx.Response:
        """Translate a Bedrock Converse API response to OpenAI chat.completion format."""
        output = data.get("output") or {}
        message = output.get("message") or {}
        content_blocks = message.get("content") or []
        text = " ".join(
            block.get("text", "")
            for block in content_blocks
            if isinstance(block, dict) and "text" in block
        )
        usage = data.get("usage") or {}
        body = {
            "id": f"chatcmpl-bedrock-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": int(usage.get("inputTokens") or 0),
                "completion_tokens": int(usage.get("outputTokens") or 0),
                "total_tokens": int(usage.get("totalTokens") or 0),
            },
        }
        return httpx.Response(200, json=body, headers={"content-type": "application/json"})

    @staticmethod
    def attempts_header(attempts: list[ProviderAttempt]) -> str:
        compact = [a.as_dict() for a in attempts[-8:]]
        return json.dumps(compact, separators=(",", ":"))

from __future__ import annotations

import json

import httpx
import pytest

from provider_router import (
    CommercialFallbackRequiredError,
    ProviderConfig,
    ProviderRouter,
    extract_openai_text,
    is_commercial_provider,
)


@pytest.mark.anyio
async def test_provider_router_falls_back_to_second_provider(monkeypatch):
    calls: list[str] = []

    async def fake_post_chat(self, provider, payload, timeout_sec):
        calls.append(provider.provider_id)
        if provider.provider_id == "ollama-local":
            return httpx.Response(503, json={"error": "down"})
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "fallback-ok"}}]},
            headers={"content-type": "application/json"},
        )

    monkeypatch.setattr(ProviderRouter, "_post_chat", fake_post_chat)
    router = ProviderRouter(
        [
            ProviderConfig("ollama-local", "ollama", "http://localhost:11434", default_model="local", priority=0),
            ProviderConfig("openrouter", "openai-compatible", "https://openrouter.ai/api/v1", api_key="sk", default_model="cloud", priority=10),
        ]
    )

    result = await router.chat_completion({"model": "local", "messages": [{"role": "user", "content": "hi"}]}, max_retries=0)

    assert calls == ["ollama-local", "openrouter"]
    assert result.provider.provider_id == "openrouter"
    assert result.model == "cloud"
    assert extract_openai_text(result.response.json()) == "fallback-ok"


@pytest.mark.anyio
async def test_provider_router_retries_model_fallback_on_404(monkeypatch):
    models: list[str] = []

    async def fake_post_chat(self, provider, payload, timeout_sec):
        models.append(payload["model"])
        if payload["model"] == "missing-model":
            return httpx.Response(404, json={"error": "missing"})
        return httpx.Response(200, json={"choices": [{"message": {"content": "model-ok"}}]})

    monkeypatch.setattr(ProviderRouter, "_post_chat", fake_post_chat)
    router = ProviderRouter([ProviderConfig("ollama-local", "ollama", "http://localhost:11434", default_model="safe-model", priority=0)])

    result = await router.chat_completion(
        {"model": "missing-model", "messages": [{"role": "user", "content": "hi"}]},
        model_fallbacks=["safe-model"],
        max_retries=0,
    )

    assert models == ["missing-model", "safe-model"]
    assert result.model == "safe-model"


@pytest.mark.anyio
async def test_provider_router_passes_custom_provider_timeout(monkeypatch):
    captured: list[float] = []

    async def fake_post_chat(self, provider, payload, timeout_sec):
        captured.append(timeout_sec)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    monkeypatch.setattr(ProviderRouter, "_post_chat", fake_post_chat)
    router = ProviderRouter(
        [ProviderConfig("ollama-local", "ollama", "http://localhost:11434", default_model="local", priority=0)]
    )

    await router.chat_completion(
        {"model": "local", "messages": [{"role": "user", "content": "hi"}]},
        max_retries=0,
        provider_timeout_sec=7.5,
    )

    assert captured == [7.5]


def test_provider_router_attempts_header_is_compact_json():
    header = ProviderRouter.attempts_header([])
    assert json.loads(header) == []


def test_provider_router_treats_emergent_anthropic_as_commercial():
    provider = ProviderConfig(
        provider_id="anthropic-universal",
        type="emergent-anthropic",
        base_url="emergent://anthropic",
        api_key="test-key",
        default_model="claude-sonnet-4-5-20250929",
    )

    assert is_commercial_provider(provider) is True


def test_provider_router_from_env_prioritizes_nvidia_nemotron_default(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "nv-test-key")
    monkeypatch.delenv("NVIDIA_DEFAULT_MODEL", raising=False)

    router = ProviderRouter.from_env()

    assert router.providers[0].provider_id == "nvidia-nim"
    assert router.providers[0].default_model == "nvidia/nemotron-3-super-120b-a12b"


@pytest.mark.anyio
async def test_provider_router_prefers_local_then_remote_then_free_cloud(monkeypatch):
    calls: list[str] = []

    async def fake_post_chat(self, provider, payload, timeout_sec):
        calls.append(provider.provider_id)
        if provider.provider_id == "deepseek":
            return httpx.Response(200, json={"choices": [{"message": {"content": "free-cloud-ok"}}]})
        return httpx.Response(503, json={"error": "down"})

    monkeypatch.setattr(ProviderRouter, "_post_chat", fake_post_chat)
    router = ProviderRouter.from_provider_records(
        [
            {"provider_id": "anthropic", "type": "anthropic", "base_url": "https://api.anthropic.com", "default_model": "claude-sonnet-4-5"},
            {"provider_id": "remote-win", "type": "openai-compatible", "base_url": "https://my-tunnel.ngrok-free.app/v1", "default_model": "remote-model"},
            {"provider_id": "deepseek", "type": "openai-compatible", "base_url": "https://api.deepseek.com", "default_model": "deepseek-chat"},
            {"provider_id": "ollama-local", "type": "ollama", "base_url": "http://localhost:11434", "default_model": "local-model"},
        ]
    )

    result = await router.chat_completion({"model": "local-model", "messages": [{"role": "user", "content": "hi"}]}, max_retries=0)

    assert calls == ["ollama-local", "remote-win", "deepseek"]
    assert result.provider.provider_id == "deepseek"


@pytest.mark.anyio
async def test_provider_router_requires_approval_before_commercial_fallback(monkeypatch):
    async def fake_post_chat(self, provider, payload, timeout_sec):
        return httpx.Response(503, json={"error": "down"})

    monkeypatch.setattr(ProviderRouter, "_post_chat", fake_post_chat)
    router = ProviderRouter.from_provider_records(
        [
            {"provider_id": "ollama-local", "type": "ollama", "base_url": "http://localhost:11434", "default_model": "local-model"},
            {"provider_id": "anthropic", "type": "anthropic", "base_url": "https://api.anthropic.com", "default_model": "claude-sonnet-4-5"},
        ]
    )

    with pytest.raises(CommercialFallbackRequiredError) as exc:
        await router.chat_completion(
            {"model": "local-model", "messages": [{"role": "user", "content": "hi"}]},
            max_retries=0,
            allow_commercial_fallback=False,
        )

    assert exc.value.candidates == ["anthropic"]


@pytest.mark.anyio
async def test_provider_router_can_use_emergent_provider(monkeypatch):
    async def fake_emergent(self, provider, payload, timeout_sec):
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok from emergent"}}]})

    monkeypatch.setattr(ProviderRouter, "_post_emergent_chat", fake_emergent)
    router = ProviderRouter([
        ProviderConfig(
            provider_id="anthropic-universal",
            type="emergent-anthropic",
            base_url="emergent://anthropic",
            api_key="test-key",
            default_model="claude-sonnet-4-5-20250929",
        )
    ])

    result = await router.chat_completion(
        {"model": "claude-sonnet-4-5-20250929", "messages": [{"role": "user", "content": "hi"}]},
        max_retries=0,
        allow_commercial_fallback=True,
    )

    assert extract_openai_text(result.response.json()) == "ok from emergent"
"""Integration tests for ProviderRouter failover order."""

from __future__ import annotations

import httpx
import pytest

from provider_router import (
    ProviderConfig,
    ProviderFallbackError,
    ProviderRouter,
    clear_cooldowns,
)


@pytest.fixture(autouse=True)
def reset_cooldowns():
    """Ensure each test starts with no active cooldowns."""
    clear_cooldowns()
    yield
    clear_cooldowns()


@pytest.mark.anyio
async def test_failover_skips_local_uses_windows_server(monkeypatch):
    """Local Ollama down → Windows server Ollama used."""
    attempts: list[str] = []

    async def fake_post_chat(self, provider, payload, timeout_sec):
        attempts.append(provider.provider_id)
        if provider.provider_id == "ollama-local":
            return httpx.Response(503, json={"error": "local down"})
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "from-windows"}}]}
        )

    monkeypatch.setattr(ProviderRouter, "_post_chat", fake_post_chat)
    router = ProviderRouter(
        [
            ProviderConfig(
                "ollama-local",
                "ollama",
                "http://localhost:11434",
                default_model="m",
                priority=0,
            ),
            ProviderConfig(
                "ollama-windows-server",
                "ollama",
                "http://windows-server:11434",
                default_model="m",
                priority=5,
            ),
        ]
    )

    result = await router.chat_completion(
        {"model": "m", "messages": [{"role": "user", "content": "hi"}]},
        max_retries=0,
    )

    assert result.provider.provider_id == "ollama-windows-server"
    assert "ollama-local" in attempts
    assert "ollama-windows-server" in attempts


@pytest.mark.anyio
async def test_failover_chain_local_windows_hf_deepseek_anthropic(monkeypatch):
    """Full chain: local → windows → hf → deepseek → anthropic."""
    attempts: list[str] = []

    async def fake_post_chat(self, provider, payload, timeout_sec):
        attempts.append(provider.provider_id)
        # Fail everything except anthropic
        if provider.provider_id != "anthropic":
            return httpx.Response(503, json={"error": "down"})
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "from-anthropic"}}]}
        )

    monkeypatch.setattr(ProviderRouter, "_post_chat", fake_post_chat)
    router = ProviderRouter(
        [
            ProviderConfig(
                "ollama-local",
                "ollama",
                "http://localhost:11434",
                default_model="m",
                priority=0,
            ),
            ProviderConfig(
                "ollama-windows-server",
                "ollama",
                "http://192.168.1.10:11434",
                default_model="m",
                priority=5,
            ),
            ProviderConfig(
                "huggingface",
                "openai-compatible",
                "https://router.huggingface.co",
                api_key="hf-tok",
                default_model="qwen",
                priority=20,
            ),
            ProviderConfig(
                "deepseek",
                "openai-compatible",
                "https://api.deepseek.com",
                api_key="ds-key",
                default_model="ds-chat",
                priority=40,
            ),
            ProviderConfig(
                "anthropic",
                "anthropic",
                "https://api.anthropic.com",
                api_key="ant-key",
                default_model="claude-3",
                priority=50,
            ),
        ]
    )

    result = await router.chat_completion(
        {"model": "m", "messages": [{"role": "user", "content": "hi"}]},
        max_retries=0,
        allow_commercial_fallback=True,
    )

    assert result.provider.provider_id == "anthropic"
    assert attempts == [
        "ollama-local",
        "ollama-windows-server",
        "huggingface",
        "deepseek",
        "anthropic",
    ]


@pytest.mark.anyio
async def test_failover_raises_503_when_all_fail(monkeypatch):
    """All providers fail → ProviderFallbackError is raised."""

    async def fake_post_chat(self, provider, payload, timeout_sec):
        return httpx.Response(503, json={"error": "all down"})

    monkeypatch.setattr(ProviderRouter, "_post_chat", fake_post_chat)
    router = ProviderRouter(
        [
            ProviderConfig(
                "ollama-local",
                "ollama",
                "http://localhost:11434",
                default_model="m",
                priority=0,
            ),
            ProviderConfig(
                "huggingface",
                "openai-compatible",
                "https://router.huggingface.co",
                api_key="tok",
                default_model="qwen",
                priority=20,
            ),
        ]
    )

    with pytest.raises(ProviderFallbackError):
        await router.chat_completion(
            {"model": "m", "messages": [{"role": "user", "content": "hi"}]},
            max_retries=0,
        )


@pytest.mark.anyio
async def test_provider_on_cooldown_is_skipped(monkeypatch):
    """A provider on cooldown is not attempted."""
    from provider_router import mark_provider_failed

    attempts: list[str] = []

    async def fake_post_chat(self, provider, payload, timeout_sec):
        attempts.append(provider.provider_id)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    monkeypatch.setattr(ProviderRouter, "_post_chat", fake_post_chat)
    mark_provider_failed("ollama-local", cooldown_seconds=300)

    router = ProviderRouter(
        [
            ProviderConfig(
                "ollama-local",
                "ollama",
                "http://localhost:11434",
                default_model="m",
                priority=0,
            ),
            ProviderConfig(
                "huggingface",
                "openai-compatible",
                "https://router.huggingface.co",
                api_key="tok",
                default_model="qwen",
                priority=20,
            ),
        ]
    )

    result = await router.chat_completion(
        {"model": "m", "messages": [{"role": "user", "content": "hi"}]},
        max_retries=0,
    )

    # Local should be skipped, hf should be used
    assert "ollama-local" not in attempts
    assert result.provider.provider_id == "huggingface"


@pytest.mark.anyio
async def test_from_env_includes_windows_server(monkeypatch):
    """ProviderRouter.from_env() picks up OLLAMA_WINDOWS_SERVER."""
    monkeypatch.setenv("OLLAMA_WINDOWS_SERVER", "http://192.168.1.50:11434")
    monkeypatch.setenv("OLLAMA_WINDOWS_MODEL", "llama3.2")
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    router = ProviderRouter.from_env()
    ids = [p.provider_id for p in router.providers]
    assert "ollama-local" in ids
    assert "ollama-windows-server" in ids

    local_idx = ids.index("ollama-local")
    windows_idx = ids.index("ollama-windows-server")
    assert local_idx < windows_idx, "Local Ollama must come before Windows server"

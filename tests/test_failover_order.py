"""Tests that verify the exact provider priority ordering."""

from __future__ import annotations

import pytest

from provider_router import (
    ProviderConfig,
    ProviderRouter,
    clear_cooldowns,
    provider_access_tier,
    provider_sort_key,
)


@pytest.fixture(autouse=True)
def reset_cooldowns():
    clear_cooldowns()
    yield
    clear_cooldowns()


def test_provider_sort_key_order():
    """local < windows_server < free_cloud < commercial."""
    local = ProviderConfig("local", "ollama", "http://localhost:11434", priority=0)
    windows = ProviderConfig(
        "windows", "ollama", "http://192.168.1.10:11434", priority=5
    )
    hf = ProviderConfig(
        "hf",
        "openai-compatible",
        "https://router.huggingface.co",
        api_key="tok",
        priority=20,
    )
    deepseek = ProviderConfig(
        "deepseek",
        "openai-compatible",
        "https://api.deepseek.com",
        api_key="key",
        priority=40,
    )
    anthropic = ProviderConfig(
        "anthropic",
        "anthropic",
        "https://api.anthropic.com",
        api_key="key",
        priority=50,
    )

    providers = [anthropic, hf, windows, local, deepseek]
    sorted_providers = sorted(providers, key=provider_sort_key)
    ids = [p.provider_id for p in sorted_providers]

    assert ids.index("local") < ids.index("windows")
    assert ids.index("windows") < ids.index("hf")
    assert ids.index("hf") < ids.index("deepseek")
    assert ids.index("deepseek") < ids.index("anthropic")


def test_access_tier_local_ollama():
    p = ProviderConfig("local", "ollama", "http://localhost:11434", priority=0)
    assert provider_access_tier(p) == "local"


def test_access_tier_windows_server_by_ip():
    p = ProviderConfig("win", "ollama", "http://192.168.1.50:11434", priority=5)
    assert provider_access_tier(p) == "windows_server"


def test_access_tier_huggingface():
    p = ProviderConfig(
        "hf",
        "openai-compatible",
        "https://router.huggingface.co",
        api_key="tok",
        priority=20,
    )
    assert provider_access_tier(p) == "free_cloud"


def test_access_tier_deepseek():
    p = ProviderConfig(
        "ds",
        "openai-compatible",
        "https://api.deepseek.com",
        api_key="key",
        priority=40,
    )
    assert provider_access_tier(p) == "free_cloud"


def test_access_tier_anthropic():
    p = ProviderConfig(
        "ant", "anthropic", "https://api.anthropic.com", api_key="key", priority=50
    )
    assert provider_access_tier(p) == "commercial"


def test_from_env_provider_order_local_first(monkeypatch):
    """from_env() must put local Ollama first regardless of how env vars are set."""
    monkeypatch.delenv("OLLAMA_WINDOWS_SERVER", raising=False)
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    router = ProviderRouter.from_env()
    assert router.providers[0].provider_id == "ollama-local"


def test_from_env_windows_comes_before_huggingface(monkeypatch):
    monkeypatch.setenv("OLLAMA_WINDOWS_SERVER", "http://192.168.1.50:11434")
    monkeypatch.setenv("HF_TOKEN", "hf-tok")
    monkeypatch.setenv("HF_BASE_URL", "https://router.huggingface.co")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    router = ProviderRouter.from_env()
    ids = [p.provider_id for p in router.providers]
    assert "ollama-windows-server" in ids
    assert "huggingface" in ids
    assert ids.index("ollama-windows-server") < ids.index("huggingface")


def test_from_env_anthropic_comes_last(monkeypatch):
    monkeypatch.setenv("OLLAMA_WINDOWS_SERVER", "http://192.168.1.50:11434")
    monkeypatch.setenv("HF_TOKEN", "tok")
    monkeypatch.setenv("HF_BASE_URL", "https://router.huggingface.co")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "dskey")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "antkey")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")

    router = ProviderRouter.from_env()
    ids = [p.provider_id for p in router.providers]
    # Anthropic must be the very last non-emergent provider
    commercial_ids = [pid for pid in ids if pid == "anthropic"]
    assert commercial_ids, "anthropic provider must be present"
    ant_idx = ids.index("anthropic")
    # All other non-commercial providers must appear before anthropic
    for pid in ["ollama-local", "ollama-windows-server", "huggingface", "deepseek"]:
        if pid in ids:
            assert ids.index(pid) < ant_idx, f"{pid} must come before anthropic"

"""Verify every supported provider is correctly discovered, prioritised, and typed.

These tests simulate each provider being configured (fake keys) and assert:
  - from_env() registers the provider
  - provider has the expected type
  - default_model is set
  - priority is in the expected tier range
  - health_check returns True for credential-based providers
"""
from __future__ import annotations

import pytest

from provider_router import ProviderRouter, provider_access_tier


# ── helpers ───────────────────────────────────────────────────────────────────

def _router(monkeypatch, **env) -> ProviderRouter:
    """Build a ProviderRouter from_env() with only the supplied env vars active."""
    for key in [
        "NVIDIA_API_KEY", "NVidiaApiKey", "OPENCODE_ZEN_API_KEY", "DEEPSEEK_API_KEY",
        "GROQ_API_KEY", "DASHSCOPE_API_KEY", "QWEN_API_KEY", "CEREBRAS_API_KEY",
        "SAMBANOVA_API_KEY", "TOGETHER_API_KEY", "MISTRAL_API_KEY", "GOOGLE_API_KEY",
        "GEMINI_API_KEY", "OPENROUTER_API_KEY", "HF_TOKEN", "HUGGINGFACE_API_TOKEN",
        "ZHIPU_API_KEY", "MINIMAX_API_KEY", "ANTHROPIC_API_KEY", "EMERGENT_LLM_KEY",
        "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "BEDROCK_ACCESS_KEY", "BEDROCK_SECRET_KEY",
        "CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID", "OLLAMA_WINDOWS_SERVER",
        "INCLUDE_LOCAL_FALLBACK",
    ]:
        monkeypatch.delenv(key, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    return ProviderRouter.from_env()


def _get(router: ProviderRouter, provider_id: str):
    return next((p for p in router.providers if p.provider_id == provider_id), None)


# ── Nvidia NIM ────────────────────────────────────────────────────────────────

def test_nvidia_nim_discovery(monkeypatch):
    r = _router(monkeypatch, NVIDIA_API_KEY="nvkey")
    p = _get(r, "nvidia-nim")
    assert p is not None
    assert p.type == "openai-compatible"
    assert p.priority == -10
    assert provider_access_tier(p) == "nvidia_nim"
    assert p.default_model


def test_nvidia_nim_alt_key(monkeypatch):
    r = _router(monkeypatch, NVidiaApiKey="nvkey2")
    assert _get(r, "nvidia-nim") is not None


# ── OpenCode Zen ──────────────────────────────────────────────────────────────

def test_opencode_zen_discovery(monkeypatch):
    r = _router(monkeypatch, OPENCODE_ZEN_API_KEY="zenkey")
    p = _get(r, "opencode-zen")
    assert p is not None
    assert p.type == "openai-compatible"
    assert p.priority == 5
    assert "opencode.ai" in p.base_url


def test_opencode_zen_custom_base(monkeypatch):
    r = _router(monkeypatch, OPENCODE_ZEN_API_KEY="zenkey",
                OPENCODE_ZEN_BASE_URL="https://custom.opencode.ai/v1")
    p = _get(r, "opencode-zen")
    assert p.base_url == "https://custom.opencode.ai/v1"


# ── DeepSeek ──────────────────────────────────────────────────────────────────

def test_deepseek_discovery(monkeypatch):
    r = _router(monkeypatch, DEEPSEEK_API_KEY="dskey")
    p = _get(r, "deepseek")
    assert p is not None
    assert p.priority == 20
    assert "deepseek.com" in p.base_url
    assert p.default_model == "deepseek-chat"


def test_deepseek_no_base_url_required(monkeypatch):
    r = _router(monkeypatch, DEEPSEEK_API_KEY="dskey")
    p = _get(r, "deepseek")
    assert p.base_url  # defaults applied


# ── Groq ──────────────────────────────────────────────────────────────────────

def test_groq_discovery(monkeypatch):
    r = _router(monkeypatch, GROQ_API_KEY="groqkey")
    p = _get(r, "groq")
    assert p is not None
    assert p.priority == 25
    assert "groq.com" in p.base_url
    assert "llama" in p.default_model.lower()


# ── SambaNova ─────────────────────────────────────────────────────────────────

def test_sambanova_discovery(monkeypatch):
    r = _router(monkeypatch, SAMBANOVA_API_KEY="snkey")
    p = _get(r, "sambanova")
    assert p is not None
    assert p.priority == 27
    assert "sambanova.ai" in p.base_url


# ── Cerebras ──────────────────────────────────────────────────────────────────

def test_cerebras_discovery(monkeypatch):
    r = _router(monkeypatch, CEREBRAS_API_KEY="cbkey")
    p = _get(r, "cerebras")
    assert p is not None
    assert p.priority == 28
    assert "cerebras.ai" in p.base_url


# ── Qwen / DashScope ──────────────────────────────────────────────────────────

def test_qwen_dashscope_discovery(monkeypatch):
    r = _router(monkeypatch, DASHSCOPE_API_KEY="qwenkey")
    p = _get(r, "qwen-dashscope")
    assert p is not None
    assert p.priority == 30
    assert "dashscope" in p.base_url or "aliyuncs" in p.base_url


def test_qwen_alt_key(monkeypatch):
    r = _router(monkeypatch, QWEN_API_KEY="qwenkey2")
    assert _get(r, "qwen-dashscope") is not None


# ── Together AI ───────────────────────────────────────────────────────────────

def test_together_discovery(monkeypatch):
    r = _router(monkeypatch, TOGETHER_API_KEY="tokey")
    p = _get(r, "together-free")
    assert p is not None
    assert p.priority == 35
    assert "together" in p.base_url


# ── Mistral ───────────────────────────────────────────────────────────────────

def test_mistral_discovery(monkeypatch):
    r = _router(monkeypatch, MISTRAL_API_KEY="mistkey")
    p = _get(r, "mistral")
    assert p is not None
    assert p.priority == 38
    assert "mistral.ai" in p.base_url


# ── Google Gemini ─────────────────────────────────────────────────────────────

def test_gemini_discovery_google_key(monkeypatch):
    r = _router(monkeypatch, GOOGLE_API_KEY="gkey")
    p = _get(r, "google-gemini-free")
    assert p is not None
    assert p.priority == 39
    assert "googleapis.com" in p.base_url
    assert "gemini" in p.default_model


def test_gemini_discovery_gemini_key(monkeypatch):
    r = _router(monkeypatch, GEMINI_API_KEY="gkey2")
    assert _get(r, "google-gemini-free") is not None


# ── OpenRouter ────────────────────────────────────────────────────────────────

def test_openrouter_discovery(monkeypatch):
    r = _router(monkeypatch, OPENROUTER_API_KEY="orkey")
    p = _get(r, "openrouter")
    assert p is not None
    assert p.priority == 40
    assert "openrouter.ai" in p.base_url


def test_openrouter_no_base_url_required(monkeypatch):
    r = _router(monkeypatch, OPENROUTER_API_KEY="orkey")
    assert _get(r, "openrouter").base_url  # default applied


# ── HuggingFace ───────────────────────────────────────────────────────────────

def test_hf_token_discovery(monkeypatch):
    r = _router(monkeypatch, HF_TOKEN="hftoken")
    p = _get(r, "huggingface")
    assert p is not None
    assert p.priority == 45
    assert "huggingface.co" in p.base_url


def test_hf_alt_token(monkeypatch):
    r = _router(monkeypatch, HUGGINGFACE_API_TOKEN="hftoken2")
    assert _get(r, "huggingface") is not None


# ── ZhipuAI ───────────────────────────────────────────────────────────────────

def test_zhipu_discovery(monkeypatch):
    r = _router(monkeypatch, ZHIPU_API_KEY="zhipukey")
    p = _get(r, "zhipu")
    assert p is not None
    assert p.priority == 46
    assert "bigmodel.cn" in p.base_url


# ── MiniMax ───────────────────────────────────────────────────────────────────

def test_minimax_discovery(monkeypatch):
    r = _router(monkeypatch, MINIMAX_API_KEY="mmkey")
    p = _get(r, "minimax")
    assert p is not None
    assert p.priority == 47
    assert "minimax.chat" in p.base_url


# ── Anthropic direct ─────────────────────────────────────────────────────────

def test_anthropic_discovery(monkeypatch):
    r = _router(monkeypatch, ANTHROPIC_API_KEY="antkey")
    p = _get(r, "anthropic")
    assert p is not None
    assert p.type == "anthropic"
    assert p.priority == 50
    assert "anthropic.com" in p.base_url


def test_anthropic_no_base_url_required(monkeypatch):
    r = _router(monkeypatch, ANTHROPIC_API_KEY="antkey")
    assert _get(r, "anthropic").base_url


# ── AWS Bedrock ───────────────────────────────────────────────────────────────

def test_bedrock_discovery(monkeypatch):
    r = _router(monkeypatch, AWS_ACCESS_KEY_ID="AKIATEST", AWS_SECRET_ACCESS_KEY="secret")
    p = _get(r, "bedrock")
    assert p is not None
    assert p.type == "bedrock"
    assert p.priority == 15
    assert "bedrock-runtime" in p.base_url
    assert p.default_model == "us.anthropic.claude-opus-4-6-v1"


@pytest.mark.asyncio
async def test_bedrock_health_check(monkeypatch):
    r = _router(monkeypatch, AWS_ACCESS_KEY_ID="AKIATEST", AWS_SECRET_ACCESS_KEY="secret")
    p = _get(r, "bedrock")
    assert await r.health_check(p) is True


# ── Priority ordering with all providers ─────────────────────────────────────

def test_full_priority_order(monkeypatch):
    r = _router(
        monkeypatch,
        NVIDIA_API_KEY="nvkey",
        OPENCODE_ZEN_API_KEY="zenkey",
        AWS_ACCESS_KEY_ID="AKIATEST", AWS_SECRET_ACCESS_KEY="secret",
        DEEPSEEK_API_KEY="dskey",
        SAMBANOVA_API_KEY="snkey",
        CEREBRAS_API_KEY="cbkey",
        GROQ_API_KEY="groqkey",
        DASHSCOPE_API_KEY="qwenkey",
        TOGETHER_API_KEY="tokey",
        MISTRAL_API_KEY="mistkey",
        GEMINI_API_KEY="gkey",
        OPENROUTER_API_KEY="orkey",
        HF_TOKEN="hftoken",
        ZHIPU_API_KEY="zhipukey",
        MINIMAX_API_KEY="mmkey",
        ANTHROPIC_API_KEY="antkey",
    )
    ids = [p.provider_id for p in r.providers]
    # Nvidia must be first (nvidia_nim tier)
    assert ids[0] == "nvidia-nim"
    # Bedrock (commercial tier, priority 15) must come before Anthropic (priority 50)
    assert ids.index("bedrock") < ids.index("anthropic")
    # Groq (priority 25) before OpenRouter (priority 40) — both free_cloud tier
    assert ids.index("groq") < ids.index("openrouter")
    # All 16 providers discovered
    assert len(r.providers) == 16


def test_no_providers_when_no_keys(monkeypatch):
    r = _router(monkeypatch)
    assert len(r.providers) == 0

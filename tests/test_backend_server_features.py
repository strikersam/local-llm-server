"""Tests for backend/server.py cloud model catalog, multi-agent loop, and
context management utilities added in the multi-agent orchestration commit."""

from __future__ import annotations

import json
import os

import httpx
import pytest

# Ensure backend.server can be imported without a live MongoDB.
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("JWT_SECRET", "test-secret-for-tests-only")
os.environ.setdefault("ADMIN_EMAIL", "admin@test.local")
os.environ.setdefault("ADMIN_PASSWORD", "TestPassword1!")

from backend.server import (  # noqa: E402
    AGENT_ROLE_MODELS,
    PREDEFINED_MODELS,
    _mask_observations,
    _run_agent_loop,
)
from backend.llm_providers import LlmProviderConfig  # noqa: E402

# ── PREDEFINED_MODELS catalog ──────────────────────────────────────────────────

EXPECTED_PROVIDERS = {"openrouter", "huggingface", "ollama", "together"}
REQUIRED_MODEL_FIELDS = {"id", "name", "role", "tier"}
VALID_TIERS = {"flagship", "balanced", "fast"}
VALID_ROLES = {"planner", "executor", "verifier"}


def test_predefined_models_covers_all_providers():
    assert set(PREDEFINED_MODELS.keys()) == EXPECTED_PROVIDERS


def test_predefined_models_each_provider_is_non_empty():
    for provider, models in PREDEFINED_MODELS.items():
        assert len(models) > 0, f"provider '{provider}' has no models"


def test_predefined_models_required_fields_present():
    for provider, models in PREDEFINED_MODELS.items():
        for m in models:
            missing = REQUIRED_MODEL_FIELDS - m.keys()
            assert not missing, f"{provider}/{m.get('id')} missing fields: {missing}"


def test_predefined_models_valid_tiers():
    for provider, models in PREDEFINED_MODELS.items():
        for m in models:
            assert m["tier"] in VALID_TIERS, (
                f"{provider}/{m['id']} has invalid tier '{m['tier']}'"
            )


def test_predefined_models_valid_roles():
    for provider, models in PREDEFINED_MODELS.items():
        for m in models:
            assert isinstance(m["role"], list), f"{provider}/{m['id']} 'role' must be a list"
            for r in m["role"]:
                assert r in VALID_ROLES, (
                    f"{provider}/{m['id']} has unknown role '{r}'"
                )


def test_predefined_models_each_provider_has_at_least_one_planner_and_executor():
    for provider, models in PREDEFINED_MODELS.items():
        roles_covered = {r for m in models for r in m["role"]}
        assert "planner" in roles_covered, f"'{provider}' has no planner model"
        assert "executor" in roles_covered, f"'{provider}' has no executor model"


def test_predefined_models_no_duplicate_ids_per_provider():
    for provider, models in PREDEFINED_MODELS.items():
        ids = [m["id"] for m in models]
        assert len(ids) == len(set(ids)), f"'{provider}' has duplicate model IDs: {ids}"


def test_openrouter_flagship_models_present():
    ids = {m["id"] for m in PREDEFINED_MODELS["openrouter"]}
    assert "deepseek/deepseek-r1" in ids
    assert "qwen/qwen3-235b-a22b" in ids


def test_huggingface_flagship_models_present():
    ids = {m["id"] for m in PREDEFINED_MODELS["huggingface"]}
    assert "Qwen/QwQ-32B" in ids
    assert "deepseek-ai/DeepSeek-R1" in ids


def test_together_models_present():
    ids = {m["id"] for m in PREDEFINED_MODELS["together"]}
    assert "deepseek-ai/DeepSeek-R1" in ids


# ── AGENT_ROLE_MODELS ─────────────────────────────────────────────────────────

def test_agent_role_models_covers_all_providers():
    assert set(AGENT_ROLE_MODELS.keys()) == EXPECTED_PROVIDERS


def test_agent_role_models_has_three_roles_per_provider():
    required = {"planner", "executor", "verifier"}
    for provider, roles in AGENT_ROLE_MODELS.items():
        assert set(roles.keys()) == required, (
            f"'{provider}' role map missing: {required - roles.keys()}"
        )


def test_agent_role_models_models_are_non_empty_strings():
    for provider, roles in AGENT_ROLE_MODELS.items():
        for role, model_id in roles.items():
            assert isinstance(model_id, str) and model_id, (
                f"'{provider}.{role}' must be a non-empty string, got: {model_id!r}"
            )


def test_agent_role_models_planner_and_verifier_are_reasoning_models():
    """Planner and Verifier should be assigned to reasoning (DeepSeek/QwQ) models."""
    reasoning_substrings = ("deepseek", "qwq", "r1", "reasoning")
    for provider in ("openrouter", "together"):
        for role in ("planner", "verifier"):
            model_id = AGENT_ROLE_MODELS[provider][role].lower()
            assert any(s in model_id for s in reasoning_substrings), (
                f"'{provider}.{role}' expected a reasoning model, got '{model_id}'"
            )


# ── _mask_observations ────────────────────────────────────────────────────────

def test_mask_observations_truncates_old_assistant_long_messages():
    msgs = [
        {"role": "assistant", "content": "x" * 500},  # index 0, old → truncated
        {"role": "user", "content": "question"},
        {"role": "assistant", "content": "short"},
        {"role": "user", "content": "q2"},
        {"role": "assistant", "content": "y" * 500},  # index 4, recent → kept
    ]
    result = _mask_observations(msgs, max_chars=300)
    # First assistant message should be truncated
    assert len(result[0]["content"]) <= 300 + len(" … [truncated]")
    assert result[0]["content"].endswith("[truncated]")
    # Last 4 messages are "recent" (indices >= len-4=1) — index 4 is kept as-is
    assert result[4]["content"] == "y" * 500


def test_mask_observations_leaves_short_messages_unchanged():
    msgs = [
        {"role": "assistant", "content": "short reply"},
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "ok"},
        {"role": "user", "content": "continue"},
        {"role": "assistant", "content": "done"},
    ]
    result = _mask_observations(msgs, max_chars=300)
    for orig, res in zip(msgs, result):
        assert res["content"] == orig["content"]


def test_mask_observations_does_not_mutate_input():
    long_content = "a" * 500
    msgs = [{"role": "assistant", "content": long_content}] + [
        {"role": "user", "content": "x"}
    ] * 4
    _mask_observations(msgs, max_chars=300)
    assert msgs[0]["content"] == long_content  # original unchanged


def test_mask_observations_preserves_message_count():
    msgs = [{"role": "user", "content": "hi"}] * 10
    result = _mask_observations(msgs)
    assert len(result) == 10


# ── _run_agent_loop ───────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_run_agent_loop_success(monkeypatch):
    """Verify _run_agent_loop calls AgentRunner.run and returns the summary."""
    mock_result = {"summary": "Agent reached a conclusion."}
    
    class MockRunner:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
        async def run(self, **kwargs):
            self.run_kwargs = kwargs
            return mock_result

    monkeypatch.setattr("agent.loop.AgentRunner", MockRunner)
    
    provider = {"type": "ollama", "base_url": "http://localhost:11434", "api_key": None}
    result = await _run_agent_loop(
        instruction="Do something",
        session_messages=[{"role": "user", "content": "hi"}],
        wiki_index="Index text",
        provider=provider,
        requested_model="m1",
        github_token="gh-token",
    )
    
    assert result == "Agent reached a conclusion."

@pytest.mark.anyio
async def test_run_agent_loop_failure(monkeypatch):
    """Verify _run_agent_loop handles AgentRunner exceptions gracefully."""
    
    class MockRunner:
        def __init__(self, **kwargs): pass
        async def run(self, **kwargs):
            raise RuntimeError("Crash")

    monkeypatch.setattr("agent.loop.AgentRunner", MockRunner)
    
    provider = {"type": "ollama", "base_url": "http://localhost:11434", "api_key": None}
    result = await _run_agent_loop(
        instruction="Do something",
        session_messages=[],
        wiki_index="",
        provider=provider,
    )
    
    assert "Agent error: Crash" in result

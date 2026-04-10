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

def _make_mock_transport(responses: list[str]):
    """Return an httpx transport that cycles through provided response strings."""
    call_count = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        idx = min(call_count["n"], len(responses) - 1)
        call_count["n"] += 1
        body = {"choices": [{"message": {"content": responses[idx]}}]}
        return httpx.Response(200, json=body)

    return httpx.MockTransport(handler)


@pytest.mark.anyio
async def test_run_agent_loop_returns_verifier_response_for_long_executor_output(monkeypatch):
    """When executor produces ≥200 chars, verifier runs and its output is returned."""
    planner_resp = "1. Step one\n2. Step two"
    executor_resp = "E" * 250  # long enough to trigger verifier
    verifier_resp = "Verified final answer."

    call_log: list[str] = []

    async def mock_chat(cfg: LlmProviderConfig, *, messages, model, temperature, client=None):
        if messages[0]["content"].startswith("You are the Planner"):
            call_log.append("planner")
            return planner_resp
        if messages[0]["content"].startswith("You are the Executor"):
            call_log.append("executor")
            return executor_resp
        if messages[0]["content"].startswith("You are the Verifier"):
            call_log.append("verifier")
            return verifier_resp
        return "unexpected"

    monkeypatch.setattr("backend.server.chat_completion_text", mock_chat)

    provider = {"type": "openrouter", "base_url": "https://openrouter.ai/api", "api_key": "sk-test"}
    result = await _run_agent_loop(
        instruction="Write a detailed essay.",
        session_messages=[{"role": "user", "content": "go"}],
        wiki_index="",
        provider=provider,
        requested_model=None,
    )

    assert result == verifier_resp
    assert call_log == ["planner", "executor", "verifier"]


@pytest.mark.anyio
async def test_run_agent_loop_skips_verifier_for_short_executor_output(monkeypatch):
    """When executor produces <200 chars, verifier is skipped."""
    call_log: list[str] = []

    async def mock_chat(cfg: LlmProviderConfig, *, messages, model, temperature, client=None):
        if messages[0]["content"].startswith("You are the Planner"):
            call_log.append("planner")
            return "1. Just do it"
        if messages[0]["content"].startswith("You are the Executor"):
            call_log.append("executor")
            return "Short answer."  # < 200 chars → verifier skipped
        call_log.append("verifier")
        return "should not be called"

    monkeypatch.setattr("backend.server.chat_completion_text", mock_chat)

    provider = {"type": "ollama", "base_url": "http://localhost:11434", "api_key": None}
    result = await _run_agent_loop(
        instruction="Quick question.",
        session_messages=[],
        wiki_index="",
        provider=provider,
        requested_model=None,
    )

    assert result == "Short answer."
    assert "verifier" not in call_log


@pytest.mark.anyio
async def test_run_agent_loop_verifier_failure_falls_back_to_executor(monkeypatch):
    """If verifier raises, executor's response is returned as fallback."""
    async def mock_chat(cfg: LlmProviderConfig, *, messages, model, temperature, client=None):
        if messages[0]["content"].startswith("You are the Planner"):
            return "1. Step"
        if messages[0]["content"].startswith("You are the Executor"):
            return "E" * 250
        raise RuntimeError("verifier API error")

    monkeypatch.setattr("backend.server.chat_completion_text", mock_chat)

    provider = {"type": "openrouter", "base_url": "https://openrouter.ai/api", "api_key": "k"}
    result = await _run_agent_loop(
        instruction="Task",
        session_messages=[],
        wiki_index="",
        provider=provider,
        requested_model=None,
    )

    assert result == "E" * 250


@pytest.mark.anyio
async def test_run_agent_loop_requested_model_overrides_all_roles(monkeypatch):
    """Passing requested_model forces all three phases to use that model."""
    used_models: list[str] = []

    async def mock_chat(cfg: LlmProviderConfig, *, messages, model, temperature, client=None):
        used_models.append(model)
        if messages[0]["content"].startswith("You are the Planner"):
            return "1. One step"
        if messages[0]["content"].startswith("You are the Executor"):
            return "E" * 250
        return "verified"

    monkeypatch.setattr("backend.server.chat_completion_text", mock_chat)

    provider = {"type": "openrouter", "base_url": "https://openrouter.ai/api", "api_key": "k"}
    await _run_agent_loop(
        instruction="Do something",
        session_messages=[],
        wiki_index="",
        provider=provider,
        requested_model="my-custom-model",
    )

    assert all(m == "my-custom-model" for m in used_models), (
        f"Not all phases used the override model: {used_models}"
    )


@pytest.mark.anyio
async def test_run_agent_loop_uses_correct_role_models_for_together(monkeypatch):
    """The loop should pick AGENT_ROLE_MODELS['together'] when provider type is 'together'."""
    used_models: list[str] = []

    async def mock_chat(cfg: LlmProviderConfig, *, messages, model, temperature, client=None):
        used_models.append(model)
        if messages[0]["content"].startswith("You are the Planner"):
            return "Plan"
        return "R" * 200  # executor short response → no verifier

    monkeypatch.setattr("backend.server.chat_completion_text", mock_chat)

    provider = {"type": "together", "base_url": "https://api.together.xyz", "api_key": "k"}
    await _run_agent_loop(
        instruction="Hi",
        session_messages=[],
        wiki_index="",
        provider=provider,
        requested_model=None,
    )

    expected_planner = AGENT_ROLE_MODELS["together"]["planner"]
    expected_executor = AGENT_ROLE_MODELS["together"]["executor"]
    assert used_models[0] == expected_planner
    assert used_models[1] == expected_executor

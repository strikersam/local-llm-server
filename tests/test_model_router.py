"""Tests for the dynamic model router."""

from __future__ import annotations

import os
import pytest

from router.model_router import ModelRouter, RoutingDecision, reset_router, get_router
from router.classifier import classify_task
from router.health import invalidate_cache as invalidate_health_cache


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_router(monkeypatch):
    """Reset the router singleton and model map cache between tests."""
    reset_router()
    # Ensure clean env
    monkeypatch.delenv("MODEL_MAP", raising=False)
    monkeypatch.delenv("ROUTER_EXTRA_MODELS", raising=False)
    yield
    reset_router()


def _router() -> ModelRouter:
    return ModelRouter()


# ── Manual override ────────────────────────────────────────────────────────────

def test_manual_override_takes_highest_priority():
    decision = _router().route(
        requested_model="claude-opus-4-6",
        override_model="qwen3-coder:7b",
    )
    assert decision.resolved_model == "qwen3-coder:7b"
    assert decision.mode == "manual"
    assert decision.selection_source == "override"


def test_manual_override_strips_whitespace():
    decision = _router().route(override_model="  deepseek-r1:32b  ")
    assert decision.resolved_model == "deepseek-r1:32b"
    assert decision.mode == "manual"


def test_empty_override_falls_through_to_auto():
    decision = _router().route(
        requested_model="claude-sonnet-4-6",
        override_model="",
    )
    assert decision.mode == "auto"


def test_none_override_falls_through_to_auto():
    decision = _router().route(
        requested_model="claude-sonnet-4-6",
        override_model=None,
    )
    assert decision.mode == "auto"


# ── Built-in MODEL_MAP (Anthropic aliases) ────────────────────────────────────

def test_claude_opus_maps_to_reasoning_model():
    decision = _router().route(requested_model="claude-opus-4-6")
    assert decision.resolved_model == "deepseek-r1:32b"
    assert decision.selection_source == "model_map"
    assert decision.mode == "auto"


def test_claude_sonnet_maps_to_coder_model():
    decision = _router().route(requested_model="claude-sonnet-4-6")
    assert decision.resolved_model == "qwen3-coder:30b"
    assert decision.selection_source == "model_map"


def test_claude_haiku_maps_to_lightweight_coder_model():
    # Haiku (smallest/cheapest Claude) routes to the lightest local model
    decision = _router().route(requested_model="claude-haiku-4-5-20251001")
    assert decision.resolved_model == "qwen3-coder:7b"


def test_all_claude_3_opus_variants_map_to_reasoning():
    for alias in ["claude-3-opus-20240229", "claude-opus-4-5", "claude-opus-4"]:
        reset_router()
        d = _router().route(requested_model=alias)
        assert d.resolved_model == "deepseek-r1:32b", f"Failed for {alias}"


# ── MODEL_MAP env override ─────────────────────────────────────────────────────

def test_env_model_map_overrides_builtin(monkeypatch):
    monkeypatch.setenv("MODEL_MAP", "claude-sonnet-4-6:deepseek-r1:32b")
    reset_router()
    decision = _router().route(requested_model="claude-sonnet-4-6")
    assert decision.resolved_model == "deepseek-r1:32b"
    assert decision.selection_source == "model_map"


def test_env_model_map_wildcard(monkeypatch):
    monkeypatch.setenv("MODEL_MAP", "*:qwen3-coder:7b")
    reset_router()
    decision = _router().route(requested_model="some-unknown-model")
    assert decision.resolved_model == "qwen3-coder:7b"
    assert decision.selection_source == "model_map"


# ── Local model passthrough ────────────────────────────────────────────────────

def test_known_local_model_passthrough():
    decision = _router().route(requested_model="qwen3-coder:30b")
    assert decision.resolved_model == "qwen3-coder:30b"
    assert decision.selection_source == "passthrough"


def test_known_local_reasoning_passthrough():
    decision = _router().route(requested_model="deepseek-r1:32b")
    assert decision.resolved_model == "deepseek-r1:32b"
    assert decision.selection_source == "passthrough"


# ── Heuristic routing ──────────────────────────────────────────────────────────

def test_unknown_model_falls_to_heuristic():
    decision = _router().route(requested_model="some-unknown-model-xyz")
    assert decision.resolved_model in ("qwen3-coder:30b", "deepseek-r1:32b")
    assert decision.selection_source in ("heuristic", "default")


def test_no_model_returns_default():
    decision = _router().route()
    assert decision.resolved_model  # not empty
    assert decision.mode == "auto"


# ── Task classification ────────────────────────────────────────────────────────

def test_agent_plan_classifies_as_reasoning():
    assert classify_task(endpoint_type="agent_plan") == "reasoning"


def test_agent_execute_classifies_as_code_generation():
    assert classify_task(endpoint_type="agent_execute") == "code_generation"


def test_agent_verify_classifies_as_code_generation():
    assert classify_task(endpoint_type="agent_verify") == "code_generation"


def test_tool_use_detected():
    assert classify_task(has_tools=True) == "tool_use"


def test_code_generation_keyword():
    msgs = [{"role": "user", "content": "Please implement a Python function that sorts a list."}]
    cat = classify_task(messages=msgs)
    assert cat == "code_generation"


def test_code_debugging_keyword():
    msgs = [{"role": "user", "content": "Fix the bug in this function: ```python\ndef foo(): pass\n```"}]
    cat = classify_task(messages=msgs)
    assert cat == "code_debugging"


def test_code_review_keyword():
    msgs = [{"role": "user", "content": "Please review this code and suggest improvements: ```python\n...\n```"}]
    cat = classify_task(messages=msgs)
    assert cat == "code_review"


def test_reasoning_keyword():
    msgs = [{"role": "user", "content": "Analyze the tradeoffs between microservices and monolithic architecture."}]
    cat = classify_task(messages=msgs)
    assert cat == "reasoning"


def test_long_context_classification():
    cat = classify_task(context_tokens=20000)
    assert cat == "long_context"


def test_empty_messages_defaults_to_conversation():
    cat = classify_task(messages=[])
    assert cat == "conversation"


# ── Routing decision metadata ──────────────────────────────────────────────────

def test_to_meta_has_required_fields():
    decision = _router().route(requested_model="claude-opus-4-6")
    meta = decision.to_meta()
    assert "routing_mode" in meta
    assert "routing_requested_model" in meta
    assert "routing_resolved_model" in meta
    assert "routing_reason" in meta
    assert "routing_task_category" in meta
    assert "routing_selection_source" in meta
    assert "routing_fallback_chain" in meta
    assert "routing_provider" in meta


def test_manual_override_meta_mode():
    decision = _router().route(override_model="qwen3-coder:7b")
    meta = decision.to_meta()
    assert meta["routing_mode"] == "manual"
    assert meta["routing_resolved_model"] == "qwen3-coder:7b"


# ── Fallback chain ─────────────────────────────────────────────────────────────

def test_fallback_chain_is_list():
    decision = _router().route(requested_model="claude-opus-4-6")
    assert isinstance(decision.fallback_chain, list)


def test_override_has_fallback_chain():
    decision = _router().route(override_model="custom-model:latest")
    assert isinstance(decision.fallback_chain, list)


# ── Singleton ──────────────────────────────────────────────────────────────────

def test_get_router_returns_same_instance():
    r1 = get_router()
    r2 = get_router()
    assert r1 is r2


def test_reset_clears_singleton():
    r1 = get_router()
    reset_router()
    r2 = get_router()
    assert r1 is not r2


# ── fast_response category ─────────────────────────────────────────────────────

def test_short_streaming_message_classifies_as_fast_response():
    msgs = [{"role": "user", "content": "Hi there"}]
    cat = classify_task(messages=msgs, stream=True)
    assert cat == "fast_response"


def test_short_non_streaming_not_fast_response():
    msgs = [{"role": "user", "content": "Hi there"}]
    cat = classify_task(messages=msgs, stream=False)
    # No streaming → does not qualify for fast_response
    assert cat != "fast_response"


def test_code_message_not_fast_response_even_when_streaming():
    msgs = [{"role": "user", "content": "implement a sort function"}]
    cat = classify_task(messages=msgs, stream=True)
    assert cat == "code_generation"


def test_fast_response_routes_to_lightweight_model():
    # fast_response should resolve to qwen3-coder:7b (lightweight) if available
    # in the registry — it is the only model with "fast_response" in strengths
    msgs = [{"role": "user", "content": "Hello"}]
    decision = _router().route(messages=msgs, stream=True, endpoint_type="chat")
    # When 7b is in the registry, heuristic should prefer it for fast_response
    assert decision.task_category == "fast_response"
    assert decision.resolved_model == "qwen3-coder:7b"


# ── Health check integration ───────────────────────────────────────────────────

def test_health_check_disabled_returns_empty_set(monkeypatch):
    monkeypatch.setenv("ROUTER_HEALTH_CHECK_ENABLED", "false")
    invalidate_health_cache()
    from router.health import get_available_models
    result = get_available_models()
    assert result == set()


def test_is_model_available_true_when_checks_disabled(monkeypatch):
    monkeypatch.setenv("ROUTER_HEALTH_CHECK_ENABLED", "false")
    invalidate_health_cache()
    from router.health import is_model_available
    # Empty set = no filtering = everything is "available"
    assert is_model_available("any-model:latest") is True


def test_is_model_available_prefix_match(monkeypatch):
    monkeypatch.setenv("ROUTER_HEALTH_CHECK_ENABLED", "false")
    invalidate_health_cache()
    from router.health import is_model_available
    assert is_model_available("qwen3-coder:30b") is True


def test_is_model_available_boundary_matching(monkeypatch):
    """Model-name matching must respect family boundaries — a bare name like
    'qwen3' must not be reported available just because 'qwen3-coder:30b' is
    loaded. This guards against cross-family false positives in the fallback
    chain (pre-fix, 'qwen3' greedily matched any qwen3-prefixed model)."""
    import router.health as health
    monkeypatch.setenv("ROUTER_HEALTH_CHECK_ENABLED", "true")
    invalidate_health_cache()
    monkeypatch.setattr(
        health,
        "get_available_models",
        lambda: {"qwen3-coder:30b-q4_K_M", "qwen3-coder:30b", "deepseek-r1:32b"},
    )
    # Exact — OK
    assert health.is_model_available("qwen3-coder:30b") is True
    # Quantization suffix — OK (matches via "-" boundary)
    assert health.is_model_available("qwen3-coder:30b-q4_K_M") is True
    # Tag suffix — OK ("qwen3-coder" → "qwen3-coder:30b" via ":" boundary)
    assert health.is_model_available("qwen3-coder") is True
    # Cross-family false positive — MUST be rejected
    assert health.is_model_available("qwen3") is False
    # Empty/None — rejected
    assert health.is_model_available("") is False


def test_ensure_available_falls_back_when_model_missing(monkeypatch):
    """When primary model is not available, router picks an available fallback."""
    monkeypatch.setenv("ROUTER_HEALTH_CHECK_ENABLED", "true")
    invalidate_health_cache()

    # Patch is_model_available to say only the 7b model is available
    import router.model_router as mrmod
    original = mrmod.is_model_available

    def fake_available(model: str) -> bool:
        return model == "qwen3-coder:7b"

    monkeypatch.setattr(mrmod, "is_model_available", fake_available)
    try:
        decision = _router().route(requested_model="claude-opus-4-6")
        # deepseek-r1:32b would be the MODEL_MAP result but is "unavailable";
        # fallback chain should surface qwen3-coder:7b
        assert decision.resolved_model == "qwen3-coder:7b"
    finally:
        monkeypatch.setattr(mrmod, "is_model_available", original)


# ── ROUTER_EXTRA_MODELS registry extension ────────────────────────────────────

def test_extra_models_added_to_registry(monkeypatch):
    monkeypatch.setenv("ROUTER_EXTRA_MODELS", "test-model:coder:code_generation+tool_use")
    from router.registry import get_registry
    # Force reload by calling get_registry directly
    registry = get_registry()
    assert "test-model" in registry
    assert "code_generation" in registry["test-model"].strengths
    assert "tool_use" in registry["test-model"].strengths


def test_extra_models_format_handles_colons_in_strengths(monkeypatch):
    monkeypatch.setenv("ROUTER_EXTRA_MODELS", "phi4:reasoning:reasoning+analysis")
    from router.registry import get_registry
    registry = get_registry()
    assert "phi4" in registry
    assert registry["phi4"].type == "reasoning"


# ── Claude 4.7 model map (April 2026) ─────────────────────────────────────────

def test_claude_opus_47_maps_to_flagship_reasoning():
    decision = _router().route(requested_model="claude-opus-4-7")
    assert decision.resolved_model == "deepseek-r1:671b"
    assert decision.selection_source == "model_map"


def test_claude_haiku_45_maps_to_lightweight_coder():
    decision = _router().route(requested_model="claude-haiku-4-5-20251001")
    assert decision.resolved_model == "qwen3-coder:7b"
    assert decision.selection_source == "model_map"


def test_claude_35_haiku_maps_to_lightweight_coder():
    decision = _router().route(requested_model="claude-3-5-haiku-20241022")
    assert decision.resolved_model == "qwen3-coder:7b"
    assert decision.selection_source == "model_map"


def test_claude_3_haiku_maps_to_lightweight_coder():
    decision = _router().route(requested_model="claude-3-haiku-20240307")
    assert decision.resolved_model == "qwen3-coder:7b"
    assert decision.selection_source == "model_map"


# ── New model aliases ─────────────────────────────────────────────────────────

def test_llama4_alias_maps_to_maverick():
    decision = _router().route(requested_model="llama4")
    assert decision.resolved_model == "llama4-maverick:17b"
    assert decision.selection_source == "model_map"


def test_llama4_scout_alias():
    decision = _router().route(requested_model="llama4-scout")
    assert decision.resolved_model == "llama4-scout:17b"
    assert decision.selection_source == "model_map"


def test_deepseek_v3_alias():
    decision = _router().route(requested_model="deepseek-v3")
    assert decision.resolved_model == "deepseek-v3:685b"
    assert decision.selection_source == "model_map"


def test_qwen3_coder_235b_alias():
    decision = _router().route(requested_model="qwen3-coder-235b")
    assert decision.resolved_model == "qwen3-coder:235b"
    assert decision.selection_source == "model_map"


def test_qwen3_coder_short_alias():
    decision = _router().route(requested_model="qwen3-coder")
    assert decision.resolved_model == "qwen3-coder:30b"
    assert decision.selection_source == "model_map"


# ── New models are passthrough-eligible (in registry) ────────────────────────

def test_llama4_maverick_passthrough():
    decision = _router().route(requested_model="llama4-maverick:17b")
    assert decision.resolved_model == "llama4-maverick:17b"
    assert decision.selection_source == "passthrough"


def test_deepseek_v3_passthrough():
    decision = _router().route(requested_model="deepseek-v3:685b")
    assert decision.resolved_model == "deepseek-v3:685b"
    assert decision.selection_source == "passthrough"


def test_qwen3_coder_235b_passthrough():
    decision = _router().route(requested_model="qwen3-coder:235b")
    assert decision.resolved_model == "qwen3-coder:235b"
    assert decision.selection_source == "passthrough"


# ── data_analysis task classification ────────────────────────────────────────

def test_pandas_classified_as_data_analysis():
    msgs = [{"role": "user", "content": "Help me load a pandas DataFrame from this CSV and compute groupby aggregations."}]
    cat = classify_task(messages=msgs)
    assert cat == "data_analysis"


def test_numpy_classified_as_data_analysis():
    msgs = [{"role": "user", "content": "Normalise this numpy array and apply standardization."}]
    cat = classify_task(messages=msgs)
    assert cat == "data_analysis"


def test_sklearn_classified_as_data_analysis():
    msgs = [{"role": "user", "content": "Train a scikit-learn classification model with cross-validation."}]
    cat = classify_task(messages=msgs)
    assert cat == "data_analysis"


def test_ml_keyword_classified_as_data_analysis():
    msgs = [{"role": "user", "content": "Help me build a machine learning pipeline for feature engineering."}]
    cat = classify_task(messages=msgs)
    assert cat == "data_analysis"


def test_code_debug_overrides_data_analysis():
    # A debugging request that mentions pandas still classifies as code_debugging
    msgs = [{"role": "user", "content": "Fix the bug in this pandas code:\n```python\ndf.groupby('x').sum()\n```"}]
    cat = classify_task(messages=msgs)
    assert cat == "code_debugging"


def test_data_analysis_routes_to_capable_model():
    msgs = [{"role": "user", "content": "Plot a seaborn heatmap of the correlation matrix."}]
    decision = _router().route(messages=msgs)
    assert decision.task_category == "data_analysis"
    # Any of the capable models is acceptable
    capable = {
        "qwen3-coder:30b", "deepseek-r1:32b", "deepseek-r1:671b",
        "qwen3-coder:235b", "llama4-maverick:17b", "llama4-scout:17b",
        "deepseek-v3:685b",
    }
    assert decision.resolved_model in capable


# ── New registry entries have correct fields ──────────────────────────────────

def test_llama4_maverick_in_registry():
    from router.registry import get_registry
    reg = get_registry()
    assert "llama4-maverick:17b" in reg
    cap = reg["llama4-maverick:17b"]
    assert "code_generation" in cap.strengths
    assert "data_analysis" in cap.strengths
    assert cap.context_window >= 131072


def test_llama4_scout_in_registry():
    from router.registry import get_registry
    reg = get_registry()
    assert "llama4-scout:17b" in reg
    cap = reg["llama4-scout:17b"]
    assert "fast_response" in cap.strengths


def test_deepseek_v3_in_registry():
    from router.registry import get_registry
    reg = get_registry()
    assert "deepseek-v3:685b" in reg
    cap = reg["deepseek-v3:685b"]
    assert "code_generation" in cap.strengths
    assert cap.cost_tier == 2


def test_qwen3_coder_235b_in_registry():
    from router.registry import get_registry
    reg = get_registry()
    assert "qwen3-coder:235b" in reg
    cap = reg["qwen3-coder:235b"]
    assert cap.cost_tier == 3
    assert "data_analysis" in cap.strengths

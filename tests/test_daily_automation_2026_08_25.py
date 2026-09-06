"""tests/test_daily_automation_2026_08_25.py — Daily automation tests (2026-08-25).

Covers the ecosystem updates applied today:
  1. config/llm/models.yaml — claude-opus-4-8 added to the YAML model catalog
     (Claude 4 Opus tier was missing; router/registry.py already had it).
  2. config/llm/models.yaml — claude-fable-5 and claude-mythos-5 added to the
     YAML model catalog (Mythos-class Claude 5, gated; registry had them but
     YAML cost/context data was absent, breaking cost tracking + context pruning).
"""
from __future__ import annotations

import pytest


# ── helpers ──────────────────────────────────────────────────────────────────

def _cfg():
    from packages.llm.config import load_config
    return load_config()


# ── Claude Opus 4.8 ──────────────────────────────────────────────────────────

class TestCatalogOpus48:
    """Verify the claude-opus-4-8 entry in config/llm/models.yaml."""

    def test_opus48_in_catalog(self) -> None:
        assert "claude-opus-4-8" in _cfg().models

    def test_opus48_provider_is_anthropic(self) -> None:
        assert _cfg().models["claude-opus-4-8"].provider == "anthropic"

    def test_opus48_context_window(self) -> None:
        assert _cfg().models["claude-opus-4-8"].context_window == 200_000

    def test_opus48_max_output_tokens(self) -> None:
        assert _cfg().models["claude-opus-4-8"].max_output_tokens == 32_000

    def test_opus48_supports_tools(self) -> None:
        assert _cfg().models["claude-opus-4-8"].supports_tools is True

    def test_opus48_supports_reasoning(self) -> None:
        assert _cfg().models["claude-opus-4-8"].supports_reasoning is True

    def test_opus48_supports_images(self) -> None:
        assert _cfg().models["claude-opus-4-8"].supports_images is True

    def test_opus48_supports_streaming(self) -> None:
        assert _cfg().models["claude-opus-4-8"].supports_streaming is True

    def test_opus48_input_cost(self) -> None:
        # Corrected 2026-09-06: official price is $5/MTok (same tier as Opus 5).
        assert _cfg().models["claude-opus-4-8"].input_cost_per_1m == 5.0

    def test_opus48_output_cost(self) -> None:
        # Corrected 2026-09-06: official price is $25/MTok output.
        assert _cfg().models["claude-opus-4-8"].output_cost_per_1m == 25.0

    def test_opus48_priority_below_claude5(self) -> None:
        """Claude 4 Opus should have lower priority (higher number) than all Claude 5."""
        models = _cfg().models
        opus48 = models["claude-opus-4-8"]
        for name in ("claude-opus-5", "claude-sonnet-5"):
            assert opus48.priority > models[name].priority, (
                f"claude-opus-4-8 priority ({opus48.priority}) should be > "
                f"{name} priority ({models[name].priority})"
            )

    def test_opus48_priority_above_haiku(self) -> None:
        """Claude Opus should have higher priority (lower number) than Haiku."""
        models = _cfg().models
        opus48 = models["claude-opus-4-8"]
        haiku = models["claude-haiku-4-5"]
        assert opus48.priority < haiku.priority

    def test_opus48_alias_resolves(self) -> None:
        """The 'opus-4-8' alias must be present."""
        model = _cfg().models["claude-opus-4-8"]
        assert "opus-4-8" in (model.aliases or [])

    def test_opus48_more_expensive_than_sonnet46(self) -> None:
        """Opus-tier should cost more than Sonnet-tier at the same generation."""
        models = _cfg().models
        opus = models["claude-opus-4-8"]
        sonnet = models["claude-sonnet-4-6"]
        assert opus.input_cost_per_1m > sonnet.input_cost_per_1m


# ── Claude Fable 5 (Mythos-class, suspended) ─────────────────────────────────

class TestCatalogFable5:
    """Verify the claude-fable-5 entry in config/llm/models.yaml."""

    def test_fable5_in_catalog(self) -> None:
        assert "claude-fable-5" in _cfg().models

    def test_fable5_provider_is_anthropic(self) -> None:
        assert _cfg().models["claude-fable-5"].provider == "anthropic"

    def test_fable5_context_window(self) -> None:
        # Corrected 2026-09-06: official context is 1M tokens (1,048,576).
        assert _cfg().models["claude-fable-5"].context_window == 1_048_576

    def test_fable5_supports_tools(self) -> None:
        assert _cfg().models["claude-fable-5"].supports_tools is True

    def test_fable5_supports_reasoning(self) -> None:
        assert _cfg().models["claude-fable-5"].supports_reasoning is True

    def test_fable5_supports_images(self) -> None:
        assert _cfg().models["claude-fable-5"].supports_images is True

    def test_fable5_input_cost_above_opus5(self) -> None:
        """Mythos-class models should be priced above Opus 5."""
        models = _cfg().models
        fable5 = models["claude-fable-5"]
        opus5 = models["claude-opus-5"]
        assert fable5.input_cost_per_1m > opus5.input_cost_per_1m

    def test_fable5_priority_above_opus5(self) -> None:
        """Fable 5 is more capable than Opus 5, so lower priority number."""
        models = _cfg().models
        assert models["claude-fable-5"].priority < models["claude-opus-5"].priority

    def test_fable5_alias_resolves(self) -> None:
        model = _cfg().models["claude-fable-5"]
        assert "fable5" in (model.aliases or [])


# ── Claude Mythos 5 (Mythos-class, approved-orgs-only) ───────────────────────

class TestCatalogMythos5:
    """Verify the claude-mythos-5 entry in config/llm/models.yaml."""

    def test_mythos5_in_catalog(self) -> None:
        assert "claude-mythos-5" in _cfg().models

    def test_mythos5_provider_is_anthropic(self) -> None:
        assert _cfg().models["claude-mythos-5"].provider == "anthropic"

    def test_mythos5_context_window(self) -> None:
        # Corrected 2026-09-06: official context is 1M tokens (1,048,576).
        assert _cfg().models["claude-mythos-5"].context_window == 1_048_576

    def test_mythos5_supports_tools(self) -> None:
        assert _cfg().models["claude-mythos-5"].supports_tools is True

    def test_mythos5_supports_reasoning(self) -> None:
        assert _cfg().models["claude-mythos-5"].supports_reasoning is True

    def test_mythos5_same_cost_as_fable5(self) -> None:
        """Same underlying model — pricing must be identical."""
        models = _cfg().models
        fable5 = models["claude-fable-5"]
        mythos5 = models["claude-mythos-5"]
        assert mythos5.input_cost_per_1m == fable5.input_cost_per_1m
        assert mythos5.output_cost_per_1m == fable5.output_cost_per_1m

    def test_mythos5_same_context_as_fable5(self) -> None:
        models = _cfg().models
        assert models["claude-mythos-5"].context_window == models["claude-fable-5"].context_window

    def test_mythos5_alias_resolves(self) -> None:
        model = _cfg().models["claude-mythos-5"]
        assert "mythos5" in (model.aliases or [])

    def test_mythos5_priority_above_opus5(self) -> None:
        models = _cfg().models
        assert models["claude-mythos-5"].priority < models["claude-opus-5"].priority


# ── Catalog completeness: all router-registry Anthropic models in YAML ────────

class TestCatalogCompleteness:
    """Cross-check that models known to the router registry are in models.yaml."""

    _EXPECTED_IN_YAML = [
        "claude-sonnet-4-6",
        "claude-haiku-4-5",
        "claude-opus-4-8",
        "claude-sonnet-5",
        "claude-opus-5",
        "claude-fable-5",
        "claude-mythos-5",
    ]

    def test_all_expected_models_present(self) -> None:
        models = _cfg().models
        missing = [m for m in self._EXPECTED_IN_YAML if m not in models]
        assert not missing, f"Models missing from models.yaml: {missing}"

    def test_no_model_has_zero_output_cost_unless_free(self) -> None:
        """Paid Anthropic models must have a non-zero output cost."""
        models = _cfg().models
        for name, m in models.items():
            if m.provider != "anthropic":
                continue
            if getattr(m, "supports_chat", True) is False:
                continue
            if m.input_cost_per_1m == 0.0:
                continue  # declared free — skip
            assert m.output_cost_per_1m > 0.0, (
                f"{name} has non-zero input cost but zero output cost"
            )

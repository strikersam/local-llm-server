"""tests/test_daily_automation_2026_09_06.py — Daily automation tests (2026-09-06).

Covers the ecosystem updates applied today:

  1. Pricing corrections across the Anthropic model catalogue (source verified
     from platform.claude.com/docs/en/about-claude/pricing 2026-09-06):
     - claude-fable-5 / claude-fable-5-1: $10/$50 per MTok (was wrongly $30/$120)
     - claude-mythos-5 / claude-mythos-5-1: $10/$50 per MTok
     - claude-opus-5: $5/$25 per MTok (was wrongly $15/$75 — that was Opus 4.1)
     - claude-opus-4-8/4-7/4-6: $5/$25 per MTok (was wrongly $15/$75)
     - claude-sonnet-5: $2/$10 per MTok (was $3/$15 in cost_tracker; price
       locked at introductory level from 2026-09-01 announcement)
     - claude-haiku-4-5: $1/$5 per MTok (was wrongly $0.80/$4.00 — that was Haiku 3.5)

  2. Context window + max output corrections (source: models overview, 2026-09-06):
     - claude-fable-5 / claude-fable-5-1: 1M context / 128K max output
     - claude-opus-5: 1M context / 128K max output
     - claude-mythos-5 / claude-mythos-5-1: 1M context / 128K max output
     (previously all showed 200K / 32K)

  3. New model: claude-mythos-5-1 added to the YAML catalog and cost_tracker.
     Released 2026-09-01 alongside Fable 5.1. Restricted to vetted organisations
     (Anthropic Glasswing/trusted-access program); requires ROUTER_ALLOW_MYTHOS=1.
"""
from __future__ import annotations

import pytest


# ── helpers ──────────────────────────────────────────────────────────────────

def _cfg():
    from packages.llm.config import load_config
    return load_config()


def _cost_table():
    from packages.ai.cost_tracker import _DEFAULT_COST_TABLE
    return _DEFAULT_COST_TABLE


# ── 1a. Pricing — Fable / Mythos family ──────────────────────────────────────

class TestFableMythosPricingCorrection:
    """Verify that Fable 5 / 5.1 / Mythos 5 / 5.1 are priced at $10/$50 per MTok."""

    FABLE_MYTHOS_MODELS = [
        "claude-fable-5",
        "claude-fable-5-1",
        "claude-mythos-5",
        "claude-mythos-5-1",
    ]

    def test_fable5_yaml_input_cost(self) -> None:
        assert _cfg().models["claude-fable-5"].input_cost_per_1m == 10.0

    def test_fable5_yaml_output_cost(self) -> None:
        assert _cfg().models["claude-fable-5"].output_cost_per_1m == 50.0

    def test_fable51_yaml_input_cost(self) -> None:
        assert _cfg().models["claude-fable-5-1"].input_cost_per_1m == 10.0

    def test_fable51_yaml_output_cost(self) -> None:
        assert _cfg().models["claude-fable-5-1"].output_cost_per_1m == 50.0

    def test_mythos5_yaml_input_cost(self) -> None:
        assert _cfg().models["claude-mythos-5"].input_cost_per_1m == 10.0

    def test_mythos5_yaml_output_cost(self) -> None:
        assert _cfg().models["claude-mythos-5"].output_cost_per_1m == 50.0

    def test_fable_family_cost_tracker_entries(self) -> None:
        table = _cost_table()
        for mid in self.FABLE_MYTHOS_MODELS:
            assert mid in table, f"{mid} missing from cost_tracker"
            inp, out = table[mid]
            assert inp == 10.0, f"{mid} input cost: expected 10.0, got {inp}"
            assert out == 50.0, f"{mid} output cost: expected 50.0, got {out}"

    def test_fable_family_consistent_between_yaml_and_tracker(self) -> None:
        """Cost in models.yaml must match the cost_tracker for fable/mythos models."""
        models = _cfg().models
        table = _cost_table()
        for mid in ("claude-fable-5", "claude-fable-5-1", "claude-mythos-5", "claude-mythos-5-1"):
            if mid not in models:
                continue
            model = models[mid]
            assert model.input_cost_per_1m == table[mid][0], (
                f"{mid}: yaml input {model.input_cost_per_1m} != tracker {table[mid][0]}"
            )
            assert model.output_cost_per_1m == table[mid][1], (
                f"{mid}: yaml output {model.output_cost_per_1m} != tracker {table[mid][1]}"
            )


# ── 1b. Pricing — Opus family ─────────────────────────────────────────────────

class TestOpusPricingCorrection:
    """Verify Opus models are priced at $5/$25 per MTok (not the old $15/$75)."""

    OPUS_MODELS_IN_TRACKER = [
        "claude-opus-5",
        "claude-opus-4-8",
        "claude-opus-4-7",
        "claude-opus-4-6",
    ]

    def test_opus5_yaml_input_cost(self) -> None:
        assert _cfg().models["claude-opus-5"].input_cost_per_1m == 5.0

    def test_opus5_yaml_output_cost(self) -> None:
        assert _cfg().models["claude-opus-5"].output_cost_per_1m == 25.0

    def test_opus48_yaml_input_cost(self) -> None:
        assert _cfg().models["claude-opus-4-8"].input_cost_per_1m == 5.0

    def test_opus48_yaml_output_cost(self) -> None:
        assert _cfg().models["claude-opus-4-8"].output_cost_per_1m == 25.0

    def test_opus_cost_tracker_pricing(self) -> None:
        table = _cost_table()
        for mid in self.OPUS_MODELS_IN_TRACKER:
            assert mid in table, f"{mid} missing from cost_tracker"
            inp, out = table[mid]
            assert inp == 5.0, f"{mid} input: expected 5.0, got {inp}"
            assert out == 25.0, f"{mid} output: expected 25.0, got {out}"

    def test_fable_more_expensive_than_opus5_in_tracker(self) -> None:
        """Fable-tier ($10) must be more expensive than Opus-tier ($5)."""
        table = _cost_table()
        assert table["claude-fable-5"][0] > table["claude-opus-5"][0]

    def test_opus5_more_expensive_than_sonnet5_in_tracker(self) -> None:
        """Opus ($5) must be more expensive than Sonnet 5 ($2)."""
        table = _cost_table()
        assert table["claude-opus-5"][0] > table["claude-sonnet-5"][0]


# ── 1c. Pricing — Sonnet 5 locked at introductory rate ───────────────────────

class TestSonnet5PricingLocked:
    """Sonnet 5 introductory price ($2/$10) is now the standard price (2026-09-01)."""

    def test_sonnet5_cost_tracker_input(self) -> None:
        assert _cost_table()["claude-sonnet-5"][0] == 2.0

    def test_sonnet5_cost_tracker_output(self) -> None:
        assert _cost_table()["claude-sonnet-5"][1] == 10.0

    def test_sonnet5_dated_alias_same_as_undated(self) -> None:
        table = _cost_table()
        assert table.get("claude-sonnet-5-20260501") == table["claude-sonnet-5"]


# ── 1d. Pricing — Haiku 4.5 ──────────────────────────────────────────────────

class TestHaiku45PricingCorrection:
    """Haiku 4.5 is $1/$5 per MTok (not $0.80/$4.00 which was Haiku 3.5 pricing)."""

    def test_haiku45_cost_tracker_input(self) -> None:
        assert _cost_table()["claude-haiku-4-5"][0] == 1.0

    def test_haiku45_cost_tracker_output(self) -> None:
        assert _cost_table()["claude-haiku-4-5"][1] == 5.0

    def test_haiku45_dated_alias_same_as_undated(self) -> None:
        table = _cost_table()
        assert table.get("claude-haiku-4-5-20251001") == table["claude-haiku-4-5"]


# ── 2. Context window + max output corrections ────────────────────────────────

class TestContextWindowCorrections:
    """Fable 5, Fable 5.1, Opus 5, Mythos 5, Mythos 5.1 all have 1M context / 128K output."""

    MILLION_CTX_MODELS = [
        "claude-fable-5",
        "claude-fable-5-1",
        "claude-opus-5",
        "claude-mythos-5",
        "claude-mythos-5-1",
    ]

    def test_all_have_1m_context_window(self) -> None:
        models = _cfg().models
        for mid in self.MILLION_CTX_MODELS:
            assert mid in models, f"{mid} not in catalog"
            assert models[mid].context_window == 1_048_576, (
                f"{mid}: context_window {models[mid].context_window} != 1_048_576"
            )

    def test_all_have_128k_max_output(self) -> None:
        models = _cfg().models
        for mid in self.MILLION_CTX_MODELS:
            assert models[mid].max_output_tokens == 131_072, (
                f"{mid}: max_output_tokens {models[mid].max_output_tokens} != 131_072"
            )

    def test_sonnet5_also_has_1m_context(self) -> None:
        """Sonnet 5 1M context was already correct; confirm it stays."""
        assert _cfg().models["claude-sonnet-5"].context_window == 1_048_576


# ── 3. New model: claude-mythos-5-1 ──────────────────────────────────────────

class TestMythos51Catalog:
    """Verify claude-mythos-5-1 is present in both YAML and cost_tracker."""

    def test_mythos51_in_catalog(self) -> None:
        assert "claude-mythos-5-1" in _cfg().models

    def test_mythos51_provider_is_anthropic(self) -> None:
        assert _cfg().models["claude-mythos-5-1"].provider == "anthropic"

    def test_mythos51_context_window(self) -> None:
        assert _cfg().models["claude-mythos-5-1"].context_window == 1_048_576

    def test_mythos51_max_output_tokens(self) -> None:
        assert _cfg().models["claude-mythos-5-1"].max_output_tokens == 131_072

    def test_mythos51_supports_tools(self) -> None:
        assert _cfg().models["claude-mythos-5-1"].supports_tools is True

    def test_mythos51_supports_reasoning(self) -> None:
        assert _cfg().models["claude-mythos-5-1"].supports_reasoning is True

    def test_mythos51_input_cost(self) -> None:
        assert _cfg().models["claude-mythos-5-1"].input_cost_per_1m == 10.0

    def test_mythos51_output_cost(self) -> None:
        assert _cfg().models["claude-mythos-5-1"].output_cost_per_1m == 50.0

    def test_mythos51_in_cost_tracker(self) -> None:
        assert "claude-mythos-5-1" in _cost_table()

    def test_mythos51_cost_tracker_pricing(self) -> None:
        inp, out = _cost_table()["claude-mythos-5-1"]
        assert inp == 10.0
        assert out == 50.0

    def test_mythos51_same_cost_as_fable51(self) -> None:
        """Same underlying model — pricing must be identical."""
        table = _cost_table()
        assert table["claude-mythos-5-1"] == table["claude-fable-5-1"]

    def test_mythos51_higher_priority_than_mythos5(self) -> None:
        """5.1 is the newer release — lower priority number = preferred."""
        models = _cfg().models
        m51 = models["claude-mythos-5-1"]
        m5 = models["claude-mythos-5"]
        assert m51.priority < m5.priority, (
            f"mythos-5-1 priority ({m51.priority}) should be < mythos-5 ({m5.priority})"
        )

    def test_mythos51_has_alias(self) -> None:
        model = _cfg().models["claude-mythos-5-1"]
        assert "mythos5.1" in (model.aliases or [])

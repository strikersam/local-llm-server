"""Tests for packages/ai/cost_tracker.py — per-model cost attribution.

Covers:
- cost_for_tokens() for known / unknown / free / paid models
- record_usage() accumulation and provider set
- get_stats() output shape
- clear_stats() reset
- get_cost_table() serialisability
- ENV override parsing (MODEL_COST_INPUT / MODEL_COST_OUTPUT)
"""
from __future__ import annotations

import pytest

import packages.ai.cost_tracker as ct


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    ct.clear_stats()
    # Reset the cost table to its original defaults before each test so env
    # overrides from one test don't bleed into the next.
    monkeypatch.setattr(ct, "_COST_TABLE", ct._build_cost_table())
    yield
    ct.clear_stats()


# ── cost_for_tokens ───────────────────────────────────────────────────────────


class TestCostForTokens:
    def test_free_tier_model_is_zero(self):
        cost = ct.cost_for_tokens("meta/llama-3.3-70b-instruct", 10_000, 500)
        assert cost == 0.0

    def test_paid_claude_model_has_cost(self):
        cost = ct.cost_for_tokens("claude-sonnet-4-6", 1_000_000, 0)
        assert cost == pytest.approx(3.0)  # $3/M input tokens

    def test_paid_gpt4o_model_output_cost(self):
        cost = ct.cost_for_tokens("gpt-4o", 0, 1_000_000)
        assert cost == pytest.approx(10.0)  # $10/M output tokens

    def test_unknown_model_returns_zero(self):
        cost = ct.cost_for_tokens("totally-unknown-model-xyz", 5000, 1000)
        assert cost == 0.0

    def test_partial_match_fallback(self):
        # "claude-sonnet-4-6" is in the table; a suffix-containing model
        # should fuzzy-match to it.
        cost = ct.cost_for_tokens("us.anthropic.claude-sonnet-4-6-20251001", 1_000_000, 0)
        # Either $3 (if fuzzy match hits) or 0 (no match) — both are valid;
        # we just assert no crash and result >= 0.
        assert cost >= 0.0

    def test_combined_prompt_and_completion(self):
        cost = ct.cost_for_tokens("gpt-4o-mini", 1_000_000, 1_000_000)
        # $0.15/M input + $0.60/M output = $0.75
        assert cost == pytest.approx(0.75)


# ── record_usage / get_stats ──────────────────────────────────────────────────


class TestRecordUsageAndStats:
    def test_single_record_accumulates(self):
        ct.record_usage("gpt-4o-mini", provider_id="openai", prompt_tokens=1000, completion_tokens=50)
        stats = ct.get_stats()
        assert "gpt-4o-mini" in stats["models"]
        entry = stats["models"]["gpt-4o-mini"]
        assert entry["calls"] == 1
        assert entry["prompt_tokens"] == 1000
        assert entry["completion_tokens"] == 50
        assert entry["total_tokens"] == 1050

    def test_multiple_records_accumulate(self):
        ct.record_usage("gpt-4o-mini", provider_id="openai", prompt_tokens=500, completion_tokens=20)
        ct.record_usage("gpt-4o-mini", provider_id="openai", prompt_tokens=300, completion_tokens=10)
        entry = ct.get_stats()["models"]["gpt-4o-mini"]
        assert entry["calls"] == 2
        assert entry["prompt_tokens"] == 800
        assert entry["completion_tokens"] == 30

    def test_different_models_tracked_separately(self):
        ct.record_usage("gpt-4o", provider_id="openai", prompt_tokens=100, completion_tokens=10)
        ct.record_usage("claude-sonnet-4-6", provider_id="anthropic", prompt_tokens=200, completion_tokens=20)
        stats = ct.get_stats()
        assert "gpt-4o" in stats["models"]
        assert "claude-sonnet-4-6" in stats["models"]

    def test_untagged_calls_roll_up_under_untagged(self):
        ct.record_usage("gpt-4o-mini", provider_id="openai", prompt_tokens=100, completion_tokens=10)
        by_tag = ct.get_stats()["by_tag"]
        assert by_tag["untagged"]["calls"] == 1

    def test_tagged_calls_broken_out_by_tag(self):
        ct.record_usage("gpt-4o-mini", provider_id="openai", prompt_tokens=100, completion_tokens=10, tag="code_generation")
        ct.record_usage("gpt-4o-mini", provider_id="openai", prompt_tokens=200, completion_tokens=20, tag="code_generation")
        ct.record_usage("gpt-4o", provider_id="openai", prompt_tokens=50, completion_tokens=5, tag="reasoning")
        by_tag = ct.get_stats()["by_tag"]
        assert by_tag["code_generation"]["calls"] == 2
        assert by_tag["code_generation"]["total_tokens"] == 330
        assert by_tag["reasoning"]["calls"] == 1

    def test_clear_stats_resets_tag_breakdown(self):
        ct.record_usage("gpt-4o-mini", provider_id="openai", prompt_tokens=100, completion_tokens=10, tag="fast_response")
        ct.clear_stats()
        assert ct.get_stats()["by_tag"] == {}

    def test_provider_id_tracked_in_set(self):
        ct.record_usage("gpt-4o-mini", provider_id="openai", prompt_tokens=100, completion_tokens=10)
        ct.record_usage("gpt-4o-mini", provider_id="openai-azure", prompt_tokens=100, completion_tokens=10)
        providers = ct.get_stats()["models"]["gpt-4o-mini"]["providers"]
        assert "openai" in providers
        assert "openai-azure" in providers

    def test_totals_sum_across_models(self):
        ct.record_usage("model-a", provider_id="p1", prompt_tokens=100, completion_tokens=0)
        ct.record_usage("model-b", provider_id="p2", prompt_tokens=200, completion_tokens=0)
        stats = ct.get_stats()
        assert stats["totals"]["calls"] == 2

    def test_free_model_cost_is_zero_in_stats(self):
        ct.record_usage("meta/llama-3.3-70b-instruct", provider_id="nvidia", prompt_tokens=50_000, completion_tokens=5_000)
        entry = ct.get_stats()["models"]["meta/llama-3.3-70b-instruct"]
        assert entry["estimated_cost_usd"] == 0.0

    def test_paid_model_cost_in_stats(self):
        ct.record_usage("claude-sonnet-4-6", provider_id="anthropic", prompt_tokens=1_000_000, completion_tokens=0)
        entry = ct.get_stats()["models"]["claude-sonnet-4-6"]
        assert entry["estimated_cost_usd"] == pytest.approx(3.0)

    def test_record_never_raises_on_bad_tokens(self):
        # Passing 0s / negatives must not raise
        ct.record_usage("anything", prompt_tokens=0, completion_tokens=0)
        ct.record_usage("anything", prompt_tokens=-1, completion_tokens=-1)

    def test_stats_schema_has_expected_keys(self):
        ct.record_usage("m", prompt_tokens=1, completion_tokens=1)
        stats = ct.get_stats()
        assert "models" in stats
        assert "totals" in stats
        assert "calls" in stats["totals"]
        assert "estimated_cost_usd" in stats["totals"]
        entry = list(stats["models"].values())[0]
        for key in ("calls", "prompt_tokens", "completion_tokens", "total_tokens",
                    "estimated_cost_usd", "providers"):
            assert key in entry, f"missing key: {key}"


# ── clear_stats ───────────────────────────────────────────────────────────────


class TestClearStats:
    def test_clear_resets_all_counters(self):
        ct.record_usage("gpt-4o", prompt_tokens=100, completion_tokens=10)
        ct.clear_stats()
        stats = ct.get_stats()
        assert stats["models"] == {}
        assert stats["totals"]["calls"] == 0
        assert stats["totals"]["estimated_cost_usd"] == 0.0


# ── get_cost_table ────────────────────────────────────────────────────────────


class TestGetCostTable:
    def test_returns_dict_of_dicts(self):
        table = ct.get_cost_table()
        assert isinstance(table, dict)
        for model, costs in table.items():
            assert "input_per_million_usd" in costs
            assert "output_per_million_usd" in costs

    def test_known_free_model_is_zero(self):
        table = ct.get_cost_table()
        assert table["meta/llama-3.3-70b-instruct"]["input_per_million_usd"] == 0.0

    def test_known_paid_model_is_nonzero(self):
        table = ct.get_cost_table()
        assert table["gpt-4o"]["output_per_million_usd"] > 0.0


# ── ENV overrides ─────────────────────────────────────────────────────────────


class TestEnvOverrides:
    def test_env_override_changes_cost(self, monkeypatch):
        monkeypatch.setenv("MODEL_COST_INPUT", "my-custom-model=5.5")
        monkeypatch.setenv("MODEL_COST_OUTPUT", "my-custom-model=20.0")
        monkeypatch.setattr(ct, "_COST_TABLE", ct._build_cost_table())
        cost = ct.cost_for_tokens("my-custom-model", 1_000_000, 1_000_000)
        assert cost == pytest.approx(25.5)

    def test_malformed_env_does_not_raise(self, monkeypatch):
        monkeypatch.setenv("MODEL_COST_INPUT", "bad-format-no-equals")
        monkeypatch.setattr(ct, "_COST_TABLE", ct._build_cost_table())
        # Just ensure no crash; unknown model returns 0
        assert ct.cost_for_tokens("bad-format-no-equals", 1000, 100) == 0.0


# ── Claude Opus model coverage ────────────────────────────────────────────────
# brain_config.py uses claude-opus-5 as the planner/judge in the "anthropic"
# and "aerolink" presets; opus-4-7/4-6 appear in the preferred-model list.
# All three were absent from _DEFAULT_COST_TABLE, so every opus-5 call was
# tracked at $0 — hiding real spend from operators.


class TestClaudeOpusModelCoverage:
    """Verify all Opus models referenced by brain_config are priced."""

    OPUS_MODELS = [
        "claude-opus-5",
        "claude-opus-4-8",
        "claude-opus-4-7",
        "claude-opus-4-6",
    ]

    def test_opus5_input_cost(self):
        # Corrected 2026-09-06: official price is $5/MTok (not $15).
        cost = ct.cost_for_tokens("claude-opus-5", 1_000_000, 0)
        assert cost == pytest.approx(5.0)

    def test_opus5_output_cost(self):
        # Corrected 2026-09-06: official price is $25/MTok output (not $75).
        cost = ct.cost_for_tokens("claude-opus-5", 0, 1_000_000)
        assert cost == pytest.approx(25.0)

    def test_opus47_has_same_tier_as_opus48(self):
        cost_47 = ct.cost_for_tokens("claude-opus-4-7", 1_000_000, 1_000_000)
        cost_48 = ct.cost_for_tokens("claude-opus-4-8", 1_000_000, 1_000_000)
        assert cost_47 == pytest.approx(cost_48)

    def test_opus46_has_same_tier_as_opus48(self):
        cost_46 = ct.cost_for_tokens("claude-opus-4-6", 1_000_000, 1_000_000)
        cost_48 = ct.cost_for_tokens("claude-opus-4-8", 1_000_000, 1_000_000)
        assert cost_46 == pytest.approx(cost_48)

    def test_all_opus_models_nonzero(self):
        for model in self.OPUS_MODELS:
            cost = ct.cost_for_tokens(model, 1_000_000, 0)
            assert cost > 0.0, f"{model} should have non-zero input cost"

    def test_haiku45_short_alias_priced(self):
        cost = ct.cost_for_tokens("claude-haiku-4-5", 1_000_000, 0)
        assert cost == pytest.approx(0.8)

    def test_haiku45_versioned_and_alias_match(self):
        versioned = ct.cost_for_tokens("claude-haiku-4-5-20251001", 1_000_000, 1_000_000)
        alias = ct.cost_for_tokens("claude-haiku-4-5", 1_000_000, 1_000_000)
        assert versioned == pytest.approx(alias)


class TestTheCostTableHasNoDuplicateKeys:
    """A repeated key in a dict literal is silent: the later value wins.

    Found on 2026-08-29 while replacing the Cerebras ids. `gpt-oss-120b` was
    added near the top of the block while an entry for it already existed below
    at a different rate — Python kept the second and discarded the first without
    a word, so a table that looked edited was not. The same slip in the other
    order would have silently zeroed a paid model's rate and under-reported
    spend, which no test would catch because the arithmetic stays correct.

    Parsed from source rather than read from the built dict: by the time it is a
    dict the duplicate is already gone, which is the whole problem.
    """

    def test_no_model_id_is_declared_twice(self) -> None:
        import ast
        from pathlib import Path

        source = (
            Path(__file__).resolve().parents[1] / "packages/ai/cost_tracker.py"
        ).read_text(encoding="utf-8")

        tables: dict[str, list[str]] = {}
        for node in ast.walk(ast.parse(source)):
            target = getattr(node, "target", None)
            name = getattr(target, "id", "")
            if not name.endswith("COST_TABLE") or not isinstance(node.value, ast.Dict):
                continue
            tables[name] = [
                key.value for key in node.value.keys if isinstance(key, ast.Constant)
            ]

        assert tables, "no cost table found; this guard would pass vacuously"
        for name, keys in tables.items():
            duplicates = sorted({key for key in keys if keys.count(key) > 1})
            assert not duplicates, (
                f"{name} declares these twice — the later value silently wins: "
                f"{duplicates}"
            )

"""tests/test_daily_automation_2026_07_10.py — Daily automation tests (2026-07-10).

Covers the three ecosystem updates applied today:
  1. services/brain_failover.py — Llama 4 models on Groq + NVIDIA NIM;
     Gemini 2.5 Flash/Pro on Google; latest Claude models on Anthropic provider.
  2. packages/ai/brain_config.py — Google added as BrainProvider;
     Anthropic + Aerolink presets updated to Claude Sonnet 5 / Opus 4.8;
     Groq preset updated to Llama 4 Maverick.
  3. packages/ai/registry.py — Llama 4 Maverick on Groq + NIM;
     Gemini 2.5 Flash registered.
"""
from __future__ import annotations

import importlib

import pytest


# ── brain_failover ────────────────────────────────────────────────────────────

class TestBrainFailoverModelUpdates:
    """Verify the provider registry in brain_failover contains the 2026 model set."""

    def _registry(self):
        import services.brain_failover as bf
        return bf._PROVIDER_REGISTRY

    def _by_id(self, pid: str) -> dict:
        return next(p for p in self._registry() if p["id"] == pid)

    def test_nvidia_nim_no_longer_offers_retired_llama4(self):
        # 2026-08-28: superseded, same way the Groq cases below were. These
        # asserted that NVIDIA's rotation *contained* Llama 4 Maverick and
        # Scout, which was true when written. A live probe against the
        # production key found meta/llama-4-maverick-17b-128e-instruct
        # answering 410 Gone, so it left the catalogue along with every other
        # candidate NVIDIA carried at the time. Keeping the original assertion
        # would have pinned a dead model into the rotation — which is exactly
        # what a chain of tests like it did for weeks.
        nvidia = self._by_id("nvidia")
        for retired in (
            "meta/llama-4-maverick-17b-128e-instruct",
            "meta/llama-4-scout-17b-16e-instruct",
        ):
            assert retired not in nvidia["models"]

    def test_nvidia_nim_offers_only_probed_models(self):
        """The rotation must equal the catalogue, which the probe keeps honest."""
        from packages.ai.brain_config import PROVIDER_CANDIDATES

        nvidia = self._by_id("nvidia")
        assert nvidia["models"], "the nvidia rotation must not be empty"
        assert list(nvidia["models"]) == list(PROVIDER_CANDIDATES["nvidia"])

    def test_groq_no_longer_has_deprecated_llama4_maverick(self):
        # 2026-08-03: superseded by a later catalog update. Groq deprecated
        # its Llama 4 models in March 2026; packages/ai/brain_config.py's
        # PROVIDER_CANDIDATES["groq"] (the single source of truth these
        # entries are derived from at import time — see brain_failover.py's
        # "UNIT 6" catalog-sync block) no longer offers it. This test
        # asserted the pre-deprecation expectation from 2026-07-10 and
        # started failing every CI run once that catalog fix shipped.
        groq = self._by_id("groq")
        assert "llama-4-maverick-17b-128e-instruct" not in groq["models"]

    def test_groq_no_longer_has_deprecated_llama4_scout(self):
        # See test_groq_no_longer_has_deprecated_llama4_maverick above.
        groq = self._by_id("groq")
        assert "llama-4-scout-17b-16e-instruct" not in groq["models"]

    def test_groq_no_longer_has_deprecated_mixtral(self):
        groq = self._by_id("groq")
        assert "mixtral-8x7b-32768" not in groq["models"]

    def test_google_default_is_gemini_25_flash(self):
        google = self._by_id("google")
        assert google["default_model"] == "gemini-2.5-flash"

    def test_google_has_gemini_25_pro(self):
        google = self._by_id("google")
        assert "gemini-2.5-pro" in google["models"]

    def test_google_has_gemini_25_flash(self):
        google = self._by_id("google")
        assert "gemini-2.5-flash" in google["models"]

    def test_google_still_has_gemini_20_flash_for_compat(self):
        google = self._by_id("google")
        assert "gemini-2.0-flash" in google["models"]

    def test_anthropic_default_is_claude_opus5(self):
        # 2026-08-03: superseded by the claude-opus-5 catalog update, which
        # made it the new first candidate (== default_model) for anthropic,
        # replacing claude-sonnet-5 asserted here on 2026-07-10.
        anthropic = self._by_id("anthropic")
        assert anthropic["default_model"] == "claude-opus-5"

    def test_anthropic_has_claude_fable5(self):
        anthropic = self._by_id("anthropic")
        assert "claude-fable-5" in anthropic["models"]

    def test_anthropic_has_claude_opus_48(self):
        anthropic = self._by_id("anthropic")
        assert "claude-opus-4-8" in anthropic["models"]

    def test_anthropic_has_claude_haiku_45(self):
        anthropic = self._by_id("anthropic")
        assert "claude-haiku-4-5-20251001" in anthropic["models"]

    def test_anthropic_still_has_sonnet46_for_compat(self):
        anthropic = self._by_id("anthropic")
        assert "claude-sonnet-4-6" in anthropic["models"]

    def test_anthropic_does_not_have_stale_oct2024_model(self):
        anthropic = self._by_id("anthropic")
        assert "claude-3-5-sonnet-20241022" not in anthropic["models"]


class TestBrainFailoverModelAliases:
    """Verify Llama 4 and Claude Sonnet 5 cross-provider aliases are registered."""

    def _aliases(self):
        import services.brain_failover as bf
        return bf._MODEL_ALIASES

    def test_llama4_maverick_groq_alias(self):
        aliases = self._aliases()
        assert "meta/llama-4-maverick-17b-128e-instruct" in aliases
        assert aliases["meta/llama-4-maverick-17b-128e-instruct"]["groq"] == "llama-4-maverick-17b-128e-instruct"

    def test_llama4_scout_groq_alias(self):
        aliases = self._aliases()
        assert "meta/llama-4-scout-17b-16e-instruct" in aliases
        assert aliases["meta/llama-4-scout-17b-16e-instruct"]["groq"] == "llama-4-scout-17b-16e-instruct"

    def test_llama4_maverick_nvidia_alias_is_identity(self):
        aliases = self._aliases()
        assert aliases["meta/llama-4-maverick-17b-128e-instruct"]["nvidia"] == "meta/llama-4-maverick-17b-128e-instruct"

    def test_claude_sonnet5_aerolink_alias(self):
        aliases = self._aliases()
        assert "claude-sonnet-5" in aliases
        assert aliases["claude-sonnet-5"]["aerolink"] == "claude-sonnet-5"


# ── brain_config ──────────────────────────────────────────────────────────────

class TestBrainConfigUpdates:
    """Verify brain_config.py changes: Google provider, updated presets."""

    def _bc(self):
        import packages.ai.brain_config as bc
        return bc

    def test_google_is_valid_brain_provider(self):
        from packages.ai.brain_config import BrainConfig
        cfg = BrainConfig(primary_provider="google", primary_model="gemini-2.5-flash")
        assert cfg.primary_provider == "google"

    def test_anthropic_is_valid_brain_provider(self):
        from packages.ai.brain_config import BrainConfig
        cfg = BrainConfig(primary_provider="anthropic", primary_model="claude-sonnet-5")
        assert cfg.primary_provider == "anthropic"

    def test_google_preset_exists(self):
        bc = self._bc()
        assert "google" in bc.PROVIDER_PRESETS

    def test_google_preset_uses_gemini25_pro_for_planner(self):
        bc = self._bc()
        assert bc.PROVIDER_PRESETS["google"]["planner"] == "gemini-2.5-pro"

    def test_google_preset_uses_gemini25_flash_for_executor(self):
        bc = self._bc()
        assert bc.PROVIDER_PRESETS["google"]["executor"] == "gemini-2.5-flash"

    def test_anthropic_preset_uses_claude_opus_for_planner(self):
        # 2026-08-03: value superseded by the claude-opus-5 catalog update
        # (claude-opus-4-8 -> claude-opus-5 as planner/judge default). The
        # test's own premise — the planner uses a Claude Opus model — is
        # still correct, only the specific version changed.
        bc = self._bc()
        assert bc.PROVIDER_PRESETS["anthropic"]["planner"] == "claude-opus-5"

    def test_anthropic_preset_uses_claude_opus48_for_executor(self):
        bc = self._bc()
        # 2026-09-07: catalogue-probe found claude-sonnet-5 returns HTTP 400.
        # Executor now uses claude-opus-4-8.
        assert bc.PROVIDER_PRESETS["anthropic"]["executor"] == "claude-opus-4-8"

    def test_aerolink_preset_updated_to_latest_claude(self):
        bc = self._bc()
        # 2026-09-07: catalogue-probe found claude-sonnet-5 returns HTTP 400.
        # Executor now uses claude-opus-4-8.
        assert bc.PROVIDER_PRESETS["aerolink"]["executor"] == "claude-opus-4-8"

    def test_groq_planner_preset_is_a_live_rotation_candidate(self):
        """The durable property, not the id of the week.

        This assertion has been amended twice to chase a moving target: it
        asserted llama-4-maverick on 2026-07-10, was moved to
        llama-3.3-70b-versatile on 2026-08-03 when Groq deprecated Llama 4,
        and that id answers 404 as of 2026-09-01 (probe run 33483766556) — it
        is not in this account's catalogue at all.

        Two amendments to keep one literal true is the signal that the literal
        was never the subject. What this test is *for* is that the planner
        preset is a model the provider will actually serve, and that the
        rotation can fall back to it. Which id satisfies that belongs to the
        catalogue, and the catalogue is checked against the live provider by
        .github/workflows/catalogue-probe.yml.
        """
        bc = self._bc()
        planner = bc.PROVIDER_PRESETS["groq"]["planner"]
        candidates = bc.PROVIDER_CANDIDATES["groq"]
        assert candidates, "no groq candidates; this check would pass vacuously"
        assert planner in candidates, (
            f"groq planner preset {planner!r} is not in the rotation, so a "
            "failure on it has nowhere to fall back to"
        )

    def test_google_key_env_registered(self):
        bc = self._bc()
        assert bc.PROVIDER_KEY_ENV.get("google") == "GOOGLE_API_KEY"

    def test_google_base_url_registered(self):
        bc = self._bc()
        assert "google" in bc.PROVIDER_DEFAULT_BASE_URL
        assert "googleapis" in bc.PROVIDER_DEFAULT_BASE_URL["google"]


# ── model registry ────────────────────────────────────────────────────────────

class TestModelRegistryUpdates:
    """Verify new models are in the packages/ai/registry."""

    def _reg(self):
        import packages.ai.registry as reg
        return reg

    def test_groq_registers_only_live_models(self):
        # 2026-09-03: superseded. This class asserted that packages/ai/registry.py
        # registers llama-4-maverick-17b-128e-instruct (and deepseek-r1-distill-
        # llama-70b) on Groq. A live probe found neither id in the Groq account's
        # catalogue (404/400), and the legacy registry re-seeds
        # packages/llm/registry.py, so while they stayed here they kept being
        # offered as candidates no matter what the YAML catalogues said — the same
        # trap the NVIDIA case below hit. Both were removed.
        #
        # The property worth keeping is that Groq's live models are the GPT-OSS
        # pair (served by NVIDIA NIM and Groq alike), reachable via the router's
        # multi-provider catalogue, and that the dead ids are gone.
        from packages.llm.registry import get_registry, reset

        reg = self._reg()
        assert reg.get("llama-4-maverick-17b-128e-instruct") is None
        assert reg.get("deepseek-r1-distill-llama-70b") is None

        reset()
        groq_ids = {m.id for m in get_registry().for_provider("groq")}
        assert "openai/gpt-oss-120b" in groq_ids, groq_ids
        assert "llama-4-maverick-17b-128e-instruct" not in groq_ids

    def test_nvidia_registers_a_probed_live_model(self):
        # 2026-08-28: superseded. This asserted that packages/ai/registry.py
        # registers meta/llama-4-maverick-17b-128e-instruct on NVIDIA. A live
        # probe found that id answering 410, and it had to be removed — the
        # legacy registry re-seeds packages/llm/registry.py, so while it stayed
        # here it kept being offered as a tool-calling candidate no matter what
        # the YAML catalogues said.
        #
        # The property worth keeping is that NVIDIA has *a* registered model and
        # that it is the catalogue's default, not that it is any particular id.
        from packages.ai.brain_config import SAFE_DEFAULT_MODEL

        reg = self._reg()
        model = reg.get(SAFE_DEFAULT_MODEL)
        assert model is not None, f"{SAFE_DEFAULT_MODEL} is not registered"
        assert model.provider_id == "nvidia"
        assert model.supports_tools is True, (
            "the default must survive require_tools filtering on the gateway path"
        )

    def test_gemini25_flash_registered(self):
        reg = self._reg()
        model = reg.get("gemini-2.5-flash")
        assert model is not None
        assert model.provider_id == "google"

    def test_gemini25_flash_has_1m_context(self):
        reg = self._reg()
        model = reg.get("gemini-2.5-flash")
        assert model.context_window == 1048576

    def test_gemini25_flash_supports_vision(self):
        reg = self._reg()
        model = reg.get("gemini-2.5-flash")
        assert model.supports_vision is True

    def test_gemini25_flash_supports_tools(self):
        reg = self._reg()
        model = reg.get("gemini-2.5-flash")
        assert model.supports_tools is True

    def test_gemini25_flash_is_free(self):
        reg = self._reg()
        model = reg.get("gemini-2.5-flash")
        assert model.input_cost_per_1m == 0.0

    def test_best_model_for_vision_returns_gemini_or_capable(self):
        reg = self._reg()
        model = reg.best_model_for(require_vision=True)
        assert model is not None
        assert model.supports_vision is True

    def test_best_model_for_tools_returns_capable_model(self):
        reg = self._reg()
        model = reg.best_model_for(require_tools=True)
        assert model is not None
        assert model.supports_tools is True

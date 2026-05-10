"""Tests for the updated model name constants introduced in the model-upgrade PR.

Covers:
  - agent/loop.py   — DEFAULT_PLANNER_MODEL, DEFAULT_JUDGE_MODEL
  - .github/scripts/implement_agent.py — CANDIDATE_MODELS list
  - .github/scripts/review_agent.py   — hardcoded model name
"""
from __future__ import annotations

import importlib
import os
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────


def _reload_agent_loop(monkeypatch, *, nvidia_key: str | None) -> types.ModuleType:
    """Reload agent.loop with a controlled NVIDIA_API_KEY value.

    This is necessary because DEFAULT_PLANNER_MODEL and DEFAULT_JUDGE_MODEL are
    module-level constants evaluated at import time.  Re-importing after changing
    the env var exercises the conditional logic in the module.
    """
    if nvidia_key is None:
        monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
        monkeypatch.delenv("NVidiaApiKey", raising=False)
    else:
        monkeypatch.setenv("NVIDIA_API_KEY", nvidia_key)
        monkeypatch.delenv("NVidiaApiKey", raising=False)

    # Remove any explicit AGENT_PLANNER_MODEL / AGENT_JUDGE_MODEL overrides so
    # the module falls through to its conditional default logic.
    monkeypatch.delenv("AGENT_PLANNER_MODEL", raising=False)
    monkeypatch.delenv("AGENT_EXECUTOR_MODEL", raising=False)
    monkeypatch.delenv("AGENT_VERIFIER_MODEL", raising=False)
    monkeypatch.delenv("AGENT_JUDGE_MODEL", raising=False)

    import agent.loop as loop_mod
    importlib.reload(loop_mod)
    return loop_mod


# ── agent/loop.py — DEFAULT_PLANNER_MODEL ─────────────────────────────────────


class TestAgentLoopPlannerModel:
    def test_planner_model_with_nvidia_key_is_nemotron_ultra(self, monkeypatch):
        """DEFAULT_PLANNER_MODEL must be nemotron-ultra-253b-v1 when NVIDIA_API_KEY is set."""
        loop = _reload_agent_loop(monkeypatch, nvidia_key="test-key")
        assert loop.DEFAULT_PLANNER_MODEL == "nvidia/llama-3.1-nemotron-ultra-253b-v1"

    def test_planner_model_without_nvidia_key_is_deepseek(self, monkeypatch):
        """DEFAULT_PLANNER_MODEL must fall back to deepseek-r1:32b without NVIDIA_API_KEY."""
        loop = _reload_agent_loop(monkeypatch, nvidia_key=None)
        assert loop.DEFAULT_PLANNER_MODEL == "deepseek-r1:32b"

    def test_planner_model_env_override_takes_precedence(self, monkeypatch):
        """AGENT_PLANNER_MODEL env var must override the auto-detected default."""
        monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
        monkeypatch.setenv("AGENT_PLANNER_MODEL", "custom-planner:latest")
        import agent.loop as loop_mod
        importlib.reload(loop_mod)
        assert loop_mod.DEFAULT_PLANNER_MODEL == "custom-planner:latest"

    def test_planner_model_is_not_old_nemotron_70b(self, monkeypatch):
        """Regression: DEFAULT_PLANNER_MODEL must not reference the retired 70B model."""
        loop = _reload_agent_loop(monkeypatch, nvidia_key="test-key")
        assert "nemotron-70b" not in loop.DEFAULT_PLANNER_MODEL

    def test_planner_model_with_nvidiaApiKey_env_var(self, monkeypatch):
        """DEFAULT_PLANNER_MODEL respects the alternative NVidiaApiKey spelling."""
        monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
        monkeypatch.setenv("NVidiaApiKey", "test-key-alt")
        monkeypatch.delenv("AGENT_PLANNER_MODEL", raising=False)
        monkeypatch.delenv("AGENT_JUDGE_MODEL", raising=False)

        import agent.loop as loop_mod
        importlib.reload(loop_mod)
        assert loop_mod.DEFAULT_PLANNER_MODEL == "nvidia/llama-3.1-nemotron-ultra-253b-v1"


# ── agent/loop.py — DEFAULT_JUDGE_MODEL ───────────────────────────────────────


class TestAgentLoopJudgeModel:
    def test_judge_model_with_nvidia_key_is_nemotron_ultra(self, monkeypatch):
        """DEFAULT_JUDGE_MODEL must be nemotron-ultra-253b-v1 when NVIDIA_API_KEY is set."""
        loop = _reload_agent_loop(monkeypatch, nvidia_key="test-key")
        assert loop.DEFAULT_JUDGE_MODEL == "nvidia/llama-3.1-nemotron-ultra-253b-v1"

    def test_judge_model_without_nvidia_key_falls_back(self, monkeypatch):
        """DEFAULT_JUDGE_MODEL must fall back to a non-nvidia model without NVIDIA_API_KEY."""
        loop = _reload_agent_loop(monkeypatch, nvidia_key=None)
        # Judge falls back to DEFAULT_VERIFIER_MODEL which is deepseek-r1:32b in local mode
        assert "nvidia" not in loop.DEFAULT_JUDGE_MODEL

    def test_judge_model_env_override(self, monkeypatch):
        """AGENT_JUDGE_MODEL env var must override the auto-detected default."""
        monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
        monkeypatch.setenv("AGENT_JUDGE_MODEL", "custom-judge:8b")
        import agent.loop as loop_mod
        importlib.reload(loop_mod)
        assert loop_mod.DEFAULT_JUDGE_MODEL == "custom-judge:8b"

    def test_judge_model_is_not_old_nemotron_70b(self, monkeypatch):
        """Regression: DEFAULT_JUDGE_MODEL must not reference the retired 70B model."""
        loop = _reload_agent_loop(monkeypatch, nvidia_key="test-key")
        assert "nemotron-70b" not in loop.DEFAULT_JUDGE_MODEL

    def test_default_judge_model_constant_exists(self):
        """DEFAULT_JUDGE_MODEL must be a module-level constant in agent.loop."""
        import agent.loop as loop_mod
        assert hasattr(loop_mod, "DEFAULT_JUDGE_MODEL")
        assert isinstance(loop_mod.DEFAULT_JUDGE_MODEL, str)
        assert loop_mod.DEFAULT_JUDGE_MODEL  # non-empty


# ── .github/scripts/implement_agent.py — CANDIDATE_MODELS ─────────────────────


class TestImplementAgentCandidateModels:
    """Tests for CANDIDATE_MODELS in .github/scripts/implement_agent.py.

    The script imports openai at the top level; we stub that module before
    loading the script so tests work without the package installed.
    """

    @pytest.fixture(autouse=True)
    def _stub_openai(self):
        """Inject a minimal openai stub into sys.modules before importing the script."""
        if "openai" not in sys.modules:
            openai_stub = types.ModuleType("openai")
            openai_stub.OpenAI = MagicMock
            openai_stub.NotFoundError = Exception
            openai_stub.PermissionDeniedError = Exception
            sys.modules["openai"] = openai_stub
            self._openai_was_stubbed = True
        else:
            self._openai_was_stubbed = False
        yield
        if self._openai_was_stubbed:
            sys.modules.pop("openai", None)

    def _load_implement_agent(self) -> types.ModuleType:
        """Load (or reload) the implement_agent script as a module."""
        scripts_dir = str(Path(__file__).resolve().parents[1] / ".github" / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        if "implement_agent" in sys.modules:
            return importlib.reload(sys.modules["implement_agent"])
        spec = importlib.util.spec_from_file_location(
            "implement_agent",
            Path(__file__).resolve().parents[1] / ".github" / "scripts" / "implement_agent.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sys.modules["implement_agent"] = mod
        return mod

    def test_candidate_models_has_three_entries(self):
        mod = self._load_implement_agent()
        assert len(mod.CANDIDATE_MODELS) == 3

    def test_first_candidate_is_nemotron_ultra_253b(self):
        """The primary (reasoning) candidate must be the updated nemotron-ultra-253b-v1."""
        mod = self._load_implement_agent()
        first_id, first_label = mod.CANDIDATE_MODELS[0]
        assert first_id == "nvidia/llama-3.1-nemotron-ultra-253b-v1"
        assert "253" in first_label or "ultra" in first_label.lower()

    def test_second_candidate_is_qwen3_coder_480b(self):
        """The second candidate must be the upgraded qwen3-coder-480b model."""
        mod = self._load_implement_agent()
        second_id, second_label = mod.CANDIDATE_MODELS[1]
        assert second_id == "qwen/qwen3-coder-480b-a35b-instruct"

    def test_third_candidate_is_qwen25_coder_32b(self):
        """The third (fallback) candidate is the stable qwen2.5-coder-32b."""
        mod = self._load_implement_agent()
        third_id, _ = mod.CANDIDATE_MODELS[2]
        assert third_id == "qwen/qwen2.5-coder-32b-instruct"

    def test_no_old_nemotron_70b_in_candidate_models(self):
        """Regression: the retired nemotron-70b must not appear in CANDIDATE_MODELS."""
        mod = self._load_implement_agent()
        for model_id, _ in mod.CANDIDATE_MODELS:
            assert "nemotron-70b" not in model_id

    def test_no_old_qwen25_coder_nvidia_in_primary_slot(self):
        """Regression: old nvidia/qwen2.5-coder-32b-instruct must not be the primary model."""
        mod = self._load_implement_agent()
        first_id, _ = mod.CANDIDATE_MODELS[0]
        assert first_id != "nvidia/qwen2.5-coder-32b-instruct"


# ── .github/scripts/review_agent.py — hardcoded model ────────────────────────


class TestReviewAgentModel:
    """Tests for the model name used in review_agent.py's main() call."""

    @pytest.fixture(autouse=True)
    def _stub_openai(self):
        if "openai" not in sys.modules:
            openai_stub = types.ModuleType("openai")
            openai_stub.OpenAI = MagicMock
            sys.modules["openai"] = openai_stub
            self._openai_was_stubbed = True
        else:
            self._openai_was_stubbed = False
        yield
        if self._openai_was_stubbed:
            sys.modules.pop("openai", None)

    def _load_review_agent(self) -> types.ModuleType:
        scripts_dir = str(Path(__file__).resolve().parents[1] / ".github" / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        spec = importlib.util.spec_from_file_location(
            "review_agent",
            Path(__file__).resolve().parents[1] / ".github" / "scripts" / "review_agent.py",
        )
        mod = importlib.util.module_from_spec(spec)
        # Remove stale cached version so we get a fresh load each time
        sys.modules.pop("review_agent", None)
        spec.loader.exec_module(mod)
        sys.modules["review_agent"] = mod
        return mod

    def test_review_agent_uses_nemotron_ultra_253b(self):
        """main() in review_agent.py must call the updated nemotron-ultra-253b-v1 model."""
        mod = self._load_review_agent()
        # Inspect the source to confirm the model string (avoids executing main())
        source = Path(__file__).resolve().parents[1].joinpath(
            ".github", "scripts", "review_agent.py"
        ).read_text()
        assert "nvidia/llama-3.1-nemotron-ultra-253b-v1" in source

    def test_review_agent_does_not_use_old_70b_model(self):
        """Regression: review_agent.py must not reference the retired nemotron-70b."""
        source = Path(__file__).resolve().parents[1].joinpath(
            ".github", "scripts", "review_agent.py"
        ).read_text()
        assert "nemotron-70b" not in source
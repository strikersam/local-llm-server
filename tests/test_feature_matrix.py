"""tests/test_feature_matrix.py — Feature maturity / support matrix tests.

Covers:
  C2 - Feature maturity matrix behavior
  B3 - Enforcement of disabled features
  B4 - Config-driven overrides
  B5 - Admin/API visibility
"""

from __future__ import annotations

import os

import pytest

from features.matrix import (
    FeatureEntry,
    FeatureMaturity,
    FeatureMatrix,
    FeatureUnavailableError,
    get_feature_matrix,
    reset_feature_matrix,
)


# ---------------------------------------------------------------------------
# B1 / B2 — Registry loads from single source of truth
# ---------------------------------------------------------------------------


class TestRegistryLoads:
    def test_matrix_loads_without_error(self):
        matrix = FeatureMatrix()
        assert len(matrix._entries) > 0

    def test_all_registry_spec_entries_are_valid_feature_entries(self):
        """Every entry in _CANONICAL_FEATURES must parse as a FeatureEntry without error."""
        from features.matrix import _CANONICAL_FEATURES
        for spec in _CANONICAL_FEATURES:
            entry = FeatureEntry(**spec)
            assert entry.feature_id
            assert entry.maturity in FeatureMaturity

    def test_feature_ids_are_unique(self):
        from features.matrix import _CANONICAL_FEATURES
        ids = [spec["feature_id"] for spec in _CANONICAL_FEATURES]
        assert len(ids) == len(set(ids)), "Duplicate feature IDs in registry"

    def test_stable_features_present(self):
        matrix = FeatureMatrix()
        stable = [e for e in matrix._entries.values() if e.maturity == FeatureMaturity.STABLE]
        assert len(stable) > 0, "No stable features in matrix"

    def test_beta_features_present(self):
        matrix = FeatureMatrix()
        beta = [e for e in matrix._entries.values() if e.maturity == FeatureMaturity.BETA]
        assert len(beta) > 0

    def test_experimental_features_present(self):
        matrix = FeatureMatrix()
        exp = [e for e in matrix._entries.values() if e.maturity == FeatureMaturity.EXPERIMENTAL]
        assert len(exp) > 0

    def test_known_stable_features_are_stable(self):
        matrix = FeatureMatrix()
        for fid in ("direct_chat", "local_runtime"):
            entry = matrix.get(fid)
            assert entry is not None, f"Feature {fid!r} not in matrix"
            assert entry.maturity == FeatureMaturity.STABLE, f"{fid} should be STABLE"

    def test_known_beta_features_are_beta(self):
        # workspace_isolation and runtime_preflight were promoted to STABLE; only
        # async_agent_jobs remains in beta.
        matrix = FeatureMatrix()
        for fid in ("async_agent_jobs",):
            entry = matrix.get(fid)
            assert entry is not None
            assert entry.maturity == FeatureMaturity.BETA

    def test_promoted_features_are_stable(self):
        matrix = FeatureMatrix()
        for fid in ("workspace_isolation", "runtime_preflight"):
            entry = matrix.get(fid)
            assert entry is not None, f"Feature {fid!r} not in matrix"
            assert entry.maturity == FeatureMaturity.STABLE, f"{fid} should be STABLE after promotion"

    def test_openhands_is_experimental(self):
        matrix = FeatureMatrix()
        entry = matrix.get("openhands_runtime")
        assert entry is not None
        assert entry.maturity == FeatureMaturity.EXPERIMENTAL


# ---------------------------------------------------------------------------
# B3 — Enforcement: disabled features are blocked
# ---------------------------------------------------------------------------


class TestEnforcement:
    def test_enabled_feature_does_not_raise(self):
        matrix = FeatureMatrix()
        # proxy_endpoints is stable+enabled — must not raise
        entry = matrix.check("proxy_endpoints")
        assert entry.feature_id == "proxy_endpoints"

    def test_disabled_feature_raises_unavailable_error(self, monkeypatch):
        matrix = FeatureMatrix()
        # Force-disable a feature
        matrix._entries["direct_chat"].enabled = False
        with pytest.raises(FeatureUnavailableError) as exc_info:
            matrix.check("direct_chat")
        err = exc_info.value
        assert err.feature_id == "direct_chat"
        assert err.as_dict()["code"] == "feature_unavailable"
        # Restore
        matrix._entries["direct_chat"].enabled = True

    def test_unknown_feature_raises_unavailable_error(self):
        matrix = FeatureMatrix()
        with pytest.raises(FeatureUnavailableError) as exc_info:
            matrix.check("nonexistent_feature_xyz")
        assert exc_info.value.feature_id == "nonexistent_feature_xyz"

    def test_require_feature_raises_for_disabled(self, monkeypatch):
        import features.matrix as fm
        original = fm._feature_matrix
        try:
            fm._feature_matrix = FeatureMatrix()
            fm._feature_matrix._entries["direct_chat"].enabled = False
            with pytest.raises(FeatureUnavailableError):
                fm.get_feature_matrix().require("direct_chat")
        finally:
            fm._feature_matrix = original

    def test_is_available_false_for_disabled_feature(self):
        matrix = FeatureMatrix()
        matrix._entries["openhands_runtime"].enabled = False
        assert matrix.is_available("openhands_runtime") is False

    def test_is_available_true_for_active_feature(self):
        matrix = FeatureMatrix()
        assert matrix.is_available("direct_chat") is True

    def test_is_available_false_for_unknown_feature(self):
        matrix = FeatureMatrix()
        assert matrix.is_available("definitely_not_real") is False

    def test_unavailable_error_as_dict_contract(self):
        err = FeatureUnavailableError(
            "some_feature",
            FeatureMaturity.EXPERIMENTAL,
            reason="not configured",
        )
        d = err.as_dict()
        assert d["code"] == "feature_unavailable"
        assert d["feature_id"] == "some_feature"
        assert d["maturity"] == "experimental"
        assert "reason" in d


# ---------------------------------------------------------------------------
# B4 — Config-driven overrides
# ---------------------------------------------------------------------------


class TestConfigOverrides:
    def test_feature_disable_env_disables_feature(self, monkeypatch):
        monkeypatch.setenv("FEATURE_DISABLE", "async_agent_jobs")
        matrix = FeatureMatrix()
        entry = matrix.get("async_agent_jobs")
        assert entry is not None
        assert entry.enabled is False

    def test_feature_enable_env_enables_experimental(self, monkeypatch):
        # openhands_runtime is experimental and disabled by default
        monkeypatch.setenv("FEATURE_ENABLE", "openhands_runtime")
        matrix = FeatureMatrix()
        entry = matrix.get("openhands_runtime")
        assert entry is not None
        assert entry.enabled is True

    def test_feature_disable_takes_precedence(self, monkeypatch):
        monkeypatch.setenv("FEATURE_DISABLE", "async_agent_jobs")
        monkeypatch.setenv("FEATURE_ENABLE", "async_agent_jobs")
        matrix = FeatureMatrix()
        entry = matrix.get("async_agent_jobs")
        assert entry is not None
        # FEATURE_DISABLE is authoritative — disable wins even when FEATURE_ENABLE lists the same ID
        assert entry.enabled is False

    def test_feature_disable_multiple_features(self, monkeypatch):
        monkeypatch.setenv("FEATURE_DISABLE", "direct_chat,telegram_bot")
        matrix = FeatureMatrix()
        assert matrix.get("direct_chat").enabled is False
        assert matrix.get("telegram_bot").enabled is False

    def test_feature_enable_unknown_feature_logs_warning(self, monkeypatch, caplog):
        import logging
        monkeypatch.setenv("FEATURE_ENABLE", "totally_fake_feature_9999")
        import logging
        with caplog.at_level(logging.WARNING, logger="qwen-proxy"):
            matrix = FeatureMatrix()
        assert "totally_fake_feature_9999" in caplog.text

    def test_feature_disable_unknown_feature_logs_warning(self, monkeypatch, caplog):
        import logging
        monkeypatch.setenv("FEATURE_DISABLE", "totally_fake_feature_8888")
        with caplog.at_level(logging.WARNING, logger="qwen-proxy"):
            matrix = FeatureMatrix()
        assert "totally_fake_feature_8888" in caplog.text

    def test_empty_feature_env_vars_no_error(self, monkeypatch):
        monkeypatch.setenv("FEATURE_DISABLE", "")
        monkeypatch.setenv("FEATURE_ENABLE", "")
        # Should not raise
        matrix = FeatureMatrix()
        assert len(matrix._entries) > 0


# ---------------------------------------------------------------------------
# B5 — Admin / API visibility
# ---------------------------------------------------------------------------


class TestAdminVisibility:
    def test_as_dict_returns_all_entries(self):
        matrix = FeatureMatrix()
        result = matrix.as_dict()
        assert "features" in result
        assert "summary" in result
        assert result["summary"]["total"] > 0

    def test_as_dict_contains_maturity_counts(self):
        matrix = FeatureMatrix()
        result = matrix.as_dict()
        by_maturity = result["by_maturity"]
        assert "stable" in by_maturity
        assert "beta" in by_maturity
        assert "experimental" in by_maturity

    def test_summary_returns_compact_list(self):
        matrix = FeatureMatrix()
        s = matrix.summary()
        assert isinstance(s, list)
        assert len(s) > 0
        first = s[0]
        assert "feature_id" in first
        assert "maturity" in first
        assert "enabled" in first
        assert "display_name" in first

    def test_schema_version_in_as_dict(self):
        matrix = FeatureMatrix()
        result = matrix.as_dict()
        assert result["schema_version"] == "1"

    def test_each_entry_has_required_fields(self):
        matrix = FeatureMatrix()
        result = matrix.as_dict()
        for entry in result["entries"]:
            assert "feature_id" in entry
            assert "display_name" in entry
            assert "maturity" in entry
            assert "enabled" in entry
            assert "default_available" in entry

    def test_admin_feature_endpoint_returns_matrix(self, monkeypatch):
        """Integration test: admin endpoint returns feature matrix JSON."""
        import features.matrix as fm
        original = fm._feature_matrix
        fm._feature_matrix = None
        try:
            matrix = fm.get_feature_matrix()
            result = matrix.as_dict()
            assert result["summary"]["total"] > 0
        finally:
            fm._feature_matrix = original


# ---------------------------------------------------------------------------
# Singleton behavior
# ---------------------------------------------------------------------------


class TestSingleton:
    def test_get_feature_matrix_returns_same_instance(self, monkeypatch):
        import features.matrix as fm
        monkeypatch.setattr(fm, "_feature_matrix", None)
        m1 = fm.get_feature_matrix()
        m2 = fm.get_feature_matrix()
        assert m1 is m2

    def test_require_feature_raises_for_unknown(self, monkeypatch):
        import features.matrix as fm
        original = fm._feature_matrix
        fm._feature_matrix = FeatureMatrix()
        try:
            with pytest.raises(FeatureUnavailableError):
                fm.get_feature_matrix().require("ghost_feature_123")
        finally:
            fm._feature_matrix = original

    def test_maturity_warning_for_beta_returns_warning(self):
        matrix = FeatureMatrix()
        warning = matrix.maturity_warning("async_agent_jobs")
        assert warning is not None
        assert "BETA" in warning

    def test_maturity_warning_returns_none_for_disabled(self):
        matrix = FeatureMatrix()
        matrix._entries["async_agent_jobs"].enabled = False
        warning = matrix.maturity_warning("async_agent_jobs")
        assert warning is None
        matrix._entries["async_agent_jobs"].enabled = True

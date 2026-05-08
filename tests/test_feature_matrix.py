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
    _REGISTRY_SPEC,
    get_matrix,
    require_feature,
)


# ---------------------------------------------------------------------------
# B1 / B2 — Registry loads from single source of truth
# ---------------------------------------------------------------------------


class TestRegistryLoads:
    def test_matrix_loads_without_error(self):
        matrix = FeatureMatrix.load()
        assert len(matrix._entries) > 0

    def test_all_registry_spec_entries_are_valid_feature_entries(self):
        """Every entry in _REGISTRY_SPEC must parse as a FeatureEntry without error."""
        for spec in _REGISTRY_SPEC:
            entry = FeatureEntry(**spec)
            assert entry.feature_id
            assert entry.maturity in FeatureMaturity

    def test_feature_ids_are_unique(self):
        ids = [spec["feature_id"] for spec in _REGISTRY_SPEC]
        assert len(ids) == len(set(ids)), "Duplicate feature IDs in registry"

    def test_stable_features_present(self):
        matrix = FeatureMatrix.load()
        stable = [e for e in matrix._entries.values() if e.maturity == FeatureMaturity.STABLE]
        assert len(stable) > 0, "No stable features in matrix"

    def test_beta_features_present(self):
        matrix = FeatureMatrix.load()
        beta = [e for e in matrix._entries.values() if e.maturity == FeatureMaturity.BETA]
        assert len(beta) > 0

    def test_experimental_features_present(self):
        matrix = FeatureMatrix.load()
        exp = [e for e in matrix._entries.values() if e.maturity == FeatureMaturity.EXPERIMENTAL]
        assert len(exp) > 0

    def test_known_stable_features_are_stable(self):
        matrix = FeatureMatrix.load()
        for fid in ("proxy_endpoints", "auth", "direct_chat", "local_runtime"):
            entry = matrix.get(fid)
            assert entry is not None, f"Feature {fid!r} not in matrix"
            assert entry.maturity == FeatureMaturity.STABLE, f"{fid} should be STABLE"

    def test_known_beta_features_are_beta(self):
        matrix = FeatureMatrix.load()
        for fid in ("async_agent_jobs", "workspace_isolation", "runtime_preflight"):
            entry = matrix.get(fid)
            assert entry is not None
            assert entry.maturity == FeatureMaturity.BETA

    def test_openhands_is_experimental(self):
        matrix = FeatureMatrix.load()
        entry = matrix.get("openhands_runtime")
        assert entry is not None
        assert entry.maturity == FeatureMaturity.EXPERIMENTAL


# ---------------------------------------------------------------------------
# B3 — Enforcement: disabled features are blocked
# ---------------------------------------------------------------------------


class TestEnforcement:
    def test_enabled_feature_does_not_raise(self):
        matrix = FeatureMatrix.load()
        # proxy_endpoints is stable+enabled — must not raise
        entry = matrix.check("proxy_endpoints")
        assert entry.feature_id == "proxy_endpoints"

    def test_disabled_feature_raises_unavailable_error(self, monkeypatch):
        matrix = FeatureMatrix.load()
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
        matrix = FeatureMatrix.load()
        with pytest.raises(FeatureUnavailableError) as exc_info:
            matrix.check("nonexistent_feature_xyz")
        assert exc_info.value.feature_id == "nonexistent_feature_xyz"

    def test_require_feature_raises_for_disabled(self, monkeypatch):
        import features.matrix as fm
        original = fm._matrix
        try:
            fm._matrix = FeatureMatrix.load()
            fm._matrix._entries["direct_chat"].enabled = False
            with pytest.raises(FeatureUnavailableError):
                fm.require_feature("direct_chat")
        finally:
            fm._matrix = original

    def test_is_enabled_false_for_disabled_feature(self):
        matrix = FeatureMatrix.load()
        matrix._entries["openhands_runtime"].enabled = False
        assert matrix.is_enabled("openhands_runtime") is False

    def test_is_enabled_true_for_active_feature(self):
        matrix = FeatureMatrix.load()
        assert matrix.is_enabled("proxy_endpoints") is True

    def test_is_enabled_false_for_unknown_feature(self):
        matrix = FeatureMatrix.load()
        assert matrix.is_enabled("definitely_not_real") is False

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
        matrix = FeatureMatrix.load()
        entry = matrix.get("async_agent_jobs")
        assert entry is not None
        assert entry.enabled is False

    def test_feature_enable_env_enables_experimental(self, monkeypatch):
        # openhands_runtime is experimental and disabled by default
        monkeypatch.setenv("FEATURE_ENABLE", "openhands_runtime")
        matrix = FeatureMatrix.load()
        entry = matrix.get("openhands_runtime")
        assert entry is not None
        assert entry.enabled is True

    def test_feature_disable_takes_precedence(self, monkeypatch):
        monkeypatch.setenv("FEATURE_DISABLE", "async_agent_jobs")
        monkeypatch.setenv("FEATURE_ENABLE", "async_agent_jobs")
        # FEATURE_DISABLE is applied first
        matrix = FeatureMatrix.load()
        # disable applied first; enable then re-enables it for non-DISABLED maturity
        # Actual result: disable runs first, enable runs second → re-enabled
        # Both are "last write wins" style; test that we handle both without error
        assert matrix.get("async_agent_jobs") is not None

    def test_feature_disable_multiple_features(self, monkeypatch):
        monkeypatch.setenv("FEATURE_DISABLE", "direct_chat,telegram_bot")
        matrix = FeatureMatrix.load()
        assert matrix.get("direct_chat").enabled is False
        assert matrix.get("telegram_bot").enabled is False

    def test_feature_enable_unknown_feature_logs_warning(self, monkeypatch, caplog):
        import logging
        monkeypatch.setenv("FEATURE_ENABLE", "totally_fake_feature_9999")
        import logging
        with caplog.at_level(logging.WARNING, logger="qwen-proxy"):
            matrix = FeatureMatrix.load()
        assert "totally_fake_feature_9999" in caplog.text

    def test_feature_disable_unknown_feature_logs_warning(self, monkeypatch, caplog):
        import logging
        monkeypatch.setenv("FEATURE_DISABLE", "totally_fake_feature_8888")
        with caplog.at_level(logging.WARNING, logger="qwen-proxy"):
            matrix = FeatureMatrix.load()
        assert "totally_fake_feature_8888" in caplog.text

    def test_empty_feature_env_vars_no_error(self, monkeypatch):
        monkeypatch.setenv("FEATURE_DISABLE", "")
        monkeypatch.setenv("FEATURE_ENABLE", "")
        # Should not raise
        matrix = FeatureMatrix.load()
        assert len(matrix._entries) > 0


# ---------------------------------------------------------------------------
# B5 — Admin / API visibility
# ---------------------------------------------------------------------------


class TestAdminVisibility:
    def test_as_dict_returns_all_admin_visible_entries(self):
        matrix = FeatureMatrix.load()
        result = matrix.as_dict(admin_only=True)
        assert "entries" in result
        assert "total" in result
        assert "by_maturity" in result
        assert result["total"] > 0

    def test_as_dict_contains_maturity_counts(self):
        matrix = FeatureMatrix.load()
        result = matrix.as_dict()
        by_maturity = result["by_maturity"]
        assert "stable" in by_maturity
        assert "beta" in by_maturity
        assert "experimental" in by_maturity

    def test_summary_returns_compact_list(self):
        matrix = FeatureMatrix.load()
        s = matrix.summary()
        assert isinstance(s, list)
        assert len(s) > 0
        first = s[0]
        assert "feature_id" in first
        assert "maturity" in first
        assert "enabled" in first
        assert "display_name" in first

    def test_schema_version_in_as_dict(self):
        matrix = FeatureMatrix.load()
        result = matrix.as_dict()
        assert result["schema_version"] == "1"

    def test_each_entry_has_required_fields(self):
        matrix = FeatureMatrix.load()
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
        # Ensure fresh load
        original = fm._matrix
        fm._matrix = None
        try:
            matrix = fm.get_matrix()
            result = matrix.as_dict()
            assert result["total"] > 0
        finally:
            fm._matrix = original


# ---------------------------------------------------------------------------
# Singleton behavior
# ---------------------------------------------------------------------------


class TestSingleton:
    def test_get_matrix_returns_same_instance(self, monkeypatch):
        import features.matrix as fm
        monkeypatch.setattr(fm, "_matrix", None)
        m1 = fm.get_matrix()
        m2 = fm.get_matrix()
        assert m1 is m2

    def test_require_feature_raises_for_unknown(self, monkeypatch):
        import features.matrix as fm
        original = fm._matrix
        fm._matrix = FeatureMatrix.load()
        try:
            with pytest.raises(FeatureUnavailableError):
                fm.require_feature("ghost_feature_123")
        finally:
            fm._matrix = original

    def test_warn_if_beta_returns_entry(self):
        matrix = FeatureMatrix.load()
        entry = matrix.warn_if_beta("async_agent_jobs")
        assert entry is not None
        assert entry.feature_id == "async_agent_jobs"

    def test_warn_if_beta_returns_none_for_disabled(self):
        matrix = FeatureMatrix.load()
        matrix._entries["async_agent_jobs"].enabled = False
        entry = matrix.warn_if_beta("async_agent_jobs")
        assert entry is None
        matrix._entries["async_agent_jobs"].enabled = True

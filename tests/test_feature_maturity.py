"""Tests for feature maturity / support matrix (Area B).

Covers:
  - Matrix loads from single source of truth
  - stable/beta/experimental/disabled classification works
  - Disabled features are blocked with structured errors
  - Beta/experimental features return warnings
  - Config overrides enable/disable features correctly
  - Admin/API output reflects actual support state
"""

from __future__ import annotations

import os

import pytest

from features.matrix import (
    FeatureMaturity,
    FeatureMatrix,
    FeatureEntry,
    FeatureUnavailableError,
    get_feature_matrix,
    reset_feature_matrix,
)


# ── Matrix loading ────────────────────────────────────────────────────────────


class TestMatrixLoad:
    def test_matrix_loads_features(self):
        reset_feature_matrix()
        matrix = FeatureMatrix()
        entries = matrix.list_all()
        assert len(entries) > 0

    def test_matrix_has_stable_features(self):
        matrix = FeatureMatrix()
        stable = matrix.list_by_maturity(FeatureMaturity.STABLE)
        assert len(stable) > 0
        # Core features must be stable
        stable_ids = {e.feature_id for e in stable}
        assert "direct_chat" in stable_ids
        assert "openai_compat" in stable_ids
        assert "provider_routing_fallback" in stable_ids

    def test_matrix_has_beta_features(self):
        matrix = FeatureMatrix()
        beta = matrix.list_by_maturity(FeatureMaturity.BETA)
        assert len(beta) > 0
        beta_ids = {e.feature_id for e in beta}
        assert "async_agent_jobs" in beta_ids

    def test_matrix_has_experimental_features(self):
        matrix = FeatureMatrix()
        exp = matrix.list_by_maturity(FeatureMaturity.EXPERIMENTAL)
        assert len(exp) > 0
        exp_ids = {e.feature_id for e in exp}
        assert "openhands_runtime" in exp_ids

    def test_matrix_loads_from_single_source(self):
        """All features come from _CANONICAL_FEATURES."""
        matrix = FeatureMatrix()
        for entry in matrix.list_all():
            assert entry.feature_id
            assert entry.display_name
            assert isinstance(entry.maturity, FeatureMaturity)


# ── Classification ────────────────────────────────────────────────────────────


class TestClassification:
    def test_stable_features_are_enabled_by_default(self):
        matrix = FeatureMatrix()
        stable = matrix.list_by_maturity(FeatureMaturity.STABLE)
        for entry in stable:
            assert entry.enabled, f"Stable feature {entry.feature_id} should be enabled"

    def test_direct_chat_is_stable(self):
        matrix = FeatureMatrix()
        entry = matrix.get("direct_chat")
        assert entry is not None
        assert entry.maturity == FeatureMaturity.STABLE
        assert entry.enabled

    def test_openhands_is_experimental(self):
        matrix = FeatureMatrix()
        entry = matrix.get("openhands_runtime")
        assert entry is not None
        assert entry.maturity == FeatureMaturity.EXPERIMENTAL


# ── Disabled feature gating ───────────────────────────────────────────────────


class TestDisabledFeatures:
    def test_disabled_feature_raises_unavailable(self):
        matrix = FeatureMatrix(config_overrides={"FEATURE_OPENHANDS_RUNTIME": "disabled"})
        with pytest.raises(FeatureUnavailableError) as exc_info:
            matrix.check_available("openhands_runtime")
        assert exc_info.value.feature_id == "openhands_runtime"

    def test_disabled_feature_not_in_enabled_list(self):
        matrix = FeatureMatrix(config_overrides={"FEATURE_DIRECT_CHAT": "disabled"})
        enabled_ids = {e.feature_id for e in matrix.list_enabled()}
        assert "direct_chat" not in enabled_ids

    def test_is_available_returns_false_for_disabled(self):
        matrix = FeatureMatrix(config_overrides={"FEATURE_TELEGRAM_BOT": "disabled"})
        assert matrix.is_available("telegram_bot") is False

    def test_is_available_returns_true_for_stable(self):
        matrix = FeatureMatrix()
        assert matrix.is_available("direct_chat") is True

    def test_unavailable_feature_structured_error(self):
        matrix = FeatureMatrix(config_overrides={"FEATURE_TUNNELS": "disabled"})
        with pytest.raises(FeatureUnavailableError) as exc_info:
            matrix.check_available("tunnels")
        err_dict = exc_info.value.as_dict()
        assert err_dict["code"] == "feature_unavailable"
        assert err_dict["feature_id"] == "tunnels"
        assert "fix_hint" in err_dict

    def test_nonexistent_feature_raises(self):
        matrix = FeatureMatrix()
        with pytest.raises(FeatureUnavailableError):
            matrix.check_available("completely_nonexistent_feature")


# ── Warnings ──────────────────────────────────────────────────────────────────


class TestMaturityWarnings:
    def test_stable_feature_no_warning(self):
        matrix = FeatureMatrix()
        assert matrix.maturity_warning("direct_chat") is None

    def test_beta_feature_warning(self):
        matrix = FeatureMatrix()
        warning = matrix.maturity_warning("async_agent_jobs")
        assert warning is not None
        assert "BETA" in warning

    def test_experimental_feature_warning(self):
        matrix = FeatureMatrix()
        warning = matrix.maturity_warning("telegram_bot")
        assert warning is not None
        assert "EXPERIMENTAL" in warning


# ── Config overrides ──────────────────────────────────────────────────────────


class TestConfigOverrides:
    def test_env_override_to_disabled(self, monkeypatch):
        monkeypatch.setenv("FEATURE_TELEGRAM_BOT", "disabled")
        reset_feature_matrix()
        matrix = FeatureMatrix()
        entry = matrix.get("telegram_bot")
        assert entry.maturity == FeatureMaturity.DISABLED
        assert not entry.enabled
        reset_feature_matrix()

    def test_env_override_to_stable(self, monkeypatch):
        monkeypatch.setenv("FEATURE_TELEGRAM_BOT", "stable")
        reset_feature_matrix()
        matrix = FeatureMatrix()
        entry = matrix.get("telegram_bot")
        assert entry.maturity == FeatureMaturity.STABLE
        reset_feature_matrix()

    def test_env_override_enabled_false(self, monkeypatch):
        monkeypatch.setenv("FEATURE_ASYNC_AGENT_JOBS", "false")
        reset_feature_matrix()
        matrix = FeatureMatrix()
        entry = matrix.get("async_agent_jobs")
        assert entry.enabled is False
        reset_feature_matrix()

    def test_explicit_config_overrides(self):
        matrix = FeatureMatrix(config_overrides={"FEATURE_TUNNELS": "beta"})
        entry = matrix.get("tunnels")
        assert entry.maturity == FeatureMaturity.BETA


# ── Serialization ─────────────────────────────────────────────────────────────


class TestMatrixSerialization:
    def test_as_dict(self):
        matrix = FeatureMatrix()
        d = matrix.as_dict()
        assert "features" in d
        assert "summary" in d
        assert d["summary"]["total"] > 0
        assert d["summary"]["by_maturity"]["stable"] > 0

    def test_as_markdown_table(self):
        matrix = FeatureMatrix()
        md = matrix.as_markdown_table()
        assert "direct_chat" in md
        assert "stable" in md
        assert "| Feature |" in md


# ── Admin visibility ──────────────────────────────────────────────────────────


class TestAdminVisibility:
    def test_admin_visible_features(self):
        matrix = FeatureMatrix()
        visible = matrix.list_admin_visible()
        assert len(visible) > 0
        for entry in visible:
            assert entry.admin_visible is True

    def test_feature_entry_has_required_fields(self):
        matrix = FeatureMatrix()
        for entry in matrix.list_all():
            d = entry.as_dict()
            assert "feature_id" in d
            assert "display_name" in d
            assert "maturity" in d
            assert "enabled" in d
            assert "key_dependencies" in d
            assert "config_flags" in d
            assert "notes" in d


# ── Singleton ─────────────────────────────────────────────────────────────────


class TestFeatureMatrixSingleton:
    def test_get_feature_matrix_returns_instance(self):
        reset_feature_matrix()
        matrix = get_feature_matrix()
        assert isinstance(matrix, FeatureMatrix)

    def test_singleton_is_reused(self):
        reset_feature_matrix()
        m1 = get_feature_matrix()
        m2 = get_feature_matrix()
        assert m1 is m2
        reset_feature_matrix()


# ── Features API ──────────────────────────────────────────────────────────────


class TestFeaturesAPI:
    @pytest.fixture()
    def proxy_client(self):
        import proxy
        from fastapi.testclient import TestClient
        return TestClient(proxy.app)

    def test_features_list_endpoint(self, proxy_client):
        response = proxy_client.get("/admin/features")
        assert response.status_code == 200
        data = response.json()
        assert "features" in data
        assert "summary" in data

    def test_features_get_single(self, proxy_client):
        response = proxy_client.get("/admin/features/direct_chat")
        assert response.status_code == 200
        data = response.json()
        assert data["feature_id"] == "direct_chat"
        assert data["maturity"] == "stable"

    def test_features_get_not_found(self, proxy_client):
        response = proxy_client.get("/admin/features/nonexistent_feature")
        assert response.status_code == 404

    def test_features_check_available(self, proxy_client):
        response = proxy_client.post(
            "/admin/features/check",
            json={"feature_id": "direct_chat"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is True

    def test_features_check_unavailable(self, proxy_client, monkeypatch):
        monkeypatch.setenv("FEATURE_TELEGRAM_BOT", "disabled")
        reset_feature_matrix()
        response = proxy_client.post(
            "/admin/features/check",
            json={"feature_id": "telegram_bot"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is False
        reset_feature_matrix()

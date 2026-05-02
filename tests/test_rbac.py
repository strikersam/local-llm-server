"""tests/test_rbac.py — Unit tests for the RBAC module."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from unittest.mock import MagicMock

from rbac import (
    UserRole,
    Permission,
    ROLE_PERMISSIONS,
    ADMIN_ACTIVITY_PERMISSIONS,
    POWER_USER_ACTIVITY_PERMISSIONS,
    get_user_role,
    has_permission,
    is_admin,
    is_power_user_or_above,
    role_label,
    require_admin,
    require_power_user,
    require_permission,
    audit,
    get_audit_log,
    mask_secret,
    mask_dict,
)


# ── Role resolution ───────────────────────────────────────────────────────────

class TestGetUserRole:

    def test_power_user_role_from_dict(self):
        assert get_user_role({"role": "power_user"}) == UserRole.POWER_USER

    def test_role_label_admin(self):
        assert role_label({"role": "admin"}) == "Admin"

    def test_role_label_power_user(self):
        assert role_label({"role": "power_user"}) == "Power User"

    def test_role_label_user(self):
        assert role_label({"role": "user"}) == "User"

    def test_is_admin_true(self):
        assert is_admin({"role": "admin"}) is True

    def test_is_admin_false_for_power_user(self):
        assert is_admin({"role": "power_user"}) is False

    def test_is_power_user_or_above_true_for_admin(self):
        assert is_power_user_or_above({"role": "admin"}) is True

    def test_is_power_user_or_above_true_for_power_user(self):
        assert is_power_user_or_above({"role": "power_user"}) is True

    def test_is_power_user_or_above_false_for_user(self):
        assert is_power_user_or_above({"role": "user"}) is False


class TestGetUserRole_Orig:

    def test_admin_role_from_dict(self):
        assert get_user_role({"role": "admin"}) == UserRole.ADMIN

    def test_user_role_from_dict(self):
        assert get_user_role({"role": "user"}) == UserRole.USER

    def test_missing_role_defaults_to_user(self):
        assert get_user_role({}) == UserRole.USER

    def test_unknown_role_defaults_to_user(self):
        assert get_user_role({"role": "superuser"}) == UserRole.USER

    def test_role_from_object_attribute(self):
        user = MagicMock()
        user.role = "admin"
        assert get_user_role(user) == UserRole.ADMIN


# ── Permission checks ─────────────────────────────────────────────────────────

class TestHasPermission:

    def test_admin_has_all_permissions(self):
        admin = {"role": "admin"}
        for p in Permission:
            assert has_permission(admin, p), f"Admin should have {p}"

    def test_user_has_own_permissions(self):
        user = {"role": "user"}
        assert has_permission(user, Permission.MANAGE_OWN_TASKS)
        assert has_permission(user, Permission.MANAGE_OWN_AGENTS)
        assert has_permission(user, Permission.CREATE_OWN_API_KEYS)

    def test_user_lacks_admin_permissions(self):
        user = {"role": "user"}
        assert not has_permission(user, Permission.VIEW_AUDIT_LOGS)
        assert not has_permission(user, Permission.MANAGE_ALL_USERS)
        assert not has_permission(user, Permission.MANAGE_PROVIDERS_GLOBAL)

    def test_admin_activity_set_is_not_empty(self):
        assert len(ADMIN_ACTIVITY_PERMISSIONS) > 0

    def test_manage_all_api_keys_is_admin_activity(self):
        assert Permission.MANAGE_ALL_API_KEYS in ADMIN_ACTIVITY_PERMISSIONS

    def test_power_user_has_workspace_permissions(self):
        pu = {"role": "power_user"}
        assert has_permission(pu, Permission.VIEW_ALL_TASKS)
        assert has_permission(pu, Permission.MANAGE_WORKSPACE_AGENTS)
        assert has_permission(pu, Permission.VIEW_RUNTIME_HEALTH)
        assert has_permission(pu, Permission.VIEW_COST_INSIGHTS)

    def test_power_user_lacks_admin_permissions(self):
        pu = {"role": "power_user"}
        assert not has_permission(pu, Permission.MANAGE_ALL_USERS)
        assert not has_permission(pu, Permission.MANAGE_PROVIDERS_GLOBAL)
        assert not has_permission(pu, Permission.MANAGE_ROUTING_POLICY)

    def test_power_user_activity_set_is_not_empty(self):
        assert len(POWER_USER_ACTIVITY_PERMISSIONS) > 0

    def test_view_runtime_health_is_power_user_activity(self):
        assert Permission.VIEW_RUNTIME_HEALTH in POWER_USER_ACTIVITY_PERMISSIONS


# ── FastAPI dependencies ──────────────────────────────────────────────────────

class TestRequireAdmin:

    def _make_request(self, role: str = "admin"):
        req = MagicMock()
        req.state.user = {"role": role, "email": "test@test.com"}
        return req

    def test_admin_passes(self):
        req = self._make_request("admin")
        user = require_admin(req)
        assert user is not None

    def test_non_admin_raises_403(self):
        req = self._make_request("user")
        with pytest.raises(HTTPException) as exc_info:
            require_admin(req)
        assert exc_info.value.status_code == 403

    def test_no_user_raises_401(self):
        req = MagicMock()
        req.state.user = None
        with pytest.raises(HTTPException) as exc_info:
            require_admin(req)
        assert exc_info.value.status_code == 401

    def test_require_permission_dep(self):
        dep = require_permission(Permission.VIEW_AUDIT_LOGS)
        req = self._make_request("admin")
        dep(req)  # should not raise

    def test_require_permission_dep_blocks_user(self):
        dep = require_permission(Permission.VIEW_AUDIT_LOGS)
        req = self._make_request("user")
        with pytest.raises(HTTPException) as exc_info:
            dep(req)
        assert exc_info.value.status_code == 403

    def test_require_power_user_passes_for_power_user(self):
        req = self._make_request("power_user")
        user = require_power_user(req)
        assert user is not None

    def test_require_power_user_passes_for_admin(self):
        req = self._make_request("admin")
        user = require_power_user(req)
        assert user is not None

    def test_require_power_user_blocks_standard_user(self):
        req = self._make_request("user")
        with pytest.raises(HTTPException) as exc_info:
            require_power_user(req)
        assert exc_info.value.status_code == 403


# ── Audit log ─────────────────────────────────────────────────────────────────

class TestAuditLog:

    def test_audit_appends_entry(self):
        import rbac
        before = len(rbac._audit_log)
        user = {"role": "admin", "email": "admin@test.com"}
        audit("test_action", user, resource="api_keys", outcome="success")
        assert len(rbac._audit_log) > before

    def test_audit_entry_fields(self):
        import rbac
        user = {"role": "user", "email": "u@test.com"}
        audit("view_task", user, resource="task", resource_id="task_123")
        entry = rbac._audit_log[-1]
        assert entry["action"] == "view_task"
        assert entry["resource"] == "task"
        assert entry["resource_id"] == "task_123"

    def test_get_audit_log(self):
        user = {"role": "admin", "email": "a@b.com"}
        audit("test_get", user)
        log = get_audit_log(limit=100)
        assert isinstance(log, list)
        assert len(log) > 0

    def test_audit_extended_fields(self):
        import rbac
        user = {"role": "admin", "email": "admin@test.com"}
        audit(
            "test_extended",
            user,
            resource="repo",
            secrets_used=["secret_abc123"],
            runtime_machine="hermes@myhost",
            repo_workspace="https://github.com/example/repo",
            agent_id="agent_def456",
        )
        entry = rbac._audit_log[-1]
        assert entry["secrets_used"] == ["secret_abc123"]
        assert entry["runtime_machine"] == "hermes@myhost"
        assert entry["repo_workspace"] == "https://github.com/example/repo"
        assert entry["agent_id"] == "agent_def456"

    def test_audit_filter_by_user_id(self):
        import rbac
        user = {"role": "user", "email": "filter_test@test.com"}
        audit("test_filter", user)
        log = get_audit_log(limit=100, user_id="filter_test@test.com")
        assert all(e["user_id"] == "filter_test@test.com" for e in log)


# ── Secret masking ────────────────────────────────────────────────────────────

class TestMaskSecret:

    def test_masks_openai_key(self):
        key = "sk-proj-test-key-for-unit-testing-12345"
        result = mask_secret(key)
        assert "sk-p" in result
        assert "****" in result
        assert "abc123def456ghi789jkl" not in result

    def test_masks_github_pat(self):
        token = "ghp_" + "a" * 36
        result = mask_secret(token)
        assert "****" in result

    def test_plain_text_unchanged(self):
        plain = "hello world"
        assert mask_secret(plain) == plain

    def test_mask_dict_hides_api_key(self):
        d = {"api_key": "sk-abc123456789xyz", "name": "test"}
        masked = mask_dict(d)
        assert masked["api_key"] != "sk-abc123456789xyz"
        assert "****" in masked["api_key"]
        assert masked["name"] == "test"

    def test_mask_dict_hides_password(self):
        d = {"password": "super-secret-password-123"}
        masked = mask_dict(d)
        assert "super-secret-password-123" not in masked["password"]

    def test_mask_dict_short_secret_fully_masked(self):
        d = {"api_key": "short"}
        masked = mask_dict(d)
        assert masked["api_key"] == "****"

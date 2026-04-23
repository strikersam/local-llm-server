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
    get_user_role,
    has_permission,
    require_admin,
    require_permission,
    audit,
    get_audit_log,
    mask_secret,
    mask_dict,
)


# ── Role resolution ───────────────────────────────────────────────────────────

class TestGetUserRole:

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


# ── Secret masking ────────────────────────────────────────────────────────────

class TestMaskSecret:

    def test_masks_openai_key(self):
        key = "sk-proj-abc123def456ghi789jkl"
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

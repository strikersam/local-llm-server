"""rbac.py — Role-Based Access Control.

Defines the two-tier user model:
  - admin:  Full platform access.  Can manage API keys (labelled "Admin Activity"),
            view secrets metadata (never raw values), manage providers/models/runtimes
            globally, view audit logs, manage all users.
  - user:   Social-login user (GitHub/Google OAuth).  Can manage their own agents,
            tasks, chats, and schedules.  Cannot view other users' sensitive config.

This module provides:
  - Role enum and permission flags
  - FastAPI dependencies for role enforcement
  - Audit log helper
  - Secret masking utility (never log raw keys)
"""

from __future__ import annotations

import hmac
import logging
import re
import time
from enum import Enum
from typing import Any

from fastapi import HTTPException, Request

log = logging.getLogger("qwen-proxy")

# ── Roles ─────────────────────────────────────────────────────────────────────

class UserRole(str, Enum):
    ADMIN = "admin"
    USER  = "user"


# ── Permission flags ──────────────────────────────────────────────────────────

class Permission(str, Enum):
    # Admin-only (labelled "Admin Activity" in UI)
    MANAGE_ALL_API_KEYS       = "manage_all_api_keys"
    VIEW_ALL_SECRETS_METADATA = "view_all_secrets_metadata"
    MANAGE_PROVIDERS_GLOBAL   = "manage_providers_global"
    MANAGE_MODELS_GLOBAL      = "manage_models_global"
    MANAGE_RUNTIMES_GLOBAL    = "manage_runtimes_global"
    VIEW_AUDIT_LOGS           = "view_audit_logs"
    MANAGE_ALL_USERS          = "manage_all_users"
    VIEW_ALL_TASKS            = "view_all_tasks"
    MANAGE_ROUTING_POLICY     = "manage_routing_policy"
    VIEW_ALL_SESSIONS         = "view_all_sessions"

    # User-level (own resources)
    MANAGE_OWN_AGENTS         = "manage_own_agents"
    MANAGE_OWN_TASKS          = "manage_own_tasks"
    MANAGE_OWN_CHATS          = "manage_own_chats"
    MANAGE_OWN_SCHEDULES      = "manage_own_schedules"
    CREATE_OWN_API_KEYS       = "create_own_api_keys"
    VIEW_OWN_USAGE            = "view_own_usage"
    USE_PROVIDERS             = "use_providers"


# ── Role → permission map ─────────────────────────────────────────────────────

ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    UserRole.ADMIN: frozenset({
        # Admin gets all permissions
        *Permission,
    }),
    UserRole.USER: frozenset({
        Permission.MANAGE_OWN_AGENTS,
        Permission.MANAGE_OWN_TASKS,
        Permission.MANAGE_OWN_CHATS,
        Permission.MANAGE_OWN_SCHEDULES,
        Permission.CREATE_OWN_API_KEYS,
        Permission.VIEW_OWN_USAGE,
        Permission.USE_PROVIDERS,
    }),
}

# Permissions that must be labelled "Admin Activity" in the UI
ADMIN_ACTIVITY_PERMISSIONS: frozenset[Permission] = frozenset({
    Permission.MANAGE_ALL_API_KEYS,
    Permission.VIEW_ALL_SECRETS_METADATA,
    Permission.MANAGE_PROVIDERS_GLOBAL,
    Permission.MANAGE_MODELS_GLOBAL,
    Permission.MANAGE_RUNTIMES_GLOBAL,
    Permission.VIEW_AUDIT_LOGS,
    Permission.MANAGE_ALL_USERS,
    Permission.MANAGE_ROUTING_POLICY,
})


# ── Access check helpers ──────────────────────────────────────────────────────

def get_user_role(user: Any) -> UserRole:
    """Extract role from a user object (dict or Pydantic model)."""
    if isinstance(user, dict):
        role_str = user.get("role", "user")
    else:
        role_str = getattr(user, "role", "user")
    try:
        return UserRole(role_str)
    except ValueError:
        return UserRole.USER


def has_permission(user: Any, permission: Permission) -> bool:
    role = get_user_role(user)
    return permission in ROLE_PERMISSIONS.get(role, frozenset())


# ── FastAPI dependencies ──────────────────────────────────────────────────────

def require_admin(request: Request) -> Any:
    """FastAPI dependency: require admin role.  Raises 403 otherwise."""
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    if get_user_role(user) != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Admin access required for this operation.",
        )
    return user


def require_authenticated(request: Request) -> Any:
    """FastAPI dependency: require any authenticated user."""
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def require_permission(permission: Permission):
    """Return a FastAPI dependency that checks for a specific permission."""
    def _dep(request: Request) -> Any:
        user = getattr(request.state, "user", None)
        if user is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        if not has_permission(user, permission):
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {permission.value}",
            )
        return user
    return _dep


# ── Audit log ─────────────────────────────────────────────────────────────────

_audit_log: list[dict[str, Any]] = []
_MAX_AUDIT_ENTRIES = 10_000


def audit(
    action: str,
    user: Any,
    *,
    resource: str | None = None,
    resource_id: str | None = None,
    outcome: str = "success",
    detail: str | None = None,
    request: Request | None = None,
) -> None:
    """Append an audit log entry.

    Never logs raw secrets.  IP address is extracted from request headers.
    """
    user_id = str(getattr(user, "_id", None) or getattr(user, "email", "unknown"))
    role = get_user_role(user).value if user else "unknown"

    entry: dict[str, Any] = {
        "timestamp": time.time(),
        "action": action,
        "user_id": mask_secret(user_id),  # user IDs are generally safe
        "role": role,
        "outcome": outcome,
    }
    if resource:
        entry["resource"] = resource
    if resource_id:
        entry["resource_id"] = resource_id
    if detail:
        entry["detail"] = detail[:500]
    if request:
        entry["ip"] = (
            request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or getattr(request.client, "host", "unknown")
        )

    _audit_log.append(entry)
    # Prune oldest entries
    while len(_audit_log) > _MAX_AUDIT_ENTRIES:
        _audit_log.pop(0)

    # Only log admin activity at INFO; user actions at DEBUG
    if role == "admin":
        log.info("AUDIT [admin] %s user=%s resource=%s outcome=%s", action, user_id, resource, outcome)
    else:
        log.debug("AUDIT [user] %s user=%s outcome=%s", action, user_id, outcome)


def get_audit_log(limit: int = 200, user_id: str | None = None) -> list[dict[str, Any]]:
    """Return recent audit log entries, newest first."""
    entries = list(reversed(_audit_log[-limit * 2:]))
    if user_id:
        entries = [e for e in entries if e.get("user_id") == user_id]
    return entries[:limit]


# ── Secret masking ────────────────────────────────────────────────────────────

# Patterns that look like secrets — mask them before logging
_SECRET_PATTERNS = [
    re.compile(r"(sk-[A-Za-z0-9\-_]{10,})", re.IGNORECASE),
    re.compile(r"(eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+)"),  # JWT
    re.compile(r"(ghp_[A-Za-z0-9]{36})", re.IGNORECASE),    # GitHub PAT
    re.compile(r"(glpat-[A-Za-z0-9\-_]{20,})", re.IGNORECASE),  # GitLab PAT
    re.compile(r"(xoxb-[0-9\-A-Za-z]{20,})"),               # Slack bot token
]


def mask_secret(value: str) -> str:
    """Redact secret-looking substrings from a string.

    Always safe to call on user-facing output and log messages.
    Returns the masked string.
    """
    if not isinstance(value, str):
        return value
    for pattern in _SECRET_PATTERNS:
        value = pattern.sub(lambda m: m.group(1)[:4] + "****" + m.group(1)[-4:], value)
    return value


def mask_dict(data: dict[str, Any], secret_keys: set[str] | None = None) -> dict[str, Any]:
    """Return a copy of *data* with secret values masked.

    Common secret key names are masked by default.  Pass *secret_keys*
    to add additional keys to mask.
    """
    default_secret_keys = {
        "api_key", "api_secret", "access_token", "refresh_token",
        "password", "secret", "token", "private_key", "client_secret",
    }
    all_secret_keys = default_secret_keys | (secret_keys or set())

    def _mask(k: str, v: Any) -> Any:
        if k.lower() in all_secret_keys:
            if isinstance(v, str) and len(v) > 8:
                return v[:4] + "****" + v[-4:]
            elif isinstance(v, str):
                return "****"
            return "****"
        if isinstance(v, str):
            return mask_secret(v)
        return v

    return {k: _mask(k, v) for k, v in data.items()}

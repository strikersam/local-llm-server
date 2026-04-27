"""rbac.py — Role-Based Access Control.

Three-tier user model:
  - admin:       Full platform access.  Can manage API keys (labelled "Admin Activity"),
                 view secrets metadata (never raw values), manage providers/models/runtimes
                 globally, view audit logs, manage all users.
  - power_user:  Elevated user — can manage workspace-level resources, view shared
                 secrets metadata, manage shared agents/tasks across the workspace,
                 view runtime health and routing decisions.  Cannot manage global
                 provider/model/runtime config or other users' accounts.
  - user:        Social-login user (GitHub/Google OAuth).  Can manage their own agents,
                 tasks, chats, and schedules.  Cannot view other users' sensitive config.

This module provides:
  - Role enum and permission flags
  - FastAPI dependencies for role enforcement
  - Audit log helper (extended: user, secrets_used, runtime_machine, repo_workspace)
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
    ADMIN      = "admin"
    POWER_USER = "power_user"
    USER       = "user"


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
    MANAGE_ROUTING_POLICY     = "manage_routing_policy"

    # Power User — workspace-level elevated access
    VIEW_ALL_TASKS            = "view_all_tasks"
    VIEW_ALL_SESSIONS         = "view_all_sessions"
    MANAGE_WORKSPACE_AGENTS   = "manage_workspace_agents"
    VIEW_WORKSPACE_SECRETS    = "view_workspace_secrets"
    MANAGE_WORKSPACE_SECRETS  = "manage_workspace_secrets"
    VIEW_RUNTIME_HEALTH       = "view_runtime_health"
    VIEW_ROUTING_DECISIONS    = "view_routing_decisions"
    MANAGE_WORKSPACE_REPOS    = "manage_workspace_repos"
    VIEW_COST_INSIGHTS        = "view_cost_insights"
    UPGRADE_USERS             = "upgrade_users"            # can promote users → power_user

    # User-level (own resources only)
    MANAGE_OWN_AGENTS         = "manage_own_agents"
    MANAGE_OWN_TASKS          = "manage_own_tasks"
    MANAGE_OWN_CHATS          = "manage_own_chats"
    MANAGE_OWN_SCHEDULES      = "manage_own_schedules"
    CREATE_OWN_API_KEYS       = "create_own_api_keys"
    VIEW_OWN_USAGE            = "view_own_usage"
    USE_PROVIDERS             = "use_providers"
    MANAGE_OWN_SECRETS        = "manage_own_secrets"
    MANAGE_OWN_REPOS          = "manage_own_repos"


# ── Role → permission map ─────────────────────────────────────────────────────

ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    UserRole.ADMIN: frozenset({
        *Permission,
    }),
    UserRole.POWER_USER: frozenset({
        # All user-level perms
        Permission.MANAGE_OWN_AGENTS,
        Permission.MANAGE_OWN_TASKS,
        Permission.MANAGE_OWN_CHATS,
        Permission.MANAGE_OWN_SCHEDULES,
        Permission.CREATE_OWN_API_KEYS,
        Permission.VIEW_OWN_USAGE,
        Permission.USE_PROVIDERS,
        Permission.MANAGE_OWN_SECRETS,
        Permission.MANAGE_OWN_REPOS,
        # Elevated workspace perms
        Permission.VIEW_ALL_TASKS,
        Permission.VIEW_ALL_SESSIONS,
        Permission.MANAGE_WORKSPACE_AGENTS,
        Permission.VIEW_WORKSPACE_SECRETS,
        Permission.MANAGE_WORKSPACE_SECRETS,
        Permission.VIEW_RUNTIME_HEALTH,
        Permission.VIEW_ROUTING_DECISIONS,
        Permission.MANAGE_WORKSPACE_REPOS,
        Permission.VIEW_COST_INSIGHTS,
        Permission.UPGRADE_USERS,
    }),
    UserRole.USER: frozenset({
        Permission.MANAGE_OWN_AGENTS,
        Permission.MANAGE_OWN_TASKS,
        Permission.MANAGE_OWN_CHATS,
        Permission.MANAGE_OWN_SCHEDULES,
        Permission.CREATE_OWN_API_KEYS,
        Permission.VIEW_OWN_USAGE,
        Permission.USE_PROVIDERS,
        Permission.MANAGE_OWN_SECRETS,
        Permission.MANAGE_OWN_REPOS,
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

# Permissions that require at least Power User role (labelled "Power User" in UI)
POWER_USER_ACTIVITY_PERMISSIONS: frozenset[Permission] = frozenset({
    Permission.VIEW_ALL_TASKS,
    Permission.VIEW_ALL_SESSIONS,
    Permission.MANAGE_WORKSPACE_AGENTS,
    Permission.VIEW_WORKSPACE_SECRETS,
    Permission.MANAGE_WORKSPACE_SECRETS,
    Permission.VIEW_RUNTIME_HEALTH,
    Permission.VIEW_ROUTING_DECISIONS,
    Permission.MANAGE_WORKSPACE_REPOS,
    Permission.VIEW_COST_INSIGHTS,
    Permission.UPGRADE_USERS,
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


def is_admin(user: Any) -> bool:
    return get_user_role(user) == UserRole.ADMIN


def is_power_user_or_above(user: Any) -> bool:
    return get_user_role(user) in (UserRole.ADMIN, UserRole.POWER_USER)


def role_label(user: Any) -> str:
    """Return a short human-readable badge label for display in the UI."""
    role = get_user_role(user)
    return {
        UserRole.ADMIN:      "Admin",
        UserRole.POWER_USER: "Power User",
        UserRole.USER:       "User",
    }[role]


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


def require_power_user(request: Request) -> Any:
    """FastAPI dependency: require Power User or Admin role.  Raises 403 otherwise."""
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    if not is_power_user_or_above(user):
        raise HTTPException(
            status_code=403,
            detail="Power User or Admin access required for this operation.",
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
    # Extended visibility fields (PROMPT 2 — audit extension)
    secrets_used: list[str] | None = None,       # secret IDs referenced (never raw values)
    runtime_machine: str | None = None,          # runtime ID + hostname that executed
    repo_workspace: str | None = None,           # git repo URL or workspace path
    agent_id: str | None = None,                 # which agent executed the task
) -> None:
    """Append an audit log entry.

    Never logs raw secrets — only secret IDs / masked references.
    IP address is extracted from request headers.
    """
    if isinstance(user, dict):
        user_id   = user.get("email") or user.get("_id") or "unknown"
        user_name = user.get("name", user_id)
    else:
        user_id   = str(getattr(user, "email", None) or getattr(user, "_id", "unknown"))
        user_name = getattr(user, "name", user_id)

    role = get_user_role(user).value if user else "unknown"

    entry: dict[str, Any] = {
        "timestamp":  time.time(),
        "action":     action,
        "user_id":    user_id,          # email / internal ID — not a secret
        "user_name":  user_name,
        "role":       role,
        "outcome":    outcome,
    }
    if resource:
        entry["resource"] = resource
    if resource_id:
        entry["resource_id"] = resource_id
    if detail:
        entry["detail"] = detail[:500]
    if secrets_used:
        # Store only the *IDs* (e.g. "secret_abc123"), never the values
        entry["secrets_used"] = [str(s)[:64] for s in secrets_used]
    if runtime_machine:
        entry["runtime_machine"] = runtime_machine
    if repo_workspace:
        entry["repo_workspace"] = repo_workspace
    if agent_id:
        entry["agent_id"] = agent_id
    if request:
        entry["ip"] = (
            request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or getattr(request.client, "host", "unknown")
        )

    _audit_log.append(entry)
    # Prune oldest entries to bound memory
    while len(_audit_log) > _MAX_AUDIT_ENTRIES:
        _audit_log.pop(0)

    # Log at appropriate severity
    if role == "admin":
        log.info(
            "AUDIT [admin] %s user=%s resource=%s outcome=%s runtime=%s",
            action, user_id, resource, outcome, runtime_machine,
        )
    elif role == "power_user":
        log.info(
            "AUDIT [power_user] %s user=%s resource=%s outcome=%s",
            action, user_id, resource, outcome,
        )
    else:
        log.debug("AUDIT [user] %s user=%s outcome=%s", action, user_id, outcome)


def get_audit_log(
    limit: int = 200,
    user_id: str | None = None,
    resource: str | None = None,
    outcome: str | None = None,
) -> list[dict[str, Any]]:
    """Return recent audit log entries, newest first.

    Supports filtering by user_id, resource, and outcome.
    """
    entries = list(reversed(_audit_log[-limit * 4:]))
    if user_id:
        entries = [e for e in entries if e.get("user_id") == user_id]
    if resource:
        entries = [e for e in entries if e.get("resource") == resource]
    if outcome:
        entries = [e for e in entries if e.get("outcome") == outcome]
    return entries[:limit]


# ── Secret masking ────────────────────────────────────────────────────────────

# Patterns that look like secrets — mask them before logging
_SECRET_PATTERNS = [
    re.compile(r"(sk-[A-Za-z0-9\-_]{10,})", re.IGNORECASE),
    re.compile(r"(eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+)"),  # JWT
    re.compile(r"(ghp_[A-Za-z0-9]{36})", re.IGNORECASE),    # GitHub PAT
    re.compile(r"(gho_[A-Za-z0-9]{36})", re.IGNORECASE),    # GitHub OAuth token
    re.compile(r"(glpat-[A-Za-z0-9\-_]{20,})", re.IGNORECASE),  # GitLab PAT
    re.compile(r"(xoxb-[0-9\-A-Za-z]{20,})"),               # Slack bot token
    re.compile(r"(ya29\.[A-Za-z0-9\-_]{40,})"),             # Google OAuth access token
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
        "github_token", "google_token", "oauth_token",
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

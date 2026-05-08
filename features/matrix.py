"""features/matrix.py — Feature maturity tiers and support matrix.

Single source of truth for feature classification.  Used to:
  - Gate disabled features
  - Surface warnings for beta/experimental features
  - Produce structured unsupported-feature errors
  - Expose support state via admin API / UI

Config overrides allow operators to enable/disable features that are
not stable by default.
"""

from __future__ import annotations

import json
import logging
import os
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

log = logging.getLogger("qwen-proxy")


# ── Maturity tiers ─────────────────────────────────────────────────────────────


class FeatureMaturity(str, Enum):
    """Feature maturity classification."""

    STABLE = "stable"
    BETA = "beta"
    EXPERIMENTAL = "experimental"
    DISABLED = "disabled"


# ── Feature entry ──────────────────────────────────────────────────────────────


class FeatureEntry(BaseModel):
    """One entry in the support matrix."""

    feature_id: str = Field(..., description="Machine-readable feature identifier")
    display_name: str = Field(..., description="Human-readable name")
    maturity: FeatureMaturity = Field(..., description="Current maturity tier")
    enabled: bool = Field(default=True, description="Whether the feature is currently enabled")
    default_availability: FeatureMaturity = Field(
        default=FeatureMaturity.STABLE,
        description="Default maturity before config overrides",
    )
    key_dependencies: list[str] = Field(
        default_factory=list,
        description="Key dependencies required for this feature",
    )
    config_flags: list[str] = Field(
        default_factory=list,
        description="Config env vars that control this feature",
    )
    admin_visible: bool = Field(default=True, description="Show in admin API/UI")
    notes: str = Field(default="", description="Caveats, limitations, or guidance")

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump()


# ── FeatureUnavailableError ────────────────────────────────────────────────────


class FeatureUnavailableError(Exception):
    """Raised when code attempts to use a feature that is disabled or unavailable."""

    def __init__(
        self,
        feature_id: str,
        maturity: FeatureMaturity,
        reason: str = "",
        fix_hint: str = "",
    ) -> None:
        self.feature_id = feature_id
        self.maturity = maturity
        self.reason = reason
        self.fix_hint = fix_hint
        msg = f"Feature '{feature_id}' is unavailable (maturity={maturity.value})"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": "feature_unavailable",
            "feature_id": self.feature_id,
            "maturity": self.maturity.value,
            "reason": self.reason,
            "fix_hint": self.fix_hint,
        }


# ── Support matrix definition ─────────────────────────────────────────────────

# This is the canonical matrix — all feature entries live here.
# Config overrides may change maturity and enabled at runtime.

_CANONICAL_FEATURES: list[dict[str, Any]] = [
    # ── Stable core ───────────────────────────────────────────────────────
    {
        "feature_id": "direct_chat",
        "display_name": "Direct Chat",
        "maturity": FeatureMaturity.STABLE,
        "enabled": True,
        "default_availability": FeatureMaturity.STABLE,
        "key_dependencies": ["Ollama or cloud provider"],
        "config_flags": [],
        "admin_visible": True,
        "notes": "Core synchronous chat feature.",
    },
    {
        "feature_id": "openai_compat",
        "display_name": "OpenAI API Compatibility",
        "maturity": FeatureMaturity.STABLE,
        "enabled": True,
        "default_availability": FeatureMaturity.STABLE,
        "key_dependencies": ["Ollama"],
        "config_flags": [],
        "admin_visible": True,
        "notes": "/v1/ chat completions endpoint.",
    },
    {
        "feature_id": "anthropic_compat",
        "display_name": "Anthropic API Compatibility",
        "maturity": FeatureMaturity.STABLE,
        "enabled": True,
        "default_availability": FeatureMaturity.STABLE,
        "key_dependencies": ["Ollama"],
        "config_flags": [],
        "admin_visible": True,
        "notes": "/v1/messages endpoint for Claude Code etc.",
    },
    {
        "feature_id": "ollama_passthrough",
        "display_name": "Ollama Native Passthrough",
        "maturity": FeatureMaturity.STABLE,
        "enabled": True,
        "default_availability": FeatureMaturity.STABLE,
        "key_dependencies": ["Ollama"],
        "config_flags": [],
        "admin_visible": True,
        "notes": "/api/* endpoints.",
    },
    {
        "feature_id": "key_management",
        "display_name": "Multi-User Key Management",
        "maturity": FeatureMaturity.STABLE,
        "enabled": True,
        "default_availability": FeatureMaturity.STABLE,
        "key_dependencies": [],
        "config_flags": ["KEYS_FILE", "API_KEYS"],
        "admin_visible": True,
        "notes": "",
    },
    {
        "feature_id": "provider_routing_fallback",
        "display_name": "Provider Routing & Fallback",
        "maturity": FeatureMaturity.STABLE,
        "enabled": True,
        "default_availability": FeatureMaturity.STABLE,
        "key_dependencies": [],
        "config_flags": ["PROVIDER_COOLDOWN_SECONDS"],
        "admin_visible": True,
        "notes": "Timeout/cooldown/failover for providers.",
    },
    {
        "feature_id": "rate_limiting",
        "display_name": "Rate Limiting",
        "maturity": FeatureMaturity.STABLE,
        "enabled": True,
        "default_availability": FeatureMaturity.STABLE,
        "key_dependencies": [],
        "config_flags": ["RATE_LIMIT_RPM"],
        "admin_visible": True,
        "notes": "Per-key RPM limiting.",
    },
    {
        "feature_id": "runtime_preflight",
        "display_name": "Runtime Preflight Validation",
        "maturity": FeatureMaturity.STABLE,
        "enabled": True,
        "default_availability": FeatureMaturity.STABLE,
        "key_dependencies": [],
        "config_flags": [],
        "admin_visible": True,
        "notes": "Structured readiness checks before execution.",
    },
    {
        "feature_id": "admin_dashboard",
        "display_name": "Admin Dashboard",
        "maturity": FeatureMaturity.STABLE,
        "enabled": True,
        "default_availability": FeatureMaturity.STABLE,
        "key_dependencies": [],
        "config_flags": ["ADMIN_SECRET"],
        "admin_visible": True,
        "notes": "",
    },
    {
        "feature_id": "observability_langfuse",
        "display_name": "Langfuse Observability (Direct Chat)",
        "maturity": FeatureMaturity.STABLE,
        "enabled": True,
        "default_availability": FeatureMaturity.STABLE,
        "key_dependencies": ["Langfuse account"],
        "config_flags": ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"],
        "admin_visible": True,
        "notes": "Traces + cost metadata.",
    },
    {
        "feature_id": "workspace_isolation",
        "display_name": "Workspace Isolation",
        "maturity": FeatureMaturity.STABLE,
        "enabled": True,
        "default_availability": FeatureMaturity.STABLE,
        "key_dependencies": [],
        "config_flags": ["WORKSPACE_BASE_ROOT", "WORKSPACE_RETENTION_TTL_SECONDS"],
        "admin_visible": True,
        "notes": "Per-session/job isolated workspaces with manifests.",
    },
    # ── Stable agent features ──────────────────────────────────────────────
    {
        "feature_id": "agent_planner_executor_verifier",
        "display_name": "Planner / Executor / Verifier Pipeline",
        "maturity": FeatureMaturity.STABLE,
        "enabled": True,
        "default_availability": FeatureMaturity.STABLE,
        "key_dependencies": ["Ollama or cloud provider"],
        "config_flags": ["AGENT_PLANNER_MODEL", "AGENT_EXECUTOR_MODEL", "AGENT_VERIFIER_MODEL"],
        "admin_visible": True,
        "notes": "Three-role plan-execute-verify loop.",
    },
    {
        "feature_id": "agent_judge",
        "display_name": "Judge (Release Gate)",
        "maturity": FeatureMaturity.STABLE,
        "enabled": True,
        "default_availability": FeatureMaturity.STABLE,
        "key_dependencies": ["Ollama or cloud provider"],
        "config_flags": ["AGENT_JUDGE_MODEL"],
        "admin_visible": True,
        "notes": "Quality gate after verification.",
    },
    {
        "feature_id": "local_runtime",
        "display_name": "Local Runtime (internal_agent)",
        "maturity": FeatureMaturity.STABLE,
        "enabled": True,
        "default_availability": FeatureMaturity.STABLE,
        "key_dependencies": [],
        "config_flags": ["RUNTIME_DEFAULT"],
        "admin_visible": True,
        "notes": "Built-in agent loop, always available.",
    },
    {
        "feature_id": "local_model_routing",
        "display_name": "Local-First Model Routing",
        "maturity": FeatureMaturity.STABLE,
        "enabled": True,
        "default_availability": FeatureMaturity.STABLE,
        "key_dependencies": ["Ollama"],
        "config_flags": [],
        "admin_visible": True,
        "notes": "",
    },
    # ── Beta ───────────────────────────────────────────────────────────────
    {
        "feature_id": "async_agent_jobs",
        "display_name": "Async Agent Jobs",
        "maturity": FeatureMaturity.BETA,
        "enabled": True,
        "default_availability": FeatureMaturity.BETA,
        "key_dependencies": ["Agent runtime"],
        "config_flags": ["DIRECT_CHAT_AGENT_WORKSPACE_ROOT"],
        "admin_visible": True,
        "notes": "Agent mode returns 202 + pollable job ID.",
    },
    {
        "feature_id": "runtime_readiness_diagnostics",
        "display_name": "Runtime Readiness Diagnostics",
        "maturity": FeatureMaturity.BETA,
        "enabled": True,
        "default_availability": FeatureMaturity.BETA,
        "key_dependencies": [],
        "config_flags": [],
        "admin_visible": True,
        "notes": "Preflight validation with structured issues.",
    },
    {
        "feature_id": "policies_governance",
        "display_name": "Policies & Governance",
        "maturity": FeatureMaturity.BETA,
        "enabled": True,
        "default_availability": FeatureMaturity.BETA,
        "key_dependencies": [],
        "config_flags": [],
        "admin_visible": True,
        "notes": "Approval gates, RBAC, admin controls.",
    },
    {
        "feature_id": "crispy_workflow",
        "display_name": "CRISPY Workflow Engine",
        "maturity": FeatureMaturity.BETA,
        "enabled": True,
        "default_availability": FeatureMaturity.BETA,
        "key_dependencies": [],
        "config_flags": ["CRISPY_ARTIFACTS_ROOT"],
        "admin_visible": True,
        "notes": "Structured build workflow with approval gates.",
    },
    {
        "feature_id": "task_harness_runtime",
        "display_name": "Task-Harness Runtime",
        "maturity": FeatureMaturity.BETA,
        "enabled": True,
        "default_availability": FeatureMaturity.BETA,
        "key_dependencies": ["task-harness binary"],
        "config_flags": ["TASK_HARNESS_REQUIRED", "TASK_HARNESS_BIN"],
        "admin_visible": True,
        "notes": "Requires external harness binary.",
    },
    # ── Experimental ───────────────────────────────────────────────────────
    {
        "feature_id": "openhands_runtime",
        "display_name": "OpenHands Runtime",
        "maturity": FeatureMaturity.EXPERIMENTAL,
        "enabled": False,
        "default_availability": FeatureMaturity.EXPERIMENTAL,
        "key_dependencies": ["Docker", "OpenHands image"],
        "config_flags": ["OPENHANDS_ENABLED"],
        "admin_visible": True,
        "notes": "Opt-in, requires Docker. Set OPENHANDS_ENABLED=true.",
    },
    {
        "feature_id": "sidecar_runtimes",
        "display_name": "Sidecar Runtimes (Hermes/OpenCode/Goose)",
        "maturity": FeatureMaturity.EXPERIMENTAL,
        "enabled": True,
        "default_availability": FeatureMaturity.EXPERIMENTAL,
        "key_dependencies": ["Sidecar process running"],
        "config_flags": [],
        "admin_visible": True,
        "notes": "Registered but may be unhealthy if sidecar is not running.",
    },
    {
        "feature_id": "telegram_bot",
        "display_name": "Telegram Bot",
        "maturity": FeatureMaturity.EXPERIMENTAL,
        "enabled": True,
        "default_availability": FeatureMaturity.EXPERIMENTAL,
        "key_dependencies": ["Telegram Bot Token"],
        "config_flags": ["TELEGRAM_BOT_TOKEN", "TELEGRAM_ALLOWED_USER_IDS"],
        "admin_visible": True,
        "notes": "Remote control via Telegram.",
    },
    {
        "feature_id": "tunnels",
        "display_name": "Tunnels (Cloudflare/ngrok)",
        "maturity": FeatureMaturity.EXPERIMENTAL,
        "enabled": True,
        "default_availability": FeatureMaturity.EXPERIMENTAL,
        "key_dependencies": ["cloudflared or ngrok"],
        "config_flags": ["NGROK_AUTH_TOKEN", "CLOUDFLARED_EXE"],
        "admin_visible": True,
        "notes": "Exposes proxy over HTTPS.",
    },
    {
        "feature_id": "multi_agent_swarm",
        "display_name": "Multi-Agent / Swarm",
        "maturity": FeatureMaturity.EXPERIMENTAL,
        "enabled": True,
        "default_availability": FeatureMaturity.EXPERIMENTAL,
        "key_dependencies": [],
        "config_flags": [],
        "admin_visible": True,
        "notes": "Agent coordination and swarm dispatch.",
    },
    {
        "feature_id": "openclaw_integration",
        "display_name": "OpenClaw Integration",
        "maturity": FeatureMaturity.EXPERIMENTAL,
        "enabled": True,
        "default_availability": FeatureMaturity.EXPERIMENTAL,
        "key_dependencies": ["OpenClaw"],
        "config_flags": [],
        "admin_visible": True,
        "notes": "Maintenance: vulnerability fixes, code scans.",
    },
    {
        "feature_id": "jcode_runtime",
        "display_name": "JCode Runtime",
        "maturity": FeatureMaturity.EXPERIMENTAL,
        "enabled": True,
        "default_availability": FeatureMaturity.EXPERIMENTAL,
        "key_dependencies": ["JCode"],
        "config_flags": [],
        "admin_visible": True,
        "notes": "JCode execution runtime.",
    },
    {
        "feature_id": "quick_actions_ios",
        "display_name": "Quick Actions / iOS Shortcuts",
        "maturity": FeatureMaturity.EXPERIMENTAL,
        "enabled": True,
        "default_availability": FeatureMaturity.EXPERIMENTAL,
        "key_dependencies": [],
        "config_flags": [],
        "admin_visible": True,
        "notes": "iOS Shortcuts integration for remote commands.",
    },
    {
        "feature_id": "machine_peer_sync",
        "display_name": "Machine Sync / Peer Sync",
        "maturity": FeatureMaturity.EXPERIMENTAL,
        "enabled": True,
        "default_availability": FeatureMaturity.EXPERIMENTAL,
        "key_dependencies": [],
        "config_flags": [],
        "admin_visible": True,
        "notes": "Sync service for multi-machine coordination.",
    },
]


# ── FeatureMatrix ──────────────────────────────────────────────────────────────


class FeatureMatrix:
    """Central support matrix — single source of truth.

    Loads the canonical feature list, applies config overrides,
    and provides query / gating / admin visibility methods.
    """

    def __init__(self, config_overrides: dict[str, str] | None = None) -> None:
        self._entries: dict[str, FeatureEntry] = {}
        self._load(config_overrides or {})

    def _load(self, config_overrides: dict[str, str]) -> None:
        """Load canonical features and apply config overrides."""
        for raw in _CANONICAL_FEATURES:
            entry = FeatureEntry(**raw)
            # Apply config overrides
            fid = entry.feature_id
            env_key = f"FEATURE_{fid.upper()}"
            # Check explicit env override first, then passed-in overrides
            override = os.environ.get(env_key) or config_overrides.get(env_key)
            if override is not None:
                self._apply_override(entry, override)
            self._entries[fid] = entry

    @staticmethod
    def _apply_override(entry: FeatureEntry, override: str) -> None:
        """Apply a config override string like 'stable', 'beta', 'disabled', 'enabled', 'true', 'false'."""
        val = override.strip().lower()
        if val in ("stable", "beta", "experimental"):
            entry.maturity = FeatureMaturity(val)
            entry.enabled = True
        elif val == "disabled":
            entry.maturity = FeatureMaturity.DISABLED
            entry.enabled = False
        elif val in ("enabled", "true", "1", "yes"):
            entry.enabled = True
        elif val in ("false", "0", "no"):
            entry.enabled = False

    # ── Query ──────────────────────────────────────────────────────────────

    def get(self, feature_id: str) -> FeatureEntry | None:
        return self._entries.get(feature_id)

    def list_all(self) -> list[FeatureEntry]:
        return list(self._entries.values())

    def list_by_maturity(self, maturity: FeatureMaturity) -> list[FeatureEntry]:
        return [e for e in self._entries.values() if e.maturity == maturity]

    def list_enabled(self) -> list[FeatureEntry]:
        return [e for e in self._entries.values() if e.enabled]

    def list_admin_visible(self) -> list[FeatureEntry]:
        return [e for e in self._entries.values() if e.admin_visible]

    # ── Gating ─────────────────────────────────────────────────────────────

    def check_available(self, feature_id: str) -> FeatureEntry:
        """Return the feature entry if available, or raise FeatureUnavailableError."""
        entry = self._entries.get(feature_id)
        if entry is None:
            raise FeatureUnavailableError(
                feature_id,
                FeatureMaturity.DISABLED,
                reason="Feature not found in support matrix.",
                fix_hint="Check the feature_id spelling or consult the support matrix.",
            )
        if not entry.enabled or entry.maturity == FeatureMaturity.DISABLED:
            raise FeatureUnavailableError(
                feature_id,
                entry.maturity,
                reason="Feature is disabled." if not entry.enabled else "Feature maturity is 'disabled'.",
                fix_hint=f"Set FEATURE_{feature_id.upper()}=enabled to override.",
            )
        return entry

    def is_available(self, feature_id: str) -> bool:
        """Return True if the feature is enabled and not disabled."""
        entry = self._entries.get(feature_id)
        return entry is not None and entry.enabled and entry.maturity != FeatureMaturity.DISABLED

    def maturity_warning(self, feature_id: str) -> str | None:
        """Return a warning string for beta/experimental features, or None."""
        entry = self._entries.get(feature_id)
        if entry is None:
            return None
        if entry.maturity == FeatureMaturity.BETA:
            return f"Feature '{feature_id}' is in BETA — behavior may change."
        if entry.maturity == FeatureMaturity.EXPERIMENTAL:
            return f"Feature '{feature_id}' is EXPERIMENTAL — use with caution, may be unstable."
        return None

    def require(self, feature_id: str) -> FeatureEntry:
        """Convenience: check_available, but returns the entry for chaining."""
        return self.check_available(feature_id)

    # ── Serialization ──────────────────────────────────────────────────────

    def as_dict(self) -> dict[str, Any]:
        return {
            "features": {fid: e.as_dict() for fid, e in self._entries.items()},
            "summary": {
                "total": len(self._entries),
                "by_maturity": {
                    m.value: len(self.list_by_maturity(m))
                    for m in FeatureMaturity
                },
                "enabled_count": len(self.list_enabled()),
            },
        }

    def as_markdown_table(self) -> str:
        """Render the matrix as a Markdown table for docs."""
        lines = [
            "| Feature | ID | Maturity | Enabled | Dependencies | Config Flags | Notes |",
            "|---------|----|----------|---------|--------------|-------------|-------|",
        ]
        for entry in sorted(self._entries.values(), key=lambda e: (e.maturity.value, e.display_name)):
            deps = ", ".join(entry.key_dependencies) or "—"
            flags = ", ".join(entry.config_flags) or "—"
            enabled = "✅" if entry.enabled else "❌"
            notes = entry.notes if entry.notes else "—"
            lines.append(
                f"| {entry.display_name} | `{entry.feature_id}` | {entry.maturity.value} | {enabled} | {deps} | {flags} | {notes} |"
            )
        return "\n".join(lines)


# ── Singleton ──────────────────────────────────────────────────────────────────

_feature_matrix: FeatureMatrix | None = None


def get_feature_matrix() -> FeatureMatrix:
    """Return the global FeatureMatrix singleton."""
    global _feature_matrix
    if _feature_matrix is None:
        _feature_matrix = FeatureMatrix()
    return _feature_matrix


def reset_feature_matrix() -> None:
    """Reset the singleton (useful for testing)."""
    global _feature_matrix
    _feature_matrix = None

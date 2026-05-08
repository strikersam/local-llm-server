"""features/matrix.py — Feature maturity and support matrix.

This is the **single source of truth** for feature classification.
Every feature has:
- a stable ID
- a maturity tier (stable / beta / experimental / disabled)
- enabled/disabled state (runtime enforcement)
- dependencies checked at startup
- config flag(s) for operator override

Usage::

    from features.matrix import require_feature, get_matrix

    # Gate an endpoint:
    require_feature("async_agent_jobs")

    # Admin/API visibility:
    matrix = get_matrix()
    print(matrix.as_dict())

Operator overrides via env vars::

    FEATURE_DISABLE=async_agent_jobs,telegram_bot   # force-disable
    FEATURE_ENABLE=openhands_runtime                # force-enable (beta/experimental only)
"""

from __future__ import annotations

import logging
import os
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

log = logging.getLogger("qwen-proxy")

# ---------------------------------------------------------------------------
# Maturity tiers
# ---------------------------------------------------------------------------


class FeatureMaturity(str, Enum):
    STABLE = "stable"
    BETA = "beta"
    EXPERIMENTAL = "experimental"
    DISABLED = "disabled"


# ---------------------------------------------------------------------------
# Feature entry model
# ---------------------------------------------------------------------------


class FeatureEntry(BaseModel):
    """Description of one feature in the support matrix."""

    feature_id: str
    display_name: str
    maturity: FeatureMaturity
    enabled: bool
    default_available: bool
    dependencies: list[str] = Field(default_factory=list)
    config_flags: list[str] = Field(default_factory=list)
    admin_visible: bool = True
    notes: str = ""
    # Runtime-populated: None = not checked yet, True/False = checked
    dependency_satisfied: bool | None = None


# ---------------------------------------------------------------------------
# Structured error returned when a feature is unavailable
# ---------------------------------------------------------------------------


class FeatureUnavailableError(Exception):
    """Raised when a disabled or unsupported feature is requested."""

    def __init__(
        self,
        feature_id: str,
        maturity: FeatureMaturity,
        reason: str = "",
    ) -> None:
        self.feature_id = feature_id
        self.maturity = maturity
        self.reason = reason
        super().__init__(
            f"Feature {feature_id!r} is unavailable "
            f"(maturity={maturity.value}, reason={reason!r})"
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": "feature_unavailable",
            "feature_id": self.feature_id,
            "maturity": self.maturity.value,
            "reason": self.reason,
        }


# ---------------------------------------------------------------------------
# Feature registry — single source of truth
# ---------------------------------------------------------------------------

# Each entry is a dict matching FeatureEntry fields.
# Maturity choices:
#   stable        — production-ready, no warnings
#   beta          — usable but may have rough edges; surfaces a warning
#   experimental  — opt-in only; disabled by default unless FEATURE_ENABLE overrides
#   disabled      — permanently off; cannot be enabled via FEATURE_ENABLE
_REGISTRY_SPEC: list[dict[str, Any]] = [
    # ── Core proxy / auth ──────────────────────────────────────────────────
    {
        "feature_id": "proxy_endpoints",
        "display_name": "OpenAI / Ollama / Anthropic proxy endpoints",
        "maturity": FeatureMaturity.STABLE,
        "enabled": True,
        "default_available": True,
        "notes": "Core proxy; always on.",
    },
    {
        "feature_id": "auth",
        "display_name": "Bearer token + key-store auth",
        "maturity": FeatureMaturity.STABLE,
        "enabled": True,
        "default_available": True,
    },
    {
        "feature_id": "rate_limiting",
        "display_name": "Per-key rate limiting",
        "maturity": FeatureMaturity.STABLE,
        "enabled": True,
        "default_available": True,
        "config_flags": ["RATE_LIMIT_RPM"],
    },
    {
        "feature_id": "provider_routing",
        "display_name": "Multi-provider routing and fallback",
        "maturity": FeatureMaturity.STABLE,
        "enabled": True,
        "default_available": True,
    },
    {
        "feature_id": "model_routing",
        "display_name": "Local model routing + alias resolution",
        "maturity": FeatureMaturity.STABLE,
        "enabled": True,
        "default_available": True,
        "config_flags": ["MODEL_MAP"],
    },
    {
        "feature_id": "key_management",
        "display_name": "API key CRUD (generate / revoke)",
        "maturity": FeatureMaturity.STABLE,
        "enabled": True,
        "default_available": True,
        "config_flags": ["KEYS_FILE"],
    },
    # ── Direct chat ────────────────────────────────────────────────────────
    {
        "feature_id": "direct_chat",
        "display_name": "Direct chat (sync, non-blocking)",
        "maturity": FeatureMaturity.STABLE,
        "enabled": True,
        "default_available": True,
    },
    # ── Agent / async jobs ─────────────────────────────────────────────────
    {
        "feature_id": "async_agent_jobs",
        "display_name": "Async agent job queue (202 + job ID)",
        "maturity": FeatureMaturity.BETA,
        "enabled": True,
        "default_available": True,
        "config_flags": ["AGENT_WORKSPACE_BASE", "AGENT_WORKSPACE_ROOT"],
        "notes": "202 response; poll /api/chat/agent-jobs/<id> for status.",
    },
    {
        "feature_id": "planner_verifier_judge",
        "display_name": "Planner / verifier / judge pipeline",
        "maturity": FeatureMaturity.BETA,
        "enabled": True,
        "default_available": True,
        "config_flags": [
            "AGENT_PLANNER_MODEL",
            "AGENT_EXECUTOR_MODEL",
            "AGENT_VERIFIER_MODEL",
        ],
    },
    {
        "feature_id": "workspace_isolation",
        "display_name": "Per-job isolated workspace (hash-based)",
        "maturity": FeatureMaturity.BETA,
        "enabled": True,
        "default_available": True,
        "config_flags": ["AGENT_WORKSPACE_BASE", "WORKSPACE_TTL_HOURS"],
    },
    # ── Runtimes ───────────────────────────────────────────────────────────
    {
        "feature_id": "runtime_preflight",
        "display_name": "Runtime readiness / preflight validation",
        "maturity": FeatureMaturity.BETA,
        "enabled": True,
        "default_available": True,
    },
    {
        "feature_id": "local_runtime",
        "display_name": "Built-in local agent runtime (internal_agent)",
        "maturity": FeatureMaturity.STABLE,
        "enabled": True,
        "default_available": True,
    },
    {
        "feature_id": "task_harness_runtime",
        "display_name": "Task-harness runtime (Docker sidecar)",
        "maturity": FeatureMaturity.BETA,
        "enabled": True,
        "default_available": False,
        "dependencies": ["task_harness"],
        "notes": "Requires task-harness Docker container running.",
    },
    {
        "feature_id": "jcode_runtime",
        "display_name": "jcode runtime",
        "maturity": FeatureMaturity.EXPERIMENTAL,
        "enabled": True,
        "default_available": False,
        "dependencies": ["jcode"],
        "config_flags": ["JCODE_BIN"],
        "notes": "Requires jcode binary on PATH or JCODE_BIN env var.",
    },
    {
        "feature_id": "openhands_runtime",
        "display_name": "OpenHands runtime (Docker)",
        "maturity": FeatureMaturity.EXPERIMENTAL,
        "enabled": False,
        "default_available": False,
        "config_flags": ["OPENHANDS_ENABLED"],
        "notes": "Opt-in via OPENHANDS_ENABLED=true. Requires Docker.",
    },
    {
        "feature_id": "aider_runtime",
        "display_name": "Aider runtime",
        "maturity": FeatureMaturity.BETA,
        "enabled": True,
        "default_available": False,
        "dependencies": ["aider"],
    },
    {
        "feature_id": "hermes_runtime",
        "display_name": "Hermes runtime (sidecar)",
        "maturity": FeatureMaturity.BETA,
        "enabled": True,
        "default_available": False,
        "notes": "Requires Hermes sidecar process.",
    },
    {
        "feature_id": "opencode_runtime",
        "display_name": "OpenCode runtime (sidecar)",
        "maturity": FeatureMaturity.EXPERIMENTAL,
        "enabled": True,
        "default_available": False,
        "notes": "Requires OpenCode sidecar process.",
    },
    {
        "feature_id": "goose_runtime",
        "display_name": "Goose runtime (sidecar)",
        "maturity": FeatureMaturity.EXPERIMENTAL,
        "enabled": True,
        "default_available": False,
        "notes": "Requires Goose sidecar process.",
    },
    # ── Integrations ───────────────────────────────────────────────────────
    {
        "feature_id": "langfuse_observability",
        "display_name": "Langfuse trace / cost observability",
        "maturity": FeatureMaturity.STABLE,
        "enabled": True,
        "default_available": False,
        "config_flags": ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"],
        "notes": "Activated when LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY are set.",
    },
    {
        "feature_id": "telegram_bot",
        "display_name": "Telegram bot remote control",
        "maturity": FeatureMaturity.BETA,
        "enabled": True,
        "default_available": False,
        "config_flags": ["TELEGRAM_BOT_TOKEN"],
        "notes": "Activated when TELEGRAM_BOT_TOKEN is set.",
    },
    {
        "feature_id": "tunnel",
        "display_name": "Tunnel / ngrok / Cloudflare remote access",
        "maturity": FeatureMaturity.BETA,
        "enabled": True,
        "default_available": False,
        "config_flags": ["NGROK_AUTHTOKEN", "CLOUDFLARE_TOKEN"],
        "notes": "Requires NGROK_AUTHTOKEN or Cloudflare tunnel config.",
    },
    {
        "feature_id": "admin_command_runner",
        "display_name": "Admin command runner (web UI)",
        "maturity": FeatureMaturity.BETA,
        "enabled": True,
        "default_available": True,
        "config_flags": ["ADMIN_SECRET"],
    },
    {
        "feature_id": "social_auth",
        "display_name": "Social / OAuth login",
        "maturity": FeatureMaturity.EXPERIMENTAL,
        "enabled": True,
        "default_available": False,
        "config_flags": ["GOOGLE_CLIENT_ID", "GITHUB_CLIENT_ID"],
    },
    {
        "feature_id": "multi_agent_swarm",
        "display_name": "Multi-agent swarm orchestration",
        "maturity": FeatureMaturity.EXPERIMENTAL,
        "enabled": True,
        "default_available": False,
        "notes": "Agent coordinator + swarm. No dedicated config flag; use /agents/swarm API.",
    },
    {
        "feature_id": "workflow_engine",
        "display_name": "CRISPY workflow engine",
        "maturity": FeatureMaturity.EXPERIMENTAL,
        "enabled": True,
        "default_available": False,
        "notes": "Gate / slice / phase workflow model.",
    },
    {
        "feature_id": "per_job_progress",
        "display_name": "Per-job progress polling (heartbeat)",
        "maturity": FeatureMaturity.BETA,
        "enabled": True,
        "default_available": True,
        "notes": "Poll GET /api/chat/agent-jobs/<id> for phase/event updates.",
    },
]


# ---------------------------------------------------------------------------
# FeatureMatrix — loads registry and applies operator overrides
# ---------------------------------------------------------------------------


class FeatureMatrix:
    """Runtime-evaluated support matrix.

    Load once with :meth:`load` (or via the :func:`get_matrix` singleton).
    Operator can override maturity enforcement via env vars:

    - ``FEATURE_DISABLE=id1,id2``  — force-disable these features
    - ``FEATURE_ENABLE=id1,id2``   — force-enable experimental/disabled features
      (cannot enable features with maturity==DISABLED)
    """

    def __init__(self, entries: list[FeatureEntry]) -> None:
        self._entries: dict[str, FeatureEntry] = {e.feature_id: e for e in entries}

    @classmethod
    def load(cls) -> "FeatureMatrix":
        entries = [FeatureEntry(**spec) for spec in _REGISTRY_SPEC]
        matrix = cls(entries)
        matrix._apply_operator_overrides()
        return matrix

    # ── Enforcement ───────────────────────────────────────────────────────

    def check(self, feature_id: str) -> FeatureEntry:
        """Return entry for *feature_id*.  Raises :exc:`FeatureUnavailableError` if disabled."""
        entry = self._entries.get(feature_id)
        if entry is None:
            raise FeatureUnavailableError(
                feature_id,
                FeatureMaturity.DISABLED,
                reason="feature not found in support matrix",
            )
        if not entry.enabled or entry.maturity == FeatureMaturity.DISABLED:
            raise FeatureUnavailableError(
                feature_id,
                entry.maturity,
                reason=f"feature is {entry.maturity.value}",
            )
        return entry

    def warn_if_beta(self, feature_id: str) -> FeatureEntry | None:
        """Return entry with a warning log for beta/experimental features.

        Returns None if feature is disabled (does not raise).
        """
        entry = self._entries.get(feature_id)
        if entry is None:
            return None
        if not entry.enabled or entry.maturity == FeatureMaturity.DISABLED:
            return None
        if entry.maturity == FeatureMaturity.BETA:
            log.warning(
                "Feature %r is in BETA — behaviour may change in future versions.",
                feature_id,
            )
        elif entry.maturity == FeatureMaturity.EXPERIMENTAL:
            log.warning(
                "Feature %r is EXPERIMENTAL — opt-in only, not recommended for production.",
                feature_id,
            )
        return entry

    def is_enabled(self, feature_id: str) -> bool:
        entry = self._entries.get(feature_id)
        if entry is None:
            return False
        return entry.enabled and entry.maturity != FeatureMaturity.DISABLED

    def get(self, feature_id: str) -> FeatureEntry | None:
        return self._entries.get(feature_id)

    # ── Admin / API output ────────────────────────────────────────────────

    def as_dict(self, admin_only: bool = False) -> dict[str, Any]:
        entries = [
            e.model_dump()
            for e in self._entries.values()
            if not admin_only or e.admin_visible
        ]
        return {
            "schema_version": "1",
            "total": len(entries),
            "by_maturity": self._counts_by_maturity(),
            "entries": entries,
        }

    def summary(self) -> list[dict[str, Any]]:
        """Compact summary suitable for health/status APIs."""
        return [
            {
                "feature_id": e.feature_id,
                "display_name": e.display_name,
                "maturity": e.maturity.value,
                "enabled": e.enabled,
            }
            for e in self._entries.values()
            if e.admin_visible
        ]

    # ── Internals ─────────────────────────────────────────────────────────

    def _apply_operator_overrides(self) -> None:
        raw_disable = os.environ.get("FEATURE_DISABLE", "")
        raw_enable = os.environ.get("FEATURE_ENABLE", "")

        for fid in (f.strip() for f in raw_disable.split(",") if f.strip()):
            if fid in self._entries:
                self._entries[fid].enabled = False
                log.info("Feature %r force-disabled via FEATURE_DISABLE", fid)
            else:
                log.warning("FEATURE_DISABLE: unknown feature %r (ignored)", fid)

        for fid in (f.strip() for f in raw_enable.split(",") if f.strip()):
            entry = self._entries.get(fid)
            if entry is None:
                log.warning("FEATURE_ENABLE: unknown feature %r (ignored)", fid)
                continue
            if entry.maturity == FeatureMaturity.DISABLED:
                log.warning(
                    "FEATURE_ENABLE: feature %r has maturity=disabled and cannot be enabled",
                    fid,
                )
                continue
            entry.enabled = True
            log.info("Feature %r force-enabled via FEATURE_ENABLE", fid)

    def _counts_by_maturity(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for e in self._entries.values():
            k = e.maturity.value
            counts[k] = counts.get(k, 0) + 1
        return counts


# ---------------------------------------------------------------------------
# Singleton + convenience helpers
# ---------------------------------------------------------------------------

_matrix: FeatureMatrix | None = None


def get_matrix() -> FeatureMatrix:
    """Return the process-level singleton FeatureMatrix (loaded once)."""
    global _matrix
    if _matrix is None:
        _matrix = FeatureMatrix.load()
    return _matrix


def require_feature(feature_id: str) -> FeatureEntry:
    """Gate a code path on the feature being enabled.

    Raises :exc:`FeatureUnavailableError` if not enabled.
    """
    return get_matrix().check(feature_id)

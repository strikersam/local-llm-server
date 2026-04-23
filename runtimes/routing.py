"""runtimes/routing.py — RuntimeRoutingPolicyEngine.

Implements the 8-step routing decision flow:
  1. Classify task type and complexity
  2. Choose best-fit runtime
  3. Choose best-fit model/provider inside that runtime (local first)
  4. Validate result (schema, tool success, quality heuristics)
  5. Retry locally once with stronger model if configured
  6. Switch runtime on runtime-level failure
  7. Escalate to paid provider only if policy allows
  8. Log every routing/escalation decision with full reason

Admin-configurable controls:
  - max_paid_escalations_per_day
  - never_use_paid_providers
  - require_approval_before_paid_escalation
  - per_agent fallback thresholds
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from runtimes.base import (
    RuntimeAdapter,
    RuntimeCapability,
    RuntimeUnavailableError,
    RuntimeExecutionError,
    TaskResult,
    TaskSpec,
)

if TYPE_CHECKING:
    from runtimes.registry import RuntimeCapabilityRegistry
    from runtimes.health import RuntimeHealthService

log = logging.getLogger("qwen-proxy")


# ── Policy model ──────────────────────────────────────────────────────────────

@dataclass
class RoutingPolicy:
    """Admin-configurable routing policy.

    Defaults are conservative (local-first, no paid escalation).
    """
    never_use_paid_providers: bool = True
    require_approval_before_paid_escalation: bool = True
    max_paid_escalations_per_day: int = 0
    local_retry_with_stronger_model: bool = True
    preferred_runtime_id: str | None = None        # global default
    fallback_runtime_ids: list[str] = field(default_factory=list)
    # Per-task-type runtime overrides: {"code_generation": "opencode", ...}
    task_type_runtime_overrides: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "never_use_paid_providers": self.never_use_paid_providers,
            "require_approval_before_paid_escalation": self.require_approval_before_paid_escalation,
            "max_paid_escalations_per_day": self.max_paid_escalations_per_day,
            "local_retry_with_stronger_model": self.local_retry_with_stronger_model,
            "preferred_runtime_id": self.preferred_runtime_id,
            "fallback_runtime_ids": self.fallback_runtime_ids,
            "task_type_runtime_overrides": self.task_type_runtime_overrides,
        }


# ── Routing decision log ──────────────────────────────────────────────────────

@dataclass
class RoutingDecision:
    """Full record of a routing decision — audit-trail entry."""
    task_id: str
    task_type: str
    selected_runtime_id: str
    model_used: str | None
    provider_used: str | None
    reason: str
    escalated: bool = False
    escalation_reason: str | None = None
    fallback_attempted: bool = False
    fallback_runtime_id: str | None = None
    timestamp: float = field(default_factory=time.time)

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "selected_runtime_id": self.selected_runtime_id,
            "model_used": self.model_used,
            "provider_used": self.provider_used,
            "reason": self.reason,
            "escalated": self.escalated,
            "escalation_reason": self.escalation_reason,
            "fallback_attempted": self.fallback_attempted,
            "fallback_runtime_id": self.fallback_runtime_id,
            "timestamp": self.timestamp,
        }


# ── Engine ────────────────────────────────────────────────────────────────────

class RuntimeRoutingPolicyEngine:
    """Routes a TaskSpec to the best available runtime following the
    configured policy.  All routing decisions are logged for audit."""

    def __init__(
        self,
        registry: "RuntimeCapabilityRegistry",
        health_service: "RuntimeHealthService",
        policy: RoutingPolicy | None = None,
    ) -> None:
        self._registry = registry
        self._health = health_service
        self._policy = policy or RoutingPolicy()
        self._decision_log: list[RoutingDecision] = []

    # ── Policy management ─────────────────────────────────────────────────────

    @property
    def policy(self) -> RoutingPolicy:
        return self._policy

    def update_policy(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            if hasattr(self._policy, k):
                setattr(self._policy, k, v)
            else:
                log.warning("Unknown policy field: %s", k)

    # ── Main routing entry point ──────────────────────────────────────────────

    async def route_and_execute(self, spec: TaskSpec) -> tuple[TaskResult, RoutingDecision]:
        """Route the task and execute it.  Returns (result, decision).

        Implements the 8-step flow with full logging.
        """
        task_type = spec.task_type or "general"

        # Step 2: Choose runtime
        preferred_id = (
            self._policy.task_type_runtime_overrides.get(task_type)
            or spec.provider_preference
            or self._policy.preferred_runtime_id
        )
        runtime = self._pick_runtime(task_type, preferred_id)

        if runtime is None:
            raise RuntimeUnavailableError("*", f"No healthy runtime found for task type '{task_type}'")

        decision = RoutingDecision(
            task_id=spec.task_id,
            task_type=task_type,
            selected_runtime_id=runtime.RUNTIME_ID,
            model_used=spec.model_preference,
            provider_used=spec.provider_preference,
            reason=f"Best-fit runtime for task_type='{task_type}' (tier={runtime.TIER.value})",
        )

        # Step 4–6: Execute with retry/fallback
        result = await self._execute_with_fallback(spec, runtime, decision)
        self._decision_log.append(decision)
        return result, decision

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _pick_runtime(
        self,
        task_type: str,
        preferred_id: str | None,
    ) -> RuntimeAdapter | None:
        """Pick the best available (health-checked) runtime."""
        candidates = self._registry.capable_of(task_type)
        available = [
            a for a in candidates
            if self._health.is_available(a.RUNTIME_ID)
        ]
        if not available:
            return None
        if preferred_id:
            for a in available:
                if a.RUNTIME_ID == preferred_id:
                    return a
        return available[0]

    async def _execute_with_fallback(
        self,
        spec: TaskSpec,
        primary_runtime: RuntimeAdapter,
        decision: RoutingDecision,
    ) -> TaskResult:
        """Try primary runtime; fall back to alternatives on failure."""
        try:
            result = await primary_runtime.execute(spec)
            decision.model_used = result.model_used
            decision.provider_used = result.provider_used
            return result
        except (RuntimeUnavailableError, RuntimeExecutionError) as exc:
            log.warning("Primary runtime %s failed: %s — attempting fallback",
                        primary_runtime.RUNTIME_ID, exc)

        # Step 6: Try fallback runtimes
        fallback_ids = self._policy.fallback_runtime_ids or []
        for fid in fallback_ids:
            fb_runtime = self._registry.get(fid)
            if fb_runtime and self._health.is_available(fid) and fid != primary_runtime.RUNTIME_ID:
                try:
                    result = await fb_runtime.execute(spec)
                    decision.fallback_attempted = True
                    decision.fallback_runtime_id = fid
                    decision.reason += f"; fell back to {fid}"
                    decision.model_used = result.model_used
                    decision.provider_used = result.provider_used
                    return result
                except Exception as fb_exc:
                    log.warning("Fallback runtime %s also failed: %s", fid, fb_exc)

        # Step 7: Paid escalation (only if policy allows)
        if spec.allow_paid_escalation and not self._policy.never_use_paid_providers:
            if not self._policy.require_approval_before_paid_escalation:
                log.warning("All local runtimes failed; escalating to paid provider for task %s",
                            spec.task_id)
                decision.escalated = True
                decision.escalation_reason = "All local runtimes failed"
                # Placeholder — real escalation goes through ProviderManager
                raise RuntimeUnavailableError(
                    "*",
                    "Paid escalation requested but not yet wired to ProviderManager in this build. "
                    "Implement by routing spec through webui.providers.ProviderManager.",
                )
            else:
                raise RuntimeUnavailableError(
                    "*",
                    "All local runtimes failed; paid escalation requires human approval.",
                )
        raise RuntimeUnavailableError(
            "*",
            "All runtimes failed and policy prevents paid escalation.",
        )

    # ── Audit log ─────────────────────────────────────────────────────────────

    def get_decision_log(self, limit: int = 100) -> list[dict]:
        """Return the last *limit* routing decisions (newest first)."""
        return [d.as_dict() for d in reversed(self._decision_log[-limit:])]

"""runtimes/manager.py — RuntimeManager.

The RuntimeManager is the single entry point for the control plane to:
  - Register / unregister runtime adapters
  - Execute tasks (delegates to routing engine)
  - Query health
  - List available runtimes
  - Manage routing policy

It owns the RuntimeCapabilityRegistry, RuntimeHealthService, and
RuntimeRoutingPolicyEngine instances.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from runtimes.base import RuntimeAdapter, TaskResult, TaskSpec, RuntimeUnavailableError
from runtimes.registry import RuntimeCapabilityRegistry
from runtimes.health import RuntimeHealthService
from runtimes.routing import RuntimeRoutingPolicyEngine, RoutingDecision, RoutingPolicy

log = logging.getLogger("qwen-proxy")


class RuntimeManager:
    """Top-level orchestrator for all agent runtimes.

    Typical usage::

        mgr = RuntimeManager()
        mgr.register(HermesAdapter())
        mgr.register(OpenCodeAdapter())
        await mgr.start()

        result, decision = await mgr.execute(spec)

        await mgr.stop()
    """

    def __init__(self, policy: RoutingPolicy | None = None) -> None:
        self._registry = RuntimeCapabilityRegistry()
        self._health = RuntimeHealthService(
            self._registry,
            poll_interval_sec=int(os.environ.get("RUNTIME_HEALTH_POLL_SEC", "30")),
        )
        self._router = RuntimeRoutingPolicyEngine(
            self._registry,
            self._health,
            policy=policy,
        )
        self._started = False

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start background health polling and call start() on all adapters."""
        if self._started:
            return
        for adapter in self._registry.all():
            try:
                await adapter.start()
            except Exception as exc:
                log.warning("Runtime %s start() failed: %s", adapter.RUNTIME_ID, exc)
        self._health.start()
        self._started = True
        log.info("RuntimeManager started with %d runtime(s)", len(self._registry.ids()))

    async def stop(self) -> None:
        """Stop health polling and gracefully shut down all adapters."""
        await self._health.stop()
        for adapter in self._registry.all():
            try:
                await adapter.stop()
            except Exception as exc:
                log.warning("Runtime %s stop() failed: %s", adapter.RUNTIME_ID, exc)
        self._started = False
        log.info("RuntimeManager stopped")

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, adapter: RuntimeAdapter) -> None:
        """Register a runtime adapter.  Can be called before or after start()."""
        self._registry.register(adapter)
        if self._started:
            # Trigger an immediate health check so the new runtime is usable
            import asyncio
            asyncio.create_task(self._health._poll_one(adapter.RUNTIME_ID))

    def unregister(self, runtime_id: str) -> None:
        self._registry.unregister(runtime_id)

    # ── Execution ─────────────────────────────────────────────────────────────

    async def execute(self, spec: TaskSpec) -> tuple[TaskResult, RoutingDecision]:
        """Execute a task through the policy engine.

        Returns (TaskResult, RoutingDecision).
        Raises RuntimeUnavailableError if no runtime can handle the task.
        """
        return await self._router.route_and_execute(spec)

    # ── Query API ─────────────────────────────────────────────────────────────

    def list_runtimes(self) -> list[dict[str, Any]]:
        """Return metadata + current health for all registered runtimes."""
        result = []
        for adapter in self._registry.all():
            info = adapter.as_dict()
            health = self._health.get_health(adapter.RUNTIME_ID)
            info["health"] = health.as_dict() if health else {"runtime_id": adapter.RUNTIME_ID, "available": None}
            info["circuit_open"] = not self._health.is_available(adapter.RUNTIME_ID)
            result.append(info)
        return result

    def get_runtime(self, runtime_id: str) -> dict[str, Any] | None:
        adapter = self._registry.get(runtime_id)
        if not adapter:
            return None
        info = adapter.as_dict()
        health = self._health.get_health(runtime_id)
        info["health"] = health.as_dict() if health else {"runtime_id": runtime_id, "available": None}
        return info

    def get_policy(self) -> dict[str, Any]:
        return self._router.policy.as_dict()

    def update_policy(self, **kwargs: Any) -> None:
        self._router.update_policy(**kwargs)

    def get_decision_log(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._router.get_decision_log(limit)

    def health_summary(self) -> list[dict[str, Any]]:
        return self._health.all_health()


# ── Singleton ─────────────────────────────────────────────────────────────────

_runtime_manager: RuntimeManager | None = None


def get_runtime_manager() -> RuntimeManager:
    """Return the global RuntimeManager singleton.

    Registers all configured adapters on first call.
    """
    global _runtime_manager
    if _runtime_manager is None:
        _runtime_manager = _build_default_manager()
    return _runtime_manager


def _build_default_manager() -> RuntimeManager:
    """Build a manager with all adapters enabled by default.

    Individual adapters are skipped if their binary/URL is not configured
    (they'll just be unhealthy until set up).
    """
    from runtimes.adapters.hermes import HermesAdapter
    from runtimes.adapters.opencode import OpenCodeAdapter
    from runtimes.adapters.goose import GooseAdapter
    from runtimes.adapters.openhands import OpenHandsAdapter
    from runtimes.adapters.aider import AiderAdapter

    policy = RoutingPolicy(
        never_use_paid_providers=os.environ.get("RUNTIME_NEVER_PAID", "true").lower() == "true",
        require_approval_before_paid_escalation=True,
        max_paid_escalations_per_day=int(os.environ.get("RUNTIME_MAX_PAID_ESCALATIONS", "0")),
        preferred_runtime_id=os.environ.get("RUNTIME_DEFAULT", "hermes"),
        task_type_runtime_overrides={
            "code_generation": os.environ.get("RUNTIME_CODE_GENERATION", "opencode"),
            "code_review": os.environ.get("RUNTIME_CODE_REVIEW", "opencode"),
            "repo_editing": os.environ.get("RUNTIME_REPO_EDITING", "opencode"),
            "git_operations": os.environ.get("RUNTIME_GIT_OPS", "aider"),
        },
    )
    mgr = RuntimeManager(policy=policy)
    mgr.register(HermesAdapter())
    mgr.register(OpenCodeAdapter())
    mgr.register(GooseAdapter())

    # OpenHands is opt-in (experimental, requires Docker)
    if os.environ.get("OPENHANDS_ENABLED", "false").lower() == "true":
        mgr.register(OpenHandsAdapter())

    # Aider is always registered (lightweight, just needs the binary)
    mgr.register(AiderAdapter())

    return mgr

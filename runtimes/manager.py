"""runtimes/manager.py — RuntimeManager.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from runtimes.base import RuntimeAdapter, RuntimeUnavailableError, TaskResult, TaskSpec
from runtimes.health import RuntimeHealthService
from runtimes.registry import RuntimeCapabilityRegistry
from runtimes.routing import RoutingDecision, RoutingPolicy, RuntimeRoutingPolicyEngine

log = logging.getLogger("qwen-proxy")

class RuntimeManager:
    def __init__(self, policy: RoutingPolicy | None = None) -> None:
        self._registry = RuntimeCapabilityRegistry()
        self._health = RuntimeHealthService(self._registry, poll_interval_sec=int(os.environ.get("RUNTIME_HEALTH_POLL_SEC", "30")))
        self._router = RuntimeRoutingPolicyEngine(self._registry, self._health, policy=policy)
        self._started = False

    async def start(self) -> None:
        if self._started: return
        for adapter in self._registry.all():
            try: await adapter.start()
            except Exception as exc: log.warning("Runtime %s start failed: %s", adapter.RUNTIME_ID, exc)
        self._health.start()
        self._started = True

    async def stop(self) -> None:
        await self._health.stop()
        for adapter in self._registry.all():
            try: await adapter.stop()
            except Exception as exc: log.warning("Runtime %s stop failed: %s", adapter.RUNTIME_ID, exc)
        self._started = False

    def register(self, adapter: RuntimeAdapter) -> None:
        self._registry.register(adapter)
        if self._started:
            import asyncio
            asyncio.create_task(self._health._poll_one(adapter.RUNTIME_ID))

    def unregister(self, runtime_id: str) -> None:
        self._registry.unregister(runtime_id)

    async def execute(self, spec: TaskSpec) -> tuple[TaskResult, RoutingDecision]:
        return await self._router.route_and_execute(spec)

    def select_runtime(self, task_type: str, preferred_id: str | None = None) -> tuple[RuntimeAdapter | None, list[dict]]:
        return self._router._pick_runtime(task_type, preferred_id)

    async def get_runtime_health(self, runtime_id: str) -> dict | None:
        circuit = self._health._circuits.get(runtime_id)
        if circuit: circuit.record_success()
        await self._health._poll_one(runtime_id)
        health = self._health.get_health(runtime_id)
        return health.as_dict() if health else None

_runtime_manager: RuntimeManager | None = None

def get_runtime_manager() -> RuntimeManager:
    global _runtime_manager
    if _runtime_manager is None: _runtime_manager = _build_default_manager()
    return _runtime_manager

def _build_default_manager() -> RuntimeManager:
    from runtimes.adapters.aider import AiderAdapter
    from runtimes.adapters.claude_code import ClaudeCodeAdapter
    from runtimes.adapters.goose import GooseAdapter
    from runtimes.adapters.hermes import HermesAdapter
    from runtimes.adapters.internal_agent import InternalAgentAdapter
    from runtimes.adapters.docker_agent import DockerAgentAdapter
    from runtimes.adapters.jcode import JCodeAdapter
    from runtimes.adapters.opencode import OpenCodeAdapter
    from runtimes.adapters.openhands import OpenHandsAdapter
    from runtimes.adapters.task_harness import TaskHarnessAdapter

    policy = RoutingPolicy(
        never_use_paid_providers=os.environ.get("RUNTIME_NEVER_PAID", "false").lower() == "true",
        require_approval_before_paid_escalation=os.environ.get("RUNTIME_REQUIRE_APPROVAL", "false").lower() == "true",
        max_paid_escalations_per_day=int(os.environ.get("RUNTIME_MAX_PAID_ESCALATIONS", "0")),
        preferred_runtime_id=os.environ.get("RUNTIME_DEFAULT", "docker_agent" if os.environ.get("AGENT_MODE_DOCKER", "false").lower() == "true" else "internal_agent"),
        fallback_runtime_ids=["internal_agent"],
        task_type_runtime_overrides={k: v for k, v in {"code_generation": os.environ.get("RUNTIME_CODE_GENERATION"), "code_review": os.environ.get("RUNTIME_CODE_REVIEW"), "repo_editing": os.environ.get("RUNTIME_REPO_EDITING"), "git_operations": os.environ.get("RUNTIME_GIT_OPS")}.items() if v}
    )

    mgr = RuntimeManager(policy=policy)
    mgr.register(InternalAgentAdapter())
    if os.environ.get("AGENT_MODE_DOCKER", "false").lower() == "true": mgr.register(DockerAgentAdapter())
    mgr.register(HermesAdapter())
    mgr.register(OpenCodeAdapter())
    mgr.register(GooseAdapter())
    mgr.register(ClaudeCodeAdapter())
    if os.environ.get("TASK_HARNESS_ENABLED", "false").lower() == "true": mgr.register(TaskHarnessAdapter())
    if os.environ.get("OPENHANDS_ENABLED", "false").lower() == "true": mgr.register(OpenHandsAdapter())
    mgr.register(AiderAdapter())
    mgr.register(JCodeAdapter())
    return mgr

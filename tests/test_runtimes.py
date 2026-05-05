"""tests/test_runtimes.py — Unit tests for the runtime abstraction layer.

Tests cover:
  - RuntimeAdapter ABC contract
  - RuntimeCapabilityRegistry capability lookups and tier ordering
  - RuntimeRoutingPolicyEngine routing decisions, fallback, and policy
  - RuntimeHealthService circuit-breaker logic
  - All adapter metadata (does not require running runtimes)
  - RBAC module helpers
"""

from __future__ import annotations

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from runtimes.base import (
    RuntimeAdapter,
    RuntimeCapability,
    RuntimeTier,
    IntegrationMode,
    RuntimeDependency,
    RuntimeHealth,
    RuntimePreflightError,
    TaskResult,
    TaskSpec,
    RuntimeUnavailableError,
    RuntimeExecutionError,
)
from runtimes.registry import RuntimeCapabilityRegistry, TASK_CAPABILITY_MAP
from runtimes.health import RuntimeHealthService, CircuitState
from runtimes.routing import RuntimeRoutingPolicyEngine, RoutingPolicy


# ── Stub adapter for testing ─────────────────────────────────────────────────

class StubAdapter(RuntimeAdapter):
    RUNTIME_ID    = "stub"
    DISPLAY_NAME  = "Stub"
    DESCRIPTION   = "Test stub runtime"
    TIER          = RuntimeTier.FIRST_CLASS
    INTEGRATION_MODE = IntegrationMode.NATIVE
    CAPABILITIES  = frozenset({
        RuntimeCapability.CODE_GENERATION,
        RuntimeCapability.CODE_REVIEW,
        RuntimeCapability.FILE_READ_WRITE,
    })

    def __init__(self, config=None, *, health_available=True, fail=False):
        super().__init__(config)
        self._health_available = health_available
        self._fail = fail

    async def health_check(self) -> RuntimeHealth:
        return RuntimeHealth(
            runtime_id=self.RUNTIME_ID,
            available=self._health_available,
            version="test-1.0",
            latency_ms=5.0,
        )

    async def execute(self, spec: TaskSpec) -> TaskResult:
        if self._fail:
            raise RuntimeExecutionError(self.RUNTIME_ID, "Simulated failure", spec.task_id)
        return TaskResult(
            runtime_id=self.RUNTIME_ID,
            task_id=spec.task_id,
            success=True,
            output="stub output",
            model_used="stub-model",
            provider_used="local",
        )


class TierTwoStub(StubAdapter):
    RUNTIME_ID   = "stub_t2"
    DISPLAY_NAME = "Stub Tier 2"
    TIER         = RuntimeTier.TIER_2


class TaskHarnessStub(StubAdapter):
    RUNTIME_ID = "task_harness_stub"

    def required_dependencies(self):
        return [
            RuntimeDependency(
                name="task-harness",
                config_var="TASK_HARNESS_BIN",
                install_hint="Install a compatible harness and point TASK_HARNESS_BIN at it.",
            )
        ]


# ── Registry tests ─────────────────────────────────────────────────────────────

class TestRuntimeCapabilityRegistry:

    def test_register_and_get(self):
        reg = RuntimeCapabilityRegistry()
        adapter = StubAdapter()
        reg.register(adapter)
        assert reg.get("stub") is adapter

    def test_register_duplicate_replaces(self):
        reg = RuntimeCapabilityRegistry()
        a1 = StubAdapter()
        a2 = StubAdapter()
        reg.register(a1)
        reg.register(a2)
        assert reg.get("stub") is a2

    def test_unregister(self):
        reg = RuntimeCapabilityRegistry()
        reg.register(StubAdapter())
        reg.unregister("stub")
        assert reg.get("stub") is None

    def test_ids_returns_list(self):
        reg = RuntimeCapabilityRegistry()
        reg.register(StubAdapter())
        reg.register(TierTwoStub())
        assert set(reg.ids()) == {"stub", "stub_t2"}

    def test_capable_of_code_generation(self):
        reg = RuntimeCapabilityRegistry()
        reg.register(StubAdapter())
        capable = reg.capable_of("code_generation")
        assert len(capable) == 1
        assert capable[0].RUNTIME_ID == "stub"

    def test_capable_of_requires_missing_capability(self):
        reg = RuntimeCapabilityRegistry()
        reg.register(StubAdapter())
        # WEB_BROWSE is not in StubAdapter.CAPABILITIES
        capable = reg.capable_of("web_browse")
        assert len(capable) == 0

    def test_capable_of_tier_ordering(self):
        reg = RuntimeCapabilityRegistry()
        reg.register(TierTwoStub())
        reg.register(StubAdapter())  # FIRST_CLASS
        capable = reg.capable_of("code_generation")
        # FIRST_CLASS should come first
        assert capable[0].TIER == RuntimeTier.FIRST_CLASS

    def test_best_for_prefers_requested_runtime(self):
        reg = RuntimeCapabilityRegistry()
        reg.register(StubAdapter())
        reg.register(TierTwoStub())
        best = reg.best_for("code_generation", preferred_runtime_id="stub_t2")
        assert best.RUNTIME_ID == "stub_t2"

    def test_best_for_returns_none_when_no_match(self):
        reg = RuntimeCapabilityRegistry()
        assert reg.best_for("agent_delegation") is None

    def test_as_list(self):
        reg = RuntimeCapabilityRegistry()
        reg.register(StubAdapter())
        lst = reg.as_list()
        assert len(lst) == 1
        assert lst[0]["runtime_id"] == "stub"
        assert "capabilities" in lst[0]

    def test_adapter_missing_runtime_id_raises(self):
        class BadAdapter(RuntimeAdapter):
            RUNTIME_ID = ""
            async def health_check(self): ...
            async def execute(self, spec): ...
        reg = RuntimeCapabilityRegistry()
        with pytest.raises(ValueError, match="RUNTIME_ID"):
            reg.register(BadAdapter())


# ── CircuitState tests ─────────────────────────────────────────────────────────

class TestCircuitState:

    def test_starts_closed(self):
        cs = CircuitState("test")
        assert not cs.is_open

    def test_opens_after_threshold(self):
        cs = CircuitState("test")
        from runtimes.health import CB_FAILURE_THRESHOLD
        for _ in range(CB_FAILURE_THRESHOLD):
            cs.record_failure()
        assert cs.is_open

    def test_closes_on_success(self):
        cs = CircuitState("test")
        from runtimes.health import CB_FAILURE_THRESHOLD
        for _ in range(CB_FAILURE_THRESHOLD):
            cs.record_failure()
        assert cs.is_open
        cs.record_success()
        assert not cs.is_open


class TestRuntimePreflight:

    def test_missing_task_harness_binary_returns_structured_preflight_issue(self, monkeypatch):
        adapter = TaskHarnessStub()
        monkeypatch.delenv("TASK_HARNESS_BIN", raising=False)
        monkeypatch.setattr("shutil.which", lambda name: None)

        report = asyncio.run(
            adapter.readiness_check(
                TaskSpec(task_id="task-1", instruction="run", workspace_path=".")
            )
        )

        assert report.ready is False
        issue = report.issues[0]
        assert issue.code == "missing_binary"
        assert issue.details["binary"] == "task-harness"
        assert issue.details["config_var"] == "TASK_HARNESS_BIN"
        assert "Install a compatible harness" in (issue.fix_hint or "")

    def test_runtime_api_returns_preflight_report(self, monkeypatch):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from runtimes.api import runtime_router
        from runtimes.manager import RuntimeManager

        manager = RuntimeManager()
        manager.register(TaskHarnessStub())
        monkeypatch.setattr("runtimes.api.get_runtime_manager", lambda: manager)
        monkeypatch.setattr("shutil.which", lambda name: None)

        app = FastAPI()
        app.include_router(runtime_router)
        client = TestClient(app)

        response = client.post(
            "/runtimes/task_harness_stub/run",
            json={"instruction": "hello", "workspace_path": "."},
        )

        assert response.status_code == 412
        body = response.json()["detail"]
        assert body["runtime_id"] == "task_harness_stub"
        assert body["issues"][0]["code"] == "missing_binary"

    def test_routing_engine_falls_back_when_primary_preflight_fails(self, monkeypatch):
        reg = RuntimeCapabilityRegistry()
        failing = TaskHarnessStub()
        healthy = StubAdapter()
        reg.register(failing)
        reg.register(healthy)

        health = MagicMock()
        health.is_available.return_value = True
        engine = RuntimeRoutingPolicyEngine(
            reg,
            health,
            policy=RoutingPolicy(preferred_runtime_id="task_harness_stub", fallback_runtime_ids=["stub"]),
        )
        monkeypatch.setattr("shutil.which", lambda name: None if name == "task-harness" else "/usr/bin/git")

        result, decision = asyncio.run(
            engine.route_and_execute(TaskSpec(task_id="task-2", instruction="run", workspace_path="."))
        )

        assert result.runtime_id == "stub"
        assert decision.fallback_attempted is True
        assert decision.fallback_runtime_id == "stub"


# ── RoutingPolicy tests ───────────────────────────────────────────────────────

class TestRoutingPolicy:

    def test_default_policy_is_local_first(self):
        policy = RoutingPolicy()
        assert policy.never_use_paid_providers is True
        assert policy.require_approval_before_paid_escalation is True
        assert policy.max_paid_escalations_per_day == 0

    def test_as_dict(self):
        policy = RoutingPolicy(preferred_runtime_id="hermes")
        d = policy.as_dict()
        assert d["preferred_runtime_id"] == "hermes"
        assert "never_use_paid_providers" in d


# ── Routing engine tests ──────────────────────────────────────────────────────

class TestRuntimeRoutingPolicyEngine:

    def _make_engine(self, health_available=True, fail=False, policy=None):
        reg = RuntimeCapabilityRegistry()
        adapter = StubAdapter(health_available=health_available, fail=fail)
        reg.register(adapter)

        # Mock health service
        health = MagicMock()
        health.is_available.return_value = health_available

        engine = RuntimeRoutingPolicyEngine(reg, health, policy=policy)
        return engine, adapter

    def test_route_returns_result_and_decision(self):
        engine, _ = self._make_engine()
        spec = TaskSpec(task_id="t1", instruction="do something", task_type="code_generation")
        result, decision = asyncio.run(engine.route_and_execute(spec))
        assert result.success is True
        assert decision.selected_runtime_id == "stub"
        assert decision.task_id == "t1"

    def test_no_available_runtime_raises(self):
        engine, _ = self._make_engine(health_available=False)
        spec = TaskSpec(task_id="t2", instruction="test", task_type="code_generation")
        with pytest.raises(RuntimeUnavailableError):
            asyncio.run(engine.route_and_execute(spec))

    def test_decision_log_populated(self):
        engine, _ = self._make_engine()
        spec = TaskSpec(task_id="t3", instruction="test", task_type="general")
        asyncio.run(engine.route_and_execute(spec))
        log = engine.get_decision_log()
        assert len(log) == 1
        assert log[0]["task_id"] == "t3"

    def test_policy_prefers_runtime_override(self):
        reg = RuntimeCapabilityRegistry()
        reg.register(StubAdapter())
        reg.register(TierTwoStub())

        health = MagicMock()
        health.is_available.return_value = True

        policy = RoutingPolicy(task_type_runtime_overrides={"code_generation": "stub_t2"})
        engine = RuntimeRoutingPolicyEngine(reg, health, policy=policy)

        spec = TaskSpec(task_id="t4", instruction="write code", task_type="code_generation")
        result, decision = asyncio.run(engine.route_and_execute(spec))
        assert decision.selected_runtime_id == "stub_t2"


# ── Adapter metadata tests ────────────────────────────────────────────────────

class TestAdapterMetadata:
    """Verify all adapters have required metadata without needing a running runtime."""

    def _check_adapter(self, adapter: RuntimeAdapter):
        assert adapter.RUNTIME_ID, "RUNTIME_ID must not be empty"
        assert adapter.DISPLAY_NAME, "DISPLAY_NAME must not be empty"
        assert isinstance(adapter.TIER, RuntimeTier)
        assert isinstance(adapter.INTEGRATION_MODE, IntegrationMode)
        assert isinstance(adapter.CAPABILITIES, frozenset)
        d = adapter.as_dict()
        assert "runtime_id" in d
        assert "capabilities" in d

    def test_hermes_metadata(self):
        from runtimes.adapters.hermes import HermesAdapter
        self._check_adapter(HermesAdapter())

    def test_opencode_metadata(self):
        from runtimes.adapters.opencode import OpenCodeAdapter
        self._check_adapter(OpenCodeAdapter())

    def test_goose_metadata(self):
        from runtimes.adapters.goose import GooseAdapter
        self._check_adapter(GooseAdapter())

    def test_openhands_metadata(self):
        from runtimes.adapters.openhands import OpenHandsAdapter
        self._check_adapter(OpenHandsAdapter())

    def test_aider_metadata(self):
        from runtimes.adapters.aider import AiderAdapter
        self._check_adapter(AiderAdapter())

    def test_hermes_is_first_class(self):
        from runtimes.adapters.hermes import HermesAdapter
        assert HermesAdapter.TIER == RuntimeTier.FIRST_CLASS

    def test_opencode_is_first_class(self):
        from runtimes.adapters.opencode import OpenCodeAdapter
        assert OpenCodeAdapter.TIER == RuntimeTier.FIRST_CLASS

    def test_goose_is_tier_2(self):
        from runtimes.adapters.goose import GooseAdapter
        assert GooseAdapter.TIER == RuntimeTier.TIER_2

    def test_openhands_is_experimental(self):
        from runtimes.adapters.openhands import OpenHandsAdapter
        assert OpenHandsAdapter.TIER == RuntimeTier.EXPERIMENTAL

    def test_aider_is_tier_3(self):
        from runtimes.adapters.aider import AiderAdapter
        assert AiderAdapter.TIER == RuntimeTier.TIER_3

    def test_hermes_supports_scheduled_tasks(self):
        from runtimes.adapters.hermes import HermesAdapter
        assert HermesAdapter().supports(RuntimeCapability.SCHEDULED_TASKS)

    def test_opencode_supports_repo_editing(self):
        from runtimes.adapters.opencode import OpenCodeAdapter
        assert OpenCodeAdapter().supports(RuntimeCapability.REPO_EDITING)

    def test_aider_supports_git_operations(self):
        from runtimes.adapters.aider import AiderAdapter
        assert AiderAdapter().supports(RuntimeCapability.GIT_OPERATIONS)

    def test_hermes_health_returns_health_object_when_offline(self):
        from runtimes.adapters.hermes import HermesAdapter
        adapter = HermesAdapter({"base_url": "http://localhost:1"})
        health = asyncio.run(adapter.health_check())
        assert isinstance(health, RuntimeHealth)
        assert health.available is False
        assert health.error is not None

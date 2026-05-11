"""Tests for runtimes/routing.py _pick_runtime refactor introduced in this PR.

The method signature changed to return tuple[RuntimeAdapter | None, list[dict]]
and now populates candidates_info with runtime_id, tier, available, and health.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from runtimes.base import (
    IntegrationMode,
    RuntimeAdapter,
    RuntimeCapability,
    RuntimeHealth,
    RuntimeTier,
    TaskResult,
    TaskSpec,
)
from runtimes.health import RuntimeHealthService
from runtimes.registry import RuntimeCapabilityRegistry
from runtimes.routing import RoutingPolicy, RuntimeRoutingPolicyEngine


# ── Minimal stub adapters for testing ─────────────────────────────────────────

class _StubAdapter(RuntimeAdapter):
    RUNTIME_ID = "stub_runtime"
    DISPLAY_NAME = "Stub"
    DESCRIPTION = "Stub adapter for tests"
    TIER = RuntimeTier.FIRST_CLASS
    INTEGRATION_MODE = IntegrationMode.NATIVE
    DOCS_URL = ""
    # Include all capabilities needed for code_generation task type
    CAPABILITIES = frozenset({
        RuntimeCapability.CODE_GENERATION,
        RuntimeCapability.FILE_READ_WRITE,
    })

    async def health_check(self) -> RuntimeHealth:
        """
        Report this adapter's health as available.
        
        Returns:
            RuntimeHealth: An object containing this adapter's `runtime_id` and `available=True`.
        """
        return RuntimeHealth(runtime_id=self.RUNTIME_ID, available=True)

    async def execute(self, spec: TaskSpec) -> TaskResult:
        """
        Execute the given task specification and return a successful TaskResult from this adapter.
        
        Parameters:
            spec (TaskSpec): Task specification whose `task_id` will be propagated into the result.
        
        Returns:
            TaskResult: A successful result with `runtime_id` set to this adapter's `RUNTIME_ID`, `task_id` taken from `spec.task_id`, `success` equal to `True`, and `output` equal to `"ok"`.
        """
        return TaskResult(
            runtime_id=self.RUNTIME_ID,
            task_id=spec.task_id,
            success=True,
            output="ok",
        )


class _AltAdapter(RuntimeAdapter):
    RUNTIME_ID = "alt_runtime"
    DISPLAY_NAME = "Alt"
    DESCRIPTION = "Alternative adapter"
    TIER = RuntimeTier.TIER_2
    INTEGRATION_MODE = IntegrationMode.NATIVE
    DOCS_URL = ""
    CAPABILITIES = frozenset({
        RuntimeCapability.CODE_GENERATION,
        RuntimeCapability.FILE_READ_WRITE,
    })

    async def health_check(self) -> RuntimeHealth:
        """
        Report this adapter's health as available.
        
        Returns:
            RuntimeHealth: An object containing this adapter's `runtime_id` and `available=True`.
        """
        return RuntimeHealth(runtime_id=self.RUNTIME_ID, available=True)

    async def execute(self, spec: TaskSpec) -> TaskResult:
        """
        Execute the task spec for the alternative adapter.
        
        Parameters:
            spec (TaskSpec): Task specification whose `task_id` will be copied into the result.
        
        Returns:
            TaskResult: A result with `runtime_id` set to this adapter's `RUNTIME_ID`, `task_id` copied from `spec.task_id`, `success` set to `True`, and `output` set to `"alt ok"`.
        """
        return TaskResult(
            runtime_id=self.RUNTIME_ID,
            task_id=spec.task_id,
            success=True,
            output="alt ok",
        )


def _make_engine(adapters, availability_map: dict[str, bool]) -> RuntimeRoutingPolicyEngine:
    """
    Create a RuntimeRoutingPolicyEngine configured with the given adapters and a deterministic health cache for testing.
    
    Parameters:
        adapters (iterable[RuntimeAdapter]): Adapter classes to register in the engine's capability registry.
        availability_map (dict[str, bool]): Mapping from adapter RUNTIME_ID to seeded availability; missing IDs default to True.
    
    Returns:
        RuntimeRoutingPolicyEngine: Engine whose registry contains the provided adapters, whose RuntimeHealthService cache is seeded according to availability_map, and whose RoutingPolicy has never_use_paid_providers=True.
    """
    registry = RuntimeCapabilityRegistry()
    for adapter in adapters:
        registry.register(adapter)

    health_service = RuntimeHealthService(registry=registry)
    # Seed the health cache directly
    for adapter in adapters:
        avail = availability_map.get(adapter.RUNTIME_ID, True)
        health_service._cache[adapter.RUNTIME_ID] = RuntimeHealth(
            runtime_id=adapter.RUNTIME_ID, available=avail
        )

    policy = RoutingPolicy(never_use_paid_providers=True)
    return RuntimeRoutingPolicyEngine(registry, health_service, policy)


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_pick_runtime_returns_tuple():
    """_pick_runtime must return a 2-tuple (adapter, candidates_info)."""
    stub = _StubAdapter()
    engine = _make_engine([stub], {stub.RUNTIME_ID: True})
    result = engine._pick_runtime("code_generation", None)
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_pick_runtime_returns_adapter_when_available():
    """
    Verifies that _pick_runtime selects and returns the registered adapter when its health indicates it is available.
    
    The test seeds the engine's health cache with the stub adapter marked available and asserts the returned adapter is the same stub instance.
    """
    stub = _StubAdapter()
    engine = _make_engine([stub], {stub.RUNTIME_ID: True})
    adapter, candidates_info = engine._pick_runtime("code_generation", None)
    assert adapter is stub


def test_pick_runtime_returns_none_when_no_available_runtimes():
    stub = _StubAdapter()
    engine = _make_engine([stub], {stub.RUNTIME_ID: False})
    adapter, candidates_info = engine._pick_runtime("code_generation", None)
    assert adapter is None


def test_pick_runtime_candidates_info_non_empty():
    stub = _StubAdapter()
    engine = _make_engine([stub], {stub.RUNTIME_ID: True})
    _, candidates_info = engine._pick_runtime("code_generation", None)
    assert isinstance(candidates_info, list)
    assert len(candidates_info) >= 1


def test_pick_runtime_candidates_info_has_required_keys():
    stub = _StubAdapter()
    engine = _make_engine([stub], {stub.RUNTIME_ID: True})
    _, candidates_info = engine._pick_runtime("code_generation", None)
    entry = candidates_info[0]
    assert "runtime_id" in entry
    assert "tier" in entry
    assert "available" in entry
    assert "health" in entry


def test_pick_runtime_candidates_info_runtime_id_matches():
    stub = _StubAdapter()
    engine = _make_engine([stub], {stub.RUNTIME_ID: True})
    _, candidates_info = engine._pick_runtime("code_generation", None)
    assert candidates_info[0]["runtime_id"] == stub.RUNTIME_ID


def test_pick_runtime_candidates_info_available_reflects_health():
    stub = _StubAdapter()
    engine = _make_engine([stub], {stub.RUNTIME_ID: False})
    _, candidates_info = engine._pick_runtime("code_generation", None)
    assert candidates_info[0]["available"] is False


def test_pick_runtime_preferred_id_selects_matching():
    stub = _StubAdapter()
    alt = _AltAdapter()
    engine = _make_engine([stub, alt], {stub.RUNTIME_ID: True, alt.RUNTIME_ID: True})
    adapter, _ = engine._pick_runtime("code_generation", alt.RUNTIME_ID)
    assert adapter is alt


def test_pick_runtime_preferred_id_unavailable_falls_back_to_first():
    stub = _StubAdapter()
    alt = _AltAdapter()
    # alt is unavailable but stub is available
    engine = _make_engine([stub, alt], {stub.RUNTIME_ID: True, alt.RUNTIME_ID: False})
    adapter, _ = engine._pick_runtime("code_generation", alt.RUNTIME_ID)
    # preferred (alt) is not available, should fall back to stub
    assert adapter is stub


def test_pick_runtime_no_candidates_returns_empty_list():
    """When no runtimes are registered for the task type, candidates_info is empty."""
    stub = _StubAdapter()
    engine = _make_engine([stub], {stub.RUNTIME_ID: True})
    # "scheduled" requires SCHEDULED_TASKS which stub doesn't have
    adapter, candidates_info = engine._pick_runtime("scheduled", None)
    assert adapter is None
    assert candidates_info == []


def test_pick_runtime_candidates_info_tier_is_string():
    stub = _StubAdapter()
    engine = _make_engine([stub], {stub.RUNTIME_ID: True})
    _, candidates_info = engine._pick_runtime("code_generation", None)
    assert isinstance(candidates_info[0]["tier"], str)


def test_pick_runtime_candidates_info_health_dict_or_none():
    stub = _StubAdapter()
    engine = _make_engine([stub], {stub.RUNTIME_ID: True})
    _, candidates_info = engine._pick_runtime("code_generation", None)
    health = candidates_info[0]["health"]
    # health is either None or a dict with standard keys
    if health is not None:
        assert "runtime_id" in health
        assert "available" in health


def test_pick_runtime_multiple_candidates_all_in_info():
    stub = _StubAdapter()
    alt = _AltAdapter()
    engine = _make_engine([stub, alt], {stub.RUNTIME_ID: True, alt.RUNTIME_ID: True})
    _, candidates_info = engine._pick_runtime("code_generation", None)
    runtime_ids = {c["runtime_id"] for c in candidates_info}
    assert stub.RUNTIME_ID in runtime_ids
    assert alt.RUNTIME_ID in runtime_ids
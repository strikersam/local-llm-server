"""Tests for concurrent execution in MultiAgentSwarm."""

from __future__ import annotations

import asyncio
import time

import pytest

from agent.coordinate import AgentConfig, TaskInput, build_swarm, build_task_specs
from agent.coordinator import AgentSpec, MultiAgentSwarm, TaskSpec


@pytest.mark.anyio
async def test_independent_tasks_run_concurrently(monkeypatch, tmp_path):
    """Two independent tasks should complete faster than running sequentially."""
    TASK_DURATION = 0.3

    class FakeRunner:
        def __init__(self, **kwargs):
            pass

        async def run(self, **kwargs):
            await asyncio.sleep(TASK_DURATION)
            return {
                "summary": "done",
                "plan": {"steps": []},
                "steps": [],
                "commits": [],
            }

    monkeypatch.setattr("agent.coordinator.AgentRunner", FakeRunner)

    swarm = MultiAgentSwarm(
        ollama_base="http://localhost:11434", workspace_root=str(tmp_path)
    )
    agents = [
        AgentSpec(agent_id="a1", capabilities=["general"], max_parallel_tasks=1),
        AgentSpec(agent_id="a2", capabilities=["general"], max_parallel_tasks=1),
    ]
    tasks = [
        TaskSpec(task_id="t1", instruction="task 1", task_type="general"),
        TaskSpec(task_id="t2", instruction="task 2", task_type="general"),
    ]

    start = time.perf_counter()
    result = await swarm.run(
        goal="concurrent test", agents=agents, tasks=tasks, max_concurrent=2
    )
    elapsed = time.perf_counter() - start

    assert result.workers[0]["status"] == "ok"
    assert result.workers[1]["status"] == "ok"
    # Concurrent execution should complete significantly faster than 2 * TASK_DURATION
    assert elapsed < TASK_DURATION * 1.8, (
        f"Tasks appear sequential: {elapsed:.2f}s >= {TASK_DURATION * 1.8:.2f}s"
    )


@pytest.mark.anyio
async def test_dependent_tasks_are_not_concurrent(monkeypatch, tmp_path):
    """Dependent tasks must run sequentially respecting dependency order."""
    start_times: dict[str, float] = {}
    end_times: dict[str, float] = {}
    TASK_DURATION = 0.2

    class FakeRunner:
        def __init__(self, **kwargs):
            pass

        async def run(self, **kwargs):
            tid = kwargs["instruction"].split(":")[0]
            start_times[tid] = time.perf_counter()
            await asyncio.sleep(TASK_DURATION)
            end_times[tid] = time.perf_counter()
            return {
                "summary": "done",
                "plan": {"steps": []},
                "steps": [],
                "commits": [],
            }

    monkeypatch.setattr("agent.coordinator.AgentRunner", FakeRunner)

    swarm = MultiAgentSwarm(
        ollama_base="http://localhost:11434", workspace_root=str(tmp_path)
    )
    agents = [AgentSpec(agent_id="a1", capabilities=["general"], max_parallel_tasks=1)]
    tasks = [
        TaskSpec(task_id="t1", instruction="t1: first", task_type="general"),
        TaskSpec(
            task_id="t2",
            instruction="t2: second",
            task_type="general",
            dependencies=["t1"],
        ),
    ]

    result = await swarm.run(
        goal="sequential test", agents=agents, tasks=tasks, max_concurrent=2
    )

    assert all(w["status"] == "ok" for w in result.workers)
    # t2 must start after t1 ends
    assert start_times["t2"] >= end_times["t1"], "t2 started before t1 finished"


@pytest.mark.anyio
async def test_swarm_result_aggregation(monkeypatch, tmp_path):
    """run() should return completed/failed counts in CoordinatorResult."""
    call_n = {"n": 0}

    class FakeRunner:
        def __init__(self, **kwargs):
            pass

        async def run(self, **kwargs):
            call_n["n"] += 1
            return {
                "summary": f"done-{call_n['n']}",
                "plan": {"steps": []},
                "steps": [],
                "commits": [],
            }

    monkeypatch.setattr("agent.coordinator.AgentRunner", FakeRunner)

    swarm = MultiAgentSwarm(
        ollama_base="http://localhost:11434", workspace_root=str(tmp_path)
    )
    agents = [AgentSpec(agent_id="a", capabilities=["general"])]
    tasks = [
        TaskSpec(task_id=f"t{i}", instruction=f"task {i}", task_type="general")
        for i in range(4)
    ]

    result = await swarm.run(
        goal="aggregation test", agents=agents, tasks=tasks, max_concurrent=4
    )
    d = result.as_dict()

    assert d["workers"] is not None
    assert len(d["workers"]) == 4
    ok_count = sum(1 for w in d["workers"] if w["status"] == "ok")
    assert ok_count == 4

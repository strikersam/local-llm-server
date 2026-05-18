"""Tests for MultiAgentSwarm using the coordinate module helpers."""

from __future__ import annotations

import asyncio

import pytest

from agent.coordinate import (
    AgentConfig,
    TaskInput,
    build_agent_specs,
    build_swarm,
    build_task_specs,
)
from agent.coordinator import AgentSpec, MultiAgentSwarm, TaskSpec


def test_build_swarm_registers_agents(tmp_path):
    configs = [
        AgentConfig(
            agent_id="p1", name="planner", role="planner", capabilities=["research"]
        ),
        AgentConfig(
            agent_id="c1", name="coder", role="executor", capabilities=["code"]
        ),
        AgentConfig(
            agent_id="r1", name="reviewer", role="reviewer", capabilities=["review"]
        ),
    ]
    swarm, agents = build_swarm(configs, workspace_root=str(tmp_path))
    assert len(agents) == 3
    roles = {a.role for a in agents}
    assert {"planner", "executor", "reviewer"} == roles


def test_dependency_ordering_is_respected(monkeypatch, tmp_path):
    order: list[str] = []

    class FakeRunner:
        def __init__(self, **kwargs):
            pass

        async def run(self, **kwargs):
            order.append(kwargs["instruction"])
            return {
                "summary": kwargs["instruction"],
                "plan": {"steps": []},
                "steps": [],
                "commits": [],
            }

    monkeypatch.setattr("agent.coordinator.AgentRunner", FakeRunner)

    configs = [
        AgentConfig(
            agent_id="a1", name="planner", role="planner", capabilities=["general"]
        ),
    ]
    tasks_in = [
        TaskInput(instruction="research first", task_type="general", task_id="t1"),
        TaskInput(
            instruction="code second",
            task_type="general",
            task_id="t2",
            dependencies=["t1"],
        ),
        TaskInput(
            instruction="review third",
            task_type="general",
            task_id="t3",
            dependencies=["t2"],
        ),
    ]
    swarm, agents = build_swarm(configs, workspace_root=str(tmp_path))
    tasks = build_task_specs(tasks_in)

    result = asyncio.run(
        swarm.run(goal="test", agents=agents, tasks=tasks, max_concurrent=3)
    )

    assert order == ["research first", "code second", "review third"]
    assert all(w["status"] == "ok" for w in result.workers)


def test_blocked_task_when_dependency_missing(monkeypatch, tmp_path):
    swarm = MultiAgentSwarm(
        ollama_base="http://localhost:11434", workspace_root=str(tmp_path)
    )
    agents = [AgentSpec(agent_id="w", capabilities=["general"])]
    tasks = [
        TaskSpec(
            task_id="blocked", instruction="cannot run", dependencies=["missing-dep"]
        )
    ]

    result = asyncio.run(
        swarm.run(goal="test", agents=agents, tasks=tasks, max_concurrent=1)
    )

    assert result.workers[0]["status"] == "blocked"


def test_failed_task_does_not_deadlock_remaining(monkeypatch, tmp_path):
    call_count = {"n": 0}

    class FakeRunner:
        def __init__(self, **kwargs):
            pass

        async def run(self, **kwargs):
            call_count["n"] += 1
            if "fail" in kwargs["instruction"]:
                raise RuntimeError("forced failure")
            return {"summary": "ok", "plan": {"steps": []}, "steps": [], "commits": []}

    monkeypatch.setattr("agent.coordinator.AgentRunner", FakeRunner)

    configs = [
        AgentConfig(agent_id="a", name="a", role="worker", capabilities=["general"])
    ]
    tasks_in = [
        TaskInput(instruction="will fail", task_type="general", task_id="t1"),
        TaskInput(instruction="independent task", task_type="general", task_id="t2"),
    ]
    swarm, agents = build_swarm(configs, workspace_root=str(tmp_path))
    tasks = build_task_specs(tasks_in)

    result = asyncio.run(
        swarm.run(goal="test", agents=agents, tasks=tasks, max_concurrent=2)
    )

    statuses = {w["task_id"]: w["status"] for w in result.workers}
    # Independent task should succeed even though t1 failed
    assert statuses.get("t2") == "ok"

"""Tests for agent/coordinate.py models, helpers, and v2 router."""

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

from agent.coordinator import AgentSpec, TaskSpec

# ─── Model tests ───────────────────────────────────────────────────────────────


def test_agent_config_defaults():
    cfg = AgentConfig(name="planner", role="planner", capabilities=["research"])
    assert cfg.role == "planner"
    assert "research" in cfg.capabilities
    assert cfg.max_parallel_tasks == 1


def test_task_input_aliases():
    t = TaskInput(instruction="do something", task_type="code", id="my-id")
    assert t.resolved_task_id() == "my-id"
    assert t.resolved_task_type() == "code"
    assert t.resolved_instruction() == "do something"


def test_task_input_defaults():
    t = TaskInput(instruction="default task")
    assert t.resolved_task_type() == "general"
    assert t.priority == 0
    assert t.dependencies == []


# ─── Helper tests ──────────────────────────────────────────────────────────────


def test_build_agent_specs_with_configs():
    configs = [
        AgentConfig(
            agent_id="a1",
            name="planner",
            role="planner",
            capabilities=["research", "analysis"],
        ),
        AgentConfig(
            agent_id="a2", name="coder", role="executor", capabilities=["code"]
        ),
    ]
    specs = build_agent_specs(configs)
    assert len(specs) == 2
    assert specs[0].agent_id == "a1"
    assert "research" in specs[0].capabilities
    assert specs[1].agent_id == "a2"


def test_build_agent_specs_empty_returns_default():
    specs = build_agent_specs([])
    assert len(specs) == 1
    assert specs[0].agent_id == "default-worker"
    assert "general" in specs[0].capabilities


def test_build_task_specs():
    inputs = [
        TaskInput(instruction="plan first", task_type="research", task_id="t1"),
        TaskInput(
            instruction="code second",
            task_type="code",
            task_id="t2",
            dependencies=["t1"],
        ),
    ]
    specs = build_task_specs(inputs)
    assert len(specs) == 2
    assert specs[0].task_id == "t1"
    assert specs[1].dependencies == ["t1"]


def test_build_task_specs_with_type_alias():
    t = TaskInput(instruction="do work", type="debugging", task_id="t1")
    specs = build_task_specs([t])
    assert specs[0].task_type == "debugging"


# ─── Swarm integration ─────────────────────────────────────────────────────────


def test_build_swarm_returns_swarm_and_agents(tmp_path):
    configs = [
        AgentConfig(
            agent_id="a1", name="planner", role="planner", capabilities=["research"]
        ),
    ]
    swarm, agents = build_swarm(
        configs, ollama_base="http://localhost:11434", workspace_root=str(tmp_path)
    )
    assert swarm is not None
    assert len(agents) == 1
    assert agents[0].agent_id == "a1"


def test_coordinate_dependency_order_via_helpers(monkeypatch, tmp_path):
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
        TaskInput(instruction="step 1", task_type="general", task_id="t1"),
        TaskInput(
            instruction="step 2", task_type="general", task_id="t2", dependencies=["t1"]
        ),
    ]

    swarm, agents = build_swarm(
        configs, ollama_base="http://localhost:11434", workspace_root=str(tmp_path)
    )
    tasks = build_task_specs(tasks_in)

    result = asyncio.run(
        swarm.run(
            goal="test",
            agents=agents,
            tasks=tasks,
            max_concurrent=2,
        )
    )

    assert order == ["step 1", "step 2"]
    assert all(w["status"] == "ok" for w in result.workers)

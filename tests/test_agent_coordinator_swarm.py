from __future__ import annotations

import asyncio

from agent.coordinator import AgentSpec, MultiAgentSwarm, TaskSpec


def test_multi_agent_swarm_respects_dependencies(monkeypatch, tmp_path):
    order: list[str] = []

    class FakeRunner:
        def __init__(self, **kwargs):
            pass

        async def run(self, **kwargs):
            order.append(kwargs["instruction"])
            return {"summary": kwargs["instruction"], "plan": {"steps": []}, "steps": [], "commits": []}

    monkeypatch.setattr("agent.coordinator.AgentRunner", FakeRunner)
    swarm = MultiAgentSwarm(ollama_base="http://localhost:11434", workspace_root=str(tmp_path))

    result = asyncio.run(
        swarm.run(
            goal="ship feature",
            agents=[AgentSpec(agent_id="planner", capabilities=["planning", "general"]), AgentSpec(agent_id="coder", capabilities=["code"])],
            tasks=[
                TaskSpec(task_id="plan", instruction="plan first", task_type="planning"),
                TaskSpec(task_id="code", instruction="code second", task_type="code", dependencies=["plan"]),
            ],
            max_concurrent=2,
        )
    )

    assert order == ["plan first", "code second"]
    assert [worker["status"] for worker in result.workers] == ["ok", "ok"]


def test_multi_agent_swarm_blocks_missing_dependency(monkeypatch, tmp_path):
    swarm = MultiAgentSwarm(ollama_base="http://localhost:11434", workspace_root=str(tmp_path))

    result = asyncio.run(
        swarm.run(
            goal="ship feature",
            agents=[AgentSpec(agent_id="worker", capabilities=["general"])],
            tasks=[TaskSpec(task_id="blocked", instruction="cannot run", dependencies=["missing"])],
            max_concurrent=1,
        )
    )

    assert result.workers[0]["status"] == "blocked"
    assert "missing" in result.workers[0]["error"]
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from agents.api import agent_router
from agents.store import AgentDefinition, AgentStore, set_agent_store
from tasks.models import Task, TaskStatus
from tasks.store import TaskStore, set_task_store


def _build_client() -> TestClient:
    app = FastAPI()

    @app.middleware("http")
    async def inject_user(request: Request, call_next):
        request.state.user = {"email": "owner@example.com", "role": "admin"}
        return await call_next(request)

    app.include_router(agent_router)
    return TestClient(app)


def test_list_agents_reports_running_status_from_open_tasks() -> None:
    agent_store = AgentStore()
    set_agent_store(agent_store)
    task_store = TaskStore()
    set_task_store(task_store)

    busy = AgentDefinition(
        owner_id="owner@example.com",
        agent_id="agent_busy",
        name="Busy Agent",
        task_types=["general"],
        is_public=True,
    )
    idle = AgentDefinition(
        owner_id="owner@example.com",
        agent_id="agent_idle",
        name="Idle Agent",
        task_types=["general"],
        is_public=True,
    )

    import asyncio

    asyncio.run(agent_store.create(busy))
    asyncio.run(agent_store.create(idle))
    asyncio.run(
        task_store.create(
            Task(
                owner_id="owner@example.com",
                title="Active task",
                agent_id="agent_busy",
                status=TaskStatus.IN_PROGRESS,
                pending_agent_run=True,
            )
        )
    )

    client = _build_client()
    response = client.get("/api/agents/")
    assert response.status_code == 200, response.text

    agents = {agent["agent_id"]: agent for agent in response.json()["agents"]}
    assert agents["agent_busy"]["status"] == "running"
    assert agents["agent_busy"]["open_task_count"] == 1
    assert agents["agent_idle"]["status"] == "idle"
    assert agents["agent_idle"]["open_task_count"] == 0

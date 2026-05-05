"""Tests for the Multica-style task workflow."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import asyncio
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from agents.store import AgentDefinition, AgentStore, set_agent_store
from tasks.api import task_router
from tasks.models import ApprovalCheckpoint, Task, TaskCreateRequest, TaskStatus
from tasks.service import TaskExecutionCoordinator, TaskWorkflowService
from tasks.store import TaskStore, set_task_store


@pytest.fixture()
def task_store() -> TaskStore:
    store = TaskStore()
    set_task_store(store)
    return store


@pytest.fixture()
def agent_store() -> AgentStore:
    store = AgentStore()
    set_agent_store(store)
    return store


@pytest.fixture()
def workflow(task_store: TaskStore) -> TaskWorkflowService:
    return TaskWorkflowService(store=task_store)


@pytest.fixture()
def api_client(task_store: TaskStore) -> TestClient:
    app = FastAPI()

    @app.middleware("http")
    async def inject_user(request: Request, call_next):
        request.state.user = SimpleNamespace(email="owner@example.com", role="admin")
        return await call_next(request)

    app.include_router(task_router)
    return TestClient(app)


def test_task_create_request_accepts_status():
    body = TaskCreateRequest(title="Ship review", status=TaskStatus.IN_REVIEW)
    assert body.status is TaskStatus.IN_REVIEW


@pytest.mark.asyncio
async def test_workflow_enforces_blocked_reason_and_legal_transitions(workflow: TaskWorkflowService):
    task = Task(owner_id="owner@example.com", title="Fix auth", agent_id="agent_builder")

    with pytest.raises(ValueError, match="blocked_reason"):
        workflow.transition(task, TaskStatus.BLOCKED, actor="user:owner@example.com")

    workflow.transition(task, TaskStatus.IN_PROGRESS, actor="agent:builder")
    assert task.status is TaskStatus.IN_PROGRESS
    assert task.pending_agent_run is True

    workflow.transition(
        task,
        TaskStatus.BLOCKED,
        actor="agent:builder",
        blocked_reason="Waiting for credentials",
    )
    assert task.status is TaskStatus.BLOCKED
    assert task.blocked_reason == "Waiting for credentials"

    with pytest.raises(ValueError, match="Cannot transition"):
        workflow.transition(task, TaskStatus.DONE, actor="user:owner@example.com")


@pytest.mark.asyncio
async def test_comment_on_review_task_requeues_execution(workflow: TaskWorkflowService):
    task = Task(
        owner_id="owner@example.com",
        title="Review this patch",
        agent_id="agent_writer",
        status=TaskStatus.IN_REVIEW,
        review_reason="Needs confirmation from a human reviewer",
    )

    comment = workflow.add_comment(
        task,
        author="owner@example.com",
        body="Please address the naming issue in the helper.",
    )

    assert comment.reply_to is None
    assert task.status is TaskStatus.IN_PROGRESS
    assert task.pending_agent_run is True
    assert any("re-entered execution" in entry.message for entry in task.execution_log)


@pytest.mark.asyncio
async def test_comment_on_review_task_without_agent_still_requeues_execution(workflow: TaskWorkflowService):
    task = Task(
        owner_id="owner@example.com",
        title="Review this patch",
        status=TaskStatus.IN_REVIEW,
        review_reason="Needs confirmation from a human reviewer",
    )

    workflow.add_comment(
        task,
        author="owner@example.com",
        body="Please continue with the internal fallback runtime.",
    )

    assert task.status is TaskStatus.IN_PROGRESS
    assert task.pending_agent_run is True


@pytest.mark.asyncio
async def test_create_task_auto_assigns_best_available_agent(
    workflow: TaskWorkflowService,
    agent_store: AgentStore,
):
    await agent_store.create(
        AgentDefinition(
            owner_id="owner@example.com",
            agent_id="agent_general",
            name="General Agent",
            model="qwen3-coder:30b",
            task_types=["general"],
            is_public=True,
        )
    )
    await agent_store.create(
        AgentDefinition(
            owner_id="owner@example.com",
            agent_id="agent_codegen",
            name="Code Agent",
            model="qwen3-coder:30b",
            task_types=["code_generation"],
            is_public=True,
        )
    )

    task = Task(
        owner_id="owner@example.com",
        title="Generate endpoint",
        description="Create the missing endpoint.",
        task_type="code_generation",
    )

    await workflow.create_task(task, actor="owner@example.com")

    assert task.agent_id == "agent_codegen"
    assert task.pending_agent_run is True
    assert any(entry.event_type == "agent_auto_assigned" for entry in task.execution_log)


@pytest.mark.asyncio
async def test_rejecting_checkpoint_requeues_task(workflow: TaskWorkflowService):
    task = Task(
        owner_id="owner@example.com",
        title="Prepare release",
        agent_id="agent_release",
        status=TaskStatus.IN_REVIEW,
        requires_approval=True,
        review_reason="Approve release notes",
        approval_checkpoints=[ApprovalCheckpoint(description="Approve release notes")],
    )
    checkpoint = task.approval_checkpoints[0]

    workflow.record_approval(
        task,
        checkpoint_id=checkpoint.checkpoint_id,
        approved=False,
        actor="owner@example.com",
        reason="Add the missing breaking-change note",
    )

    assert task.status is TaskStatus.IN_PROGRESS
    assert task.pending_agent_run is True
    assert checkpoint.approved is False


@pytest.mark.asyncio
async def test_transition_to_in_progress_requeues_even_without_agent(workflow: TaskWorkflowService):
    task = Task(
        owner_id="owner@example.com",
        title="Resume backlog item",
        status=TaskStatus.TODO,
    )

    workflow.transition(task, TaskStatus.IN_PROGRESS, actor="owner@example.com")

    assert task.status is TaskStatus.IN_PROGRESS
    assert task.pending_agent_run is True


@dataclass
class _FakeDecision:
    selected_runtime_id: str
    model_used: str | None
    provider_used: str | None
    reason: str
    escalated: bool = False
    escalation_reason: str | None = None
    fallback_attempted: bool = False
    fallback_runtime_id: str | None = None


@dataclass
class _FakeResult:
    runtime_id: str
    task_id: str
    success: bool
    output: str
    model_used: str | None = None
    provider_used: str | None = None
    tokens_used: int | None = None
    cost_usd: float | None = None
    execution_time_ms: float | None = None
    artifacts: list[dict] | None = None
    tool_calls: list[dict] | None = None
    escalation_reason: str | None = None
    metadata: dict | None = None


class _FakeRuntimeManager:
    def __init__(self) -> None:
        self.specs = []

    async def execute(self, spec):
        self.specs.append(spec)
        return (
            _FakeResult(
                runtime_id="hermes",
                task_id=spec.task_id,
                success=True,
                output="Implemented the requested change and opened it for review.",
                model_used=spec.model_preference,
                provider_used="local",
                tokens_used=321,
                cost_usd=0.0,
                metadata={
                    "task_status": "in_review",
                    "review_reason": "Ready for human approval",
                    "agent_comment": "I implemented the change and need a review.",
                },
            ),
            _FakeDecision(
                selected_runtime_id="hermes",
                model_used=spec.model_preference,
                provider_used="local",
                reason="Preferred agent runtime",
            ),
        )


@pytest.mark.asyncio
async def test_execution_coordinator_uses_assigned_agent_runtime_and_logs_history(
    task_store: TaskStore,
    agent_store: AgentStore,
):
    agent = AgentDefinition(
        owner_id="owner@example.com",
        agent_id="agent_writer",
        name="Writer",
        model="qwen3-coder:30b",
        runtime_id="hermes",
        system_prompt="Be precise and ask for approval when code is ready.",
        task_types=["code_generation"],
        cost_policy="local_only",
    )
    await agent_store.create(agent)

    task = Task(
        owner_id="owner@example.com",
        title="Implement the handler",
        description="Update the task workflow handler.",
        prompt="Implement the handler and summarize the result.",
        agent_id=agent.agent_id,
        task_type="code_generation",
        pending_agent_run=True,
    )
    await task_store.create(task)

    coordinator = TaskExecutionCoordinator(
        store=task_store,
        workflow=TaskWorkflowService(store=task_store),
        agent_store=agent_store,
        runtime_manager=_FakeRuntimeManager(),
        workspace_root="/tmp/workspace",
    )

    updated = await coordinator.execute(task.task_id)

    assert updated.status is TaskStatus.IN_REVIEW
    assert updated.review_reason == "Ready for human approval"
    assert updated.last_runtime_id == "hermes"
    assert updated.last_model_used == "qwen3-coder:30b"
    assert updated.pending_agent_run is False
    assert updated.comments[-1].author == "agent:agent_writer"
    assert updated.comments[-1].body == "I implemented the change and need a review."
    assert any("Runtime selected" in entry.message for entry in updated.execution_log)

    runtime_manager = coordinator.runtime_manager
    assert runtime_manager.specs[0].provider_preference == "hermes"
    assert runtime_manager.specs[0].model_preference == "qwen3-coder:30b"
    assert runtime_manager.specs[0].context["agent"]["system_prompt"] == agent.system_prompt


def test_create_task_persists_requested_status(api_client: TestClient):
    response = api_client.post("/api/tasks/", json={"title": "Review me", "status": "in_review"})

    assert response.status_code == 201
    assert response.json()["task"]["status"] == "in_review"


def test_run_task_endpoint_schedules_execution(api_client: TestClient, task_store: TaskStore, monkeypatch):
    task = Task(owner_id="owner@example.com", title="Run me now", pending_agent_run=True)
    asyncio.run(task_store.create(task))

    calls: list[str] = []

    class _StubCoordinator:
        def __init__(self, **kwargs):
            pass

        async def execute(self, task_id: str):
            calls.append(task_id)

    monkeypatch.setattr("tasks.api.TaskExecutionCoordinator", _StubCoordinator)

    response = api_client.post(f"/api/tasks/{task.task_id}/run")

    assert response.status_code == 202
    assert response.json()["queued"] is True
    assert response.json()["task"]["task_id"] == task.task_id
    assert calls == [task.task_id]


@pytest.mark.asyncio
async def test_scheduler_trigger_creates_real_task(
    task_store: TaskStore,
    workflow: TaskWorkflowService,
):
    from agent.scheduler import AgentScheduler
    from tasks.automation import TaskAutomationService

    automation = TaskAutomationService(store=task_store, workflow=workflow)
    scheduler = AgentScheduler(on_fire=automation.handle_scheduled_job)

    job = scheduler.create(
        name="Daily review",
        cron="0 9 * * 1",
        instruction="Review the backlog",
        agent_id="agent_writer",
        task_type="code_review",
    )
    scheduler.trigger(job.job_id)
    await asyncio.sleep(0)

    tasks = await task_store.list_all()
    assert len(tasks) == 1
    assert tasks[0].source == "scheduler"
    assert tasks[0].source_run_id == job.job_id
    assert tasks[0].agent_id == "agent_writer"
    assert tasks[0].pending_agent_run is True
    scheduler.shutdown()


@pytest.mark.asyncio
async def test_end_to_end_api_task_creation_and_execution_history(
    api_client: TestClient,
    task_store: TaskStore,
    agent_store: AgentStore,
):
    agent = AgentDefinition(
        owner_id="owner@example.com",
        agent_id="agent_e2e",
        name="E2E Agent",
        model="qwen3-coder:30b",
        runtime_id="hermes",
        system_prompt="Complete the task and leave a review summary.",
        task_types=["code_generation"],
    )
    await agent_store.create(agent)

    create_response = api_client.post(
        "/api/tasks/",
        json={
            "title": "Implement workflow API",
            "prompt": "Implement the workflow API and summarize what changed.",
            "agent_id": agent.agent_id,
            "task_type": "code_generation",
        },
    )
    assert create_response.status_code == 201
    task_id = create_response.json()["task"]["task_id"]

    coordinator = TaskExecutionCoordinator(
        store=task_store,
        workflow=TaskWorkflowService(store=task_store),
        agent_store=agent_store,
        runtime_manager=_FakeRuntimeManager(),
        workspace_root="/tmp/workspace",
    )
    await coordinator.execute(task_id)

    fetch_response = api_client.get(f"/api/tasks/{task_id}")
    assert fetch_response.status_code == 200
    task = fetch_response.json()["task"]
    assert task["status"] == "in_review"
    assert task["last_runtime_id"] == "hermes"
    assert task["last_model_used"] == "qwen3-coder:30b"
    assert task["comments"][-1]["author"] == "agent:agent_e2e"
    assert any(entry["event_type"] == "runtime_selected" for entry in task["execution_log"])


@pytest.mark.asyncio
async def test_execution_timeout_marks_task_failed(
    task_store: TaskStore,
    workflow: TaskWorkflowService,
) -> None:
    task = Task(
        owner_id="owner@example.com",
        title="Long running task",
        prompt="Do something slow.",
        task_type="code_generation",
        pending_agent_run=True,
    )
    await task_store.create(task)

    class _SlowRuntimeManager:
        async def execute(self, spec):
            await asyncio.sleep(0.05)

    coordinator = TaskExecutionCoordinator(
        store=task_store,
        workflow=workflow,
        runtime_manager=_SlowRuntimeManager(),
        workspace_root="/tmp/workspace",
        execution_timeout_s=0.01,
    )

    updated = await coordinator.execute(task.task_id)

    assert updated.status is TaskStatus.FAILED
    assert updated.pending_agent_run is False
    assert updated.error_message is not None
    assert "timed out" in updated.error_message.lower()


@pytest.mark.asyncio
async def test_coordinator_deduplicates_overlapping_execution_requests(task_store: TaskStore) -> None:
    task = Task(
        owner_id="owner@example.com",
        title="Only run once",
        pending_agent_run=True,
    )
    await task_store.create(task)

    started = asyncio.Event()
    release = asyncio.Event()

    class _SlowRuntimeManager:
        def __init__(self) -> None:
            self.calls = 0

        async def execute(self, spec):
            self.calls += 1
            started.set()
            await release.wait()
            return (
                _FakeResult(
                    runtime_id="internal_agent",
                    task_id=spec.task_id,
                    success=True,
                    output="done",
                ),
                _FakeDecision(
                    selected_runtime_id="internal_agent",
                    model_used=None,
                    provider_used="local",
                    reason="dedupe test",
                ),
            )

    runtime_manager = _SlowRuntimeManager()
    coordinator = TaskExecutionCoordinator(
        store=task_store,
        workflow=TaskWorkflowService(store=task_store),
        runtime_manager=runtime_manager,
        workspace_root="/tmp/workspace",
    )

    first = asyncio.create_task(coordinator.execute(task.task_id))
    await started.wait()
    second = asyncio.create_task(coordinator.execute(task.task_id))

    await asyncio.sleep(0)
    release.set()
    await asyncio.gather(first, second)

    assert runtime_manager.calls == 1

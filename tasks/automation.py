"""Helpers that turn scheduler and playbook activity into real tasks."""

from __future__ import annotations

from tasks.models import TaskStatus
from tasks.models import Task
from tasks.service import TaskWorkflowService
from tasks.store import TaskStore, get_task_store


class TaskAutomationService:
    """Creates tasks from scheduler and playbook runs using one workflow."""

    def __init__(
        self,
        *,
        store: TaskStore | None = None,
        workflow: TaskWorkflowService | None = None,
        owner_id: str = "system",
    ) -> None:
        self.store = store or get_task_store()
        self.workflow = workflow or TaskWorkflowService(store=self.store)
        self.owner_id = owner_id

    async def handle_scheduled_job(self, job) -> Task:
        task = Task(
            owner_id=self.owner_id,
            title=job.name,
            description=f"Scheduled job fired from cron `{job.cron}`.",
            prompt=job.instruction,
            agent_id=getattr(job, "agent_id", None),
            runtime_id=getattr(job, "runtime_id", None),
            model_preference=getattr(job, "model", None),
            task_type=getattr(job, "task_type", "scheduled"),
            requires_approval=getattr(job, "requires_approval", False),
            tags=list(getattr(job, "tags", []) or []),
            status=getattr(job, "initial_status", None) or getattr(job, "status", None) or TaskStatus.TODO,
            source="scheduler",
            source_id=job.job_id,
            source_run_id=job.job_id,
        )
        return await self.workflow.create_task(task, actor=f"scheduler:{job.job_id}")

    async def create_playbook_task(
        self,
        *,
        owner_id: str,
        playbook_id: str,
        run_id: str,
        playbook_name: str,
        step_id: int,
        instruction: str,
        agent_id: str | None = None,
        model: str | None = None,
        runtime_id: str | None = None,
        tags: list[str] | None = None,
    ) -> Task:
        task = Task(
            owner_id=owner_id,
            title=f"{playbook_name} · Step {step_id}",
            description=f"Playbook step {step_id} created from playbook {playbook_name}.",
            prompt=instruction,
            agent_id=agent_id,
            runtime_id=runtime_id,
            model_preference=model,
            task_type="scheduled",
            tags=list(tags or []),
            source="playbook",
            source_id=playbook_id,
            source_run_id=run_id,
        )
        return await self.workflow.create_task(task, actor=f"playbook:{playbook_id}")

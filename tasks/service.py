"""Domain services for task workflow and runtime-backed execution."""

from __future__ import annotations

import logging
import time
from typing import Any

from agents.store import AgentDefinition, AgentStore, get_agent_store
from runtimes.base import TaskResult, TaskSpec
from runtimes.manager import RuntimeManager, get_runtime_manager
from tasks.models import Task, TaskComment, TaskStatus
from tasks.store import TaskStore, get_task_store

log = logging.getLogger("qwen-proxy")


ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.TODO: {TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED, TaskStatus.FAILED},
    TaskStatus.IN_PROGRESS: {TaskStatus.IN_REVIEW, TaskStatus.BLOCKED, TaskStatus.DONE, TaskStatus.FAILED},
    TaskStatus.IN_REVIEW: {TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED, TaskStatus.DONE},
    TaskStatus.BLOCKED: {TaskStatus.IN_PROGRESS, TaskStatus.FAILED},
    TaskStatus.FAILED: {TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED},
    TaskStatus.DONE: {TaskStatus.IN_PROGRESS},
}


class TaskWorkflowService:
    """Owns lifecycle transitions, comment semantics, and approval rules."""

    def __init__(self, *, store: TaskStore | None = None) -> None:
        self.store = store or get_task_store()

    async def create_task(self, task: Task, *, actor: str) -> Task:
        self._validate_status_payload(task.status, blocked_reason=task.blocked_reason, review_reason=task.review_reason)
        auto_assigned_agent: AgentDefinition | None = None
        if not task.agent_id and task.status in {TaskStatus.TODO, TaskStatus.IN_PROGRESS}:
            auto_assigned_agent = await self._select_agent(task)
            if auto_assigned_agent is not None:
                task.agent_id = auto_assigned_agent.agent_id
        if task.agent_id and task.status in {TaskStatus.TODO, TaskStatus.IN_PROGRESS}:
            task.pending_agent_run = True
        task.add_log(
            f"Task created by {actor}",
            event_type="task_created",
            actor=actor,
            task_status=task.status,
            metadata={"source": task.source},
        )
        if auto_assigned_agent is not None:
            task.add_log(
                f"Auto-assigned to {auto_assigned_agent.name}",
                event_type="agent_auto_assigned",
                actor="system:auto-assignment",
                task_status=task.status,
                metadata={
                    "agent_id": auto_assigned_agent.agent_id,
                    "runtime_id": auto_assigned_agent.runtime_id,
                    "task_type": task.task_type,
                },
            )
        await self.store.create(task)
        return task

    async def save(self, task: Task) -> Task:
        await self.store.update(task)
        return task

    def transition(
        self,
        task: Task,
        status: TaskStatus,
        *,
        actor: str,
        blocked_reason: str | None = None,
        review_reason: str | None = None,
        message: str | None = None,
        pending_agent_run: bool | None = None,
    ) -> Task:
        if status != task.status:
            allowed = ALLOWED_TRANSITIONS.get(task.status, set())
            if status not in allowed:
                raise ValueError(f"Cannot transition task from {task.status.value} to {status.value}")

        self._validate_status_payload(status, blocked_reason=blocked_reason, review_reason=review_reason)

        task.status = status
        task.blocked_reason = blocked_reason if status is TaskStatus.BLOCKED else None
        task.review_reason = review_reason if status is TaskStatus.IN_REVIEW else None

        if status is TaskStatus.IN_PROGRESS:
            if task.started_at is None:
                task.started_at = time.time()
            if pending_agent_run is None:
                task.pending_agent_run = bool(task.agent_id)
            else:
                task.pending_agent_run = pending_agent_run
        elif status in {TaskStatus.IN_REVIEW, TaskStatus.BLOCKED, TaskStatus.DONE, TaskStatus.FAILED}:
            task.pending_agent_run = bool(pending_agent_run) if pending_agent_run is not None else False

        if status is TaskStatus.DONE and task.completed_at is None:
            task.completed_at = time.time()
        if status in {TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED, TaskStatus.IN_REVIEW, TaskStatus.FAILED}:
            if status is not TaskStatus.DONE:
                task.completed_at = None

        task.add_log(
            message or f"Task moved to {status.value} by {actor}",
            event_type="status_changed",
            actor=actor,
            task_status=status,
            metadata={
                "blocked_reason": blocked_reason,
                "review_reason": review_reason,
            },
        )
        return task

    def assign_agent(self, task: Task, agent_id: str | None, *, actor: str) -> Task:
        previous = task.agent_id
        task.agent_id = agent_id
        if agent_id and task.status in {TaskStatus.TODO, TaskStatus.IN_PROGRESS}:
            task.pending_agent_run = True
        task.add_log(
            f"Agent assignment updated by {actor}",
            event_type="agent_assigned",
            actor=actor,
            task_status=task.status,
            metadata={"previous_agent_id": previous, "agent_id": agent_id},
        )
        return task

    def add_comment(
        self,
        task: Task,
        *,
        author: str,
        body: str,
        reply_to: str | None = None,
    ) -> TaskComment:
        if reply_to and not any(comment.comment_id == reply_to for comment in task.comments):
            raise ValueError(f"Unknown parent comment: {reply_to}")

        comment = TaskComment(author=author, body=body, reply_to=reply_to)
        task.comments.append(comment)
        task.add_log(
            f"Comment added by {author}",
            event_type="comment_added",
            actor=author,
            task_status=task.status,
            metadata={"comment_id": comment.comment_id, "reply_to": reply_to},
        )

        is_agent = author.startswith("agent:")
        if not is_agent and task.agent_id and task.status is TaskStatus.IN_REVIEW:
            self.transition(
                task,
                TaskStatus.IN_PROGRESS,
                actor=author,
                message=f"Task re-entered execution after comment by {author}",
                pending_agent_run=True,
            )

        return comment

    def record_approval(
        self,
        task: Task,
        *,
        checkpoint_id: str,
        approved: bool,
        actor: str,
        reason: str | None = None,
    ) -> Task:
        checkpoint = next(
            (item for item in task.approval_checkpoints if item.checkpoint_id == checkpoint_id),
            None,
        )
        if checkpoint is None:
            raise ValueError(f"Unknown checkpoint: {checkpoint_id}")

        checkpoint.approved = approved
        checkpoint.approved_by = actor
        checkpoint.approved_at = time.time()
        checkpoint.reason = reason

        if approved:
            pending_required = [
                item for item in task.approval_checkpoints
                if item.required and item.approved is not True
            ]
            if not pending_required:
                self.transition(
                    task,
                    TaskStatus.DONE,
                    actor=actor,
                    message=f"All approvals completed by {actor}",
                )
        else:
            self.transition(
                task,
                TaskStatus.IN_PROGRESS,
                actor=actor,
                message=f"Checkpoint rejected by {actor}; task returned to execution",
                pending_agent_run=bool(task.agent_id),
            )

        task.add_log(
            f"Checkpoint {'approved' if approved else 'rejected'} by {actor}",
            event_type="approval_decision",
            actor=actor,
            task_status=task.status,
            metadata={"checkpoint_id": checkpoint_id, "approved": approved, "reason": reason},
        )
        return task

    def retry(self, task: Task, *, actor: str) -> Task:
        if task.status not in {TaskStatus.FAILED, TaskStatus.BLOCKED, TaskStatus.IN_REVIEW}:
            raise ValueError(f"Retry is only allowed for failed, blocked, or in_review tasks (got {task.status.value})")

        if task.status is TaskStatus.IN_REVIEW:
            self.transition(
                task,
                TaskStatus.IN_PROGRESS,
                actor=actor,
                message=f"Review retry requested by {actor}",
                pending_agent_run=bool(task.agent_id),
            )
        else:
            self.transition(
                task,
                TaskStatus.TODO if task.status is TaskStatus.FAILED else TaskStatus.IN_PROGRESS,
                actor=actor,
                message=f"Task reset for retry by {actor}",
                pending_agent_run=bool(task.agent_id),
            )
        task.error_message = None
        return task

    def escalate(self, task: Task, *, actor: str, reason: str | None = None) -> Task:
        task.escalation_count += 1
        task.escalation_reason = reason or task.escalation_reason
        self.transition(
            task,
            TaskStatus.BLOCKED,
            actor=actor,
            blocked_reason=reason or "Escalated for human intervention",
            message=f"Task escalated by {actor}",
        )
        return task

    def _validate_status_payload(
        self,
        status: TaskStatus,
        *,
        blocked_reason: str | None,
        review_reason: str | None,
    ) -> None:
        if status is TaskStatus.BLOCKED and not blocked_reason:
            raise ValueError("blocked_reason is required when moving a task to blocked")
        if status is TaskStatus.IN_REVIEW and not review_reason:
            raise ValueError("review_reason is required when moving a task to in_review")

    async def _select_agent(self, task: Task) -> AgentDefinition | None:
        agent_store = get_agent_store()
        runtime_manager = get_runtime_manager()
        candidates = await agent_store.list_for_user(task.owner_id, include_public=True)
        if not candidates:
            return None

        def _score(agent: AgentDefinition) -> tuple[int, int, float]:
            score = 0
            task_types = {task_type.strip().lower() for task_type in (agent.task_types or []) if task_type}
            task_type = (task.task_type or "general").strip().lower()

            if task_type and task_type in task_types:
                score += 100
            elif "general" in task_types:
                score += 45
            elif not task_types:
                score += 20

            if task.runtime_id and agent.runtime_id == task.runtime_id:
                score += 30
            elif not task.runtime_id and agent.runtime_id:
                runtime = runtime_manager.get_runtime(agent.runtime_id)
                if runtime and runtime.get("health", {}).get("available") is True:
                    score += 15

            if task.model_preference and agent.model == task.model_preference:
                score += 10

            if agent.is_public:
                score += 5

            if any(tag.startswith("crispy:") for tag in agent.tags):
                score += 3

            return (score, -agent.use_count, -agent.created_at)

        ranked = sorted(candidates, key=_score, reverse=True)
        best = ranked[0]
        best_score = _score(best)[0]
        if best_score <= 0:
            return None
        return best


class TaskExecutionCoordinator:
    """Executes tasks through the runtime layer using agent definitions."""

    def __init__(
        self,
        *,
        store: TaskStore | None = None,
        workflow: TaskWorkflowService | None = None,
        agent_store: AgentStore | None = None,
        runtime_manager: RuntimeManager | None = None,
        workspace_root: str = ".",
    ) -> None:
        self.store = store or get_task_store()
        self.workflow = workflow or TaskWorkflowService(store=self.store)
        self.agent_store = agent_store or get_agent_store()
        self.runtime_manager = runtime_manager or get_runtime_manager()
        self.workspace_root = workspace_root

    async def execute(self, task_id: str) -> Task:
        task = await self.store.get(task_id)
        if task is None:
            raise ValueError(f"Task not found: {task_id}")
        if not task.pending_agent_run:
            return task

        agent = await self._resolve_agent(task)

        self.workflow.transition(
            task,
            TaskStatus.IN_PROGRESS,
            actor=f"agent:{agent.agent_id}" if agent else "system:dispatcher",
            message=f"Execution started for task {task.task_id}",
            pending_agent_run=False,
        )
        task.add_log(
            "Resolved execution context",
            event_type="execution_context",
            actor=f"agent:{agent.agent_id}" if agent else "system:dispatcher",
            task_status=task.status,
            metadata={
                "agent_id": agent.agent_id if agent else None,
                "runtime_id": task.runtime_id or (agent.runtime_id if agent else None),
                "model": task.model_preference or (agent.model if agent else None),
            },
        )
        await self.store.update(task)

        try:
            spec = self._build_spec(task, agent)
            result, decision = await self.runtime_manager.execute(spec)

            task.last_runtime_id = decision.selected_runtime_id
            task.last_model_used = result.model_used or decision.model_used
            task.tokens_used = result.tokens_used
            task.cost_usd = result.cost_usd
            task.result = result.output
            task.error_message = None
            task.add_log(
                f"Runtime selected: {decision.selected_runtime_id}",
                event_type="runtime_selected",
                actor="system:dispatcher",
                task_status=task.status,
                runtime_id=decision.selected_runtime_id,
                model_used=result.model_used or decision.model_used,
                metadata={
                    "reason": decision.reason,
                    "fallback_runtime_id": decision.fallback_runtime_id,
                    "fallback_attempted": decision.fallback_attempted,
                },
            )

            await self._apply_result(task, agent, result)
        except Exception as exc:
            log.error("Error executing task %s: %s", task.task_id, exc, exc_info=True)
            task.error_message = str(exc)
            self.workflow.transition(
                task,
                TaskStatus.FAILED,
                actor="system:coordinator",
                message=f"Execution failed: {exc}",
            )
        finally:
            await self.store.update(task)
        return task

    async def _resolve_agent(self, task: Task) -> AgentDefinition | None:
        if task.agent_id:
            agent = await self.agent_store.get(task.agent_id, owner_id=None)
            if agent:
                agent.record_use()
                await self.agent_store.update(agent)
                return agent

        if task.agent_id:
            log.warning("Assigned agent %s not found; falling back to task configuration", task.agent_id)
        auto_assigned = await self.workflow._select_agent(task)
        if auto_assigned is not None:
            previous = task.agent_id
            task.agent_id = auto_assigned.agent_id
            task.add_log(
                f"Auto-assigned to {auto_assigned.name}",
                event_type="agent_auto_assigned",
                actor="system:auto-assignment",
                task_status=task.status,
                metadata={
                    "previous_agent_id": previous,
                    "agent_id": auto_assigned.agent_id,
                    "runtime_id": auto_assigned.runtime_id,
                },
            )
            await self.store.update(task)
            auto_assigned.record_use()
            await self.agent_store.update(auto_assigned)
            return auto_assigned
        return None

    def _build_spec(self, task: Task, agent: AgentDefinition | None) -> TaskSpec:
        task_type = task.task_type or (agent.task_types[0] if agent and agent.task_types else "general")
        runtime_preference = task.runtime_id or (agent.runtime_id if agent else None)
        model_preference = task.model_preference or (agent.model if agent else None)
        allow_paid_escalation = bool(agent and agent.cost_policy != "local_only")

        return TaskSpec(
            task_id=task.task_id,
            instruction=self._compose_instruction(task, agent),
            task_type=task_type,
            workspace_path=self.workspace_root,
            model_preference=model_preference,
            provider_preference=runtime_preference,
            allow_paid_escalation=allow_paid_escalation,
            context={
                "task": {
                    "title": task.title,
                    "description": task.description,
                    "prompt": task.prompt,
                    "tags": task.tags,
                    "requires_approval": task.requires_approval,
                },
                "agent": {
                    "agent_id": agent.agent_id if agent else None,
                    "name": agent.name if agent else "Default Agent",
                    "system_prompt": agent.system_prompt if agent else "",
                    "cost_policy": agent.cost_policy if agent else "local_only",
                    "task_types": agent.task_types if agent else [],
                },
                "comments": [comment.model_dump() for comment in task.comments[-20:]],
                "history": [entry.model_dump() for entry in task.execution_log[-20:]],
            },
        )

    async def _apply_result(self, task: Task, agent: AgentDefinition | None, result: TaskResult) -> None:
        metadata = result.metadata or {}
        actor = f"agent:{agent.agent_id}" if agent else f"runtime:{result.runtime_id}"
        task.add_log(
            "Execution completed" if result.success else "Execution failed",
            event_type="execution_finished" if result.success else "execution_failed",
            actor=actor,
            task_status=task.status,
            runtime_id=result.runtime_id,
            model_used=result.model_used,
            tokens=result.tokens_used,
            raw_trace=metadata.get("raw_trace"),
            metadata={
                "provider_used": result.provider_used,
                "artifacts": result.artifacts,
                "tool_calls": result.tool_calls,
                "execution_time_ms": result.execution_time_ms,
            },
        )

        if not result.success:
            task.error_message = result.output
            self.workflow.transition(
                task,
                TaskStatus.FAILED,
                actor=actor,
                message=f"Execution failed on runtime {result.runtime_id}",
            )
            return

        agent_comment = metadata.get("agent_comment")
        if agent_comment:
            self.workflow.add_comment(task, author=actor, body=agent_comment)

        next_status = metadata.get("task_status")
        if task.requires_approval and next_status in (None, TaskStatus.DONE.value):
            next_status = TaskStatus.IN_REVIEW.value
            metadata.setdefault("review_reason", "Awaiting approval before completion")

        if next_status == TaskStatus.BLOCKED.value:
            self.workflow.transition(
                task,
                TaskStatus.BLOCKED,
                actor=actor,
                blocked_reason=metadata.get("blocked_reason") or "Agent reported a blocker",
                message=f"Execution blocked on runtime {result.runtime_id}",
            )
        elif next_status == TaskStatus.IN_REVIEW.value:
            self.workflow.transition(
                task,
                TaskStatus.IN_REVIEW,
                actor=actor,
                review_reason=metadata.get("review_reason") or "Awaiting review",
                message=f"Execution finished and moved to review on runtime {result.runtime_id}",
            )
        else:
            self.workflow.transition(
                task,
                TaskStatus.DONE,
                actor=actor,
                message=f"Execution finished successfully on runtime {result.runtime_id}",
            )

    def _compose_instruction(self, task: Task, agent: AgentDefinition | None) -> str:
        parts: list[str] = []
        if agent and agent.system_prompt:
            parts.append(f"System prompt:\n{agent.system_prompt.strip()}")
        parts.append(f"Task title: {task.title}")
        if task.description:
            parts.append(f"Task description:\n{task.description.strip()}")
        if task.prompt:
            parts.append(f"Task prompt:\n{task.prompt.strip()}")
        if task.comments:
            comment_lines = [
                f"- {comment.author}: {comment.body}"
                for comment in task.comments[-10:]
            ]
            parts.append("Task discussion:\n" + "\n".join(comment_lines))
        if task.review_reason:
            parts.append(f"Review context:\n{task.review_reason}")
        if task.blocked_reason:
            parts.append(f"Blocked context:\n{task.blocked_reason}")
        return "\n\n".join(parts)

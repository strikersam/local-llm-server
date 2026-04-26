"""FastAPI routes for the task workflow system."""

from __future__ import annotations

import logging
from typing import Any
from collections.abc import Mapping

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from tasks.models import (
    ApprovalRequest,
    CommentAddRequest,
    Task,
    TaskCreateRequest,
    TaskPriority,
    TaskStatus,
    TaskUpdateRequest,
)
from tasks.service import TaskWorkflowService
from tasks.store import TaskStore, get_task_store

log = logging.getLogger("qwen-proxy")

task_router = APIRouter(prefix="/api/tasks", tags=["tasks"])


async def _current_user(request: Request) -> Any:
    user = getattr(request.state, "user", None)
    if user is not None:
        return user

    try:
        from server import get_current_user
    except ModuleNotFoundError:
        from backend.server import get_current_user

    return await get_current_user(request)


def _get_store(_: Request) -> TaskStore:
    return get_task_store()


def _get_workflow(request: Request) -> TaskWorkflowService:
    return TaskWorkflowService(store=_get_store(request))


def _is_admin(user: Any) -> bool:
    if isinstance(user, Mapping):
        return user.get("role", "user") == "admin"
    return getattr(user, "role", getattr(user, "get", lambda k, d=None: d)("role", "user")) == "admin"


def _user_id(user: Any) -> str:
    if isinstance(user, Mapping):
        return str(user.get("_id") or user.get("id") or user.get("email") or "unknown")
    return str(getattr(user, "_id", None) or getattr(user, "id", None) or getattr(user, "email", "unknown"))


async def _load_task(request: Request, task_id: str, user: Any) -> tuple[Task, TaskStore, str]:
    store = _get_store(request)
    owner_id = None if _is_admin(user) else _user_id(user)
    task = await store.get(task_id, owner_id=owner_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task, store, _user_id(user)


@task_router.post("/", status_code=201)
async def create_task(body: TaskCreateRequest, request: Request, user: Any = Depends(_current_user)) -> dict[str, Any]:
    workflow = _get_workflow(request)
    task = Task(
        owner_id=_user_id(user),
        title=body.title,
        description=body.description,
        prompt=body.prompt,
        agent_id=body.agent_id,
        runtime_id=body.runtime_id,
        model_preference=body.model_preference,
        priority=body.priority,
        task_type=body.task_type,
        tags=body.tags,
        due_date=body.due_date,
        requires_approval=body.requires_approval,
        status=body.status,
        review_reason="Created in review lane" if body.status is TaskStatus.IN_REVIEW else None,
    )
    try:
        await workflow.create_task(task, actor=_user_id(user))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"task": task.as_dict()}


@task_router.get("/")
async def list_tasks(
    request: Request,
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    agent_id: str | None = None,
    tag: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: Any = Depends(_current_user),
) -> dict[str, Any]:
    store = _get_store(request)
    owner_id = _user_id(user)

    if _is_admin(user):
        tasks = await store.list_all(status=status, limit=limit, offset=offset)
    else:
        tasks = await store.list_for_user(
            owner_id,
            status=status,
            priority=priority,
            agent_id=agent_id,
            tag=tag,
            limit=limit,
            offset=offset,
        )
    return {"tasks": [task.as_dict() for task in tasks]}


@task_router.get("/counts")
async def task_counts(request: Request, user: Any = Depends(_current_user)) -> dict[str, Any]:
    counts = await _get_store(request).count_for_user(_user_id(user))
    return {"counts": counts}


@task_router.get("/due-soon")
async def tasks_due_soon(request: Request, within_hours: int = 24, user: Any = Depends(_current_user)) -> dict[str, Any]:
    tasks = await _get_store(request).get_due_soon(within_hours)
    if not _is_admin(user):
        uid = _user_id(user)
        tasks = [task for task in tasks if task.owner_id == uid]
    return {"tasks": [task.as_dict() for task in tasks]}


@task_router.get("/{task_id}")
async def get_task(task_id: str, request: Request, user: Any = Depends(_current_user)) -> dict[str, Any]:
    task, _, _ = await _load_task(request, task_id, user)
    return {"task": task.as_dict()}


@task_router.patch("/{task_id}")
async def update_task(task_id: str, body: TaskUpdateRequest, request: Request, user: Any = Depends(_current_user)) -> dict[str, Any]:
    task, store, actor = await _load_task(request, task_id, user)
    workflow = _get_workflow(request)
    updates = body.model_dump(exclude_none=True)

    if "title" in updates:
        task.title = updates["title"]
    if "description" in updates:
        task.description = updates["description"]
    if "prompt" in updates:
        task.prompt = updates["prompt"]
    if "runtime_id" in updates:
        task.runtime_id = updates["runtime_id"]
    if "model_preference" in updates:
        task.model_preference = updates["model_preference"]
    if "priority" in updates:
        task.priority = updates["priority"]
    if "task_type" in updates:
        task.task_type = updates["task_type"]
    if "tags" in updates:
        task.tags = updates["tags"]
    if "due_date" in updates:
        task.due_date = updates["due_date"]
    if "requires_approval" in updates:
        task.requires_approval = updates["requires_approval"]
    if "agent_id" in updates:
        workflow.assign_agent(task, updates["agent_id"], actor=actor)

    if body.status is not None:
        try:
            workflow.transition(
                task,
                body.status,
                actor=actor,
                blocked_reason=task.blocked_reason or "Manually blocked" if body.status is TaskStatus.BLOCKED else None,
                review_reason=task.review_reason or "Awaiting review" if body.status is TaskStatus.IN_REVIEW else None,
                pending_agent_run=bool(task.agent_id) if body.status is TaskStatus.IN_PROGRESS else None,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    await store.update(task)
    return {"task": task.as_dict()}


@task_router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: str, request: Request, user: Any = Depends(_current_user)) -> None:
    owner_id = None if _is_admin(user) else _user_id(user)
    deleted = await _get_store(request).delete(task_id, owner_id=owner_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")


@task_router.post("/{task_id}/comments", status_code=201)
async def add_comment(task_id: str, body: CommentAddRequest, request: Request, user: Any = Depends(_current_user)) -> dict[str, Any]:
    task, store, actor = await _load_task(request, task_id, user)
    workflow = _get_workflow(request)
    try:
        comment = workflow.add_comment(task, author=actor, body=body.body, reply_to=body.reply_to)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await store.update(task)
    return {"comment": comment.model_dump(), "task": task.as_dict()}


@task_router.post("/{task_id}/approve")
async def approve_checkpoint(task_id: str, body: ApprovalRequest, request: Request, user: Any = Depends(_current_user)) -> dict[str, Any]:
    task, store, actor = await _load_task(request, task_id, user)
    workflow = _get_workflow(request)
    try:
        workflow.record_approval(
            task,
            checkpoint_id=body.checkpoint_id,
            approved=body.approve,
            actor=actor,
            reason=body.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await store.update(task)
    return {"task": task.as_dict()}


@task_router.post("/{task_id}/retry")
async def retry_task(task_id: str, request: Request, user: Any = Depends(_current_user)) -> dict[str, Any]:
    task, store, actor = await _load_task(request, task_id, user)
    workflow = _get_workflow(request)
    try:
        workflow.retry(task, actor=actor)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await store.update(task)
    return {"task": task.as_dict()}


@task_router.post("/{task_id}/escalate")
async def escalate_task(task_id: str, request: Request, user: Any = Depends(_current_user)) -> dict[str, Any]:
    task, store, actor = await _load_task(request, task_id, user)
    workflow = _get_workflow(request)
    workflow.escalate(task, actor=actor)
    await store.update(task)
    return {"task": task.as_dict()}

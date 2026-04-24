"""tasks/api.py — FastAPI routes for the task/issue system."""

from __future__ import annotations

import time
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel

from tasks.models import (
    Task,
    TaskStatus,
    TaskPriority,
    TaskComment,
    ApprovalCheckpoint,
    TaskCreateRequest,
    TaskUpdateRequest,
    CommentAddRequest,
    ApprovalRequest,
)
from tasks.store import TaskStore, get_task_store

log = logging.getLogger("qwen-proxy")

task_router = APIRouter(prefix="/api/tasks", tags=["tasks"])


# ── Dependency helpers ────────────────────────────────────────────────────────

def _get_user(request: Request) -> Any:
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def _get_store(request: Request) -> TaskStore:
    # Use the global task store (shared with dispatcher)
    return get_task_store()


def _is_admin(user: Any) -> bool:
    return getattr(user, "role", getattr(user, "get", lambda k, d=None: d)("role", "user")) == "admin"


def _user_id(user: Any) -> str:
    return str(getattr(user, "_id", None) or getattr(user, "id", None) or getattr(user, "email", "unknown"))


# ── Routes ────────────────────────────────────────────────────────────────────

@task_router.post("/", status_code=201)
async def create_task(
    body: TaskCreateRequest,
    request: Request,
) -> dict:
    user = _get_user(request)
    store = _get_store(request)

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
    )
    await store.create(task)
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
) -> dict:
    user = _get_user(request)
    store = _get_store(request)
    owner_id = _user_id(user)

    # Admins can see all tasks; regular users see only their own
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
    return {"tasks": [t.as_dict() for t in tasks]}


@task_router.get("/counts")
async def task_counts(request: Request) -> dict:
    """Return task counts per status for the current user."""
    user = _get_user(request)
    store = _get_store(request)
    counts = await store.count_for_user(_user_id(user))
    return {"counts": counts}


@task_router.get("/due-soon")
async def tasks_due_soon(
    request: Request,
    within_hours: int = 24,
) -> dict:
    """Tasks due within the next N hours (admin) or user's own tasks."""
    user = _get_user(request)
    store = _get_store(request)
    tasks = await store.get_due_soon(within_hours)
    if not _is_admin(user):
        uid = _user_id(user)
        tasks = [t for t in tasks if t.owner_id == uid]
    return {"tasks": [t.as_dict() for t in tasks]}


@task_router.get("/{task_id}")
async def get_task(task_id: str, request: Request) -> dict:
    user = _get_user(request)
    store = _get_store(request)
    owner_id = None if _is_admin(user) else _user_id(user)
    task = await store.get(task_id, owner_id=owner_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task": task.as_dict()}


@task_router.patch("/{task_id}")
async def update_task(
    task_id: str,
    body: TaskUpdateRequest,
    request: Request,
) -> dict:
    user = _get_user(request)
    store = _get_store(request)
    owner_id = None if _is_admin(user) else _user_id(user)
    task = await store.get(task_id, owner_id=owner_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    updates = body.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(task, field, value)

    # Track status timestamps
    if body.status == TaskStatus.IN_PROGRESS and task.started_at is None:
        task.started_at = time.time()
    if body.status == TaskStatus.DONE and task.completed_at is None:
        task.completed_at = time.time()

    await store.update(task)
    return {"task": task.as_dict()}


@task_router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: str, request: Request) -> None:
    user = _get_user(request)
    store = _get_store(request)
    owner_id = None if _is_admin(user) else _user_id(user)
    deleted = await store.delete(task_id, owner_id=owner_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")


# ── Comments ──────────────────────────────────────────────────────────────────

@task_router.post("/{task_id}/comments", status_code=201)
async def add_comment(
    task_id: str,
    body: CommentAddRequest,
    request: Request,
) -> dict:
    user = _get_user(request)
    store = _get_store(request)
    owner_id = None if _is_admin(user) else _user_id(user)
    task = await store.get(task_id, owner_id=owner_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    comment = TaskComment(
        author=_user_id(user),
        body=body.body,
        reply_to=body.reply_to,
    )
    task.comments.append(comment)
    await store.update(task)
    return {"comment": comment.model_dump()}


# ── Approval ──────────────────────────────────────────────────────────────────

@task_router.post("/{task_id}/approve")
async def approve_checkpoint(
    task_id: str,
    body: ApprovalRequest,
    request: Request,
) -> dict:
    user = _get_user(request)
    store = _get_store(request)
    owner_id = None if _is_admin(user) else _user_id(user)
    task = await store.get(task_id, owner_id=owner_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    checkpoint = next(
        (c for c in task.approval_checkpoints if c.checkpoint_id == body.checkpoint_id),
        None,
    )
    if checkpoint is None:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    checkpoint.approved = body.approve
    checkpoint.approved_by = _user_id(user)
    checkpoint.approved_at = time.time()
    checkpoint.reason = body.reason
    task.add_log(
        f"Checkpoint '{checkpoint.description}' {'approved' if body.approve else 'rejected'} by {_user_id(user)}",
        level="info" if body.approve else "warning",
    )
    await store.update(task)
    return {"task": task.as_dict()}


# ── Execution actions ─────────────────────────────────────────────────────────

@task_router.post("/{task_id}/retry")
async def retry_task(task_id: str, request: Request) -> dict:
    """Reset a failed task to TODO for re-execution."""
    user = _get_user(request)
    store = _get_store(request)
    owner_id = None if _is_admin(user) else _user_id(user)
    task = await store.get(task_id, owner_id=owner_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = TaskStatus.TODO
    task.started_at = None
    task.add_log("Task reset for retry by user", level="info")
    await store.update(task)
    return {"task": task.as_dict()}


@task_router.post("/{task_id}/escalate")
async def escalate_task(task_id: str, request: Request) -> dict:
    """Mark a task as requiring escalation."""
    user = _get_user(request)
    store = _get_store(request)
    owner_id = None if _is_admin(user) else _user_id(user)
    task = await store.get(task_id, owner_id=owner_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    task.escalation_count += 1
    task.status = TaskStatus.BLOCKED
    task.add_log("Task manually escalated", level="warning")
    await store.update(task)
    return {"task": task.as_dict()}

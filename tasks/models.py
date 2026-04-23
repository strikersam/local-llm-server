"""tasks/models.py — Pydantic models for the task/issue system."""

from __future__ import annotations

import time
import secrets
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class TaskStatus(str, Enum):
    TODO        = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW   = "in_review"
    BLOCKED     = "blocked"
    DONE        = "done"


class TaskPriority(str, Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"
    URGENT = "urgent"


class ExecutionLogEntry(BaseModel):
    """Single entry in a task's execution log."""
    timestamp: float = Field(default_factory=time.time)
    level: str = "info"           # info | warning | error
    message: str
    runtime_id: str | None = None
    model_used: str | None = None
    tokens: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskComment(BaseModel):
    """Comment or reply on a task."""
    comment_id: str = Field(default_factory=lambda: f"cmt_{secrets.token_hex(6)}")
    author: str                   # user email or "agent:<agent_id>"
    body: str = Field(..., min_length=1, max_length=10_000)
    created_at: float = Field(default_factory=time.time)
    reply_to: str | None = None   # parent comment_id for threads


class ApprovalCheckpoint(BaseModel):
    """Human approval gate in a task's execution."""
    checkpoint_id: str = Field(default_factory=lambda: f"chk_{secrets.token_hex(6)}")
    description: str
    required: bool = True
    approved: bool | None = None    # None = pending
    approved_by: str | None = None
    approved_at: float | None = None
    reason: str | None = None       # approval or rejection reason


class Task(BaseModel):
    """Full task/issue document."""

    # Identity
    task_id: str = Field(default_factory=lambda: f"task_{secrets.token_hex(8)}")
    owner_id: str = Field(..., description="ID of the user who created this task")
    title: str = Field(..., min_length=1, max_length=512)
    description: str = Field(default="", max_length=32_000)

    # Agent assignment
    agent_id: str | None = None     # assigned agent profile id
    runtime_id: str | None = None   # preferred runtime
    model_preference: str | None = None

    # Classification
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    task_type: str = Field(default="general", max_length=64)
    tags: list[str] = Field(default_factory=list)

    # Scheduling
    due_date: float | None = None   # epoch timestamp

    # Prompt / instructions
    prompt: str = Field(default="", max_length=32_000,
                        description="Specific instruction sent to the agent")

    # Approval
    requires_approval: bool = False
    approval_checkpoints: list[ApprovalCheckpoint] = Field(default_factory=list)

    # Execution tracking
    execution_log: list[ExecutionLogEntry] = Field(default_factory=list)
    last_runtime_id: str | None = None
    last_model_used: str | None = None
    tokens_used: int | None = None
    cost_usd: float | None = None

    # Comments
    comments: list[TaskComment] = Field(default_factory=list)

    # Timestamps
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None

    # Escalation
    escalation_count: int = 0
    escalation_reason: str | None = None

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        if len(v) > 20:
            raise ValueError("Maximum 20 tags per task")
        return [t.strip()[:64] for t in v if t.strip()]

    def touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = time.time()

    def add_log(self, message: str, level: str = "info", **kwargs: Any) -> None:
        self.execution_log.append(ExecutionLogEntry(
            message=message,
            level=level,
            **kwargs,
        ))
        self.touch()

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump()


# ── Request/response schemas ──────────────────────────────────────────────────

class TaskCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    description: str = Field(default="", max_length=32_000)
    prompt: str = Field(default="", max_length=32_000)
    agent_id: str | None = Field(default=None, max_length=64)
    runtime_id: str | None = Field(default=None, max_length=64)
    model_preference: str | None = Field(default=None, max_length=200)
    priority: TaskPriority = TaskPriority.MEDIUM
    task_type: str = Field(default="general", max_length=64)
    tags: list[str] = Field(default_factory=list)
    due_date: float | None = None
    requires_approval: bool = False


class TaskUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=512)
    description: str | None = Field(default=None, max_length=32_000)
    prompt: str | None = Field(default=None, max_length=32_000)
    agent_id: str | None = Field(default=None, max_length=64)
    runtime_id: str | None = Field(default=None, max_length=64)
    model_preference: str | None = Field(default=None, max_length=200)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    task_type: str | None = Field(default=None, max_length=64)
    tags: list[str] | None = None
    due_date: float | None = None
    requires_approval: bool | None = None


class CommentAddRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=10_000)
    reply_to: str | None = Field(default=None, max_length=64)


class ApprovalRequest(BaseModel):
    checkpoint_id: str
    approve: bool
    reason: str | None = Field(default=None, max_length=2000)

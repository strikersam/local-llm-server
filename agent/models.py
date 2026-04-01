from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentStep(BaseModel):
    id: int = Field(..., ge=1)
    description: str = Field(..., min_length=1)
    files: list[str] = Field(default_factory=list)
    type: Literal["edit", "create", "analyze"]


class AgentPlan(BaseModel):
    goal: str = Field(..., min_length=1)
    steps: list[AgentStep] = Field(default_factory=list, max_length=5)


class ToolCall(BaseModel):
    tool: Literal["read_file", "write_file", "apply_diff", "list_files", "search_code", "finish"]
    args: dict[str, Any] = Field(default_factory=dict)


class VerificationResult(BaseModel):
    status: Literal["pass", "fail"]
    issues: list[str] = Field(default_factory=list)


class AgentRunRequest(BaseModel):
    instruction: str = Field(..., min_length=1, max_length=8000)
    model: str | None = None
    provider_id: str | None = Field(default=None, max_length=64)
    workspace_id: str | None = Field(default=None, max_length=64)
    auto_commit: bool = False
    max_steps: int = Field(default=5, ge=1, le=5)


class AgentSessionCreateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    provider_id: str | None = Field(default=None, max_length=64)
    workspace_id: str | None = Field(default=None, max_length=64)


class AgentSessionMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class AgentSession(BaseModel):
    session_id: str
    title: str
    provider_id: str | None = None
    workspace_id: str | None = None
    created_at: str
    updated_at: str
    history: list[AgentSessionMessage] = Field(default_factory=list)
    last_plan: AgentPlan | None = None
    last_result: dict[str, Any] | None = None

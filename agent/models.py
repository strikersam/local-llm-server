from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Event log  (append-only session journal)
# ---------------------------------------------------------------------------

EventType = Literal[
    # Existing agent session events
    "user_message",
    "assistant_message",
    "tool_call",
    "tool_result",
    "step_start",
    "step_complete",
    "compaction",
    "error",
    # CRISPY workflow engine events
    "workflow_created",
    "workflow_done",
    "workflow_cancelled",
    "workflow_resumed",
    "phase_started",
    "phase_complete",
    "phase_failed",
    "gate_created",
    "gate_approved",
    "gate_rejected",
    "slices_registered",
    "slice_started",
    "slice_complete",
    "slice_failed",
]


class AgentEvent(BaseModel):
    """A single entry in the session's append-only event log.

    Inspired by Anthropic's Managed Agents architecture: the session is a
    durable event log that lives *outside* Claude's context window.  The
    harness queries it with ``getEvents(from_position)`` to reconstruct
    whatever slice of history the model needs for the current turn.
    """

    event_type: EventType
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = ""       # filled by AgentSessionStore
    position: int = 0         # filled by AgentSessionStore (monotonic)


class AgentStep(BaseModel):
    id: int = Field(..., ge=1)
    description: str = Field(..., min_length=1)
    files: list[str] = Field(default_factory=list)
    type: Literal["edit", "create", "analyze", "github"]


class AgentPlan(BaseModel):
    goal: str = Field(..., min_length=1)
    steps: list[AgentStep] = Field(default_factory=list)  # truncated by max_steps in loop.py


class ToolCall(BaseModel):
    tool: Literal[
        "read_file",
        "head_file",      # JIT retrieval: first N lines only
        "file_index",     # JIT retrieval: lightweight file list with sizes
        "write_file",
        "apply_diff",
        "list_files",
        "search_code",
        "recall_memory",
        "save_memory",
        "spawn_subagent",
        "github_read_repo_file",
        "github_list_repos",
        "github_list_branches",
        "github_create_branch",
        "github_commit_changes",
        "github_open_pull_request",
        "finish",
    ]
    args: dict[str, Any] = Field(default_factory=dict)


class VerificationResult(BaseModel):
    status: Literal["pass", "fail"]
    issues: list[str] = Field(default_factory=list)

    @field_validator("issues", mode="before")
    @classmethod
    def coerce_issues_to_str(cls, v: Any) -> list[str]:
        if not isinstance(v, list):
            return []
        result = []
        for item in v:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                text = item.get("issue") or item.get("description") or item.get("message") or str(item)
                result.append(str(text))
            else:
                result.append(str(item))
        return result


class AgentRunRequest(BaseModel):
    instruction: str = Field(..., min_length=1, max_length=8000)
    model: str | None = None
    provider_id: str | None = Field(default=None, max_length=64)
    workspace_id: str | None = Field(default=None, max_length=64)
    auto_commit: bool = False
    max_steps: int = Field(default=10, ge=1, le=20)


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
    # Total events appended to the durable event log for this session.
    # Used by the harness to know the current log position without loading all events.
    event_count: int = 0

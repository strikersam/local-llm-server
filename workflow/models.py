"""workflow/models.py — CRISPY Workflow Engine data models.

All public types are Pydantic BaseModels.  The approval gate, slices,
artifacts, and check runs are first-class citizens — not dicts.

Lifecycle statuses
------------------
WorkflowStatus:
  pending → context → research → investigate → structure → plan
  → awaiting_approval  ← HARD GATE (no code path can skip this)
  → executing → reviewing → verifying → done
  Failed / cancelled can occur from any state.

PhaseStatus / SliceStatus:
  pending → running → done | failed | skipped
"""
from __future__ import annotations

import time
from typing import Any, Literal

from pydantic import BaseModel, Field

# ── Literals ─────────────────────────────────────────────────────────────────

WorkflowStatus = Literal[
    "pending",
    "context",
    "research",
    "investigate",
    "structure",
    "plan",
    "awaiting_approval",  # HARD GATE
    "executing",
    "reviewing",
    "verifying",
    "done",
    "failed",
    "cancelled",
]

PhaseType = Literal[
    "context",
    "research",
    "investigate",
    "structure",
    "plan",
    "execute",
    "review",
    "verify",
    "report",
]

PhaseStatus = Literal["pending", "running", "done", "failed", "skipped"]

SliceStatus = Literal["pending", "running", "applied", "failed", "skipped"]

AgentRole = Literal["architect", "scout", "coder", "reviewer", "verifier"]

# ── Helpers ───────────────────────────────────────────────────────────────────


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ── Model routing config ──────────────────────────────────────────────────────


class ModelRoutingConfig(BaseModel):
    """Explicit per-role model assignments for a workflow run.

    All fields are optional — absent fields fall back to env vars or
    ModelRouter heuristics.  Stored in WorkflowRun so every run has a
    durable, auditable record of which model drove each role.
    """

    architect: str | None = None
    scout: str | None = None
    coder: str | None = None
    reviewer: str | None = None
    verifier: str | None = None


# ── Artifact ──────────────────────────────────────────────────────────────────


class Artifact(BaseModel):
    """A durable, phase-produced document (markdown or JSON)."""

    artifact_id: str = Field(..., description="Unique ID, e.g. 'art_<hex6>'")
    run_id: str
    phase: str  # PhaseType or slice_id
    name: str = Field(
        ...,
        description="Filename, e.g. 'context.md', 'slice-01.md', 'verify-01.json'",
    )
    path: str = Field(..., description="Absolute path on disk")
    content_hash: str = Field(default="", description="SHA-256 of file content")
    created_at: str = Field(default_factory=_now)
    size_bytes: int = Field(default=0)

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump()


# ── ApprovalGate ──────────────────────────────────────────────────────────────


class ApprovalGate(BaseModel):
    """Hard approval gate between plan and execution.

    The workflow engine sets status="pending" immediately after the plan
    phase and blocks all further phase execution until status is changed
    to "approved" (via POST /workflow/{id}/approve) or "rejected".

    This gate is MANDATORY — no code path in PhaseRunner or WorkflowEngine
    may advance past it unless gate.status == "approved".
    """

    gate_id: str
    run_id: str
    status: Literal["pending", "approved", "rejected"] = "pending"
    # Artifacts the reviewer must inspect before approving
    requires_review_of: list[str] = Field(
        default_factory=lambda: ["structure.md", "plan.md"],
        description="Artifact names human must review before approving",
    )
    approved_by: str | None = None
    approved_at: str | None = None
    rejection_reason: str | None = None
    created_at: str = Field(default_factory=_now)


# ── CheckRun ─────────────────────────────────────────────────────────────────


class CheckRun(BaseModel):
    """Structured, execution-based verification result.

    Verifier agents produce ONLY structured CheckRuns — no free-text
    "looks good" verdicts.  passed == (exit_code == 0).
    """

    check_id: str
    slice_id: str
    run_id: str
    commands: list[str] = Field(
        ...,
        description="Commands executed (e.g. ['pytest -x', 'ruff check .'])",
    )
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    passed: bool = Field(default=False, description="True iff exit_code == 0")
    duration_ms: int = 0
    ran_at: str = Field(default_factory=_now)

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump()


# ── Slice ─────────────────────────────────────────────────────────────────────


class Slice(BaseModel):
    """An independently deliverable unit of work within the execute phase.

    Each slice must:
    - Target specific files
    - Be independently reviewable and verifiable
    - Include tests as a deliverable (enforced by Architect when creating slices)
    """

    slice_id: str = Field(..., description="Unique ID, e.g. 'sl_<hex6>'")
    run_id: str
    index: int = Field(..., ge=1, description="1-based slice number")
    title: str
    description: str
    files: list[str] = Field(
        default_factory=list,
        description="Target files this slice must touch",
    )
    status: SliceStatus = "pending"
    check_run: CheckRun | None = None
    artifact_paths: list[str] = Field(
        default_factory=list,
        description="Absolute paths to slice + review + verify artifacts",
    )
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump()


# ── Phase ─────────────────────────────────────────────────────────────────────


class Phase(BaseModel):
    """A single phase in the CRISPY lifecycle."""

    phase_id: str
    run_id: str
    name: PhaseType
    status: PhaseStatus = "pending"
    agent_role: AgentRole
    artifact_paths: list[str] = Field(
        default_factory=list,
        description="Absolute paths to artifacts produced by this phase",
    )
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump()


# ── WorkflowRun ───────────────────────────────────────────────────────────────


class WorkflowRun(BaseModel):
    """Top-level CRISPY workflow run.

    A WorkflowRun is the single source of truth for a build request.
    It is persisted to SQLite and resumable after server restart.
    """

    run_id: str = Field(..., description="Unique ID, e.g. 'wf_<hex8>'")
    title: str
    request: str = Field(..., description="Original user request (verbatim)")
    status: WorkflowStatus = "pending"
    phases: list[Phase] = Field(default_factory=list)
    slices: list[Slice] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)
    approval_gate: ApprovalGate | None = None
    model_routing: ModelRoutingConfig = Field(default_factory=ModelRoutingConfig)
    workspace_root: str | None = None
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)
    # event_count mirrors agent/state.py — tracks position in the event log
    event_count: int = 0

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump()

    def artifact_by_name(self, name: str) -> Artifact | None:
        """Return the first artifact matching *name*, or None."""
        for a in self.artifacts:
            if a.name == name:
                return a
        return None

    def phase_by_type(self, phase_type: PhaseType) -> Phase | None:
        """Return the first Phase of *phase_type*, or None."""
        for p in self.phases:
            if p.name == phase_type:
                return p
        return None

    def slice_by_id(self, slice_id: str) -> Slice | None:
        """Return the Slice with *slice_id*, or None."""
        for s in self.slices:
            if s.slice_id == slice_id:
                return s
        return None


# ── API request/response models ───────────────────────────────────────────────


class WorkflowBuildRequest(BaseModel):
    """Request body for POST /workflow/build."""

    request: str = Field(
        ...,
        min_length=10,
        max_length=16000,
        description="The build request / task description",
    )
    title: str | None = Field(default=None, max_length=200)
    workspace_root: str | None = Field(
        default=None,
        description="Absolute path to the workspace. Defaults to server root.",
    )
    model_routing: ModelRoutingConfig = Field(default_factory=ModelRoutingConfig)


class WorkflowApproveRequest(BaseModel):
    """Request body for POST /workflow/{id}/approve."""

    approved_by: str = Field(
        default="human",
        max_length=200,
        description="Username or identifier of the approver",
    )


class WorkflowRejectRequest(BaseModel):
    """Request body for POST /workflow/{id}/reject."""

    reason: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Reason for rejecting the plan",
    )
    rejected_by: str = Field(default="human", max_length=200)


class SliceRunRequest(BaseModel):
    """Request body for POST /workflow/{id}/slices/{slice_id}/run."""

    force: bool = Field(
        default=False,
        description="Re-run even if slice already has status=applied",
    )

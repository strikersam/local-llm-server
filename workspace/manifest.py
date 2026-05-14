"""workspace/manifest.py — Workspace manifest schema.

Each isolated workspace has a manifest.json describing its identity,
paths, lifecycle, and metadata.  The manifest is the single source of
truth for workspace state and is read/written by WorkspaceManager.
"""

from __future__ import annotations

import time
from typing import Any, Literal

from pydantic import BaseModel, Field

# Schema version — bump when the manifest format changes.
MANIFEST_SCHEMA_VERSION = 1

WorkspaceStatusLiteral = Literal[
    "creating",
    "ready",
    "active",
    "paused",
    "completed",
    "failed",
    "cancelling",
    "cancelled",
    "archived",
    "cleaned",
]

RESUMABLE_STATES: frozenset[WorkspaceStatusLiteral] = frozenset(
    {"ready", "active", "paused"}
)

ACTIVE_STATES: frozenset[WorkspaceStatusLiteral] = frozenset(
    {"creating", "ready", "active", "paused"}
)

CLEANABLE_STATES: frozenset[WorkspaceStatusLiteral] = frozenset(
    {"completed", "failed", "cancelled", "archived"}
)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class WorkspaceManifest(BaseModel):
    """Structured manifest for an isolated workspace."""

    session_id: str = Field(..., description="Session this workspace belongs to")
    job_id: str | None = Field(default=None, description="Job this workspace belongs to (if any)")
    created_at: str = Field(default_factory=_now)
    last_heartbeat: str = Field(default_factory=_now)
    runtime_type: str = Field(default="local", description="local, container, etc.")
    status: WorkspaceStatusLiteral = Field(default="creating")
    root_path: str = Field(..., description="Resolved workspace root directory")
    source_path: str | None = Field(default=None, description="Source/work tree subdirectory")
    checkpoints_path: str | None = Field(default=None, description="Checkpoints/state subdirectory")
    logs_path: str | None = Field(default=None, description="Logs subdirectory")
    artifacts_path: str | None = Field(default=None, description="Artifacts output subdirectory")
    temp_path: str | None = Field(default=None, description="Temp files subdirectory")
    repo_url: str | None = Field(default=None, description="Source repo if applicable")
    cleanup_eligible: bool = Field(default=False, description="True when status allows cleanup")
    schema_version: int = Field(default=MANIFEST_SCHEMA_VERSION, description="Manifest schema version")

    def update_status(self, status: WorkspaceStatusLiteral) -> None:
        """Transition to a new status and update cleanup eligibility."""
        self.status = status
        self.last_heartbeat = _now()
        self.cleanup_eligible = status in CLEANABLE_STATES

    def heartbeat(self) -> None:
        """Touch the last_heartbeat timestamp."""
        self.last_heartbeat = _now()

    @property
    def is_resumable(self) -> bool:
        return self.status in RESUMABLE_STATES

    @property
    def is_active(self) -> bool:
        return self.status in ACTIVE_STATES

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump()

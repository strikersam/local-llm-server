"""agent/job_manager.py — Async agent job lifecycle manager.

Manages agent jobs with queued/running/succeeded/failed/cancelled states,
heartbeat timestamps, and progress events.  Integrates with the
WorkspaceManager for isolated per-session/job workspace provisioning.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import secrets
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable

log = logging.getLogger("qwen-agent")

_WORKSPACE_COMPONENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@dataclass
class AgentJob:
    job_id: str
    session_id: str
    instruction: str
    owner_id: str | None = None
    status: str = "queued"
    phase: str = "queued"
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    heartbeat_at: str = field(default_factory=_now)
    runtime_id: str = "internal_agent"
    workspace_path: str | None = None
    requested_model: str | None = None
    provider_id: str | None = None
    progress_events: list[dict[str, Any]] = field(default_factory=list)
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "session_id": self.session_id,
            "instruction": self.instruction,
            "owner_id": self.owner_id,
            "status": self.status,
            "phase": self.phase,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "heartbeat_at": self.heartbeat_at,
            "runtime_id": self.runtime_id,
            "workspace_path": self.workspace_path,
            "requested_model": self.requested_model,
            "provider_id": self.provider_id,
            "progress_events": self.progress_events,
            "result": self.result,
            "error": self.error,
        }


class AgentJobManager:
    def __init__(self, workspace_manager: Any | None = None) -> None:
        self._jobs: dict[str, AgentJob] = {}
        self._tasks: dict[str, asyncio.Task[Any]] = {}
        self._workspace_manager = workspace_manager

    def create_job(
        self,
        *,
        session_id: str,
        instruction: str,
        owner_id: str | None = None,
        runtime_id: str = "internal_agent",
        workspace_path: str | None = None,
        requested_model: str | None = None,
        provider_id: str | None = None,
    ) -> AgentJob:
        job = AgentJob(
            job_id=f"aj_{secrets.token_hex(8)}",
            session_id=session_id,
            instruction=instruction,
            owner_id=owner_id,
            runtime_id=runtime_id,
            workspace_path=workspace_path,
            requested_model=requested_model,
            provider_id=provider_id,
        )
        self._jobs[job.job_id] = job

        # If a workspace_manager is configured and no explicit workspace_path,
        # provision an isolated workspace through it.
        if workspace_path is None and self._workspace_manager is not None:
            try:
                from workspace.manager import validate_session_id, validate_job_id
                validate_session_id(session_id)
                validate_job_id(job.job_id)
                manifest = self._workspace_manager.create_workspace(
                    session_id=session_id,
                    job_id=job.job_id,
                    runtime_type=runtime_id,
                )
                job.workspace_path = manifest.root_path
            except Exception as exc:
                log.warning(
                    "Failed to provision isolated workspace for job %s: %s — "
                    "falling back to raw workspace_path",
                    job.job_id, exc,
                )

        self._append_event(job.job_id, phase="queued", message="Job queued")
        return job

    def get_job(self, job_id: str) -> AgentJob | None:
        return self._jobs.get(job_id)

    def list_jobs(self, session_id: str | None = None) -> list[AgentJob]:
        jobs = list(self._jobs.values())
        if session_id:
            jobs = [job for job in jobs if job.session_id == session_id]
        return jobs

    def start_job(
        self,
        job_id: str,
        runner: Callable[[Callable[[str, str], None]], Awaitable[dict[str, Any]]],
    ) -> AgentJob:
        job = self._jobs[job_id]
        if job_id in self._tasks and not self._tasks[job_id].done():
            return job

        # Activate workspace if manager is configured
        if self._workspace_manager is not None and job.workspace_path:
            try:
                self._workspace_manager.activate(job.session_id, job.job_id)
            except Exception:
                pass

        self._tasks[job_id] = asyncio.create_task(self._run_job(job, runner))
        return job

    def cancel_job(self, job_id: str) -> AgentJob | None:
        job = self._jobs.get(job_id)
        if job is None:
            return None
        task = self._tasks.get(job_id)
        if task and not task.done():
            task.cancel()
        job.status = "cancelled"
        job.phase = "cancelled"
        job.updated_at = _now()
        job.heartbeat_at = job.updated_at
        self._append_event(job_id, phase="cancelled", message="Job cancelled")

        # Mark workspace as cancelled if manager is configured
        if self._workspace_manager is not None and job.workspace_path:
            try:
                self._workspace_manager.cancel(job.session_id, job.job_id)
            except Exception:
                pass

        return job

    async def _run_job(
        self,
        job: AgentJob,
        runner: Callable[[Callable[[str, str], None]], Awaitable[dict[str, Any]]],
    ) -> None:
        def heartbeat(phase: str, message: str) -> None:
            self._append_event(job.job_id, phase=phase, message=message)

        job.status = "running"
        job.phase = "starting"
        job.updated_at = _now()
        job.heartbeat_at = job.updated_at
        heartbeat("starting", "Job started")
        try:
            result = await runner(heartbeat)
            job.result = result
            job.status = "succeeded"
            job.phase = "completed"
            heartbeat("completed", "Job completed")
        except asyncio.CancelledError:
            job.status = "cancelled"
            job.phase = "cancelled"
            heartbeat("cancelled", "Job cancelled")
            raise
        except Exception as exc:
            log.exception("Agent job %s failed", job.job_id)
            job.status = "failed"
            job.phase = "failed"
            job.error = {
                "type": exc.__class__.__name__,
                "message": str(exc),
            }
            heartbeat("failed", str(exc))
        finally:
            job.updated_at = _now()
            job.heartbeat_at = job.updated_at

            # Complete or fail the workspace
            if self._workspace_manager is not None and job.workspace_path:
                try:
                    if job.status == "succeeded":
                        self._workspace_manager.complete(job.session_id, job.job_id)
                    elif job.status == "failed":
                        self._workspace_manager.fail(job.session_id, job.job_id)
                except Exception:
                    pass

    def _append_event(self, job_id: str, *, phase: str, message: str) -> None:
        job = self._jobs[job_id]
        timestamp = _now()
        job.phase = phase
        job.updated_at = timestamp
        job.heartbeat_at = timestamp
        job.progress_events.append({"timestamp": timestamp, "phase": phase, "message": message})


# ── Legacy workspace helpers (kept for backward compatibility) ────────────────

def make_isolated_workspace(root: Path, session_id: str, job_id: str) -> Path:
    """Create an isolated workspace directory under *root*.

    This is the legacy path used before WorkspaceManager.  It still
    validates IDs and hashes directory names, but the preferred path is
    to use WorkspaceManager.create_workspace() which also produces
    manifests, subdirectories, and lifecycle management.
    """
    session_component = _workspace_component(session_id, field_name="session_id")
    job_component = _workspace_component(job_id, field_name="job_id")
    workspace = (root / session_component / job_component).resolve()
    root_resolved = root.resolve()
    if root_resolved not in workspace.parents:
        raise ValueError("workspace path escaped root")
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def _workspace_component(value: str, *, field_name: str) -> str:
    if not _WORKSPACE_COMPONENT_RE.fullmatch(value):
        raise ValueError(f"Invalid {field_name}")
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return digest[:24]

from __future__ import annotations

import asyncio
import logging
import secrets
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable

log = logging.getLogger("qwen-agent")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@dataclass
class AgentJob:
    job_id: str
    session_id: str
    instruction: str
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
    def __init__(self) -> None:
        self._jobs: dict[str, AgentJob] = {}
        self._tasks: dict[str, asyncio.Task[Any]] = {}

    def create_job(
        self,
        *,
        session_id: str,
        instruction: str,
        runtime_id: str = "internal_agent",
        workspace_path: str | None = None,
        requested_model: str | None = None,
        provider_id: str | None = None,
    ) -> AgentJob:
        job = AgentJob(
            job_id=f"aj_{secrets.token_hex(8)}",
            session_id=session_id,
            instruction=instruction,
            runtime_id=runtime_id,
            workspace_path=workspace_path,
            requested_model=requested_model,
            provider_id=provider_id,
        )
        self._jobs[job.job_id] = job
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

    def _append_event(self, job_id: str, *, phase: str, message: str) -> None:
        job = self._jobs[job_id]
        timestamp = _now()
        job.phase = phase
        job.updated_at = timestamp
        job.heartbeat_at = timestamp
        job.progress_events.append({"timestamp": timestamp, "phase": phase, "message": message})


def make_isolated_workspace(root: Path, session_id: str, job_id: str) -> Path:
    workspace = root / session_id / job_id
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace

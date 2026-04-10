"""agent/scheduler.py — Scheduled Agent Jobs

Cron-based job scheduler.  Each job holds an agent instruction that is
dispatched (via the *on_fire* callback) when its cron schedule fires.
External webhooks can also fire jobs immediately via :meth:`trigger`.

Requires ``apscheduler`` (installed as a dependency).  When apscheduler is
not available the scheduler still works — jobs are registered and can be
triggered manually; the background cron execution is simply disabled.
"""
from __future__ import annotations

import logging
import secrets
import time
from dataclasses import dataclass
from typing import Any, Callable

log = logging.getLogger("qwen-scheduler")

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger

    _HAS_APSCHEDULER = True
except ImportError:  # pragma: no cover
    _HAS_APSCHEDULER = False


@dataclass
class ScheduledJob:
    job_id: str
    name: str
    cron: str       # standard 5-field cron expression, e.g. "0 9 * * 1"
    instruction: str
    created_at: str
    last_run: str | None = None
    run_count: int = 0
    enabled: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "name": self.name,
            "cron": self.cron,
            "instruction": self.instruction,
            "created_at": self.created_at,
            "last_run": self.last_run,
            "run_count": self.run_count,
            "enabled": self.enabled,
        }


class AgentScheduler:
    """Register, list, trigger, and delete cron-scheduled agent jobs.

    Usage::

        sched = AgentScheduler(on_fire=lambda job: print(job.instruction))
        job = sched.create(name="daily-lint", cron="0 9 * * *",
                           instruction="Run wiki lint and report")
        sched.trigger(job.job_id)   # fire immediately (webhook-style)
    """

    def __init__(
        self,
        on_fire: Callable[[ScheduledJob], None] | None = None,
    ) -> None:
        self._jobs: dict[str, ScheduledJob] = {}
        self._on_fire = on_fire
        self._aps: Any = None
        if _HAS_APSCHEDULER:
            self._aps = BackgroundScheduler()
            self._aps.start()
            log.info("APScheduler background scheduler started")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create(
        self,
        *,
        name: str,
        cron: str,
        instruction: str,
    ) -> ScheduledJob:
        """Register a new job.  Returns the created :class:`ScheduledJob`."""
        job_id = "job_" + secrets.token_hex(6)
        job = ScheduledJob(
            job_id=job_id,
            name=name,
            cron=cron,
            instruction=instruction,
            created_at=_now(),
        )
        self._jobs[job_id] = job
        self._register_aps(job)
        log.info("Scheduled job created: id=%s name=%r cron=%r", job_id, name, cron)
        return job

    def trigger(self, job_id: str) -> ScheduledJob:
        """Fire a job immediately (webhook / manual trigger)."""
        job = self._jobs.get(job_id)
        if not job:
            raise KeyError(f"Job {job_id!r} not found")
        self._fire(job_id)
        return self._jobs[job_id]

    def delete(self, job_id: str) -> bool:
        """Remove a job. Returns *True* if it existed."""
        if job_id not in self._jobs:
            return False
        del self._jobs[job_id]
        if self._aps:
            try:
                self._aps.remove_job(job_id)
            except Exception:
                pass
        log.info("Scheduled job deleted: id=%s", job_id)
        return True

    def list(self) -> list[ScheduledJob]:
        return list(self._jobs.values())

    def get(self, job_id: str) -> ScheduledJob | None:
        return self._jobs.get(job_id)

    def shutdown(self) -> None:
        if self._aps and self._aps.running:
            self._aps.shutdown(wait=False)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _register_aps(self, job: ScheduledJob) -> None:
        if not self._aps:
            return
        try:
            parts = job.cron.strip().split()
            if len(parts) != 5:
                log.warning("Invalid cron expression %r for job %s", job.cron, job.job_id)
                return
            trigger = CronTrigger(
                minute=parts[0],
                hour=parts[1],
                day=parts[2],
                month=parts[3],
                day_of_week=parts[4],
            )
            self._aps.add_job(
                self._fire,
                trigger=trigger,
                args=[job.job_id],
                id=job.job_id,
            )
        except Exception as exc:
            log.warning("Could not register APScheduler job %s: %s", job.job_id, exc)

    def _fire(self, job_id: str) -> None:
        job = self._jobs.get(job_id)
        if not job or not job.enabled:
            return
        job.last_run = _now()
        job.run_count += 1
        log.info("Firing job %s (%s)", job_id, job.name)
        if self._on_fire:
            try:
                self._on_fire(job)
            except Exception as exc:
                log.error("on_fire callback for job %s raised: %s", job_id, exc)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

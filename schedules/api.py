"""schedules/api.py — Control-plane facing schedule management.

Exposes the agent scheduler under /api/schedules/* so the Control Plane UI
can manage autopilot jobs without using the legacy /agent/scheduler/* paths.

Routes:
  GET    /api/schedules             list all schedules
  POST   /api/schedules             create a schedule
  GET    /api/schedules/{id}        get a single schedule
  PATCH  /api/schedules/{id}        toggle status (active / paused)
  POST   /api/schedules/{id}/run    trigger immediately
  DELETE /api/schedules/{id}        delete
  GET    /api/schedules/{id}/runs   run history (run_count + last_run)
"""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from agent.scheduler import get_scheduler

log = logging.getLogger("qwen-proxy")

schedules_router = APIRouter(prefix="/api/schedules", tags=["schedules"])


# ── Request models ────────────────────────────────────────────────────────────

class ScheduleCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    agent_id: str | None = Field(default=None, max_length=64)
    cron: str = Field(..., min_length=9, max_length=100)
    instruction: str = Field(default="", max_length=4000)
    approval_gate: bool = False
    runtime_id: str | None = Field(default=None, max_length=64)
    model: str | None = Field(default=None, max_length=200)
    tags: list[str] = Field(default_factory=list)


class ScheduleToggleRequest(BaseModel):
    status: Literal["active", "paused"]


# ── Routes ────────────────────────────────────────────────────────────────────

@schedules_router.get("/")
async def list_schedules(request: Request) -> dict:
    """List all scheduled jobs."""
    sched = get_scheduler()
    return {"schedules": [j.as_dict() for j in sched.list()]}


@schedules_router.post("/")
async def create_schedule(body: ScheduleCreateRequest, request: Request) -> dict:
    """Create a new scheduled job."""
    sched = get_scheduler()
    job = sched.create(
        name=body.name,
        cron=body.cron,
        instruction=body.instruction,
        agent_id=body.agent_id,
        runtime_id=body.runtime_id,
        model=body.model,
        requires_approval=body.approval_gate,
        tags=body.tags,
    )
    return job.as_dict()


@schedules_router.get("/{schedule_id}")
async def get_schedule(schedule_id: str, request: Request) -> dict:
    """Get a single schedule by ID."""
    sched = get_scheduler()
    job = sched.get(schedule_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Schedule '{schedule_id}' not found")
    return job.as_dict()


@schedules_router.patch("/{schedule_id}")
async def toggle_schedule(
    schedule_id: str, body: ScheduleToggleRequest, request: Request
) -> dict:
    """Pause or activate a schedule."""
    sched = get_scheduler()
    try:
        job = sched.toggle(schedule_id, enabled=(body.status == "active"))
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Schedule '{schedule_id}' not found")
    return job.as_dict()


@schedules_router.post("/{schedule_id}/run")
async def run_schedule_now(schedule_id: str, request: Request) -> dict:
    """Trigger a schedule to run immediately."""
    sched = get_scheduler()
    try:
        job = sched.trigger(schedule_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Schedule '{schedule_id}' not found")
    return {"status": "triggered", "schedule": job.as_dict()}


@schedules_router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: str, request: Request) -> dict:
    """Delete a schedule."""
    sched = get_scheduler()
    deleted = sched.delete(schedule_id)
    return {"deleted": deleted}


@schedules_router.get("/{schedule_id}/runs")
async def get_schedule_runs(schedule_id: str, request: Request) -> dict:
    """Return run history for a schedule (run_count + last_run from in-memory state)."""
    sched = get_scheduler()
    job = sched.get(schedule_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Schedule '{schedule_id}' not found")
    return {
        "schedule_id": schedule_id,
        "run_count": job.run_count,
        "last_run": job.last_run,
    }

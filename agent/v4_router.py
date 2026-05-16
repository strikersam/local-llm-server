"""agent/v4_router.py — LLM Relay v4 Dashboard API

REST surface for the continuous-improvement dashboard:

  GET  /v4/status                      — system health + improvement loop status
  GET  /v4/improvements                — list active/resolved issues
  POST /v4/improvements/scan           — trigger immediate scan (all checks)
  POST /v4/improvements/security-scan  — trigger security scan only
  POST /v4/improvements/{id}/resolve   — mark issue resolved
  POST /v4/report-bug                  — manual bug report → self-healing agent
  GET  /v4/quick-notes                 — list quick notes
  POST /v4/quick-notes                 — add quick note (URL or text)
  GET  /v4/scheduler/jobs              — list improvement jobs
  POST /v4/scheduler/trigger/{job_id}  — fire a job immediately
  POST /v4/ci-failure                  — webhook for CI failure events
  GET  /v4/log-monitor/stats           — log monitor stats
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel

log = logging.getLogger("qwen-proxy")

v4_router = APIRouter(prefix="/v4", tags=["v4-dashboard"])


# ── Auth helper ───────────────────────────────────────────────────────────────

def _require_admin(authorization: Annotated[str | None, Header()] = None) -> None:
    admin_token = os.environ.get("ADMIN_TOKEN", "") or os.environ.get("ADMIN_SECRET", "")
    if not admin_token:
        return  # open in dev mode — no token configured
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    token = authorization[7:]
    if not hmac.compare_digest(
        hashlib.sha256(token.encode()).digest(),
        hashlib.sha256(admin_token.encode()).digest(),
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


# ── Pydantic models ───────────────────────────────────────────────────────────

class BugReportRequest(BaseModel):
    title: str
    description: str
    severity: Literal["critical", "high", "medium", "low"] = "medium"


class QuickNoteRequest(BaseModel):
    content: str
    category: Literal["bug", "feature", "improvement", "research"] = "improvement"


class CIFailureWebhook(BaseModel):
    test: str = "unknown-test"
    error: str = ""
    workflow: str = "ci"
    branch: str = "master"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@v4_router.get("/status")
async def get_v4_status() -> dict:
    """System health and improvement loop status — no auth required."""
    from agent.improvement_loop import get_improvement_loop
    from agent.self_healing import get_self_healing_agent

    loop = get_improvement_loop()
    healer = get_self_healing_agent()

    loop_status = loop.get_status() if loop else {}
    recent_events = healer.get_events()[-5:] if healer else []

    return {
        "system": "local-llm-server",
        "dashboard_version": "4",
        "timestamp": _now(),
        "improvement_loop": {
            "active": loop is not None,
            **loop_status,
        },
        "self_healing": {
            "active": healer is not None,
            "recent_events": recent_events,
        },
    }


@v4_router.get("/improvements")
async def list_improvements(
    _: Annotated[None, Depends(_require_admin)],
) -> dict:
    """List active and resolved improvement issues."""
    from agent.improvement_loop import get_improvement_loop

    loop = get_improvement_loop()
    if not loop:
        return {"active": [], "resolved": [], "total": 0}

    state = loop.get_status()
    return {
        "active": state.get("active_issues", []),
        "resolved": state.get("resolved_issues", []),
        "total": state.get("issues_detected", 0),
        "last_scan": state.get("last_scan"),
        "scan_count": state.get("scan_count", 0),
        "last_test_result": state.get("last_test_result"),
        "failing_tests": state.get("failing_tests", []),
    }


@v4_router.post("/improvements/scan")
async def trigger_scan(
    _: Annotated[None, Depends(_require_admin)],
) -> dict:
    """Trigger an immediate codebase scan (runs synchronously in a thread)."""
    import asyncio

    from agent.improvement_loop import get_improvement_loop

    loop = get_improvement_loop()
    if not loop:
        raise HTTPException(status_code=503, detail="Improvement loop not running")

    issues = await asyncio.get_event_loop().run_in_executor(None, loop.trigger_scan)
    return {
        "issues_found": len(issues),
        "issues": [i.as_dict() for i in issues],
        "scanned_at": _now(),
    }


@v4_router.post("/improvements/{issue_id}/resolve")
async def resolve_improvement(
    issue_id: str,
    _: Annotated[None, Depends(_require_admin)],
) -> dict:
    """Mark an improvement issue as resolved."""
    from agent.improvement_loop import get_improvement_loop

    loop = get_improvement_loop()
    if not loop:
        raise HTTPException(status_code=503, detail="Improvement loop not running")

    if not loop.mark_resolved(issue_id):
        raise HTTPException(status_code=404, detail=f"Issue {issue_id!r} not found")
    return {"issue_id": issue_id, "resolved": True}


@v4_router.post("/report-bug")
async def report_bug(request: BugReportRequest) -> dict:
    """Manual bug report. Queues a self-healing fix task."""
    from agent.self_healing import get_self_healing_agent

    healer = get_self_healing_agent()
    if not healer:
        raise HTTPException(status_code=503, detail="Self-healing agent not running")

    event = await healer.on_manual_report(
        title=request.title,
        description=request.description,
        severity=request.severity,
    )
    return {
        "event_id": event.event_id,
        "title": event.title,
        "message": "Bug report queued for the self-healing agent",
    }


@v4_router.post("/ci-failure")
async def ci_failure_webhook(payload: CIFailureWebhook) -> dict:
    """Receive CI failure notifications (called by the continuous-improvement workflow)."""
    from agent.self_healing import get_self_healing_agent

    healer = get_self_healing_agent()
    if not healer:
        log.warning("/v4/ci-failure received but SelfHealingAgent is not running")
        return {"accepted": False, "reason": "self-healing agent not running"}

    event = await healer.on_ci_failure(payload.model_dump())
    return {"accepted": True, "event_id": event.event_id}


@v4_router.get("/quick-notes")
async def list_quick_notes(
    _: Annotated[None, Depends(_require_admin)],
) -> dict:
    """List all quick notes."""
    from agent.quick_note import get_quick_note_queue

    try:
        q = get_quick_note_queue()
    except RuntimeError:
        return {"notes": [], "total": 0, "pending": 0}

    notes = q.list_all()
    return {
        "notes": [n.as_dict() for n in notes],
        "total": len(notes),
        "pending": sum(1 for n in notes if n.status == "pending"),
    }


@v4_router.post("/quick-notes")
async def add_quick_note(request: QuickNoteRequest) -> dict:
    """Add a quick note (URL for content fetch, or plain-text instruction)."""
    from agent.quick_note import get_quick_note_queue

    try:
        q = get_quick_note_queue()
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Quick note queue not initialised")

    content = request.content.strip()
    if not content.startswith(("http://", "https://")):
        content = f"text:{content}"

    note = q.add(content)
    return {
        "note_id": note.note_id,
        "status": note.status,
        "category": request.category,
        "message": "Quick note queued for processing",
    }


@v4_router.get("/scheduler/jobs")
async def list_scheduler_jobs(
    _: Annotated[None, Depends(_require_admin)],
) -> dict:
    """List all scheduled improvement jobs."""
    from agent.scheduler import get_scheduler

    try:
        jobs = get_scheduler().list()
        return {"jobs": [j.as_dict() for j in jobs], "total": len(jobs)}
    except RuntimeError:
        return {"jobs": [], "total": 0, "error": "Scheduler not initialised"}


@v4_router.post("/scheduler/trigger/{job_id}")
async def trigger_job(
    job_id: str,
    _: Annotated[None, Depends(_require_admin)],
) -> dict:
    """Trigger a scheduled job immediately."""
    from agent.scheduler import get_scheduler

    try:
        job = get_scheduler().trigger(job_id)
        return {"job_id": job.job_id, "name": job.name, "triggered_at": _now()}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@v4_router.post("/improvements/security-scan")
async def trigger_security_scan(
    _: Annotated[None, Depends(_require_admin)],
) -> dict:
    """Run bandit + safety + secret grep and register findings as improvement issues."""
    import asyncio

    from agent.improvement_loop import get_improvement_loop

    loop = get_improvement_loop()
    if not loop:
        raise HTTPException(status_code=503, detail="Improvement loop not running")

    findings = await asyncio.get_event_loop().run_in_executor(None, loop._scan_security)
    new_issues = loop._filter_new_issues(findings)
    for issue in new_issues:
        loop._register_issue(issue)
        loop._schedule_fix(issue)
    return {
        "findings": len(findings),
        "new_issues": len(new_issues),
        "details": [i.as_dict() for i in findings],
        "scanned_at": _now(),
    }


@v4_router.get("/log-monitor/stats")
async def log_monitor_stats() -> dict:
    """Return log monitor statistics — no auth required."""
    from agent.log_monitor import get_log_monitor

    monitor = get_log_monitor()
    if not monitor:
        return {"active": False}
    return {"active": True, **monitor.get_stats()}


# ── Agency endpoints ──────────────────────────────────────────────────────────

@v4_router.get("/agency/status")
async def agency_status() -> dict:
    """Return agency status and recent cycle history."""
    from agent.agency import get_agency

    agency = get_agency()
    if not agency:
        return {"active": False}
    return {"active": True, **agency.get_status()}


@v4_router.post("/agency/run-cycle")
async def agency_run_cycle(
    _: Annotated[None, Depends(_require_admin)],
) -> dict:
    """Trigger an immediate CEO assessment cycle."""
    from agent.agency import get_agency

    agency = get_agency()
    if not agency:
        raise HTTPException(status_code=503, detail="Agency not running")

    result = await agency.run_cycle()
    return result.as_dict()


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

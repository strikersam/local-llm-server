"""workflow/api.py — FastAPI router for all /workflow/* endpoints.

All 13 endpoints are wired here and mounted into the main proxy.py app.
Auth reuses the existing verify_api_key dependency (imported at runtime
from proxy.py context via FastAPI dependency injection pattern).

Endpoints
---------
POST   /workflow/build                         Create + start a workflow run
GET    /workflow/                              List runs (paginated)
GET    /workflow/{run_id}                      Get full WorkflowRun
POST   /workflow/{run_id}/approve              Approve the plan (lift gate)
POST   /workflow/{run_id}/reject               Reject the plan (fail run)
POST   /workflow/{run_id}/resume               Resume a paused/failed run
POST   /workflow/{run_id}/cancel               Cancel a run

GET    /workflow/{run_id}/artifacts            List all artifacts
GET    /workflow/{run_id}/artifacts/{name}     Get artifact content (raw text)
GET    /workflow/{run_id}/slices               List all slices
POST   /workflow/{run_id}/slices/{slice_id}/run  Manually run a slice

GET    /workflow/{run_id}/checks               List all CheckRuns
POST   /workflow/{run_id}/verify               Trigger full verification pass
GET    /workflow/{run_id}/events               Get event log (queryable)
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from workflow.engine import WorkflowEngine, get_engine
from workflow.models import (
    WorkflowApproveRequest,
    WorkflowBuildRequest,
    WorkflowRejectRequest,
    WorkflowRun,
    WorkflowStatus,
    SliceRunRequest,
)

log = logging.getLogger("crispy-api")

workflow_router = APIRouter(prefix="/workflow", tags=["workflow"])


# ── Engine dependency ─────────────────────────────────────────────────────────

def _engine() -> WorkflowEngine:
    return get_engine()


# ── Helper: 404 if run not found ─────────────────────────────────────────────

def _get_run_or_404(run_id: str, engine: WorkflowEngine) -> WorkflowRun:
    run = engine.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"WorkflowRun {run_id!r} not found")
    return run


# ── Endpoints ─────────────────────────────────────────────────────────────────

@workflow_router.post("/build", status_code=202)
async def build(
    body: WorkflowBuildRequest,
    engine: WorkflowEngine = Depends(_engine),
) -> dict[str, Any]:
    """Create a new CRISPY workflow run and begin pre-gate phase execution.

    Returns immediately (202 Accepted) with the initial WorkflowRun.
    Poll GET /workflow/{run_id} to track progress.
    The run will pause at 'awaiting_approval' before any code is written.
    """
    run = await engine.create_run(body)
    log.info("Workflow build requested: run=%s", run.run_id)
    return {
        "run_id": run.run_id,
        "status": run.status,
        "title": run.title,
        "message": (
            "Workflow created. Pre-gate phases running asynchronously. "
            "Poll GET /workflow/{run_id} for status. "
            "The run will pause for human approval before executing any code."
        ),
        "run": run.as_dict(),
    }


@workflow_router.get("/")
def list_runs(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status: str | None = Query(default=None),
    engine: WorkflowEngine = Depends(_engine),
) -> dict[str, Any]:
    """List all workflow runs, newest first."""
    # Validate status if provided
    valid_statuses = {
        "pending", "context", "research", "investigate", "structure", "plan",
        "awaiting_approval", "executing", "reviewing", "verifying",
        "done", "failed", "cancelled",
    }
    if status and status not in valid_statuses:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status filter. Valid values: {sorted(valid_statuses)}",
        )
    typed_status: WorkflowStatus | None = status  # type: ignore[assignment]
    runs = engine.list_runs(limit=limit, offset=offset, status=typed_status)
    return {
        "runs": [r.as_dict() for r in runs],
        "count": len(runs),
        "limit": limit,
        "offset": offset,
    }


@workflow_router.get("/{run_id}")
def get_run(
    run_id: str,
    engine: WorkflowEngine = Depends(_engine),
) -> dict[str, Any]:
    """Get full WorkflowRun state including phases, slices, and artifacts."""
    run = _get_run_or_404(run_id, engine)
    return run.as_dict()


@workflow_router.post("/{run_id}/approve")
async def approve(
    run_id: str,
    body: WorkflowApproveRequest,
    engine: WorkflowEngine = Depends(_engine),
) -> dict[str, Any]:
    """Approve the plan and lift the ApprovalGate.

    The run must be in 'awaiting_approval' status.  Post-gate execution
    (slice execute → review → verify → report) will begin asynchronously.
    """
    _get_run_or_404(run_id, engine)
    try:
        updated = engine.approve(run_id, approved_by=body.approved_by)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "run_id": run_id,
        "status": updated.status,
        "message": "Plan approved. Execution has begun.",
        "gate": updated.approval_gate.model_dump() if updated.approval_gate else None,
    }


@workflow_router.post("/{run_id}/reject")
async def reject(
    run_id: str,
    body: WorkflowRejectRequest,
    engine: WorkflowEngine = Depends(_engine),
) -> dict[str, Any]:
    """Reject the plan with a reason. The run will be marked as failed."""
    _get_run_or_404(run_id, engine)
    try:
        updated = engine.reject(run_id, reason=body.reason, rejected_by=body.rejected_by)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "run_id": run_id,
        "status": updated.status,
        "reason": body.reason,
        "gate": updated.approval_gate.model_dump() if updated.approval_gate else None,
    }


@workflow_router.post("/{run_id}/resume")
async def resume(
    run_id: str,
    engine: WorkflowEngine = Depends(_engine),
) -> dict[str, Any]:
    """Resume a paused or interrupted run from its last completed phase."""
    _get_run_or_404(run_id, engine)
    try:
        updated = engine.resume(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"run_id": run_id, "status": updated.status}


@workflow_router.post("/{run_id}/cancel")
async def cancel(
    run_id: str,
    engine: WorkflowEngine = Depends(_engine),
) -> dict[str, Any]:
    """Cancel a non-terminal run."""
    _get_run_or_404(run_id, engine)
    try:
        updated = engine.cancel(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"run_id": run_id, "status": updated.status}


@workflow_router.get("/{run_id}/artifacts")
def list_artifacts(
    run_id: str,
    engine: WorkflowEngine = Depends(_engine),
) -> dict[str, Any]:
    """List all artifacts for a run (metadata only, no content)."""
    run = _get_run_or_404(run_id, engine)
    return {
        "run_id": run_id,
        "artifacts": [a.as_dict() for a in run.artifacts],
        "count": len(run.artifacts),
    }


@workflow_router.get("/{run_id}/artifacts/{artifact_name:path}")
def get_artifact_content(
    run_id: str,
    artifact_name: str,
    engine: WorkflowEngine = Depends(_engine),
) -> dict[str, Any]:
    """Get the raw text content of a named artifact."""
    _get_run_or_404(run_id, engine)
    art_store = engine._artifact_store
    art = art_store.get_by_name(run_id, artifact_name)
    if art is None:
        raise HTTPException(
            status_code=404,
            detail=f"Artifact {artifact_name!r} not found for run {run_id}",
        )
    content = art_store.get_content(art.artifact_id)
    return {
        "run_id": run_id,
        "artifact": art.as_dict(),
        "content": content,
    }


@workflow_router.get("/{run_id}/slices")
def list_slices(
    run_id: str,
    engine: WorkflowEngine = Depends(_engine),
) -> dict[str, Any]:
    """List all slices for a run."""
    run = _get_run_or_404(run_id, engine)
    return {
        "run_id": run_id,
        "slices": [s.as_dict() for s in run.slices],
        "count": len(run.slices),
    }


@workflow_router.post("/{run_id}/slices/{slice_id}/run")
async def run_slice(
    run_id: str,
    slice_id: str,
    body: SliceRunRequest,
    engine: WorkflowEngine = Depends(_engine),
) -> dict[str, Any]:
    """Manually trigger execution of a specific slice.

    By default, a slice that has already been 'applied' will not be re-run.
    Set force=true to override.
    """
    _get_run_or_404(run_id, engine)
    try:
        sl = await engine.run_slice(run_id, slice_id, force=body.force)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"run_id": run_id, "slice": sl.as_dict()}


@workflow_router.get("/{run_id}/checks")
def list_checks(
    run_id: str,
    engine: WorkflowEngine = Depends(_engine),
) -> dict[str, Any]:
    """List all CheckRuns (verification results) for a run."""
    run = _get_run_or_404(run_id, engine)
    checks = [s.check_run.as_dict() for s in run.slices if s.check_run is not None]
    return {"run_id": run_id, "checks": checks, "count": len(checks)}


@workflow_router.post("/{run_id}/verify")
async def verify(
    run_id: str,
    engine: WorkflowEngine = Depends(_engine),
) -> dict[str, Any]:
    """Trigger verification for all applied-but-unverified slices."""
    _get_run_or_404(run_id, engine)
    try:
        check_runs = await engine.run_verify(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "run_id": run_id,
        "checks_run": len(check_runs),
        "results": [cr.as_dict() for cr in check_runs],
    }


@workflow_router.get("/{run_id}/events")
def get_events(
    run_id: str,
    from_position: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    engine: WorkflowEngine = Depends(_engine),
) -> dict[str, Any]:
    """Return a positional slice of the workflow event log.

    Queryable by from_position for efficient polling without re-reading
    the full log.  Events are append-only and positional — position 0 is
    the first event.
    """
    _get_run_or_404(run_id, engine)
    events = engine.get_events(run_id, from_position=from_position, limit=limit)
    return {
        "run_id": run_id,
        "events": events,
        "count": len(events),
        "from_position": from_position,
    }


@workflow_router.get("/agents")
def get_agent_team(
    engine: WorkflowEngine = Depends(_engine),
) -> dict[str, Any]:
    """Return the current agent team composition.

    Shows which model is assigned to each role, and each agent's permission
    profile.  The key invariant — coder model ≠ reviewer model — should be
    visible here.

    Example response::

        {
          "swarm_active": true,
          "agents": [
            {"role": "coder",    "model": "qwen3-coder:30b",  "can_write": true, ...},
            {"role": "reviewer", "model": "deepseek-r1:32b",  "can_review": true, ...},
            ...
          ]
        }
    """
    swarm = engine.swarm
    if swarm is None:
        # agents package not available — return defaults from env
        import os
        _defaults = {
            "architect": ("Architect", "qwen3-coder:30b",  False, False, False),
            "scout":     ("Scout",     "deepseek-r1:32b",  False, False, False),
            "coder":     ("Coder",     "qwen3-coder:30b",  True,  False, False),
            "reviewer":  ("Reviewer",  "deepseek-r1:32b",  False, False, True),
            "verifier":  ("Verifier",  "qwen3-coder:7b",   False, True,  False),
        }
        agents = [
            {
                "role": role,
                "name": name,
                "model": os.environ.get(f"CRISPY_{role.upper()}_MODEL", default_model),
                "can_write": cw, "can_execute": ce, "can_review": cr,
            }
            for role, (name, default_model, cw, ce, cr) in _defaults.items()
        ]
        return {"swarm_active": False, "agents": agents}

    return {
        "swarm_active": True,
        "agents": swarm.team_summary(),
        "coder_model": swarm.get_profile("coder").model,
        "reviewer_model": swarm.get_profile("reviewer").model,
        "models_differ": swarm.get_profile("coder").model != swarm.get_profile("reviewer").model,
    }

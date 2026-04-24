"""runtimes/api.py — FastAPI routes for the runtime layer.

Exposes:
  GET  /runtimes/             — list all registered runtimes + health
  GET  /runtimes/{id}         — get single runtime details
  GET  /runtimes/health       — health summary for all runtimes
  GET  /runtimes/policy       — current routing policy
  PUT  /runtimes/policy       — update routing policy (admin only)
  GET  /runtimes/decisions    — routing decision audit log
  POST /runtimes/{id}/run     — execute a task on a specific runtime
  POST /runtimes/{id}/start   — start a stopped runtime container (admin only)
  POST /runtimes/{id}/stop    — stop a running runtime container (admin only)
  POST /runtimes/start-all    — start all runtime containers (admin only)
  POST /runtimes/stop-all     — stop all runtime containers (admin only)
"""

from __future__ import annotations

import secrets
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from runtimes.base import TaskSpec, RuntimeUnavailableError, RuntimeExecutionError
from runtimes.manager import get_runtime_manager
from runtimes.control import start_runtime, stop_runtime, start_all_runtimes, stop_all_runtimes

log = logging.getLogger("qwen-proxy")

runtime_router = APIRouter(prefix="/runtimes", tags=["runtimes"])


# ── Request/response models ───────────────────────────────────────────────────

class PolicyUpdateBody(BaseModel):
    never_use_paid_providers: bool | None = None
    require_approval_before_paid_escalation: bool | None = None
    max_paid_escalations_per_day: int | None = Field(default=None, ge=0, le=1000)
    preferred_runtime_id: str | None = Field(default=None, max_length=64)
    fallback_runtime_ids: list[str] | None = None
    task_type_runtime_overrides: dict[str, str] | None = None


class RunTaskBody(BaseModel):
    instruction: str = Field(..., min_length=1, max_length=16_000)
    task_type: str = Field(default="general", max_length=64)
    workspace_path: str | None = Field(default=None, max_length=512)
    model_preference: str | None = Field(default=None, max_length=200)
    timeout_sec: int = Field(default=300, ge=10, le=3600)
    context: dict[str, Any] = Field(default_factory=dict)
    tool_allowlist: list[str] | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _require_admin(request: Request) -> None:
    """Dependency: reject non-admin callers."""
    user = getattr(request.state, "user", None)
    if user is None or getattr(user, "role", "user") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


# ── Routes ────────────────────────────────────────────────────────────────────

@runtime_router.get("/")
async def list_runtimes() -> dict:
    """List all registered runtimes with current health status."""
    mgr = get_runtime_manager()
    return {"runtimes": mgr.list_runtimes()}


@runtime_router.get("/health")
async def runtime_health_summary() -> dict:
    """Health snapshot for all runtimes (circuit-breaker state included)."""
    mgr = get_runtime_manager()
    return {"health": mgr.health_summary()}


@runtime_router.get("/policy")
async def get_policy() -> dict:
    return {"policy": get_runtime_manager().get_policy()}


@runtime_router.put("/policy")
async def update_policy(
    body: PolicyUpdateBody,
    request: Request,
) -> dict:
    """Update the routing policy.  Admin only."""
    _require_admin(request)
    mgr = get_runtime_manager()
    updates = body.model_dump(exclude_none=True)
    mgr.update_policy(**updates)
    return {"policy": mgr.get_policy(), "message": "Policy updated"}


@runtime_router.get("/decisions")
async def get_decision_log(limit: int = 100) -> dict:
    """Routing decision audit log (newest first)."""
    if limit < 1 or limit > 1000:
        limit = 100
    mgr = get_runtime_manager()
    return {"decisions": mgr.get_decision_log(limit)}


@runtime_router.get("/{runtime_id}")
async def get_runtime(runtime_id: str) -> dict:
    """Get details for a single runtime."""
    mgr = get_runtime_manager()
    info = mgr.get_runtime(runtime_id)
    if info is None:
        raise HTTPException(status_code=404, detail=f"Runtime '{runtime_id}' not found")
    return info


@runtime_router.post("/{runtime_id}/run")
async def run_task_on_runtime(
    runtime_id: str,
    body: RunTaskBody,
) -> dict:
    """Execute a task on a specific runtime (bypasses routing policy)."""
    mgr = get_runtime_manager()
    adapter = mgr._registry.get(runtime_id)
    if adapter is None:
        raise HTTPException(status_code=404, detail=f"Runtime '{runtime_id}' not found")

    spec = TaskSpec(
        task_id=f"direct-{secrets.token_hex(6)}",
        instruction=body.instruction,
        task_type=body.task_type,
        workspace_path=body.workspace_path,
        model_preference=body.model_preference,
        timeout_sec=body.timeout_sec,
        context=body.context,
        tool_allowlist=body.tool_allowlist,
    )

    try:
        result = await adapter.execute(spec)
        return {"result": result.as_dict()}
    except RuntimeUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeExecutionError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── Runtime Lifecycle Control ─────────────────────────────────────────────────


@runtime_router.post("/{runtime_id}/start")
async def start_runtime_container(runtime_id: str, request: Request) -> dict:
    """Start a stopped runtime container (requires admin)."""
    _require_admin(request)
    return await start_runtime(runtime_id)


@runtime_router.post("/{runtime_id}/stop")
async def stop_runtime_container(runtime_id: str, request: Request) -> dict:
    """Stop a running runtime container (requires admin)."""
    _require_admin(request)
    return await stop_runtime(runtime_id)


@runtime_router.post("/start-all")
async def start_all(request: Request) -> dict:
    """Start all runtime containers (requires admin)."""
    _require_admin(request)
    return await start_all_runtimes()


@runtime_router.post("/stop-all")
async def stop_all(request: Request) -> dict:
    """Stop all runtime containers (requires admin)."""
    _require_admin(request)
    return await stop_all_runtimes()

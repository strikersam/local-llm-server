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

import asyncio
import secrets
import logging
from typing import Any
from collections.abc import Mapping

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from runtimes.base import (
    TaskSpec,
    RuntimeExecutionError,
    RuntimePreflightError,
    RuntimeUnavailableError,
)
from runtimes.manager import get_runtime_manager
from runtimes.control import start_runtime, stop_runtime, start_all_runtimes, stop_all_runtimes

log = logging.getLogger("qwen-proxy")

runtime_router = APIRouter(prefix="/runtimes", tags=["runtimes"])


# ── Request/response models ───────────────────────────────────────────────────

class PolicyUpdateBody(BaseModel):
    # Core runtime policy fields
    never_use_paid_providers: bool | None = None
    require_approval_before_paid_escalation: bool | None = None
    max_paid_escalations_per_day: int | None = Field(default=None, ge=0, le=1000)
    preferred_runtime_id: str | None = Field(default=None, max_length=64)
    fallback_runtime_ids: list[str] | None = None
    task_type_runtime_overrides: dict[str, str] | None = None
    # Rich UI format from RoutingPolicyPage: 4-tier pool config + escalation triggers.
    # The frontend sends {pools, policy, triggers}; we persist the whole payload in
    # the config store so GET /runtimes/policy can return it for round-trip fidelity.
    pools: dict | None = None
    policy: dict | None = None
    triggers: list | None = None


class RunTaskBody(BaseModel):
    instruction: str = Field(..., min_length=1, max_length=16_000)
    task_type: str = Field(default="general", max_length=64)
    workspace_path: str | None = Field(default=None, max_length=512)
    model_preference: str | None = Field(default=None, max_length=200)
    timeout_sec: int = Field(default=300, ge=10, le=3600)
    context: dict[str, Any] = Field(default_factory=dict)
    tool_allowlist: list[str] | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _require_admin(request: Request) -> None:
    """Dependency: reject unauthenticated or non-admin callers.

    Returns 401 for missing/unsigned requests and 403 for authenticated
    non-admin users so the frontend can distinguish "log in again" from
    "you'll never have access".
    """
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    role = user.get("role", "user") if isinstance(user, Mapping) else getattr(user, "role", "user")
    if role != "admin":
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


@runtime_router.post("/health/refresh")
async def refresh_runtime_health() -> dict:
    """Force an immediate health check for all runtimes."""
    mgr = get_runtime_manager()
    health = await mgr._health.verify_all()
    return {"health": health, "message": "Health refresh complete"}


_RICH_POLICY_KEY = "ui_routing_policy"


async def _load_rich_policy() -> dict:
    """Return the persisted rich UI policy (pools + policy + triggers), or {}."""
    try:
        from webui.config_store import JsonConfigStore
        return (await asyncio.to_thread(JsonConfigStore().load, _RICH_POLICY_KEY)) or {}
    except Exception:
        log.debug("Could not load rich UI routing policy", exc_info=True)
        return {}


async def _save_rich_policy(data: dict) -> None:
    from webui.config_store import JsonConfigStore
    try:
        await asyncio.to_thread(JsonConfigStore().save, _RICH_POLICY_KEY, data)
    except Exception:
        log.exception("Failed to persist rich UI routing policy")
        raise


@runtime_router.get("/policy")
async def get_policy() -> dict:
    core = get_runtime_manager().get_policy()
    rich = await _load_rich_policy()
    # Merge: rich provides UI-only keys (pools, triggers); core wins on any collision.
    return {"policy": {**rich, **core}}


@runtime_router.put("/policy")
async def update_policy(
    body: PolicyUpdateBody,
    request: Request,
    _: Any = Depends(_require_admin),
) -> dict:
    """Update the routing policy.  Admin only.

    Accepts both the minimal core format {never_use_paid_providers, …} and the
    richer UI format {pools, policy: {neverUseCommercial, …}, triggers} from
    RoutingPolicyPage.  The two formats are merged so the UI round-trips
    cleanly.
    """
    mgr = get_runtime_manager()

    # Map UI camelCase booleans → internal snake_case core flags
    ui_policy: dict = body.policy or {}
    core_updates: dict = body.model_dump(exclude_none=True, exclude={"pools", "policy", "triggers"})
    if ui_policy.get("neverUseCommercial") is not None:
        core_updates.setdefault("never_use_paid_providers", ui_policy["neverUseCommercial"])
    if ui_policy.get("askBeforeCommercial") is not None:
        core_updates.setdefault("require_approval_before_paid_escalation", ui_policy["askBeforeCommercial"])

    if core_updates:
        mgr.update_policy(**core_updates)

    # Persist the rich UI payload (pools + policy + triggers) for round-trip fidelity.
    rich: dict = {}
    if body.pools is not None:
        rich["pools"] = body.pools
    if body.policy is not None:
        rich["policy"] = body.policy
    if body.triggers is not None:
        rich["triggers"] = body.triggers
    existing = await _load_rich_policy()
    if rich:
        existing.update(rich)
        try:
            await _save_rich_policy(existing)
        except Exception as exc:
            raise HTTPException(status_code=500, detail="Failed to persist routing policy") from exc

    core = mgr.get_policy()
    return {"policy": {**existing, **core}, "message": "Policy updated"}


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
        report = await adapter.readiness_check(spec)
        if not report.ready:
            raise RuntimePreflightError(runtime_id, report)
        result = await adapter.execute(spec)
        return {"result": result.as_dict()}
    except RuntimePreflightError as exc:
        raise HTTPException(status_code=412, detail=exc.report.as_dict()) from exc
    except RuntimeUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeExecutionError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── Runtime Lifecycle Control ─────────────────────────────────────────────────


@runtime_router.post("/{runtime_id}/start")
async def start_runtime_container(runtime_id: str) -> dict:
    """Start a stopped runtime container."""
    result = await start_runtime(runtime_id)
    # 200 with informational payload — not an error (allows UI to show remote/local info)
    if result.get("docker_unavailable") or result.get("remote_managed"):
        return result
    if result.get("status") == "error":
        # Ensure external errors never leak stack traces or internal details
        internal_error = str(result.get("error", "Unknown"))
        log.error(f"Runtime start failed for {runtime_id}: {internal_error}")
        raise HTTPException(status_code=500, detail="Internal server error during runtime startup")
    return result


@runtime_router.post("/{runtime_id}/stop")
async def stop_runtime_container(runtime_id: str) -> dict:
    """Stop a running runtime container."""
    result = await stop_runtime(runtime_id)
    if result.get("docker_unavailable"):
        return result
    if result.get("status") == "error":
        internal_error = str(result.get("error", "Unknown"))
        log.error(f"Runtime stop failed for {runtime_id}: {internal_error}")
        raise HTTPException(status_code=500, detail="Internal server error during runtime shutdown")
    return result


@runtime_router.post("/start-all")
async def start_all() -> dict:
    """Start all runtime containers.

    Returns partial results — individual runtime failures are included
    in the response body rather than raising a 500, so the frontend can
    show per-runtime status even when some runtimes (e.g. Docker-based
    ones) are unavailable on the current host.
    """
    result = await start_all_runtimes()
    errors = {
        rt_id: rt_res.get("error", "Unknown error")
        for rt_id, rt_res in result.get("runtimes", {}).items()
        if rt_res.get("status") == "error"
    }
    if errors:
        result["errors"] = errors
        result["partial"] = True
        log.warning("start-all: %d runtime(s) failed: %s", len(errors), errors)
    return result


@runtime_router.post("/stop-all")
async def stop_all() -> dict:
    """Stop all runtime containers.

    Returns partial results — individual runtime failures are included
    in the response body rather than raising a 500.
    """
    result = await stop_all_runtimes()
    errors = {
        rt_id: rt_res.get("error", "Unknown error")
        for rt_id, rt_res in result.get("runtimes", {}).items()
        if rt_res.get("status") == "error"
    }
    if errors:
        result["errors"] = errors
        result["partial"] = True
        log.warning("stop-all: %d runtime(s) failed: %s", len(errors), errors)
    return result

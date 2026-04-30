"""routing/api.py — Control-plane routing policy endpoints.

Exposes the RuntimeRoutingPolicyEngine configuration under /api/routing/*
so the Control Plane UI can manage the 4-tier escalation policy without
going through the /runtimes/ prefix.

Routes:
  GET  /api/routing/policy   get current routing policy
  PUT  /api/routing/policy   update routing policy (admin only)
  GET  /api/routing/stats    escalation decisions + local ratio
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from runtimes.manager import get_runtime_manager

log = logging.getLogger("qwen-proxy")

routing_router = APIRouter(prefix="/api/routing", tags=["routing"])


# ── Admin guard ───────────────────────────────────────────────────────────────

async def _require_admin(request: Request) -> None:
    user = getattr(request.state, "user", None) or {}
    role = user.get("role", "user") if isinstance(user, Mapping) else "user"
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


# ── Request model ─────────────────────────────────────────────────────────────

class PolicyUpdateRequest(BaseModel):
    never_use_paid_providers: bool | None = None
    require_approval_before_paid_escalation: bool | None = None
    max_paid_escalations_per_day: int | None = Field(default=None, ge=0, le=1000)
    preferred_runtime_id: str | None = Field(default=None, max_length=64)
    fallback_runtime_ids: list[str] | None = None
    task_type_runtime_overrides: dict[str, str] | None = None


# ── Routes ────────────────────────────────────────────────────────────────────

@routing_router.get("/policy")
async def get_routing_policy(request: Request) -> dict:
    """Return the current runtime routing policy."""
    mgr = get_runtime_manager()
    return {"policy": mgr.get_policy()}


@routing_router.put("/policy")
async def update_routing_policy(
    body: PolicyUpdateRequest,
    request: Request,
    _: Any = Depends(_require_admin),
) -> dict:
    """Update the routing policy.  Admin only."""
    mgr = get_runtime_manager()
    updates = body.model_dump(exclude_none=True)
    mgr.update_policy(**updates)
    return {"policy": mgr.get_policy(), "message": "Policy updated"}


@routing_router.get("/stats")
async def get_routing_stats(request: Request, limit: int = 50) -> dict:
    """Return routing decision log + escalation stats."""
    if limit < 1 or limit > 500:
        limit = 50
    mgr = get_runtime_manager()
    decisions = mgr.get_decision_log(limit)
    escalated = [d for d in decisions if d.get("escalated")]
    total = len(decisions)
    local_count = sum(
        1 for d in decisions
        if not d.get("escalated") and not str(d.get("selected_runtime_id", "")).startswith("paid:")
    )
    return {
        "total_decisions": total,
        "escalated_count": len(escalated),
        "local_ratio": round(local_count / total, 3) if total else 1.0,
        "decisions": decisions,
    }

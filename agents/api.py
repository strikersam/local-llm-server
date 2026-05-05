"""agents/api.py — FastAPI router for user-defined agent CRUD.

Endpoints:
  GET    /api/agents/             list agents (own + public; admin sees all)
  POST   /api/agents/             create agent
  GET    /api/agents/{id}         get agent detail
  PUT    /api/agents/{id}         update agent
  DELETE /api/agents/{id}         delete agent
  POST   /api/agents/{id}/use     record a use (for analytics)

RBAC:
  - Standard User:  own agents + public agents
  - Power User:     workspace agents (all public + own)
  - Admin:          all agents
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from rbac import (
    UserRole,
    Permission,
    audit,
    get_user_role,
    has_permission,
    require_authenticated,
    require_admin,
)
from agents.store import (
    AgentDefinition,
    AgentCreateRequest,
    AgentUpdateRequest,
    get_agent_store,
)
from runtimes.manager import get_runtime_manager
from tasks.models import TaskStatus
from tasks.store import get_task_store

log = logging.getLogger("qwen-proxy")
agent_router = APIRouter(prefix="/api/agents", tags=["agents"])


def _get_user(request: Request) -> dict:
    user = getattr(request.state, "user", None) or {}
    return user


def _user_id(user: Any) -> str:
    if isinstance(user, dict):
        return user.get("email") or user.get("_id") or "unknown"
    return str(getattr(user, "email", None) or getattr(user, "_id", "unknown"))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _with_runtime_health(agent_dict: dict) -> dict:
    """Annotate an agent dict with its runtime's current health status."""
    rid = agent_dict.get("runtime_id")
    if not rid:
        return agent_dict
    try:
        info = get_runtime_manager().get_runtime(rid)
        if info:
            health = info.get("health") or {}
            agent_dict["runtime_health"] = {
                "available": health.get("available"),
                "latency_ms": health.get("latency_ms"),
                "error": health.get("error"),
            }
    except Exception:
        pass
    return agent_dict


def _apply_activity_status(
    agent_dict: dict,
    *,
    open_task_count: int,
    active_task_count: int,
) -> dict:
    runtime_health = agent_dict.get("runtime_health") or {}
    runtime_available = runtime_health.get("available")

    if active_task_count > 0 or open_task_count > 0:
        status = "running"
    elif runtime_available is False:
        status = "error"
    else:
        status = "idle"

    agent_dict["status"] = status
    agent_dict["open_task_count"] = open_task_count
    agent_dict["active_task_count"] = active_task_count
    if active_task_count > 0 and not agent_dict.get("last_active"):
        agent_dict["last_active"] = agent_dict.get("updated_at") or agent_dict.get("last_used_at")
    return agent_dict


# ── List ──────────────────────────────────────────────────────────────────────

@agent_router.get("/")
async def list_agents(request: Request):
    """List agents visible to the current user, enriched with runtime health."""
    user = _get_user(request)
    uid  = _user_id(user)
    store = get_agent_store()

    if get_user_role(user) == UserRole.ADMIN:
        agents = await store.list_all()
    else:
        agents = await store.list_for_user(uid, include_public=True)

    task_store = get_task_store()
    owner_scope = None if get_user_role(user) == UserRole.ADMIN else uid
    open_counts = await task_store.count_by_agent(
        owner_id=owner_scope,
        statuses={
            TaskStatus.TODO,
            TaskStatus.IN_PROGRESS,
            TaskStatus.IN_REVIEW,
            TaskStatus.BLOCKED,
        },
    )
    active_counts = await task_store.count_by_agent(
        owner_id=owner_scope,
        statuses={TaskStatus.IN_PROGRESS},
    )

    enriched = []
    for agent in agents:
        agent_dict = _with_runtime_health(agent.as_dict())
        enriched.append(
            _apply_activity_status(
                agent_dict,
                open_task_count=open_counts.get(agent.agent_id, 0),
                active_task_count=active_counts.get(agent.agent_id, 0),
            )
        )

    return {
        "agents": enriched,
        "total": len(agents),
    }


@agent_router.get("/runtimes")
async def list_runtime_agents(request: Request):
    """Return all system-registered runtime agents with live health status.

    Combines the AgentStore entries (name, model, task_types, cost_policy)
    with the RuntimeManager's live health data (available, latency_ms).
    This is the canonical source of truth for the agent roster UI.
    """
    store = get_agent_store()
    mgr   = get_runtime_manager()

    # Pull every registered runtime adapter from the manager
    runtime_infos = {r["runtime_id"]: r for r in mgr.list_runtimes()}

    # Pull matching agent definitions (system agents tagged "runtime")
    all_agents = await store.list_all()
    system_agents = {
        a.agent_id: a for a in all_agents
        if "runtime" in (a.tags or [])
    }

    roster: list[dict] = []
    for rid, rt_info in runtime_infos.items():
        entry: dict = {
            "runtime_id": rid,
            "display_name": rt_info.get("display_name", rid),
            "description": rt_info.get("description", ""),
            "tier": rt_info.get("tier"),
            "capabilities": rt_info.get("capabilities", []),
            "integration_mode": rt_info.get("integration_mode"),
            "health": rt_info.get("health") or {"available": None},
            "circuit_open": rt_info.get("circuit_open", False),
        }
        # Merge in agent profile fields when available
        agent = system_agents.get(rid)
        if agent:
            entry.update({
                "agent_id": agent.agent_id,
                "name": agent.name,
                "model": agent.model,
                "task_types": agent.task_types,
                "cost_policy": agent.cost_policy,
                "tags": agent.tags,
            })
        else:
            entry["agent_id"] = None

        roster.append(entry)

    # Sort: available first, then by tier
    roster.sort(key=lambda r: (
        r["health"].get("available") is not True,
        r.get("tier", "z"),
    ))

    return {"runtimes": roster, "total": len(roster)}


# ── Create ────────────────────────────────────────────────────────────────────

@agent_router.post("/", status_code=201)
async def create_agent(request: Request, body: AgentCreateRequest):
    """Create a new agent definition."""
    user = _get_user(request)
    uid  = _user_id(user)

    # Power users can create public (workspace) agents; standard users only own
    if body.is_public and not has_permission(user, Permission.MANAGE_WORKSPACE_AGENTS):
        raise HTTPException(
            status_code=403,
            detail="Only Power Users and Admins may create public (workspace) agents.",
        )

    agent = AgentDefinition(
        owner_id=uid,
        **body.model_dump(),
    )
    agent.sync_compat_fields()
    store = get_agent_store()
    await store.create(agent)

    audit("agent.create", user, resource="agent", resource_id=agent.agent_id)
    log.info("Agent created: %s by %s", agent.agent_id, uid)

    return agent.as_dict()


# ── Get ───────────────────────────────────────────────────────────────────────

@agent_router.get("/{agent_id}")
async def get_agent(agent_id: str, request: Request):
    """Get a single agent by ID."""
    user  = _get_user(request)
    uid   = _user_id(user)
    store = get_agent_store()

    # Admin sees all; users see own + public
    owner_filter = None if get_user_role(user) == UserRole.ADMIN else uid
    agent = await store.get(agent_id, owner_id=owner_filter)

    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id!r} not found.")

    return agent.as_dict()


# ── Update ────────────────────────────────────────────────────────────────────

@agent_router.put("/{agent_id}")
async def update_agent(agent_id: str, request: Request, body: AgentUpdateRequest):
    """Update an agent.  Only the owner or an admin may update."""
    user  = _get_user(request)
    uid   = _user_id(user)
    store = get_agent_store()

    # Fetch without owner filter to detect 404 vs 403
    agent = await store.get(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id!r} not found.")

    if agent.owner_id != uid and get_user_role(user) != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="You do not own this agent.")

    # Changing is_public requires power user or admin
    if body.is_public is True and not has_permission(user, Permission.MANAGE_WORKSPACE_AGENTS):
        raise HTTPException(
            status_code=403,
            detail="Only Power Users and Admins may make agents public.",
        )

    update_data = body.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(agent, k, v)
    agent.sync_compat_fields()

    await store.update(agent)
    audit("agent.update", user, resource="agent", resource_id=agent_id)
    return agent.as_dict()


# ── Delete ────────────────────────────────────────────────────────────────────

@agent_router.delete("/{agent_id}", status_code=204)
async def delete_agent(agent_id: str, request: Request):
    """Delete an agent.  Only the owner or admin may delete."""
    user  = _get_user(request)
    uid   = _user_id(user)
    store = get_agent_store()

    owner_filter = None if get_user_role(user) == UserRole.ADMIN else uid
    ok = await store.delete(agent_id, owner_id=owner_filter)

    if not ok:
        raise HTTPException(
            status_code=404,
            detail=f"Agent {agent_id!r} not found or you do not have permission to delete it.",
        )
    audit("agent.delete", user, resource="agent", resource_id=agent_id)


# ── Record use ────────────────────────────────────────────────────────────────

@agent_router.post("/{agent_id}/use")
async def record_agent_use(agent_id: str, request: Request):
    """Increment the use counter for analytics."""
    user  = _get_user(request)
    uid   = _user_id(user)
    store = get_agent_store()

    agent = await store.get(agent_id, owner_id=uid)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id!r} not found.")

    agent.record_use()
    await store.update(agent)
    return {"agent_id": agent_id, "use_count": agent.use_count}

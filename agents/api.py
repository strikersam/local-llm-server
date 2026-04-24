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

log = logging.getLogger("qwen-proxy")
agent_router = APIRouter(prefix="/api/agents", tags=["agents"])


def _get_user(request: Request) -> dict:
    user = getattr(request.state, "user", None) or {}
    return user


def _user_id(user: Any) -> str:
    if isinstance(user, dict):
        return user.get("email") or user.get("_id") or "unknown"
    return str(getattr(user, "email", None) or getattr(user, "_id", "unknown"))


# ── List ──────────────────────────────────────────────────────────────────────

@agent_router.get("/")
async def list_agents(request: Request):
    """List agents visible to the current user."""
    user = _get_user(request)
    uid  = _user_id(user)
    store = get_agent_store()

    if get_user_role(user) == UserRole.ADMIN:
        agents = await store.list_all()
    else:
        agents = await store.list_for_user(uid, include_public=True)

    return {"agents": [a.as_dict() for a in agents], "total": len(agents)}


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

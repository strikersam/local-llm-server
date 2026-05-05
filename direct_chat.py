"""direct_chat.py — Direct chat endpoints for v3 dashboard.

Handles chat sessions and message sending for the Direct Chat feature.
Protected by JWT authentication (v3 auth system).
Delegates to LLM providers via the proxy's routing system.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from agent.job_manager import AgentJobManager, make_isolated_workspace
from tokens import verify_token
from provider_router import ProviderRouter
from runtimes.adapters.internal_agent import InternalAgentAdapter
from runtimes.base import TaskSpec

log = logging.getLogger("qwen-proxy")
OLLAMA_BASE = os.environ.get("OLLAMA_BASE", "http://localhost:11434")
direct_chat_router = APIRouter(prefix="/api/chat", tags=["chat"])

# Session store for direct chat
from agent.state import AgentSessionStore
_direct_chat_store = AgentSessionStore(db_path="direct_chat_sessions.db")
_agent_jobs = AgentJobManager()
_agent_workspace_root = Path(os.environ.get("DIRECT_CHAT_AGENT_WORKSPACE_ROOT", ".data/direct-chat-agent-workspaces"))


def _ensure_session(session_id: str, user: UserInfo) -> None:
    if _direct_chat_store.get(session_id) is None:
        _direct_chat_store.create_with_id(
            session_id=session_id,
            title=f"Direct chat for {user.email}",
            owner_id=user.email,
        )


def _session_history(session_id: str) -> list[dict[str, str]]:
    session = _direct_chat_store.get(session_id)
    if session is None:
        return []
    return [item.model_dump() for item in session.history]


class UserInfo(BaseModel):
    """Current user from JWT token."""
    id: str
    email: str


def _get_bearer_token(authorization: str | None = Header(None)) -> str:
    """Extract bearer token from Authorization header."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    return authorization[7:].strip()


async def _get_current_user(token: Annotated[str, Depends(_get_bearer_token)]) -> UserInfo:
    """Extract and validate current user from JWT token."""
    payload = verify_token(token, token_type="access")
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return UserInfo(
        id=payload.get("sub", ""),
        email=payload.get("email", ""),
    )


class ChatSendRequest(BaseModel):
    """Send chat message request."""
    content: str
    session_id: str | None = None
    model: str | None = None
    provider_id: str | None = None
    temperature: float | None = None
    agent_mode: bool = False
    allow_commercial_fallback_once: bool = False


async def _get_github_token_for_user(user_email: str) -> str | None:
    """Fetch GitHub token for user from secrets store or environment."""
    try:
        from secrets_store import get_secrets_store
        from rbac import get_user_role
        store = get_secrets_store()
        uid = user_email
        role = get_user_role({"email": user_email})  # Simplified
        recs = await store.list_for_user(uid, role)
        for rec in recs:
            if "github" in rec.tags or rec.name.lower().startswith("github"):
                value = await store.get_value(rec.secret_id, uid, role)
                if value:
                    return value
    except Exception as e:
        log.debug("Could not fetch GitHub token from secrets: %s", e)
    # Fallback: env var
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


@direct_chat_router.post("/send")
async def send_chat_message(
    req: ChatSendRequest,
    request: Request,
    user: Annotated[UserInfo, Depends(_get_current_user)],
):
    """Send a chat message (Direct Chat feature).

    If agent_mode is True, runs an agent loop to perform the instruction.
    Otherwise, routes the message to the appropriate LLM provider based on the model parameter.
    """
    if req.agent_mode:
        return await _handle_agent_mode(req, user, request)
    else:
        return await _handle_regular_chat(req, user, request)


async def _handle_regular_chat(
    req: ChatSendRequest,
    user: UserInfo,
    request: Request,
):
    """Handle regular chat (non-agent mode)."""
    log.info(f"Chat message from {user.email}: {req.content[:50]}...")

    # Load history if session_id is provided
    session_id = req.session_id
    if session_id:
        history = _session_history(session_id)
    else:
        session_id = str(uuid.uuid4())
        history = []
    _ensure_session(session_id, user)

    # Build OpenAI-compatible request
    payload = {
        "messages": history + [{"role": "user", "content": req.content}],
        "model": req.model or "nemotron-3-super-120b-a12b",
        "stream": False,
    }
    if req.temperature is not None:
        payload["temperature"] = req.temperature

    # Use the provider router from the app state
    router: ProviderRouter = request.app.state.PROVIDER_ROUTER
    try:
        # Try to get the provider if provider_id is specified
        provider = None
        if req.provider_id:
            # Find the provider in the router's list
            for p in router.providers:
                if p.provider_id == req.provider_id:
                    provider = p
                    break
            if not provider:
                log.warning(f"Provider {req.provider_id} not found, using default router")

        # Call the router
        if provider:
            # We want to try just this provider, but we don't have a method for that.
            # We can temporarily set the router's providers to just this one.
            original_providers = router.providers
            router.providers = [provider]
            try:
                result = await router.chat_completion(payload)
            finally:
                router.providers = original_providers
        else:
            result = await router.chat_completion(payload)

        # Extract the assistant message and log the provider used
        assistant_message = result.response.json()["choices"][0]["message"]["content"]
        used_provider_id = result.provider.provider_id
        used_model = result.model
        log.info(f"Used provider: {used_provider_id}, model: {used_model}")

        # Update history with the new user message and assistant response
        _direct_chat_store.append_message(session_id, "user", req.content)
        _direct_chat_store.append_message(session_id, "assistant", assistant_message)

        return JSONResponse(content={
            "session_id": session_id,
            "response": assistant_message,
        })
    except Exception as e:
        log.error(f"Failed to get provider response: {e}")
        raise HTTPException(status_code=500, detail="Failed to get provider response")

async def _handle_agent_mode(
    req: ChatSendRequest,
    user: UserInfo,
    request: Request,
):
    """Handle agent mode asynchronously via a background job."""
    log.info(f"Agent mode chat from {user.email}: {req.content[:50]}...")

    # Load history if session_id is provided
    session_id = req.session_id
    if session_id:
        history = _session_history(session_id)
    else:
        session_id = str(uuid.uuid4())
        history = []
    _ensure_session(session_id, user)
    _direct_chat_store.append_message(session_id, "user", req.content)

    github_token = await _get_github_token_for_user(user.email)
    if not github_token:
        log.warning(f"No GitHub token found for user {user.email}")

    job = _agent_jobs.create_job(
        session_id=session_id,
        instruction=req.content,
        requested_model=req.model,
        provider_id=req.provider_id,
    )
    workspace_root = make_isolated_workspace(_agent_workspace_root, session_id, job.job_id)
    job.workspace_path = str(workspace_root)

    adapter = InternalAgentAdapter(config={"workspace_root": str(workspace_root)})
    spec = TaskSpec(
        task_id=job.job_id,
        instruction=req.content,
        task_type="code_generation",
        workspace_path=str(workspace_root),
        model_preference=req.model,
        timeout_sec=int(os.environ.get("DIRECT_CHAT_AGENT_TIMEOUT_SEC", "900")),
        context={
            "conversation": history,
            "max_steps": 10,
            "owner_id": user.id,
            "user_email": user.email,
            "session_id": session_id,
        },
    )

    report = await adapter.readiness_check(spec)
    if not report.ready:
        raise HTTPException(status_code=412, detail=report.as_dict())

    async def _run_agent_job(heartbeat):
        from agent.loop import AgentRunner

        heartbeat("planning", "Runtime preflight passed")
        runner = AgentRunner(
            ollama_base=OLLAMA_BASE,
            workspace_root=str(workspace_root),
            provider_headers={},
            provider_chain=[],
            allow_commercial_fallback=req.allow_commercial_fallback_once,
            provider_temperature=req.temperature,
            session_store=None,
            github_token=github_token,
            email=user.email,
            department=None,
            key_id=None,
        )
        heartbeat("execution", "Agent execution started")
        result = await runner.run(
            instruction=req.content,
            history=history,
            requested_model=req.model,
            auto_commit=True,
            max_steps=10,
            user_id=user.id,
            department=None,
            key_id=None,
            memory_store=None,
            session_id=None,
        )
        heartbeat("verification", "Planner/executor/verifier flow completed")
        assistant_message = result.get("summary", "Agent completed")
        _direct_chat_store.append_message(session_id, "assistant", assistant_message)
        return {
            "session_id": session_id,
            "response": assistant_message,
            "agent_result": result,
            "runtime": {
                "runtime_id": adapter.RUNTIME_ID,
                "workspace_path": str(workspace_root),
                "requested_model": req.model,
                "resolved_model": req.model,
            },
        }

    _agent_jobs.start_job(job.job_id, _run_agent_job)

    return JSONResponse(
        status_code=202,
        content={
            "session_id": session_id,
            "job_id": job.job_id,
            "status": job.status,
            "phase": job.phase,
            "message": "Agent workflow queued. Poll the job endpoint for progress.",
        },
    )


@direct_chat_router.get("/agent-jobs/{job_id}")
async def get_agent_job(
    job_id: str,
    user: Annotated[UserInfo, Depends(_get_current_user)],
):
    job = _agent_jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Agent job not found")
    session = _direct_chat_store.get(job.session_id)
    if session and session.owner_id and session.owner_id != user.email:
        raise HTTPException(status_code=403, detail="Agent job belongs to another user")
    return job.as_dict()


@direct_chat_router.post("/agent-jobs/{job_id}/cancel")
async def cancel_agent_job(
    job_id: str,
    user: Annotated[UserInfo, Depends(_get_current_user)],
):
    job = _agent_jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Agent job not found")
    session = _direct_chat_store.get(job.session_id)
    if session and session.owner_id and session.owner_id != user.email:
        raise HTTPException(status_code=403, detail="Agent job belongs to another user")
    cancelled = _agent_jobs.cancel_job(job_id)
    assert cancelled is not None
    return cancelled.as_dict()


@direct_chat_router.get("/sessions")
async def list_chat_sessions(
    user: Annotated[UserInfo, Depends(_get_current_user)],
):
    """List chat sessions for current user."""
    sessions = [
        session for session in _direct_chat_store.list()
        if not session.owner_id or session.owner_id == user.email
    ]
    return {
        "sessions": [
            {
                "_id": session.session_id,
                "title": session.title,
                "updated_at": session.updated_at,
            }
            for session in sessions
        ],
        "total": len(sessions),
    }


@direct_chat_router.get("/sessions/{session_id}")
async def get_chat_session(
    session_id: str,
    user: Annotated[UserInfo, Depends(_get_current_user)],
):
    """Get a specific chat session."""
    history = _direct_chat_store.get(session_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if history.owner_id and history.owner_id != user.email:
        raise HTTPException(status_code=403, detail="Session belongs to another user")
    # We don't store the title, so we'll set it to the first user message or "Untitled"
    title = "Untitled chat"
    if history.history:
        # Look for the first user message
        for msg in history.history:
            if msg.role == "user":
                title = msg.content[:50]  # truncate
                break
    return {
        "session_id": session_id,
        "title": title,
        "history": [msg.model_dump() for msg in history.history],
        "messages": [msg.model_dump() for msg in history.history],
    }


@direct_chat_router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    user: Annotated[UserInfo, Depends(_get_current_user)],
):
    """Delete a chat session."""
    session = _direct_chat_store.get(session_id)
    if session and session.owner_id and session.owner_id != user.email:
        raise HTTPException(status_code=403, detail="Session belongs to another user")
    _direct_chat_store.delete(session_id)
    return {"deleted": True, "session_id": session_id}

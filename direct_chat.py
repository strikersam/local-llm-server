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
from typing import Annotated, Any

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
    metadata: dict[str, Any] | None = None
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


def _is_trivial_message(content: str) -> bool:
    if not content or not isinstance(content, str):
        return False
    stripped = content.strip()
    lowered = stripped.lower()

    trivial_phrases = {
        "hello", "hi", "hey", "sup", "yo", "greetings",
        "good morning", "good afternoon", "good evening",
        "how are you", "what's up", "hi there", "hello there", "hey there",
        "thanks", "thank you", "ok", "okay", "sounds good", "got it",
        "what can you do", "who are you", "what are you",
    }
    if lowered in trivial_phrases:
        return True
    words = stripped.split()
    if len(words) <= 4:
        return True
    if lowered.endswith("?") and len(words) <= 12 and not any(
        kw in lowered for kw in (
            "file", "code", "write", "create", "fix", "build", "run",
            "edit", "generate", "deploy", "commit", "push", "implement", "refactor",
        )
    ):
        return True
    return False


@direct_chat_router.post("/send")
async def send_chat_message(
    req: ChatSendRequest,
    request: Request,
    user: Annotated[UserInfo, Depends(_get_current_user)],
):
    if req.agent_mode and _is_trivial_message(req.content):
        log.info(f"Trivial message detected, forcing regular chat mode for: {req.content[:50]}...")
        req.agent_mode = False
    if req.agent_mode:
        return await _handle_agent_mode(req, user, request)
    else:
        return await _handle_regular_chat(req, user, request)


async def _handle_regular_chat(
    req: ChatSendRequest,
    user: UserInfo,
    request: Request,
):
    log.info(f"Chat message from {user.email}: {req.content[:50]}...")
    session_id = req.session_id
    if session_id:
        history = _session_history(session_id)
    else:
        session_id = str(uuid.uuid4())
        history = []
    _ensure_session(session_id, user)
    system_prompt = (
        "You are a helpful coding assistant integrated with a self-hosted AI proxy server. "
        "You can answer questions about code, explain concepts, review snippets, and assist "
        "with software engineering tasks. "
        "For tasks that require reading or editing files in a GitHub repository "
        "(e.g. opening PRs, committing changes, browsing repo contents), ask the user to "
        "enable Agent Mode — that unlocks the GitHub tools needed to take those actions. "
        "Never refuse to help; always guide the user toward the right mode or approach."
    )
    payload = {
        "messages": [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": req.content}],
        "model": req.model or "nemotron-3-super-120b-a12b",
        "stream": False,
    }
    if req.temperature is not None:
        payload["temperature"] = req.temperature
    router: ProviderRouter = request.app.state.PROVIDER_ROUTER
    try:
        provider = None
        if req.provider_id:
            for p in router.providers:
                if p.provider_id == req.provider_id:
                    provider = p
                    break
        if provider: result = await ProviderRouter([provider]).chat_completion(payload)
        else: result = await router.chat_completion(payload)
        assistant_message = result.response.json()["choices"][0]["message"]["content"]
        _direct_chat_store.append_message(session_id, "user", req.content)
        _direct_chat_store.append_message(session_id, "assistant", assistant_message)
        return JSONResponse(content={
            "session_id": session_id,
            "response": assistant_message
        })
    except Exception as e:
        log.error(f"Failed to get provider response: {e}")
        raise HTTPException(status_code=500, detail="Failed to get provider response")

async def _handle_agent_mode(
    req: ChatSendRequest,
    user: UserInfo,
    request: Request,
):
    log.info(f"Agent mode chat from {user.email}: {req.content[:50]}...")
    session_id = req.session_id
    if session_id: history = _session_history(session_id)
    else:
        session_id = str(uuid.uuid4())
        history = []
    _ensure_session(session_id, user)
    _direct_chat_store.append_message(session_id, "user", req.content)
    github_token = await _get_github_token_for_user(user.email)
    job = _agent_jobs.create_job(session_id=session_id, owner_id=user.email, instruction=req.content, requested_model=req.model, provider_id=req.provider_id)
    workspace_root = make_isolated_workspace(_agent_workspace_root, session_id, job.job_id)
    job.workspace_path = str(workspace_root)
    adapter = InternalAgentAdapter(config={"workspace_root": str(workspace_root)})
    spec = TaskSpec(
        task_id=job.job_id,
        instruction=req.content,
        task_type="code_generation",
        workspace_path=str(workspace_root),
        model_preference=req.model,
        timeout_sec=int(os.environ.get("DIRECT_CHAT_AGENT_TIMEOUT_SEC", "1800")),
        context={
            "conversation": history,
            "max_steps": 25,
            "owner_id": user.id,
            "user_email": user.email,
            "session_id": session_id,
            "metadata": req.metadata or {},
        },
    )
    report = await adapter.readiness_check(spec)
    if not report.ready: raise HTTPException(status_code=412, detail=report.as_dict())
    async def _run_agent_job(heartbeat):
        from agent.loop import AgentRunner
        heartbeat("planning", "Runtime preflight passed")
        app_router: ProviderRouter = request.app.state.PROVIDER_ROUTER
        sorted_providers = sorted(app_router.providers, key=lambda p: p.priority)
        primary_provider = sorted_providers[0] if sorted_providers else None
        ollama_base = primary_provider.normalized_base_url if primary_provider else OLLAMA_BASE
        primary_headers = primary_provider.auth_headers() if primary_provider and primary_provider.api_key else {}
        runner = AgentRunner(ollama_base=ollama_base, workspace_root=str(workspace_root), provider_headers=primary_headers, provider_chain=sorted_providers[1:], allow_commercial_fallback=req.allow_commercial_fallback_once, provider_temperature=req.temperature, session_store=None, github_token=github_token, email=user.email, department=None, key_id=None)
        heartbeat("execution", "Agent execution started")
        result = await runner.run(metadata=spec.context.get("metadata", {}), instruction=req.content, history=history, requested_model=req.model, auto_commit=True, max_steps=25, user_id=user.id, department=None, key_id=None, memory_store=None, session_id=session_id)
        heartbeat("verification", "Planner/executor/verifier flow completed")
        assistant_message = result.get("summary", "Agent completed")
        _direct_chat_store.append_message(session_id, "assistant", assistant_message)
        return {"session_id": session_id, "response": assistant_message}
    _agent_jobs.start_job(job.job_id, _run_agent_job)
    return JSONResponse(status_code=202, content={"session_id": session_id, "job_id": job.job_id, "status": job.status, "phase": job.phase, "message": "Agent workflow queued."})

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
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from tokens import verify_token

log = logging.getLogger("qwen-proxy")
OLLAMA_BASE = os.environ.get("OLLAMA_BASE", "http://localhost:11434")
direct_chat_router = APIRouter(prefix="/api/chat", tags=["chat"])


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
        return await _handle_regular_chat(req, user)


async def _handle_regular_chat(
    req: ChatSendRequest,
    user: UserInfo,
):
    """Handle regular chat (non-agent mode)."""
    log.info(f"Chat message from {user.email}: {req.content[:50]}...")

    # Build OpenAI-compatible request
    body = {
        "messages": [{"role": "user", "content": req.content}],
        "model": req.model or "nemotron-3-super-120b-a12b",
        "stream": False,
    }
    if req.temperature is not None:
        body["temperature"] = req.temperature

    # Forward request directly to Ollama (bypass router to use available models)
    try:
        log.info(f"Using model {body['model']}")

        # Forward to Ollama via OpenAI-compatible /v1/chat/completions endpoint
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
            ollama_url = f"{OLLAMA_BASE}/v1/chat/completions"
            response = await client.post(
                ollama_url,
                json=body,
                headers={"Content-Type": "application/json"},
            )

        if response.status_code >= 400:
            log.error(f"Ollama error {response.status_code}: {response.text}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"LLM provider error: {response.text}"
            )

        ollama_data = response.json()
        assistant_message = ollama_data["choices"][0]["message"]["content"]

        return JSONResponse(content={
            "session_id": req.session_id or "temp",
            "response": assistant_message,
        })
    except httpx.ConnectError as e:
        log.error(f"Chat connection error: {e}")
        raise HTTPException(status_code=503, detail="LLM backend unreachable")
    except Exception as e:
        log.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _handle_agent_mode(
    req: ChatSendRequest,
    user: UserInfo,
    request: Request,
):
    """Handle agent mode: run an agent loop to perform the instruction."""
    log.info(f"Agent mode chat from {user.email}: {req.content[:50]}...")

    # Fetch GitHub token for the user
    github_token = await _get_github_token_for_user(user.email)
    if not github_token:
        log.warning(f"No GitHub token found for user {user.email}")
        # We can still run the agent without GitHub token for local operations

    try:
        # Import agent components here to avoid circular imports and speed up regular chat
        from agent.loop import AgentRunner
        from agent.tools import WorkspaceTools
        from agent.context_manager import ContextManager
        from agent.models import AgentPlan
        from agent.user_memory import UserMemoryStore
        from agent.state import AgentSessionStore
        from agent.github_tools import GitHubTools
        import tempfile
        import shutil
        from pathlib import Path

        # Set up workspace root (temporary directory for this agent run)
        workspace_root = Path(tempfile.mkdtemp(prefix="agent_workspace_"))
        log.info(f"Agent workspace: {workspace_root}")

        # Initialize AgentRunner
        runner = AgentRunner(
            ollama_base=OLLAMA_BASE,
            workspace_root=str(workspace_root),
            provider_headers={},  # We don't have extra headers for now
            provider_chain=[],    # We'll use the default Ollama model
            allow_commercial_fallback=False,
            provider_temperature=req.temperature,
            session_store=None,   # We don't have a session store for agent in direct chat
            github_token=github_token,
            email=user.email,
            department=None,      # We don't have department info in JWT
            key_id=None,          # We don't have key_id in JWT
        )

        # Prepare instruction and history
        instruction = req.content
        history = []  # We don't have chat history in direct chat yet
        requested_model = req.model
        auto_commit = True
        max_steps = 10
        user_id = user.id
        department = None
        key_id = None
        memory_store = None
        session_id = req.session_id or str(uuid.uuid4())

        # Run the agent loop
        result = await runner.run(
            instruction=instruction,
            history=history,
            requested_model=requested_model,
            auto_commit=auto_commit,
            max_steps=max_steps,
            user_id=user_id,
            department=department,
            key_id=key_id,
            memory_store=memory_store,
            session_id=session_id,
        )

        # Clean up workspace
        shutil.rmtree(workspace_root, ignore_errors=True)

        # Return the result
        return JSONResponse(content={
            "session_id": session_id,
            "response": result.get("summary", "Agent completed"),
            "agent_result": result,
        })
    except Exception as e:
        log.error(f"Agent mode error: {e}")
        # Clean up workspace on error
        if 'workspace_root' in locals():
            shutil.rmtree(workspace_root, ignore_errors=True)
        raise HTTPException(status_code=500, detail=str(e))


@direct_chat_router.get("/sessions")
async def list_chat_sessions(
    user: Annotated[UserInfo, Depends(_get_current_user)],
):
    """List chat sessions for current user."""
    return {"sessions": [], "total": 0}


@direct_chat_router.get("/sessions/{session_id}")
async def get_chat_session(
    session_id: str,
    user: Annotated[UserInfo, Depends(_get_current_user)],
):
    """Get a specific chat session."""
    return {"session_id": session_id, "messages": []}


@direct_chat_router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    user: Annotated[UserInfo, Depends(_get_current_user)],
):
    """Delete a chat session."""
    return {"deleted": True, "session_id": session_id}

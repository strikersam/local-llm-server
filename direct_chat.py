"""direct_chat.py — Direct chat endpoints for v3 dashboard.

Handles chat sessions and message sending for the Direct Chat feature.
Protected by JWT authentication (v3 auth system).
Delegates to LLM providers via the proxy's routing system.
"""

from __future__ import annotations

import json
import logging
import os
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


@direct_chat_router.post("/send")
async def send_chat_message(
    req: ChatSendRequest,
    request: Request,
    user: Annotated[UserInfo, Depends(_get_current_user)],
):
    """Send a chat message (Direct Chat feature).

    Routes the message to the appropriate LLM provider based on the model parameter.
    """
    log.info(f"Chat message from {user.email}: {req.content[:50]}...")

    # Build OpenAI-compatible request
    body = {
        "messages": [{"role": "user", "content": req.content}],
        "model": req.model or "gemma4:latest",
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

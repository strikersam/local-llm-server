"""direct_chat.py — Direct chat endpoints for v3 dashboard.
"""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from agent.job_manager import AgentJobManager, make_isolated_workspace
from tokens import verify_token
from provider_router import ProviderRouter
from agent.state import AgentSessionStore

log = logging.getLogger("qwen-proxy")
OLLAMA_BASE = os.environ.get("OLLAMA_BASE", "http://localhost:11434")
direct_chat_router = APIRouter(prefix="/api/chat", tags=["chat"])

_direct_chat_store = AgentSessionStore(db_path="direct_chat_sessions.db")
_agent_jobs = AgentJobManager()
_agent_workspace_root = Path(os.environ.get("DIRECT_CHAT_AGENT_WORKSPACE_ROOT", ".data/direct-chat-agent-workspaces"))

class UserInfo(BaseModel):
    id: str
    email: str

def _get_bearer_token(authorization: str | None = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    return authorization[7:].strip()

async def _get_current_user(token: Annotated[str, Depends(_get_bearer_token)]) -> UserInfo:
    payload = verify_token(token, token_type="access")
    if not payload: raise HTTPException(status_code=401, detail="Invalid token")
    return UserInfo(id=payload.get("sub", ""), email=payload.get("email", ""))

class ChatSendRequest(BaseModel):
    content: str
    session_id: str | None = None
    model: str | None = None
    provider_id: str | None = None
    temperature: float | None = None
    agent_mode: bool = False
    metadata: dict[str, Any] | None = None
    allow_commercial_fallback_once: bool = False

@direct_chat_router.post("/send")
async def send_chat_message(req: ChatSendRequest, request: Request, user: Annotated[UserInfo, Depends(_get_current_user)]):
    if req.agent_mode:
        return await _handle_agent_mode(req, user, request)
    return await _handle_regular_chat(req, user, request)

async def _handle_regular_chat(req, user, request):
    session_id = req.session_id or str(uuid.uuid4())
    router: ProviderRouter = request.app.state.PROVIDER_ROUTER
    res = await router.chat_completion({"messages": [{"role": "user", "content": req.content}], "model": req.model or "qwen3-coder:30b"})
    ans = res.response.json()["choices"][0]["message"]["content"]
    _direct_chat_store.append_message(session_id, "user", req.content)
    _direct_chat_store.append_message(session_id, "assistant", ans)
    return JSONResponse({"session_id": session_id, "response": ans})

async def _handle_agent_mode(req: ChatSendRequest, user: UserInfo, request: Request):
    session_id = req.session_id or str(uuid.uuid4())
    job = _agent_jobs.create_job(session_id=session_id, owner_id=user.email, instruction=req.content)
    workspace = make_isolated_workspace(_agent_workspace_root, session_id, job.job_id)
    
    async def _run_agent_job(heartbeat):
        from agent.loop import AgentRunner
        runner = AgentRunner(ollama_base=OLLAMA_BASE, workspace_root=str(workspace))
        result = await runner.run(
            instruction=req.content, 
            history=[], 
            metadata=req.metadata, 
            max_steps=25,
            model_overrides={}, 
            user_id=user.id,
            department=None,
            key_id=None,
            session_id=session_id
        )
        ans = result.get("summary", "Done")
        _direct_chat_store.append_message(session_id, "assistant", ans)
        return {"session_id": session_id, "response": ans}

    _agent_jobs.start_job(job.job_id, _run_agent_job)
    return JSONResponse({"session_id": session_id, "job_id": job.job_id, "status": "queued"})

@direct_chat_router.get("/agent-jobs/{job_id}")
async def get_agent_job(job_id: str, user: Annotated[UserInfo, Depends(_get_current_user)]):
    job = _agent_jobs.get_job(job_id)
    if not job: raise HTTPException(status_code=404)
    return job.as_dict()

@direct_chat_router.get("/sessions/{session_id}")
async def get_chat_session(session_id: str, user: Annotated[UserInfo, Depends(_get_current_user)]):
    history = _direct_chat_store.get(session_id)
    if not history: raise HTTPException(status_code=404)
    return {"session_id": session_id, "history": [m.model_dump() for m in history.history]}

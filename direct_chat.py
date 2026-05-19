from __future__ import annotations
from agent.user_memory import UserMemoryStore
"""direct_chat.py — Direct chat endpoints for v3 dashboard.

Handles chat sessions and message sending for the Direct Chat feature.
Protected by JWT authentication (v3 auth system).
Delegates to LLM providers via the proxy's routing system.
"""


import asyncio
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
from agent.intent import detect_intent, INTENT_EXECUTION, INTENT_CLARIFY, INTENT_ANALYSIS, INTENT_CONVERSATION
from agent.doctor import DirectChatDoctor, translate_error_to_conversational
from agent.schemas import DirectChatState
from tokens import verify_token
from provider_router import ProviderRouter
from runtimes.adapters.internal_agent import InternalAgentAdapter
from runtimes.base import TaskSpec
from agent.models import ResumeRequest

log = logging.getLogger("qwen-proxy")
OLLAMA_BASE = os.environ.get("OLLAMA_BASE", "http://localhost:11434")
direct_chat_router = APIRouter(prefix="/api/chat", tags=["chat"])

# Session store for direct chat
from agent.state import AgentSessionStore
_direct_chat_store = AgentSessionStore(db_path="direct_chat_sessions.db")
_agent_jobs = AgentJobManager()


def get_agent_job_manager() -> AgentJobManager:
    """Public accessor for the module-level AgentJobManager singleton."""
    return _agent_jobs
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


class AgentEventModel(BaseModel):
    """Tool-call event shape consumed by ToolCallViewer.jsx.

    ToolCallViewer reads call.tool_name, call.status, call.input, call.output,
    and call.id — the old field names (tool/args/result) are preserved as
    aliases for backward compatibility.
    """
    id: str | None = None
    type: str
    # ToolCallViewer fields
    tool_name: str | None = None
    status: str | None = None
    input: dict | None = None
    output: str | None = None
    # legacy/extra fields kept for other consumers
    tool: str | None = None
    args: dict | None = None
    result: str | None = None
    message: str | None = None


class AgentJobModel(BaseModel):
    job_id: str
    status: str
    phase: str
    progress_events: list[dict]


class AgentStatusResponse(BaseModel):
    has_events: bool
    agents: list[AgentJobModel]
    tool_calls: list[AgentEventModel]
    latest_summary: str
    latest_error: str
    state: DirectChatState | None = None
    humanized_progress: str | None = None


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
    repo_url: str | None = None
    repo_ref: str | None = None


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
    """Detect simple greetings/replies to avoid unnecessary agent promotion."""
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
    # Short messages that mention git/PR ops are non-trivial regardless of word count.
    _git_multi_word = ("pull request", "pull requests", "code review")
    _git_keywords = {
        "pr", "prs", "commit", "commits", "push", "clone", "branch", "branches",
        "repo", "repos", "repository", "git", "merge", "diff", "patch",
        "file", "files", "code", "write", "create", "fix", "build", "run",
        "edit", "generate", "deploy", "implement", "refactor", "analyze",
        "analyse", "audit", "investigate", "explain", "review",
    }
    word_tokens = {w.strip(".,!?;:()[]{}\"'").lower() for w in stripped.split()}
    if any(phrase in lowered for phrase in _git_multi_word) or (word_tokens & _git_keywords):
        return False
    if len(words) <= 4:
        return True
    if lowered.endswith("?") and len(words) <= 12:
        return True
    return False


@direct_chat_router.post("/send")
async def send_chat_message(
    req: ChatSendRequest,
    request: Request,
    user: Annotated[UserInfo, Depends(_get_current_user)],
):
    """Unified orchestration entry point for all direct chat messages."""

    # 1. Intent Detection
    intent = detect_intent(req.content)
    session_id = req.session_id or str(uuid.uuid4())
    _ensure_session(session_id, user)

    # 2. Sticky Context Recovery
    session = _direct_chat_store.get(session_id)
    if not req.repo_url and session and session.repo_url:
        req.repo_url = session.repo_url
        log.info(f"Restored sticky repo context: {req.repo_url}")
    if not req.repo_ref and session and session.repo_ref:
        req.repo_ref = session.repo_ref

    # 3. Handle Special Intents
    if intent == INTENT_CLARIFY:
        msg = "I can definitely help with that, but could you please provide a bit more detail on what exactly you'd like me to change or fix? I want to make sure I have all the context before I start."
        _direct_chat_store.append_message(session_id, "user", req.content)
        _direct_chat_store.append_message(session_id, "assistant", msg)
        return JSONResponse(content={"session_id": session_id, "response": msg, "intent": intent, "state": DirectChatState.NEEDS_INPUT})

    # 4. Auto-promotion to Execution Flow
    # We promote if intent is execution/analysis, unless explicitly disabled or trivial
    is_technical = intent in (INTENT_EXECUTION, INTENT_ANALYSIS)
    is_trivial = _is_trivial_message(req.content)

    should_execute = (req.agent_mode or is_technical) and not (is_trivial and not req.agent_mode)

    if should_execute:
        return await _handle_agent_mode(req, user, request, session_id, intent)
    else:
        return await _handle_regular_chat(req, user, request, session_id)


async def _handle_regular_chat(
    req: ChatSendRequest,
    user: UserInfo,
    request: Request,
    session_id: str,
):
    log.info(f"Chat message from {user.email}: {req.content[:50]}...")
    history = _session_history(session_id)

    system_prompt = (
        "You are a helpful coding assistant integrated with a self-hosted AI proxy server. "
        "You can answer questions about code, explain concepts, review snippets, and assist "
        "with software engineering tasks. "
        "For tasks that require reading or editing files in a GitHub repository "
        "(e.g. opening PRs, committing changes, browsing repo contents), I will automatically "
        "detect your intent and start an execution workflow. "
        "Never refuse to help; always guide the user toward the right approach."
    )
    payload = {
        "messages": [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": req.content}],
        "model": req.model or "nvidia/nemotron-3-super-120b-a12b",
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
        if not hasattr(result, "response"):
            log.error(f"Provider response object missing response: {type(result)}")
            raise HTTPException(status_code=500, detail="Invalid provider response format")
        assistant_message = result.response.json()["choices"][0]["message"]["content"]
        _direct_chat_store.append_message(session_id, "user", req.content)
        _direct_chat_store.append_message(session_id, "assistant", assistant_message)
        return JSONResponse(content={
            "session_id": session_id,
            "response": assistant_message,
            "state": DirectChatState.ASSISTANT_REPLY
        })
    except Exception as e:
        log.error(f"Failed to get provider response: {e}")
        raise HTTPException(status_code=500, detail="Failed to get provider response")

async def _handle_agent_mode(
    req: ChatSendRequest,
    user: UserInfo,
    request: Request,
    session_id: str,
    intent: str,
):
    try:
        return await _do_handle_agent_mode(req, user, request, session_id, intent)
    except HTTPException as he:
        if he.status_code == 412:
            msg = translate_error_to_conversational(he.detail)
            _direct_chat_store.append_message(session_id, "assistant", msg)

            if os.environ.get("DIRECT_CHAT_STRICT_PREFLIGHT") == "true":
                return JSONResponse(status_code=412, content={"detail": he.detail})

            return JSONResponse(status_code=200, content={
                "session_id": session_id,
                "response": msg,
                "preflight_failed": True,
                "detail": he.detail,
                "state": DirectChatState.FAILED_WITH_FIX_HINT
            })
        raise
    except Exception as e:
        log.exception("Agent mode failed")
        raise

async def _do_handle_agent_mode(
    req: ChatSendRequest,
    user: UserInfo,
    request: Request,
    session_id: str,
    intent: str,
):
    log.info(f"Execution flow for {user.email}: {req.content[:50]}...")
    history = _session_history(session_id)
    
    # Persist context
    if req.repo_url or req.repo_ref:
        _direct_chat_store.update_repo_context(session_id, req.repo_url, req.repo_ref)
    _direct_chat_store.update_task_context(session_id, objective=req.content)

    # Preflight
    ws_mgr = request.app.state.webui_workspaces
    if req.repo_url:
        validation = await ws_mgr.validate_repo_ref(req.repo_url, req.repo_ref)
        if not validation["ok"]:
            raise HTTPException(status_code=412, detail={"ready": False, "issues": validation["issues"]})

    import inspect
    _token_res = _get_github_token_for_user(user.email)
    github_token = await _token_res if inspect.isawaitable(_token_res) else _token_res

    # Preflight Doctor (cached)
    session = _direct_chat_store.get(session_id)
    preflight_passed = session.metadata.get("preflight_passed") if session and session.metadata else False
    if not preflight_passed:
        doctor = DirectChatDoctor(github_token=github_token)
        report = await doctor.check_all(repo_url=req.repo_url, repo_ref=req.repo_ref)
        if not report.ready:
            raise HTTPException(status_code=412, detail=report.model_dump())
        if session:
            new_meta = dict(session.metadata or {})
            new_meta["preflight_passed"] = True
            _direct_chat_store.update_session_metadata(session_id, new_meta)

    # Job Creation
    job = _agent_jobs.create_job(session_id=session_id, owner_id=user.email, instruction=req.content, requested_model=req.model, provider_id=req.provider_id)

    # Workspace Bootstrap
    workspace_root = None
    if req.repo_url:
        try:
            manifest = ws_mgr.create_workspace(session_id=session_id, job_id=job.job_id, repo_url=req.repo_url, repo_ref=req.repo_ref, github_token=github_token)
            workspace_root = Path(manifest.root_path)
        except Exception as e:
            log.warning(f"Bootstrap fail: {e}")
            if any(kw in str(e).lower() for kw in ("auth", "denied")):
                _direct_chat_store.append_message(session_id, "assistant", f"I hit an access issue while setting up the workspace for {req.repo_url}. Please check your token in Settings.")

    if not workspace_root:
        workspace_root = make_isolated_workspace(_agent_workspace_root, session_id, job.job_id)
    job.workspace_path = str(workspace_root)

    # Runtime Selection
    from runtimes.manager import get_runtime_manager
    runtime_mgr = get_runtime_manager()
    task_type = "repo_editing" if intent == INTENT_EXECUTION else "code_review"
    primary_runtime, _ = runtime_mgr.select_runtime(task_type)
    # We prefer the internal agent for Direct Chat due to its rich interactive features
    # but we'll respect the selected adapter if it's a specialized one.
    adapter = primary_runtime or InternalAgentAdapter(config={"workspace_root": str(workspace_root)})
    spec = TaskSpec(
        task_id=job.job_id,
        instruction=req.content,
        task_type=task_type,
        workspace_path=str(workspace_root),
        model_preference=req.model,
        timeout_sec=int(os.environ.get("DIRECT_CHAT_AGENT_TIMEOUT_SEC", "1800")),
        context={
            "conversation": history,
            "max_steps": 30,
            "owner_id": user.id,
            "user_email": user.email,
            "session_id": session_id,
            "metadata": req.metadata or {},
            "github_token": github_token,
        },
    )

    _direct_chat_store.append_message(session_id, "user", req.content)

    # Extract required state before background job starts (it may lose request context)
    app_router: ProviderRouter = request.app.state.PROVIDER_ROUTER
    sorted_providers = sorted(app_router.providers, key=lambda p: p.priority)
    primary_provider = sorted_providers[0] if sorted_providers else None
    ollama_base = primary_provider.normalized_base_url if primary_provider else OLLAMA_BASE
    primary_headers = primary_provider.auth_headers() if primary_provider and primary_provider.api_key else {}

    # Interactive Gating Helper
    async def wait_for_resume(job_id: str, session_id: str):
        """Wait for the user to resume the job via the resume endpoint."""
        while True:
            _s = _direct_chat_store.get(session_id)
            if _s and _s.resume_payload:
                payload = _s.resume_payload
                _direct_chat_store.update_resume_payload(session_id, None)
                return payload
            await asyncio.sleep(1.0)

    async def _run_agent_job(heartbeat):
        log.info(f"Background agent job starting: job_id={job.job_id} session_id={session_id}")
        try:
            return await _do_run_agent_job(heartbeat)
        except Exception as e:
            log.exception(f"Background agent job {job.job_id} failed")
            heartbeat("failed", str(e))
            return {"session_id": session_id, "error": str(e), "status": "failed"}

    async def _do_run_agent_job(heartbeat):
        from agent.loop import AgentRunner

        _spec = spec
        # If we selected a specialized external runtime, delegate to its execute() method
        if adapter.RUNTIME_ID != "internal_agent":
            heartbeat("execution", f"Dispatching task to specialized runtime: {adapter.RUNTIME_ID}")
            try:
                res = await adapter.execute(_spec)
                _direct_chat_store.append_message(session_id, "assistant", res.output)
                return {"session_id": session_id, "response": res.output}
            except Exception as e:
                log.exception(f"External runtime {adapter.RUNTIME_ID} failed")
                heartbeat("failed", str(e))
                return {"session_id": session_id, "error": str(e)}

        # Otherwise, proceed with the rich Internal Agent cognition flow
        heartbeat("planning", "Analyzing repository and creating an execution plan")

        _active_job = _agent_jobs.get_job(job.job_id)
        def _on_tool_call(tn: str, args: dict, res: Any) -> None:
            if not _active_job: return
            _active_job.progress_events.append({
                "timestamp": _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime()),
                "type": "tool_call", "phase": "execution", "tool_name": tn, "args": args, "message": f"Tool: {tn}"
            })

        import time as _time

        # Connect the selected adapter's execution logic if it's not the internal agent
        # For now, we still prefer InternalAgent for the rich interactive features
        # but we use the adapter's properties.

        runner = AgentRunner(
            ollama_base=ollama_base, workspace_root=str(workspace_root),
            provider_headers=primary_headers, provider_chain=sorted_providers[1:],
            allow_commercial_fallback=req.allow_commercial_fallback_once, provider_temperature=req.temperature,
            github_token=github_token, email=user.email, tool_callback=_on_tool_call,
        )

        # Cognition Stage: Planning
        # We use the runner to plan, which is compatible with most task types
        plan = await runner.plan(
            instruction=req.content, history=history, requested_model=req.model,
            max_steps=30, user_id=user.id, session_id=session_id, memory_store=UserMemoryStore(),
            metadata=req.metadata
        )

        # Check for risky plans that need approval
        if plan.requires_risky_review:
            heartbeat("needs_approval", f"I've created a plan, but it involves sensitive changes to security or core files. Please review and approve to proceed. Goal: {plan.goal}")
            resume_data = await wait_for_resume(job.job_id, session_id)
            if resume_data.get("action") != "approve":
                heartbeat("failed", "Task cancelled by user during approval.")
                _direct_chat_store.append_message(session_id, "assistant", "I've cancelled the task as requested.")
                return {"session_id": session_id, "status": "cancelled", "summary": "User rejected plan."}

        heartbeat("execution", "Executing planned changes")
        result = await runner.run(metadata=req.metadata or {}, instruction=req.content, history=history, requested_model=req.model, auto_commit=True, max_steps=30, user_id=user.id, session_id=session_id, memory_store=UserMemoryStore())

        heartbeat("verification", "Validating the changes and ensuring quality")
        heartbeat("completed", "Task successfully completed")

        assistant_message = result.get("summary", result.get("response", "Agent completed"))
        _direct_chat_store.append_message(session_id, "assistant", assistant_message)
        return {"session_id": session_id, "response": assistant_message, "status": "succeeded"}

    _agent_jobs.start_job(job.job_id, _run_agent_job)
    return JSONResponse(status_code=202, content={"session_id": session_id, "job_id": job.job_id, "status": job.status, "phase": job.phase, "message": "Assistant is working on your request."})


@direct_chat_router.get("/agent-status", response_model=AgentStatusResponse)
async def get_agent_status(
    request: Request,
    session_id: str | None = None,
) -> AgentStatusResponse:
    user_state = getattr(request.state, "user", None)
    if not isinstance(user_state, dict) or not user_state.get("email"):
        raise HTTPException(status_code=401, detail="Authentication required")
    owner_id: str = user_state["email"]
    all_jobs = _agent_jobs.list_jobs(session_id=session_id)
    jobs = [j for j in all_jobs if getattr(j, "owner_id", None) == owner_id]

    tool_calls: list[AgentEventModel] = []
    agents: list[AgentJobModel] = []
    latest_summary = ""
    latest_error = ""
    has_events = False

    sorted_jobs = sorted(jobs, key=lambda j: j.updated_at, reverse=True)
    current_state = DirectChatState.ASSISTANT_REPLY
    humanized_progress = ""

    if sorted_jobs:
        latest_job = sorted_jobs[0]
        current_state = _map_job_status_to_state(latest_job.status, latest_job.phase)
        last_msg = latest_job.progress_events[-1].get("message") if latest_job.progress_events else None
        humanized_progress = _humanize_phase(latest_job.phase, last_msg, latest_job.updated_at)

    for job in jobs:
        jd = job.as_dict()
        events = jd.get("progress_events") or []
        if events: has_events = True
        agents.append(AgentJobModel(job_id=jd["job_id"], status=jd["status"], phase=jd["phase"], progress_events=events))
        for idx, evt in enumerate(events):
            if evt.get("type") == "tool_call":
                tn = evt.get("tool_name") or evt.get("tool")
                tool_calls.append(AgentEventModel(
                    id=f"{jd['job_id']}-{idx}", type="tool_call", tool_name=tn,
                    status=evt.get("status") or ("error" if str(evt.get("result_preview") or "").startswith("[error") else "success" if evt.get("result_preview") else "pending"),
                    input=evt.get("args"), output=evt.get("result_preview") or evt.get("result"),
                    tool=tn, args=evt.get("args"), result=evt.get("result_preview") or evt.get("result"), message=evt.get("message")
                ))
        err = jd.get("error") or {}
        if err.get("message"): latest_error = err["message"]
        result = jd.get("result") or {}
        if result.get("response"): latest_summary = result["response"]
        elif result.get("summary"): latest_summary = result["summary"]

    return AgentStatusResponse(
        has_events=has_events, agents=agents, tool_calls=tool_calls,
        latest_summary=latest_summary, latest_error=latest_error,
        state=current_state, humanized_progress=humanized_progress
    )


@direct_chat_router.get("/agent-jobs/{job_id}")
async def get_agent_job(job_id: str):
    job = _agent_jobs.get_job(job_id)
    if not job: raise HTTPException(status_code=404, detail="Job not found")
    from agent.schemas import RunningJob, CompletedJob, FailedJob
    jd = job.as_dict()
    if job.status == "running":
        return RunningJob(job_id=jd["job_id"], session_id=jd["session_id"], status=jd["status"], phase=jd["phase"], progress_events=jd.get("progress_events", []), workspace_path=jd.get("workspace_path")).model_dump()
    elif job.status == "succeeded":
        return CompletedJob(job_id=jd["job_id"], session_id=jd["session_id"], status=jd["status"], phase=jd["phase"], final_message=jd.get("final_message"), result=jd.get("result")).model_dump()
    else:
        return FailedJob(job_id=jd["job_id"], session_id=jd["session_id"], status=jd["status"], phase=jd["phase"], error=jd.get("error") or {}).model_dump()

def _humanize_phase(phase: str, latest_event_msg: str | None = None, updated_at: str | None = None) -> str:
    mapping = {
        "starting": "Preparing your workspace",
        "planning": "Analyzing the repository and creating an execution plan",
        "execution": "Executing the planned changes",
        "verification": "Validating the changes and ensuring quality",
        "completed": "Task successfully completed",
        "failed": "I encountered an issue while working on the task",
        "cancelled": "The task was cancelled",
        "queued": "Waiting to start in the background",
    }
    is_slow = False
    if updated_at:
        try:
            from datetime import datetime, timezone
            last_upd = datetime.strptime(updated_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - last_upd).total_seconds() > 30: is_slow = True
        except Exception: pass

    base = mapping.get(phase, phase.capitalize())
    if latest_event_msg and phase == "execution" and "Tool: " in latest_event_msg:
        tool = latest_event_msg.replace("Tool: ", "")
        tool_mapping = {
            "read_file": "Reading relevant source files", "write_file": "Applying code modifications",
            "apply_diff": "Integrating the suggested fixes", "list_files": "Inspecting the repository structure",
            "search_code": "Searching the codebase for context", "run_command": "Running validation commands and tests",
            "github_open_pull_request": "Preparing and opening a pull request", "git_commit": "Committing the changes to the branch",
        }
        base = tool_mapping.get(tool, f"Working with {tool}")
    return f"Still {base.lower()}..." if is_slow and phase not in ("completed", "failed", "cancelled") else base

def _map_job_status_to_state(status: str, phase: str) -> DirectChatState:
    if phase == "needs_approval": return DirectChatState.NEEDS_APPROVAL
    if phase == "needs_input": return DirectChatState.NEEDS_INPUT
    if status == "running": return DirectChatState.WORKING
    if status == "succeeded": return DirectChatState.COMPLETED
    if status == "failed": return DirectChatState.FAILED_WITH_FIX_HINT
    return DirectChatState.WORKING

@direct_chat_router.post("/resume/{session_id}")
async def resume_chat_job(
    session_id: str,
    req: ResumeRequest,
    user: Annotated[UserInfo, Depends(_get_current_user)],
):
    """Resume a paused agent job with user input/action."""
    session = _direct_chat_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Store resume payload in session; the background job is polling for this
    _direct_chat_store.update_resume_payload(session_id, req.model_dump())

    # Also log the user's response in history for continuity
    msg = f"Action: {req.action}"
    if req.input: msg += f" - Input: {req.input}"
    _direct_chat_store.append_message(session_id, "user", msg)

    return {"status": "resumed", "session_id": session_id}

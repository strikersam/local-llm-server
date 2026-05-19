from __future__ import annotations
from agent.user_memory import UserMemoryStore
"""direct_chat.py — Direct chat endpoints for v3 dashboard.

Handles chat sessions and message sending for the Direct Chat feature.
Protected by JWT authentication (v3 auth system).
Delegates to LLM providers via the proxy's routing system.
"""


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
from agent.intent import detect_intent, INTENT_EXECUTION
from agent.doctor import DirectChatDoctor, translate_error_to_conversational
from agent.schemas import DirectChatState
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
    # Use token-based matching to avoid false positives ("pr" in "april", "run" in "return").
    _git_multi_word = ("pull request", "pull requests", "code review")
    _git_keywords = {
        "pr", "prs", "commit", "commits", "push", "clone", "branch", "branches",
        "repo", "repos", "repository", "git", "merge", "diff", "patch",
        "file", "files", "code", "write", "create", "fix", "build", "run",
        "edit", "generate", "deploy", "implement", "refactor",
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
    # Auto-detect intent to promote to agent mode if execution is required
    intent = detect_intent(req.content)
    if intent == INTENT_EXECUTION and not req.agent_mode:
        log.info(f"Execution intent detected for '{req.content[:50]}...', promoting to agent mode.")
        req.agent_mode = True

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
    try:
        return await _do_handle_agent_mode(req, user, request)
    except HTTPException as he:
        if he.status_code == 412:
            # Recovery: convert preflight failure into conversational assistant message
            msg = translate_error_to_conversational(he.detail)
            target_session_id = req.session_id or str(uuid.uuid4())
            _ensure_session(target_session_id, user)
            _direct_chat_store.append_message(target_session_id, "assistant", msg)

            # For backward compatibility with legacy tests, we return 412 wrapped in detail if requested
            if os.environ.get("DIRECT_CHAT_STRICT_PREFLIGHT") == "true":
                return JSONResponse(status_code=412, content={"detail": he.detail})

            return JSONResponse(status_code=200, content={
                "session_id": target_session_id,
                "response": msg,
                "preflight_failed": True,
                "detail": he.detail
            })
        raise
    except Exception as e:
        log.exception("Agent mode failed")
        raise

async def _do_handle_agent_mode(
    req: ChatSendRequest,
    user: UserInfo,
    request: Request,
):
    """
    Initiates and queues an agent-mode workflow for a direct chat message, performing repository and GitHub preflight checks before starting an asynchronous job.
    
    Performs:
    - repo_ref validation via the workspace manager,
    - optional Git/GitHub checks when the prompt suggests repository operations (missing token, missing git binary, repo/ref/path access, GitHub token validity and scopes),
    - readiness check using an internal agent adapter,
    - job creation, isolated workspace setup, and asynchronous agent execution.
    
    Parameters:
        req (ChatSendRequest): Incoming chat request including content, agent_mode controls, repo metadata, and provider/model hints.
        user (UserInfo): Authenticated user information (id and email) used for ownership and lookup.
        request (Request): FastAPI request object; used to access application state (workspaces, provider router).
    
    Returns:
        JSONResponse: HTTP 202 response containing an AcceptedJob envelope with `session_id`, `job_id`, `status`, `phase`, and `message` when the agent job is successfully queued.
    
    Raises:
        HTTPException(412): If workspace repo validation fails, if Git/GitHub preflight issues are detected (returns structured `issues`), or if the adapter readiness check reports not ready.
        HTTPException(404/500/etc.): Propagated for other unexpected failures from downstream components.
    """
    log.info(f"Agent mode chat from {user.email}: {req.content[:50]}...")
    session_id = req.session_id
    if session_id:
        history = _session_history(session_id)
        session = _direct_chat_store.get(session_id)
        if session:
            # Sticky context: reuse repo_url/repo_ref if not provided in request
            if not req.repo_url:
                req.repo_url = session.repo_url
            if not req.repo_ref:
                req.repo_ref = session.repo_ref
    else:
        session_id = str(uuid.uuid4())
        history = []

    # Persist current repo context in session
    if req.repo_url or req.repo_ref:
        _ensure_session(session_id, user)
        _direct_chat_store.update_repo_context(session_id, req.repo_url, req.repo_ref)

    # Preflight validation for repo_ref/repo_url
    ws_mgr = request.app.state.webui_workspaces
    validation = await ws_mgr.validate_repo_ref(req.repo_url, req.repo_ref)
    if not validation["ok"]:
        raise HTTPException(status_code=412, detail={"ready": False, "issues": validation["issues"]})

    _ensure_session(session_id, user)
    _direct_chat_store.append_message(session_id, "user", req.content)
    # Accept sync or async _get_github_token_for_user implementations (tests patch a sync lambda)
    import inspect
    _token_res = _get_github_token_for_user(user.email)
    if inspect.isawaitable(_token_res):
        github_token = await _token_res
    else:
        github_token = _token_res

    # Centralized Doctor-based preflight: only for prompts that appear to require repo/git access
    lc = req.content.lower()
    repo_keywords = ("repo", "git", "pull request", "pull-request", "pr", "commit", "push", "clone", "checkout", "branch")
    if any(kw in lc for kw in repo_keywords) or req.repo_url:
        doctor = DirectChatDoctor(github_token=github_token)
        report = await doctor.check_all(repo_url=req.repo_url, repo_ref=req.repo_ref)
        if not report.ready:
            raise HTTPException(status_code=412, detail=report.model_dump())

    job = _agent_jobs.create_job(session_id=session_id, owner_id=user.email, instruction=req.content, requested_model=req.model, provider_id=req.provider_id)

    # Auto-bootstrap workspace using WorkspaceManager if a repo is present
    workspace_root = None
    if req.repo_url:
        try:
            ws_mgr = request.app.state.webui_workspaces
            # Check if we can reuse an existing workspace for this session/repo
            # For now, create a new isolated one for the job to ensure clean state
            manifest = ws_mgr.create_workspace(
                session_id=session_id,
                job_id=job.job_id,
                repo_url=req.repo_url,
                repo_ref=req.repo_ref,
                github_token=github_token
            )
            workspace_root = Path(manifest.root_path)
            log.info(f"Auto-bootstrapped workspace for {req.repo_url} at {workspace_root}")
        except Exception as e:
            log.warning(f"Failed to auto-bootstrap repo workspace: {e}, falling back to local isolated workspace")

    if not workspace_root:
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
            "max_steps": 30,
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

        # Emit each tool call into the job's progress_events so the Live Agent
        # Workspace panel can display them via GET /api/chat/agent-status.
        import time as _time
        _active_job = _agent_jobs.get_job(job.job_id)

        def _on_tool_call(tool_name: str, tool_args: dict, tool_result: Any) -> None:
            if _active_job is None:
                return
            result_preview = str(tool_result)[:200] if tool_result is not None else ""
            _active_job.progress_events.append({
                "timestamp": _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime()),
                "type": "tool_call",
                "phase": "execution",
                "tool_name": tool_name,
                "args": {k: str(v)[:100] for k, v in (tool_args or {}).items()},
                "result_preview": result_preview,
                "message": f"Tool: {tool_name}",
            })

        runner = AgentRunner(
            ollama_base=ollama_base,
            workspace_root=str(workspace_root),
            provider_headers=primary_headers,
            provider_chain=sorted_providers[1:],
            allow_commercial_fallback=req.allow_commercial_fallback_once,
            provider_temperature=req.temperature,
            session_store=None,
            github_token=github_token,
            email=user.email,
            department=None,
            key_id=None,
            mcp_base_url=os.environ.get("MCP_SERVER_BASE_URL"),
            tool_callback=_on_tool_call,
        )
        heartbeat("execution", "Agent execution started")
        result = await runner.run(metadata=spec.context.get("metadata", {}), instruction=req.content, history=history, requested_model=req.model, auto_commit=True, max_steps=30, user_id=user.id, department=None, key_id=None, memory_store=UserMemoryStore(), session_id=session_id)
        heartbeat("verification", "Planner/executor/verifier flow completed")
        assistant_message = result.get("summary", "Agent completed")
        _direct_chat_store.append_message(session_id, "assistant", assistant_message)
        return {"session_id": session_id, "response": assistant_message}
    _agent_jobs.start_job(job.job_id, _run_agent_job)

    # Return a typed accepted job envelope — transport-level acknowledgement only.
    from agent.schemas import AcceptedJob
    accepted = AcceptedJob(
        session_id=session_id,
        job_id=job.job_id,
        status=job.status,
        phase=job.phase,
        message="Agent workflow queued.",
    )
    return JSONResponse(status_code=202, content=accepted.model_dump())


@direct_chat_router.get("/agent-status", response_model=AgentStatusResponse)
async def get_agent_status(
    request: Request,
    session_id: str | None = None,
) -> AgentStatusResponse:
    """Live agent workspace snapshot consumed by the Chat UI's Live Agent Workspace panel.

    The frontend polls GET /api/chat/agent-status?session_id=<id> every 2 s via
    fetchAgentWorkspaceSnapshot().  Without this endpoint the request 404s,
    fetchAgentWorkspaceSnapshot throws, and the UI stays in 'reconnecting' state
    with '0 total' tool calls forever.

    Results are scoped to the authenticated caller's jobs only.
    """
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

    # Sort jobs by updated_at to get the most recent one's state
    sorted_jobs = sorted(jobs, key=lambda j: j.updated_at, reverse=True)

    current_state = DirectChatState.ASSISTANT_REPLY
    humanized_progress = ""

    if sorted_jobs:
        latest_job = sorted_jobs[0]
        current_state = _map_job_status_to_state(latest_job.status, latest_job.phase)
        last_msg = latest_job.progress_events[-1].get("message") if latest_job.progress_events else None
        humanized_progress = _humanize_phase(latest_job.phase, last_msg)

    for job in jobs:
        jd = job.as_dict()
        events = jd.get("progress_events") or []
        if events:
            has_events = True
        agents.append(AgentJobModel(
            job_id=jd["job_id"],
            status=jd["status"],
            phase=jd["phase"],
            progress_events=events,
        ))
        for idx, evt in enumerate(events):
            if evt.get("type") == "tool_call":
                tool_name = evt.get("tool_name") or evt.get("tool")
                tool_calls.append(AgentEventModel(
                    id=f"{jd['job_id']}-{idx}",
                    type="tool_call",
                    # ToolCallViewer-required fields
                    tool_name=tool_name,
                    status=evt.get("status") or (
                        "error" if str(evt.get("result_preview") or evt.get("result") or "").startswith("[error")
                        else "success" if evt.get("result_preview") or evt.get("result")
                        else "pending"
                    ),
                    input=evt.get("args"),
                    output=evt.get("result_preview") or evt.get("result"),
                    # legacy fields
                    tool=tool_name,
                    args=evt.get("args"),
                    result=evt.get("result_preview") or evt.get("result"),
                    message=evt.get("message"),
                ))
        err = jd.get("error") or {}
        if err.get("message"):
            latest_error = err["message"]
        result = jd.get("result") or {}
        if result.get("response"):
            latest_summary = result["response"]
        elif result.get("summary"):
            latest_summary = result["summary"]

    return AgentStatusResponse(
        has_events=has_events,
        agents=agents,
        tool_calls=tool_calls,
        latest_summary=latest_summary,
        latest_error=latest_error,
        state=current_state,
        humanized_progress=humanized_progress,
    )


@direct_chat_router.get("/agent-jobs/{job_id}")
async def get_agent_job(job_id: str):
    """
    Retrieve a typed representation of an agent job by its job ID.
    
    Raises an HTTP 404 if the job does not exist. Depending on the job's status, returns a dictionary matching one of the agent job schemas:
    - For a running job: keys include `job_id`, `session_id`, `status`, `phase`, `progress_events`, and `workspace_path`.
    - For a succeeded job: keys include `job_id`, `session_id`, `status`, `phase`, `final_message`, and `result`.
    - For any other status: keys include `job_id`, `session_id`, `status`, `phase`, and `error` (an object, empty if absent).
    
    Parameters:
        job_id (str): The unique identifier of the agent job.
    
    Returns:
        dict: A serialized job representation matching `RunningJob`, `CompletedJob`, or `FailedJob` schema depending on job status.
    """
    job = _agent_jobs.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    from agent.schemas import RunningJob, CompletedJob, FailedJob
    jd = job.as_dict()
    if job.status == "running":
        running = RunningJob(
            job_id=jd["job_id"],
            session_id=jd["session_id"],
            status=jd["status"],
            phase=jd["phase"],
            progress_events=jd.get("progress_events", []),
            workspace_path=jd.get("workspace_path"),
        )
        return running.model_dump()
    elif job.status == "succeeded":
        completed = CompletedJob(
            job_id=jd["job_id"],
            session_id=jd["session_id"],
            status=jd["status"],
            phase=jd["phase"],
            final_message=jd.get("final_message"),
            result=jd.get("result"),
        )
        return completed.model_dump()
    else:
        failed = FailedJob(
            job_id=jd["job_id"],
            session_id=jd["session_id"],
            status=jd["status"],
            phase=jd["phase"],
            error=jd.get("error") or {},
        )
        return failed.model_dump()

def _humanize_phase(phase: str, latest_event_msg: str | None = None) -> str:
    """Convert technical job phases into friendly conversational progress."""
    mapping = {
        "starting": "Preparing workspace",
        "planning": "Creating a plan",
        "execution": "Working on tasks",
        "verification": "Verifying changes",
        "completed": "Task completed",
        "failed": "I encountered an issue",
        "cancelled": "Task cancelled",
        "queued": "Waiting to start",
    }
    base = mapping.get(phase, phase.capitalize())
    if latest_event_msg and phase == "execution":
        # If it's a tool call, we can be more specific
        if "Tool: " in latest_event_msg:
            tool = latest_event_msg.replace("Tool: ", "")
            tool_mapping = {
                "read_file": "Reading files",
                "write_file": "Editing files",
                "apply_diff": "Applying changes",
                "list_files": "Inspecting repository",
                "search_code": "Searching codebase",
                "run_command": "Running commands/tests",
                "github_open_pull_request": "Opening pull request",
                "git_commit": "Committing changes",
            }
            return tool_mapping.get(tool, f"Running {tool}")
    return base

def _map_job_status_to_state(status: str, phase: str) -> DirectChatState:
    if status == "running":
        return DirectChatState.WORKING
    if status == "succeeded":
        return DirectChatState.COMPLETED
    if status == "failed":
        return DirectChatState.FAILED_WITH_FIX_HINT
    return DirectChatState.WORKING

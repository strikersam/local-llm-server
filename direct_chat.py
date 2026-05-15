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


class AgentEventModel(BaseModel):
    type: str
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
    """
    Initiates and queues an agent-mode workflow for a direct chat message, performing repository and GitHub preflight checks before starting an asynchronous job.
    
    Performs:
    - repo_ref validation via the workspace manager,
    - optional Git/GitHub checks when the prompt suggests repository operations (missing token, missing git binary, repo/ref/path access, GitHub token validity and scopes),
    - readiness check using an internal agent adapter,
    - job creation, isolated workspace setup, and asynchronous agent execution.
    
    Parameters:
        req (ChatSendRequest): Incoming chat request including content, agent_mode controls, repo metadata, and provider/model hints.
        user (UserInfo): Authenticated user information (id and email) used for ownership and token lookup.
        request (Request): FastAPI request object; used to access application state (workspaces, provider router).
    
    Returns:
        JSONResponse: HTTP 202 response containing an AcceptedJob envelope with `session_id`, `job_id`, `status`, `phase`, and `message` when the agent job is successfully queued.
    
    Raises:
        HTTPException(412): If workspace repo validation fails, if Git/GitHub preflight issues are detected (returns structured `issues`), or if the adapter readiness check reports not ready.
        HTTPException(404/500/etc.): Propagated for other unexpected failures from downstream components.
    """
    log.info(f"Agent mode chat from {user.email}: {req.content[:50]}...")
    session_id = req.session_id
    if session_id: history = _session_history(session_id)
    else:
        session_id = str(uuid.uuid4())
        history = []
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

    # GitHub preflight: for prompts that appear to require repo/git access, ensure
    # a token and git binary are available and provide structured actionable errors
    # rather than letting the job enter a vague failing state.
    import shutil
    import httpx
    lc = req.content.lower()
    repo_keywords = ("repo", "git", "pull request", "pull-request", "pr", "commit", "push", "clone", "checkout", "branch")
    if any(kw in lc for kw in repo_keywords):
        issues = []
        if not github_token:
            issues.append({
                "code": "missing_github_token",
                "message": "No GitHub token available for this user.",
                "fix_hint": "Add a GitHub token in Settings or set GH_TOKEN/GITHUB_TOKEN.",
            })
        # Validate git binary
        if not shutil.which("git"):
            issues.append({
                "code": "missing_git_binary",
                "message": "'git' binary not found on PATH.",
                "fix_hint": "Install git and ensure it is on PATH.",
            })

        # If metadata provides an explicit repo_url, attempt a non-destructive access check
        repo_url = None
        try:
            if req.metadata and isinstance(req.metadata, dict):
                repo_url = req.metadata.get("repo_url") or req.metadata.get("repository")
        except Exception:
            repo_url = None

        if repo_url:
            try:
                from workspace.manager import WorkspaceManager
                mgr = WorkspaceManager()
                pre = mgr.repo_access_preflight(repo_url, github_token)
                if not pre.get("ok"):
                    issues.append({
                        "code": "git_repo_access",
                        "message": f"Could not access repository at {repo_url}.",
                        "fix_hint": "Verify the repository URL and ensure the GitHub token has access; ensure network egress to git hosts.",
                        "details": {"error": pre.get("error")},
                    })
                # Branch/ref validation if provided in metadata
                repo_ref = None
                try:
                    repo_ref = req.metadata.get("repo_ref") or req.metadata.get("branch") or req.metadata.get("ref") if req.metadata and isinstance(req.metadata, dict) else None
                except Exception:
                    repo_ref = None
                if repo_ref:
                    ref_check = mgr.validate_repo_ref(repo_url, repo_ref, github_token)
                    if not ref_check.get("ok"):
                        issues.append({
                            "code": "git_repo_ref",
                            "message": f"Could not find ref/branch '{repo_ref}' in repository {repo_url}.",
                            "fix_hint": "Verify the branch/ref name and that the token has repo access.",
                            "details": {"error": ref_check.get("error")},
                        })
                # Path validation if provided
                repo_path = None
                try:
                    repo_path = req.metadata.get("repo_path") or req.metadata.get("path") if req.metadata and isinstance(req.metadata, dict) else None
                except Exception:
                    repo_path = None
                if repo_path:
                    path_check = mgr.validate_repo_path(repo_url, repo_ref or "HEAD", repo_path, github_token)
                    if not path_check.get("ok"):
                        issues.append({
                            "code": "git_repo_path",
                            "message": f"Could not find path '{repo_path}' at ref '{repo_ref or 'HEAD'}' in repository {repo_url}.",
                            "fix_hint": "Verify path and ref; note path checks are GitHub-only unless host supports remote APIs.",
                            "details": {"error": path_check.get("error")},
                        })
            except Exception as e:
                # Fallback: surface an error indicating workspace preflight could not run.
                issues.append({
                    "code": "repo_preflight_failed",
                    "message": "Repository preflight check failed to run.",
                    "fix_hint": "Ensure the server environment allows git checks and WorkspaceManager is available.",
                    "details": {"error": str(e)},
                })

        # If a token exists, do a best-effort validation against GitHub API to detect
        # invalid tokens or insufficient scopes (we require 'repo' for repo edits).
        if github_token:
            try:
                headers = {
                    "Authorization": f"token {github_token}",
                    "Accept": "application/vnd.github+json",
                }
                resp = httpx.get("https://api.github.com/user", headers=headers, timeout=2.0)
                if resp.status_code != 200:
                    issues.append({
                        "code": "invalid_github_token",
                        "message": "GitHub token rejected by GitHub API.",
                        "fix_hint": "Reconnect GitHub in Settings or set a valid token with repo scopes.",
                        "details": {"status_code": resp.status_code},
                    })
                else:
                    scopes = resp.headers.get("X-OAuth-Scopes", "").lower()
                    if any(kw in lc for kw in ("repo", "pull", "commit", "push")) and "repo" not in scopes:
                        issues.append({
                            "code": "insufficient_github_scopes",
                            "message": "GitHub token may be missing 'repo' scope required for repository edits.",
                            "fix_hint": "Grant 'repo' scope or use a token with repository access.",
                            "details": {"scopes": scopes},
                        })
            except Exception as e:
                issues.append({
                    "code": "github_api_unreachable",
                    "message": "Could not validate GitHub token due to network error.",
                    "fix_hint": "Ensure the server can reach api.github.com or validate token in Settings.",
                    "details": {"error": str(e)},
                })
        if issues:
            raise HTTPException(status_code=412, detail={"ready": False, "issues": issues, "summary": "Git/GitHub preflight failed"})

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
    session_id: str | None = None,
    user: Annotated[UserInfo, Depends(_get_current_user)] = None,
) -> AgentStatusResponse:
    """Live agent workspace snapshot consumed by the Chat UI's Live Agent Workspace panel.

    The frontend polls GET /api/chat/agent-status?session_id=<id> every 2 s via
    fetchAgentWorkspaceSnapshot().  Without this endpoint the request 404s,
    fetchAgentWorkspaceSnapshot throws, and the UI stays in 'reconnecting' state
    with '0 total' tool calls forever.

    Results are scoped to the authenticated caller's jobs only.
    """
    all_jobs = _agent_jobs.list_jobs(session_id=session_id)
    # Filter to only the caller's jobs so progress_events / tool args from other
    # users are never exposed through this endpoint.
    owner_id = user.email if user else None
    jobs = [j for j in all_jobs if owner_id is None or getattr(j, "owner_id", owner_id) == owner_id]

    tool_calls: list[AgentEventModel] = []
    agents: list[AgentJobModel] = []
    latest_summary = ""
    latest_error = ""
    has_events = False

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
        for evt in events:
            if evt.get("type") == "tool_call":
                tool_calls.append(AgentEventModel(**{k: v for k, v in evt.items() if k in AgentEventModel.model_fields}))
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

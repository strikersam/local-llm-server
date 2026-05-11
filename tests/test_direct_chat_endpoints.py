"""Tests for direct_chat.py API endpoints changed in this PR:
  - GET /api/chat/agent-jobs/{job_id} typed response schemas
  - 404 for unknown job IDs
  - missing git binary preflight check
  - GitHub API token validation issues
  - AcceptedJob response shape from POST /api/chat/send with agent_mode=True
"""
from __future__ import annotations

import asyncio
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import direct_chat
import proxy
from agent.job_manager import AgentJobManager
from agent.state import AgentSessionStore
from runtimes.base import RuntimeReadinessReport


def _fake_user() -> direct_chat.UserInfo:
    """
    Create a fixed test UserInfo used by endpoint tests.
    
    Returns:
        direct_chat.UserInfo: A UserInfo with id "u-ep" and email "endpoints-tester@example.com".
    """
    return direct_chat.UserInfo(id="u-ep", email="endpoints-tester@example.com")


# ── GET /api/chat/agent-jobs/{job_id} ─────────────────────────────────────────

def test_get_agent_job_not_found_returns_404(monkeypatch, tmp_path: Path):
    """Requesting a nonexistent job ID returns HTTP 404."""
    monkeypatch.setattr(direct_chat, "_agent_jobs", AgentJobManager())
    proxy.app.dependency_overrides[direct_chat._get_current_user] = _fake_user
    client = TestClient(proxy.app)
    resp = client.get("/api/chat/agent-jobs/nonexistent-job-id-xyz")
    assert resp.status_code == 404
    assert "not found" in resp.json().get("detail", "").lower()
    proxy.app.dependency_overrides.clear()


def test_get_agent_job_queued_returns_failed_schema(monkeypatch, tmp_path: Path):
    """A queued/unknown status job returns the FailedJob schema (the 'else' branch)."""
    mgr = AgentJobManager()
    job = mgr.create_job(session_id="sess-q", instruction="queued job")
    # job.status is "queued" — falls through to the 'else' branch in get_agent_job
    monkeypatch.setattr(direct_chat, "_agent_jobs", mgr)
    proxy.app.dependency_overrides[direct_chat._get_current_user] = _fake_user

    client = TestClient(proxy.app)
    resp = client.get(f"/api/chat/agent-jobs/{job.job_id}")
    assert resp.status_code == 200
    body = resp.json()
    # FailedJob schema keys
    assert "error" in body
    assert body["job_id"] == job.job_id
    proxy.app.dependency_overrides.clear()


def test_get_agent_job_succeeded_returns_completed_schema(monkeypatch, tmp_path: Path):
    """A succeeded job returns CompletedJob schema with final_message and result."""
    mgr = AgentJobManager()
    job = mgr.create_job(session_id="sess-succ", instruction="success job")
    job.status = "succeeded"
    job.phase = "completed"
    job.result = {"response": "Agent done", "raw": {"summary": "Agent done"}}
    monkeypatch.setattr(direct_chat, "_agent_jobs", mgr)
    proxy.app.dependency_overrides[direct_chat._get_current_user] = _fake_user

    client = TestClient(proxy.app)
    resp = client.get(f"/api/chat/agent-jobs/{job.job_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "succeeded"
    assert body["final_message"] == "Agent done"
    assert "result" in body
    proxy.app.dependency_overrides.clear()


def test_get_agent_job_failed_returns_failed_schema(monkeypatch, tmp_path: Path):
    """A failed job returns FailedJob schema with error dict."""
    mgr = AgentJobManager()
    job = mgr.create_job(session_id="sess-fail", instruction="failing job")
    job.status = "failed"
    job.phase = "failed"
    job.error = {"code": "runtime_unavailable", "message": "Docker not running"}
    monkeypatch.setattr(direct_chat, "_agent_jobs", mgr)
    proxy.app.dependency_overrides[direct_chat._get_current_user] = _fake_user

    client = TestClient(proxy.app)
    resp = client.get(f"/api/chat/agent-jobs/{job.job_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "failed"
    assert body["error"]["code"] == "runtime_unavailable"
    proxy.app.dependency_overrides.clear()


def test_get_agent_job_running_returns_running_schema(monkeypatch, tmp_path: Path):
    """A running job returns RunningJob schema with progress_events."""
    mgr = AgentJobManager()
    job = mgr.create_job(session_id="sess-run", instruction="running job")
    job.status = "running"
    job.phase = "planning"
    job.progress_events = [{"phase": "starting", "message": "started"}]
    monkeypatch.setattr(direct_chat, "_agent_jobs", mgr)
    proxy.app.dependency_overrides[direct_chat._get_current_user] = _fake_user

    client = TestClient(proxy.app)
    resp = client.get(f"/api/chat/agent-jobs/{job.job_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "running"
    assert "progress_events" in body
    assert isinstance(body["progress_events"], list)
    proxy.app.dependency_overrides.clear()


# ── POST /api/chat/send agent_mode AcceptedJob shape ──────────────────────────

def test_agent_mode_response_has_accepted_job_shape(monkeypatch, tmp_path: Path):
    """Successful agent-mode POST returns 202 with AcceptedJob schema fields."""
    proxy.app.dependency_overrides[direct_chat._get_current_user] = _fake_user
    monkeypatch.setattr(
        direct_chat, "_direct_chat_store",
        AgentSessionStore(db_path=str(tmp_path / "chat_ep.db"))
    )
    monkeypatch.setattr(direct_chat, "_agent_jobs", AgentJobManager())
    monkeypatch.setattr(direct_chat, "_agent_workspace_root", tmp_path / "ws")

    class _FakeProvider:
        priority = 1
        api_key = None
        normalized_base_url = "http://localhost:11434"
        def auth_headers(self):
            """
            Return authentication headers to include in HTTP requests.
            
            Returns:
                dict: Mapping of HTTP header names to values. Empty dict when no authentication is configured.
            """
            return {}

    class _FakeRouter:
        providers = (_FakeProvider(),)

    monkeypatch.setattr(proxy.app.state, "PROVIDER_ROUTER", _FakeRouter(), raising=False)

    async def fake_readiness(self, spec):
        """
        Report readiness for the internal agent runtime.
        
        Parameters:
            spec: Ignored runtime specification.
        
        Returns:
            RuntimeReadinessReport: A report with `runtime_id` set to "internal_agent", `ready` set to True, and `selected_runtime` set to "internal_agent".
        """
        return RuntimeReadinessReport(
            runtime_id="internal_agent", ready=True, selected_runtime="internal_agent"
        )

    class FakeRunner:
        def __init__(self, **kwargs):
            """
            Initialize a new instance.
            
            Parameters:
                **kwargs: Arbitrary keyword arguments accepted for compatibility; this initializer does not use them.
            """
            pass
        async def run(self, **kwargs):
            """
            Run the agent runner and produce its final result payload.
            
            Parameters:
                **kwargs: Arbitrary runner options and context passed through to the runner.
            
            Returns:
                result (dict): Payload containing:
                    - "response" (str): Final textual response produced by the runner.
                    - "steps" (list): List of execution step records (empty list when no steps).
            """
            return {"response": "done", "steps": []}

    monkeypatch.setattr(
        "runtimes.adapters.internal_agent.InternalAgentAdapter.readiness_check",
        fake_readiness,
    )
    monkeypatch.setattr("agent.loop.AgentRunner", FakeRunner)

    # Patch out github token so preflight doesn't block (content has no repo keywords)
    async def fake_get_token(email):
        """
        Simulate a GitHub token lookup in tests where no token is available.
        
        Parameters:
            email (str): User email to query for a token; ignored by this fake implementation.
        
        Returns:
            None: Indicates that no token was found.
        """
        return None
    monkeypatch.setattr(direct_chat, "_get_github_token_for_user", fake_get_token)

    client = TestClient(proxy.app)
    resp = client.post(
        "/api/chat/send",
        json={"content": "Please implement this important new feature", "agent_mode": True},
    )
    assert resp.status_code == 202
    body = resp.json()
    # AcceptedJob shape
    assert "session_id" in body
    assert "job_id" in body
    assert "status" in body
    assert "phase" in body
    assert "message" in body
    assert body["message"] == "Agent workflow queued."
    proxy.app.dependency_overrides.clear()


# ── Preflight: missing git binary ─────────────────────────────────────────────

def test_agent_mode_missing_git_binary_preflight_error(monkeypatch, tmp_path: Path):
    """Missing git binary results in HTTP 412 with missing_git_binary issue code."""
    proxy.app.dependency_overrides[direct_chat._get_current_user] = _fake_user
    monkeypatch.setattr(
        direct_chat, "_direct_chat_store",
        AgentSessionStore(db_path=str(tmp_path / "chat_git.db"))
    )
    monkeypatch.setattr(direct_chat, "_agent_jobs", AgentJobManager())
    monkeypatch.setattr(direct_chat, "_agent_workspace_root", tmp_path / "ws_git")

    import shutil
    monkeypatch.setattr(shutil, "which", lambda name: None)  # no git, no docker

    async def fake_get_token(email):
        """
        Simulate a token lookup that always yields no token for the given user email.
        
        Parameters:
            email (str): User email whose token would be looked up.
        
        Returns:
            None: Indicates no token is available.
        """
        return None  # no token either
    monkeypatch.setattr(direct_chat, "_get_github_token_for_user", fake_get_token)

    client = TestClient(proxy.app)
    resp = client.post(
        "/api/chat/send",
        json={"content": "Please git clone and push branch changes", "agent_mode": True},
    )
    assert resp.status_code == 412
    detail = resp.json().get("detail", {})
    assert detail.get("ready") is False
    issues = detail.get("issues", [])
    codes = {i.get("code") for i in issues}
    assert "missing_git_binary" in codes
    proxy.app.dependency_overrides.clear()


# ── Preflight: multiple issues reported together ───────────────────────────────

def test_agent_mode_multiple_preflight_issues(monkeypatch, tmp_path: Path):
    """When both git binary and token are missing, both issues are reported."""
    proxy.app.dependency_overrides[direct_chat._get_current_user] = _fake_user
    monkeypatch.setattr(
        direct_chat, "_direct_chat_store",
        AgentSessionStore(db_path=str(tmp_path / "chat_multi.db"))
    )
    monkeypatch.setattr(direct_chat, "_agent_jobs", AgentJobManager())
    monkeypatch.setattr(direct_chat, "_agent_workspace_root", tmp_path / "ws_multi")

    import shutil
    monkeypatch.setattr(shutil, "which", lambda name: None)

    async def fake_get_token(email):
        """
        Simulate a GitHub token lookup in tests where no token is available.
        
        Parameters:
            email (str): User email to query for a token; ignored by this fake implementation.
        
        Returns:
            None: Indicates that no token was found.
        """
        return None
    monkeypatch.setattr(direct_chat, "_get_github_token_for_user", fake_get_token)

    client = TestClient(proxy.app)
    resp = client.post(
        "/api/chat/send",
        json={"content": "commit and push to repo", "agent_mode": True},
    )
    assert resp.status_code == 412
    detail = resp.json().get("detail", {})
    issues = detail.get("issues", [])
    codes = {i.get("code") for i in issues}
    # Both missing token and missing git binary should be present
    assert "missing_github_token" in codes
    assert "missing_git_binary" in codes
    proxy.app.dependency_overrides.clear()


# ── Preflight: content without git keywords passes through ────────────────────

def test_non_git_content_skips_github_preflight(monkeypatch, tmp_path: Path):
    """Content without repo-related keywords skips GitHub preflight entirely."""
    proxy.app.dependency_overrides[direct_chat._get_current_user] = _fake_user
    monkeypatch.setattr(
        direct_chat, "_direct_chat_store",
        AgentSessionStore(db_path=str(tmp_path / "chat_skip.db"))
    )
    mgr = AgentJobManager()
    monkeypatch.setattr(direct_chat, "_agent_jobs", mgr)
    monkeypatch.setattr(direct_chat, "_agent_workspace_root", tmp_path / "ws_skip")

    class _FakeProvider:
        priority = 1
        api_key = None
        normalized_base_url = "http://localhost:11434"
        def auth_headers(self):
            """
            Return authentication headers to include in HTTP requests.
            
            Returns:
                dict: Mapping of HTTP header names to values. Empty dict when no authentication is configured.
            """
            return {}

    class _FakeRouter:
        providers = (_FakeProvider(),)

    monkeypatch.setattr(proxy.app.state, "PROVIDER_ROUTER", _FakeRouter(), raising=False)

    async def fake_readiness(self, spec):
        """
        Report readiness for the internal agent runtime.
        
        Parameters:
            spec: Ignored runtime specification.
        
        Returns:
            RuntimeReadinessReport: A report with `runtime_id` set to "internal_agent", `ready` set to True, and `selected_runtime` set to "internal_agent".
        """
        return RuntimeReadinessReport(
            runtime_id="internal_agent", ready=True, selected_runtime="internal_agent"
        )

    class FakeRunner:
        def __init__(self, **kwargs):
            """
            Initialize a new instance.
            
            Parameters:
                **kwargs: Arbitrary keyword arguments accepted for compatibility; this initializer does not use them.
            """
            pass
        async def run(self, **kwargs):
            """
            Run a fake agent execution that returns a canned summary and an empty step list.
            
            Parameters:
                **kwargs: Ignored. Accepts arbitrary keyword arguments for compatibility.
            
            Returns:
                dict: A result object with keys:
                    - "response" (str): A short summary message.
                    - "steps" (list): A list of execution step records (empty in this implementation).
            """
            return {"response": "Summarized.", "steps": []}

    monkeypatch.setattr(
        "runtimes.adapters.internal_agent.InternalAgentAdapter.readiness_check",
        fake_readiness,
    )
    monkeypatch.setattr("agent.loop.AgentRunner", FakeRunner)

    async def fake_get_token(email):
        """
        Simulate a GitHub token lookup in tests where no token is available.
        
        Parameters:
            email (str): User email to query for a token; ignored by this fake implementation.
        
        Returns:
            None: Indicates that no token was found.
        """
        return None
    monkeypatch.setattr(direct_chat, "_get_github_token_for_user", fake_get_token)

    import shutil
    monkeypatch.setattr(shutil, "which", lambda name: None)  # even without git this should proceed

    client = TestClient(proxy.app)
    # "Summarize this document" has no repo keywords → preflight skipped
    resp = client.post(
        "/api/chat/send",
        json={"content": "Please implement this important feature now", "agent_mode": True},
    )
    # Should not fail with 412 — might be 202 or 200 depending on routing
    assert resp.status_code in (202, 200)
    proxy.app.dependency_overrides.clear()
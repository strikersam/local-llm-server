"""
End-to-end test for the agent chat code-change flow.

Tests the full stack with real:
  - FastAPI app (backend/server.py)
  - Auth (login → JWT)
  - Session creation and persistence
  - Agent job dispatch (POST → 202 + job_id)
  - Planner → Executor → Verifier → Judge LLM cycle
  - WorkspaceTools.write_file (file actually written to disk)
  - Job status polling (/api/chat/agent-jobs/{job_id})
  - /api/agent/status and /api/chat/agent-status alias

Only the outbound HTTP calls to LLM providers (httpx.AsyncClient.post)
are intercepted with canned JSON responses. Every other layer is real.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Canned LLM responses (OpenAI chat-completion format)
# ---------------------------------------------------------------------------

PLAN_JSON = json.dumps({
    "goal": "Create hello.txt with content Hello World",
    "steps": [
        {
            "id": 1,
            "description": "Write hello.txt to workspace",
            "files": ["hello.txt"],
            "type": "create",
            "risky": False,
            "acceptance": "hello.txt exists and contains Hello World",
        }
    ],
    "risks": [],
    "requires_risky_review": False,
})

EXECUTOR_JSON = json.dumps({
    "tool": "write_file",
    "args": {"path": "hello.txt", "content": "Hello World"},
    "explanation": "Creating hello.txt",
})

VERIFIER_JSON = json.dumps({
    "status": "pass",
    "issues": [],
    "confidence": 0.99,
})

JUDGE_JSON = json.dumps({
    "verdict": "pass",
    "summary": "File written correctly.",
    "score": 9,
})


def _openai_response(content: str) -> httpx.Response:
    """Return a real httpx.Response that looks like an OpenAI chat completion."""
    body = {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "model": "test-model",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 50, "total_tokens": 60},
    }
    return httpx.Response(200, json=body)


def _nim_post_factory(responses: list[str]):
    """
    Return an async replacement for httpx.AsyncClient.post that cycles through
    canned responses for /chat/completions calls and passes everything else
    through as a 503 (no real network in CI).
    """
    call_index = [0]

    async def _mock_post(self, url, *args, **kwargs):
        if "chat/completions" in str(url) or "messages" in str(url):
            idx = call_index[0] % len(responses)
            call_index[0] += 1
            return _openai_response(responses[idx])
        # Health checks, model lists, etc. — return 200 empty
        return httpx.Response(200, json={"object": "list", "data": []})

    return _mock_post


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth_headers(client: TestClient) -> dict[str, str]:
    resp = client.post(
        "/api/auth/login",
        json={"email": "admin@llmrelay.local", "password": "WikiAdmin2026!"},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _poll_job(client: TestClient, headers: dict, job_id: str, timeout: float = 30.0) -> dict:
    """Poll job endpoint until terminal status or timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        resp = client.get(f"/api/chat/agent-jobs/{job_id}", headers=headers)
        assert resp.status_code == 200, f"Job poll {resp.status_code}: {resp.text}"
        job = resp.json()
        if job["status"] in {"succeeded", "failed", "cancelled"}:
            return job
        time.sleep(0.2)
    return client.get(f"/api/chat/agent-jobs/{job_id}", headers=headers).json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAgentChatE2E:

    def test_agent_creates_file_in_workspace(
        self, client: TestClient, tmp_path: Path, monkeypatch
    ) -> None:
        """
        Full round-trip: login → agent-mode POST → poll to completion →
        verify hello.txt physically exists in the workspace directory.

        LLM HTTP calls are intercepted via monkeypatch (test-lifetime scope,
        so the mock stays active while the background job runs).
        """
        import backend.server as srv

        # Redirect workspace root so we can inspect written files
        monkeypatch.setattr(srv, "_CHAT_AGENT_WORKSPACE_ROOT", tmp_path)

        # Patch httpx at the instance method level so it survives background tasks
        responses = [PLAN_JSON, EXECUTOR_JSON, VERIFIER_JSON, JUDGE_JSON]
        monkeypatch.setattr(
            "httpx.AsyncClient.post",
            _nim_post_factory(responses),
        )

        headers = _auth_headers(client)
        session_id = f"e2e-{uuid.uuid4()}"

        resp = client.post(
            "/api/chat/send",
            headers=headers,
            json={
                "session_id": session_id,
                "agent_mode": True,
                "content": "Create a file called hello.txt with the content 'Hello World'",
            },
        )
        assert resp.status_code == 202, f"Expected 202, got {resp.status_code}: {resp.text}"
        body = resp.json()
        assert "job_id" in body, f"No job_id in response: {body}"
        job_id = body["job_id"]

        job = _poll_job(client, headers, job_id, timeout=30.0)

        # Detailed failure message so a regression is easy to diagnose
        workspace_files = [str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*")]
        assert job["status"] in {"succeeded", "failed"}, (
            f"Job stuck in '{job['status']}' — likely the background task was cancelled.\n"
            f"Progress: {[e['phase'] + ': ' + e['message'] for e in job.get('progress_events', [])]}"
        )

        written = list(tmp_path.rglob("hello.txt"))
        assert written, (
            f"hello.txt not found in workspace.\n"
            f"Job status:  {job['status']}\n"
            f"Job phase:   {job.get('phase')}\n"
            f"Job error:   {job.get('error')}\n"
            f"Job result:  {job.get('result')}\n"
            f"Progress:    {[e['phase'] + ': ' + e['message'] for e in job.get('progress_events', [])]}\n"
            f"Workspace:   {workspace_files}"
        )
        assert "Hello World" in written[0].read_text()

    def test_agent_job_is_202_and_pollable(self, client: TestClient, monkeypatch) -> None:
        """202 + job_id returned; job endpoint immediately reachable."""
        import backend.server as srv
        monkeypatch.setattr(srv, "_CHAT_AGENT_JOBS", srv.AgentJobManager())

        agent_loop = AsyncMock(return_value="Done")
        monkeypatch.setattr("backend.server._run_agent_loop", agent_loop)

        headers = _auth_headers(client)
        resp = client.post(
            "/api/chat/send",
            headers=headers,
            json={
                "session_id": f"smoke-{uuid.uuid4()}",
                "agent_mode": True,
                "content": "Say hello",
            },
        )
        assert resp.status_code == 202, resp.text
        job_id = resp.json().get("job_id")
        assert job_id

        poll = client.get(f"/api/chat/agent-jobs/{job_id}", headers=headers)
        assert poll.status_code == 200
        assert poll.json()["status"] in {"queued", "running", "succeeded"}

    def test_agent_status_aliases_both_respond(self, client: TestClient) -> None:
        """/api/agent/status and /api/chat/agent-status must both return 200."""
        headers = _auth_headers(client)
        for url in ["/api/agent/status", "/api/chat/agent-status"]:
            resp = client.get(url, headers=headers)
            assert resp.status_code == 200, f"{url} → {resp.status_code}: {resp.text}"

    def test_direct_chat_bypasses_agent_job(self, client: TestClient, monkeypatch) -> None:
        """agent_mode=False must use the fast LLM path and never create a job."""
        llm = AsyncMock(return_value="Four")
        agent_loop = AsyncMock(side_effect=AssertionError("agent path must not run"))
        monkeypatch.setattr("backend.server.call_llm", llm)
        monkeypatch.setattr("backend.server._run_agent_loop", agent_loop)

        headers = _auth_headers(client)
        resp = client.post(
            "/api/chat/send",
            headers=headers,
            json={
                "session_id": f"direct-{uuid.uuid4()}",
                "agent_mode": False,
                "content": "What is 2+2?",
            },
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["response"] == "Four"
        agent_loop.assert_not_called()

    def test_mcp_server_is_mounted(self, client: TestClient) -> None:
        """The MCP health endpoint must respond — verifies mcp_server is mounted."""
        resp = client.get("/mcp-internal/health")
        assert resp.status_code == 200, (
            f"/mcp-internal/health returned {resp.status_code}. "
            "mcp_server/ may not be mounted — check backend/server.py MCP mount block."
        )

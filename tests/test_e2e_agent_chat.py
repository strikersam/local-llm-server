"""
End-to-end tests for the agent chat code-change flow.

Tests the full stack with real:
  - FastAPI app (backend/server.py)
  - Auth (login → JWT)
  - Session creation and persistence
  - Agent job dispatch (POST → 202 + job_id)
  - Planner → Executor → Verifier → Judge LLM cycle
  - WorkspaceTools.write_file (file actually written to disk)
  - Job status polling (/api/chat/agent-jobs/{job_id})
  - /api/agent/status and /api/chat/agent-status alias
  - MCP tools: clone_repo, git_status, git_create_branch, git_commit, git_push
  - GitHub API tools: create_branch, open_pull_request, merge_pull_request
  - Full PR workflow: clone → edit → commit → push → open PR → merge PR

Only outbound HTTP calls (LLM providers, GitHub API) are intercepted.
All agent logic, MCP tool dispatch, and job lifecycle are real.
"""
from __future__ import annotations

import json
import time
import urllib.parse
import uuid
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
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


def _mcp_tool_response(req_id: int, result: dict | str) -> httpx.Response:
    """Build a proper JSON-RPC tools/call response for MCP tool mocks."""
    text = result if isinstance(result, str) else json.dumps(result, default=str)
    return httpx.Response(200, json={
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "content": [{"type": "text", "text": text}],
            "isError": False,
        },
    })


def _build_agent_http_mock(
    llm_responses: list[str],
    mcp_results: "dict[str, dict | str] | None" = None,
    github_post_results: "dict[str, dict] | None" = None,
    github_get_results: "dict[str, dict | list] | None" = None,
    github_put_results: "dict[str, dict] | None" = None,
):
    """
    Build mock replacements for httpx.AsyncClient.post / .get / .put.

    Routes by URL pattern:
      - chat/completions or /messages  → cycle LLM canned responses
      - /mcp-internal/mcp              → return JSON-RPC result from mcp_results
      - api.github.com POST            → return from github_post_results
      - api.github.com GET             → return from github_get_results
      - api.github.com PUT             → return from github_put_results
    """
    llm_idx = [0]

    async def mock_post(self, url, *args, **kwargs):
        url_str = str(url)
        if "chat/completions" in url_str or "/messages" in url_str:
            idx = llm_idx[0] % len(llm_responses)
            llm_idx[0] += 1
            return _openai_response(llm_responses[idx])
        if "/mcp-internal/mcp" in url_str or url_str.endswith("/mcp"):
            body = kwargs.get("json") or {}
            req_id = body.get("id", 1)
            method = body.get("method", "")
            if method == "tools/call":
                tool_name = (body.get("params") or {}).get("name", "")
                if tool_name in (mcp_results or {}):
                    return _mcp_tool_response(req_id, mcp_results[tool_name])
                # Unknown tool — return error so mis-dispatched calls fail visibly
                return httpx.Response(200, json={
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}],
                        "isError": True,
                    },
                })
            # Non-tools/call MCP request (e.g. initialize, list): return empty success
            return httpx.Response(200, json={
                "jsonrpc": "2.0", "id": req_id,
                "result": {"content": [{"type": "text", "text": "{}"}], "isError": False},
            })
        if urllib.parse.urlparse(url_str).netloc == "api.github.com" and github_post_results:
            for frag, resp in github_post_results.items():
                if frag in url_str:
                    return httpx.Response(201, json=resp)
        return httpx.Response(200, json={"object": "list", "data": []})

    async def mock_get(self, url, *args, **kwargs):
        url_str = str(url)
        if urllib.parse.urlparse(url_str).netloc == "api.github.com" and github_get_results:
            for frag, resp in github_get_results.items():
                if frag in url_str:
                    return httpx.Response(200, json=resp)
        return httpx.Response(200, json=[])

    async def mock_put(self, url, *args, **kwargs):
        url_str = str(url)
        if urllib.parse.urlparse(url_str).netloc == "api.github.com" and github_put_results:
            for frag, resp in github_put_results.items():
                if frag in url_str:
                    return httpx.Response(200, json=resp)
        return httpx.Response(200, json={})

    return mock_post, mock_get, mock_put


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
        assert job["status"] == "succeeded", (
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

    def test_mcp_client_localhost_fallback(self, monkeypatch) -> None:
        """
        get_mcp_client() must resolve to localhost when MCP_SERVER_BASE_URL is
        absent — the MCP server is mounted in-process, so self-calls work.
        This catches the production bug where clone_repo always returned
        '[tool error: mcp server unreachable]' because MCP_SERVER_BASE_URL
        was never set in the Render container.
        """
        import agent.mcp_client as _m
        monkeypatch.delenv("MCP_SERVER_BASE_URL", raising=False)
        monkeypatch.setattr(_m, "_client", None)
        monkeypatch.setenv("PORT", "9999")
        client_obj = _m.get_mcp_client()
        assert client_obj.base_url == "http://127.0.0.1:9999/mcp-internal", (
            f"Expected localhost fallback, got: {client_obj.base_url!r}. "
            "clone_repo / git tools will fail in production if this isn't set."
        )

    def test_clone_repo_hits_mcp_not_crashes(
        self, client: TestClient, monkeypatch
    ) -> None:
        """
        clone_repo must route through the MCP client (not crash the agent loop).
        With the localhost fallback fix, the MCP client calls /mcp-internal/mcp.
        We verify the agent job completes (succeeded or failed) — never 'cancelled'
        or 500, which would indicate the background task panicked.
        """
        responses = [PLAN_JSON, EXECUTOR_JSON, VERIFIER_JSON, JUDGE_JSON]
        monkeypatch.setattr("httpx.AsyncClient.post", _nim_post_factory(responses))

        # Plan that uses clone_repo so the MCP path is exercised
        clone_plan = json.dumps({
            "goal": "Clone a repo",
            "steps": [
                {
                    "id": 1,
                    "description": "Clone the repo",
                    "files": [],
                    "type": "create",
                    "risky": False,
                    "acceptance": "repo cloned",
                }
            ],
            "risks": [],
            "requires_risky_review": False,
        })
        clone_executor = json.dumps({
            "tool": "clone_repo",
            "args": {
                "workspace_id": "test-ws",
                "repo_url": "https://github.com/example/nonexistent",
                "branch": "main",
            },
            "explanation": "Cloning repo",
        })

        monkeypatch.setattr(
            "httpx.AsyncClient.post",
            _nim_post_factory([clone_plan, clone_executor, VERIFIER_JSON, JUDGE_JSON]),
        )

        headers = _auth_headers(client)
        resp = client.post(
            "/api/chat/send",
            headers=headers,
            json={
                "session_id": f"mcp-{uuid.uuid4()}",
                "agent_mode": True,
                "content": "Clone https://github.com/example/nonexistent",
            },
        )
        assert resp.status_code == 202, resp.text
        job_id = resp.json()["job_id"]

        job = _poll_job(client, headers, job_id, timeout=30.0)
        # Job must reach a terminal state — never stuck or 500
        assert job["status"] == "succeeded", (
            f"Job stuck in '{job['status']}' — agent loop may have crashed.\n"
            f"Progress: {[e['phase'] + ': ' + e['message'] for e in job.get('progress_events', [])]}"
        )


# ---------------------------------------------------------------------------
# Canned responses for GitHub API and git workflows
# ---------------------------------------------------------------------------

_GH_BRANCH_RESPONSE = {
    "ref": "refs/heads/agent/fix-bug",
    "node_id": "REF_kwDO",
    "url": "https://api.github.com/repos/strikersam/local-llm-server/git/refs/heads/agent/fix-bug",
    "object": {"sha": "abc123def456", "type": "commit"},
}

_GH_PR_RESPONSE = {
    "number": 99,
    "title": "fix: update hello function",
    "html_url": "https://github.com/strikersam/local-llm-server/pull/99",
    "state": "open",
    "head": {"ref": "agent/fix-bug", "sha": "abc123def456"},
    "base": {"ref": "main", "sha": "000000000000"},
}

_GH_MERGE_RESPONSE = {
    "sha": "deadbeef1234",
    "merged": True,
    "message": "Pull Request successfully merged",
}

_GH_ISSUE_RESPONSE = {
    "number": 42,
    "title": "Bug: hello() returns wrong string",
    "body": "The function returns 'Hello World' but should return 'Hello Agent'.",
    "state": "open",
}

_MCP_GIT_STATUS = " M src/main.py\n"
_MCP_GIT_DIFF = (
    "diff --git a/src/main.py b/src/main.py\n"
    "--- a/src/main.py\n"
    "+++ b/src/main.py\n"
    "@@ -1 +1 @@\n"
    "-def hello(): return 'Hello World'\n"
    "+def hello(): return 'Hello Agent'\n"
)


def _one_step_plan(
    tool: str, step_desc: str = "Execute task", goal: str = "Complete the task"
) -> str:
    return json.dumps({
        "goal": goal,
        "steps": [{"id": 1, "description": step_desc, "files": [],
                   "type": "create", "risky": False, "acceptance": "done"}],
        "risks": [], "requires_risky_review": False,
    })


def _multi_step_plan(steps: list[dict]) -> str:
    return json.dumps({
        "goal": "Execute multi-step workflow",
        "steps": [
            {"id": i + 1, "description": s["desc"], "files": s.get("files", []),
             "type": s.get("type", "create"), "risky": False, "acceptance": "done"}
            for i, s in enumerate(steps)
        ],
        "risks": [], "requires_risky_review": False,
    })


def _exec(tool: str, args: dict, explanation: str = "") -> str:
    return json.dumps({"tool": tool, "args": args, "explanation": explanation or tool})


# ---------------------------------------------------------------------------
# GitHub API tool tests
# ---------------------------------------------------------------------------

class TestAgentGitHubAPITools:
    """Agent-level tests for GitHub API tools (create_branch, open_pr, merge_pr)."""

    def test_agent_creates_github_branch(
        self, client: TestClient, monkeypatch
    ) -> None:
        """github_create_branch calls the GitHub API and the job succeeds."""
        plan = _one_step_plan("github_create_branch", "Create a feature branch")
        executor = _exec("github_create_branch", {
            "repo_name": "strikersam/local-llm-server",
            "branch_name": "agent/fix-bug",
            "base_branch": "main",
        })

        mock_post, mock_get, mock_put = _build_agent_http_mock(
            llm_responses=[plan, executor, VERIFIER_JSON, JUDGE_JSON],
            github_post_results={"/git/refs": _GH_BRANCH_RESPONSE},
            github_get_results={"/git/refs/heads/main": {"object": {"sha": "abc123"}}},
        )
        monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
        monkeypatch.setattr("httpx.AsyncClient.get", mock_get)

        headers = _auth_headers(client)
        resp = client.post("/api/chat/send", headers=headers, json={
            "session_id": f"gh-branch-{uuid.uuid4()}",
            "agent_mode": True,
            "content": "Create a feature branch agent/fix-bug from main",
        })
        assert resp.status_code == 202, resp.text
        job = _poll_job(client, headers, resp.json()["job_id"], timeout=30.0)
        assert job["status"] == "succeeded", (
            f"Expected succeeded but got {job['status']!r}\n"
            f"Progress: {[e['phase'] + ': ' + e['message'] for e in job.get('progress_events', [])]}"
        )

    def test_agent_opens_pull_request(
        self, client: TestClient, monkeypatch
    ) -> None:
        """github_open_pull_request calls GitHub API and job reaches terminal state."""
        plan = _one_step_plan("github_open_pull_request", "Open a pull request")
        executor = _exec("github_open_pull_request", {
            "repo_name": "strikersam/local-llm-server",
            "title": "fix: update hello function",
            "head": "agent/fix-bug",
            "base": "main",
            "body": "This PR fixes the hello() return value.",
        })

        mock_post, mock_get, mock_put = _build_agent_http_mock(
            llm_responses=[plan, executor, VERIFIER_JSON, JUDGE_JSON],
            github_post_results={"/pulls": _GH_PR_RESPONSE},
        )
        monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
        monkeypatch.setattr("httpx.AsyncClient.get", mock_get)
        monkeypatch.setattr("httpx.AsyncClient.put", mock_put)

        headers = _auth_headers(client)
        resp = client.post("/api/chat/send", headers=headers, json={
            "session_id": f"gh-pr-{uuid.uuid4()}",
            "agent_mode": True,
            "content": "Open a PR for agent/fix-bug into main",
        })
        assert resp.status_code == 202, resp.text
        job = _poll_job(client, headers, resp.json()["job_id"], timeout=30.0)
        assert job["status"] == "succeeded"

    def test_agent_merges_pull_request(
        self, client: TestClient, monkeypatch
    ) -> None:
        """github_merge_pull_request calls GitHub API PUT and job completes."""
        plan = _one_step_plan("github_merge_pull_request", "Merge the pull request")
        executor = _exec("github_merge_pull_request", {
            "repo_name": "strikersam/local-llm-server",
            "pull_number": 99,
            "merge_method": "squash",
            "commit_title": "fix: update hello function (#99)",
        })

        mock_post, mock_get, mock_put = _build_agent_http_mock(
            llm_responses=[plan, executor, VERIFIER_JSON, JUDGE_JSON],
            github_put_results={"/pulls/99/merge": _GH_MERGE_RESPONSE},
        )
        monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
        monkeypatch.setattr("httpx.AsyncClient.get", mock_get)
        monkeypatch.setattr("httpx.AsyncClient.put", mock_put)

        headers = _auth_headers(client)
        resp = client.post("/api/chat/send", headers=headers, json={
            "session_id": f"gh-merge-{uuid.uuid4()}",
            "agent_mode": True,
            "content": "Merge PR #99 with squash",
        })
        assert resp.status_code == 202, resp.text
        job = _poll_job(client, headers, resp.json()["job_id"], timeout=30.0)
        assert job["status"] == "succeeded"

    def test_agent_reads_github_issue(
        self, client: TestClient, monkeypatch
    ) -> None:
        """github_get_issue fetches from GitHub API."""
        plan = _one_step_plan("github_get_issue", "Read the issue")
        executor = _exec("github_get_issue", {
            "repo_name": "strikersam/local-llm-server",
            "issue_number": 42,
        })

        mock_post, mock_get, mock_put = _build_agent_http_mock(
            llm_responses=[plan, executor, VERIFIER_JSON, JUDGE_JSON],
            github_get_results={"/issues/42": _GH_ISSUE_RESPONSE},
        )
        monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
        monkeypatch.setattr("httpx.AsyncClient.get", mock_get)

        headers = _auth_headers(client)
        resp = client.post("/api/chat/send", headers=headers, json={
            "session_id": f"gh-issue-{uuid.uuid4()}",
            "agent_mode": True,
            "content": "Read issue #42",
        })
        assert resp.status_code == 202, resp.text
        job = _poll_job(client, headers, resp.json()["job_id"], timeout=30.0)
        assert job["status"] == "succeeded"


# ---------------------------------------------------------------------------
# MCP git tool tests (agent-level: agent dispatches MCP tools)
# ---------------------------------------------------------------------------

class TestAgentMCPGitTools:
    """Agent jobs that use MCP git tools: git_status, git_diff, git_create_branch,
    git_commit, git_push — with mocked MCP JSON-RPC responses."""

    def test_agent_git_status(self, client: TestClient, monkeypatch) -> None:
        plan = _one_step_plan("git_status", "Check git status")
        executor = _exec("git_status", {"workspace_id": "ws-agent-status"})

        mock_post, mock_get, _ = _build_agent_http_mock(
            llm_responses=[plan, executor, VERIFIER_JSON, JUDGE_JSON],
            mcp_results={"git_status": _MCP_GIT_STATUS},
        )
        monkeypatch.setattr("httpx.AsyncClient.post", mock_post)

        headers = _auth_headers(client)
        resp = client.post("/api/chat/send", headers=headers, json={
            "session_id": f"mcp-status-{uuid.uuid4()}",
            "agent_mode": True,
            "content": "Check the git status of the workspace",
        })
        assert resp.status_code == 202, resp.text
        job = _poll_job(client, headers, resp.json()["job_id"], timeout=30.0)
        assert job["status"] == "succeeded"

    def test_agent_git_diff(self, client: TestClient, monkeypatch) -> None:
        plan = _one_step_plan("git_diff", "Get the diff")
        executor = _exec("git_diff", {"workspace_id": "ws-agent-diff"})

        mock_post, _, _ = _build_agent_http_mock(
            llm_responses=[plan, executor, VERIFIER_JSON, JUDGE_JSON],
            mcp_results={"git_diff": _MCP_GIT_DIFF},
        )
        monkeypatch.setattr("httpx.AsyncClient.post", mock_post)

        headers = _auth_headers(client)
        resp = client.post("/api/chat/send", headers=headers, json={
            "session_id": f"mcp-diff-{uuid.uuid4()}",
            "agent_mode": True,
            "content": "Show the git diff",
        })
        assert resp.status_code == 202, resp.text
        job = _poll_job(client, headers, resp.json()["job_id"], timeout=30.0)
        assert job["status"] == "succeeded"

    def test_agent_git_create_branch(self, client: TestClient, monkeypatch) -> None:
        plan = _one_step_plan("git_create_branch", "Create branch")
        executor = _exec("git_create_branch", {
            "workspace_id": "ws-agent-branch",
            "branch_name": "feature/agent-fix",
        })

        mock_post, _, _ = _build_agent_http_mock(
            llm_responses=[plan, executor, VERIFIER_JSON, JUDGE_JSON],
            mcp_results={"git_create_branch": {"branch": "feature/agent-fix", "created": True}},
        )
        monkeypatch.setattr("httpx.AsyncClient.post", mock_post)

        headers = _auth_headers(client)
        resp = client.post("/api/chat/send", headers=headers, json={
            "session_id": f"mcp-branch-{uuid.uuid4()}",
            "agent_mode": True,
            "content": "Create a feature branch",
        })
        assert resp.status_code == 202, resp.text
        job = _poll_job(client, headers, resp.json()["job_id"], timeout=30.0)
        assert job["status"] == "succeeded"

    def test_agent_git_commit(self, client: TestClient, monkeypatch) -> None:
        plan = _one_step_plan("git_commit", "Commit changes")
        executor = _exec("git_commit", {
            "workspace_id": "ws-agent-commit",
            "message": "fix: correct hello function",
        })

        mock_post, _, _ = _build_agent_http_mock(
            llm_responses=[plan, executor, VERIFIER_JSON, JUDGE_JSON],
            mcp_results={"git_commit": {"committed": True, "message": "fix: correct hello function"}},
        )
        monkeypatch.setattr("httpx.AsyncClient.post", mock_post)

        headers = _auth_headers(client)
        resp = client.post("/api/chat/send", headers=headers, json={
            "session_id": f"mcp-commit-{uuid.uuid4()}",
            "agent_mode": True,
            "content": "Commit the changes",
        })
        assert resp.status_code == 202, resp.text
        job = _poll_job(client, headers, resp.json()["job_id"], timeout=30.0)
        assert job["status"] == "succeeded"

    def test_agent_git_push(self, client: TestClient, monkeypatch) -> None:
        plan = _one_step_plan("git_push", "Push to remote")
        executor = _exec("git_push", {
            "workspace_id": "ws-agent-push",
            "branch": "feature/agent-fix",
        })

        mock_post, _, _ = _build_agent_http_mock(
            llm_responses=[plan, executor, VERIFIER_JSON, JUDGE_JSON],
            mcp_results={"git_push": {"pushed": True}},
        )
        monkeypatch.setattr("httpx.AsyncClient.post", mock_post)

        headers = _auth_headers(client)
        resp = client.post("/api/chat/send", headers=headers, json={
            "session_id": f"mcp-push-{uuid.uuid4()}",
            "agent_mode": True,
            "content": "Push the feature branch to remote",
        })
        assert resp.status_code == 202, resp.text
        job = _poll_job(client, headers, resp.json()["job_id"], timeout=30.0)
        assert job["status"] == "succeeded"


# ---------------------------------------------------------------------------
# Full PR workflow tests (multi-step agent plans)
# ---------------------------------------------------------------------------

class TestAgentFullPRWorkflow:
    """
    End-to-end agent workflow tests covering the complete pull-request lifecycle:
    clone → edit → commit → push → open PR → merge PR
    """

    def test_agent_full_pr_workflow(
        self, client: TestClient, tmp_path: Path, monkeypatch
    ) -> None:
        """
        Code-change + PR-merge workflow (2 steps, stays on sequential path).

        Uses write_file (MCP) then github_merge_pull_request (GitHub API)
        to cover both tool categories without exceeding _PARALLEL_THRESHOLD=3
        and switching to MultiAgentSwarm, which is incompatible with the
        sequential mock.
        """
        import backend.server as srv
        monkeypatch.setattr(srv, "_CHAT_AGENT_WORKSPACE_ROOT", tmp_path)

        plan = _multi_step_plan([
            {"desc": "Write the fix", "files": ["src/main.py"], "type": "modify"},
            {"desc": "Merge pull request", "files": [], "type": "github"},
        ])
        exec_write = _exec("write_file", {
            "path": "src/main.py",
            "content": "def hello():\n    return 'Hello Agent'\n",
        })
        exec_merge_pr = _exec("github_merge_pull_request", {
            "repo_name": "strikersam/local-llm-server",
            "pull_number": 99,
            "merge_method": "squash",
        })

        llm_responses = [
            plan,
            exec_write, VERIFIER_JSON,
            exec_merge_pr, VERIFIER_JSON,
            JUDGE_JSON,
        ]

        mock_post, mock_get, mock_put = _build_agent_http_mock(
            llm_responses=llm_responses,
            github_put_results={"/pulls/99/merge": _GH_MERGE_RESPONSE},
        )
        monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
        monkeypatch.setattr("httpx.AsyncClient.get", mock_get)
        monkeypatch.setattr("httpx.AsyncClient.put", mock_put)

        headers = _auth_headers(client)
        resp = client.post("/api/chat/send", headers=headers, json={
            "session_id": f"pr-workflow-{uuid.uuid4()}",
            "agent_mode": True,
            "content": "Fix the hello() function and merge the PR",
        })
        assert resp.status_code == 202, resp.text
        job_id = resp.json()["job_id"]

        job = _poll_job(client, headers, job_id, timeout=30.0)
        assert job["status"] == "succeeded", (
            f"Full PR workflow job got '{job['status']}'\n"
            f"Progress: {[e['phase'] + ': ' + e['message'] for e in job.get('progress_events', [])]}"
        )

    def test_agent_issue_to_pr_workflow(
        self, client: TestClient, monkeypatch
    ) -> None:
        """
        Issue-driven workflow (2 steps, stays on sequential path).

        Uses github_get_issue then github_open_pull_request to cover reading
        an issue and opening a PR without exceeding _PARALLEL_THRESHOLD=3.
        """
        plan = _multi_step_plan([
            {"desc": "Read the issue", "files": [], "type": "analyze"},
            {"desc": "Open pull request", "files": [], "type": "github"},
        ])
        exec_get_issue = _exec("github_get_issue", {
            "repo_name": "strikersam/local-llm-server",
            "issue_number": 42,
        })
        exec_open_pr = _exec("github_open_pull_request", {
            "repo_name": "strikersam/local-llm-server",
            "title": "fix: closes #42 — update hello()",
            "head": "fix/issue-42",
            "base": "main",
            "body": "Closes #42.",
        })

        llm_responses = [
            plan,
            exec_get_issue, VERIFIER_JSON,
            exec_open_pr, VERIFIER_JSON,
            JUDGE_JSON,
        ]

        mock_post, mock_get, mock_put = _build_agent_http_mock(
            llm_responses=llm_responses,
            github_get_results={"/issues/42": _GH_ISSUE_RESPONSE},
            github_post_results={"/pulls": _GH_PR_RESPONSE},
        )
        monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
        monkeypatch.setattr("httpx.AsyncClient.get", mock_get)
        monkeypatch.setattr("httpx.AsyncClient.put", mock_put)

        headers = _auth_headers(client)
        resp = client.post("/api/chat/send", headers=headers, json={
            "session_id": f"issue-pr-{uuid.uuid4()}",
            "agent_mode": True,
            "content": "Fix issue #42 and open a PR",
        })
        assert resp.status_code == 202, resp.text
        job = _poll_job(client, headers, resp.json()["job_id"], timeout=30.0)
        assert job["status"] == "succeeded", (
            f"Expected succeeded but got {job['status']!r}\n"
            f"Progress: {[e['phase'] + ': ' + e['message'] for e in job.get('progress_events', [])]}"
        )

    def test_agent_multi_step_plan_executes_all_steps(
        self, client: TestClient, tmp_path: Path, monkeypatch
    ) -> None:
        """
        A 2-step plan writing 2 files — verifies sequential step iteration.

        Note: plans with ≥3 independent steps trigger MultiAgentSwarm
        (_PARALLEL_THRESHOLD=3), which spawns separate workers incompatible
        with a single httpx mock. Keeping it at 2 stays on the sequential path.
        """
        import backend.server as srv
        monkeypatch.setattr(srv, "_CHAT_AGENT_WORKSPACE_ROOT", tmp_path)

        plan = _multi_step_plan([
            {"desc": "Write alpha.txt", "files": ["alpha.txt"], "type": "create"},
            {"desc": "Write beta.txt", "files": ["beta.txt"], "type": "create"},
        ])
        llm_responses = [
            plan,
            _exec("write_file", {"path": "alpha.txt", "content": "alpha"}), VERIFIER_JSON,
            _exec("write_file", {"path": "beta.txt", "content": "beta"}), VERIFIER_JSON,
            JUDGE_JSON,
        ]
        monkeypatch.setattr(
            "httpx.AsyncClient.post",
            _nim_post_factory(llm_responses),
        )

        headers = _auth_headers(client)
        resp = client.post("/api/chat/send", headers=headers, json={
            "session_id": f"multi-step-{uuid.uuid4()}",
            "agent_mode": True,
            "content": "Create alpha.txt and beta.txt",
        })
        assert resp.status_code == 202, resp.text
        job = _poll_job(client, headers, resp.json()["job_id"], timeout=30.0)

        workspace_files = list(tmp_path.rglob("*.txt"))
        assert job["status"] == "succeeded", (
            f"Job stuck in '{job['status']}'\n"
            f"Progress: {[e['phase'] + ': ' + e['message'] for e in job.get('progress_events', [])]}"
        )
        assert workspace_files, (
            f"No .txt files found. Job: {job['status']}, error: {job.get('error')}\n"
            f"Progress: {[e['phase'] + ': ' + e['message'] for e in job.get('progress_events', [])]}"
        )

    def test_agent_github_comment_after_pr_merge(
        self, client: TestClient, monkeypatch
    ) -> None:
        """Merge PR then comment on the issue — tests tool chaining."""
        plan = _multi_step_plan([
            {"desc": "Merge the PR", "files": [], "type": "github"},
            {"desc": "Comment on the resolved issue", "files": [], "type": "github"},
        ])
        exec_merge = _exec("github_merge_pull_request", {
            "repo_name": "strikersam/local-llm-server",
            "pull_number": 99,
            "merge_method": "merge",
        })
        exec_comment = _exec("github_comment_on_issue", {
            "repo_name": "strikersam/local-llm-server",
            "issue_number": 42,
            "body": "Fixed in #99 — now merged to main.",
        })

        _gh_comment = {
            "id": 123456,
            "body": "Fixed in #99 — now merged to main.",
            "html_url": "https://github.com/strikersam/local-llm-server/issues/42#issuecomment-123456",
        }

        llm_responses = [
            plan,
            exec_merge, VERIFIER_JSON,
            exec_comment, VERIFIER_JSON,
            JUDGE_JSON,
        ]
        mock_post, mock_get, mock_put = _build_agent_http_mock(
            llm_responses=llm_responses,
            github_post_results={"/issues/42/comments": _gh_comment},
            github_put_results={"/pulls/99/merge": _GH_MERGE_RESPONSE},
        )
        monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
        monkeypatch.setattr("httpx.AsyncClient.get", mock_get)
        monkeypatch.setattr("httpx.AsyncClient.put", mock_put)

        headers = _auth_headers(client)
        resp = client.post("/api/chat/send", headers=headers, json={
            "session_id": f"merge-comment-{uuid.uuid4()}",
            "agent_mode": True,
            "content": "Merge PR #99 and comment on issue #42",
        })
        assert resp.status_code == 202, resp.text
        job = _poll_job(client, headers, resp.json()["job_id"], timeout=30.0)
        assert job["status"] == "succeeded"

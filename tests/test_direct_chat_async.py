from __future__ import annotations

import asyncio
import time
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

import direct_chat
import proxy
from agent.job_manager import AgentJobManager, make_isolated_workspace
from agent.state import AgentSessionStore
from runtimes.base import RuntimeReadinessReport


def _fake_user() -> direct_chat.UserInfo:
    return direct_chat.UserInfo(id="user-1", email="tester@example.com")


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self._content = content

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


class _FakeChatResult:
    def __init__(self, content: str) -> None:
        self.response = _FakeResponse(content)
        self.provider = type("Provider", (), {"provider_id": "local"})()
        self.model = "qwen3-coder:30b"


def test_agent_mode_queues_async_job(monkeypatch, tmp_path: Path):
    proxy.app.dependency_overrides[direct_chat._get_current_user] = _fake_user
    monkeypatch.setattr(direct_chat, "_direct_chat_store", AgentSessionStore(db_path=str(tmp_path / "chat.db")))
    monkeypatch.setattr(direct_chat, "_agent_jobs", AgentJobManager())
    monkeypatch.setattr(direct_chat, "_agent_workspace_root", tmp_path / "workspaces")

    # Stub PROVIDER_ROUTER so _run_agent_job can resolve provider settings
    class _FakeProvider:
        priority = 1
        api_key = None
        normalized_base_url = "http://localhost:11434"
        def auth_headers(self) -> dict[str, str]:
            return {}

    class _FakeRouter:
        providers = (_FakeProvider(),)

    monkeypatch.setattr(proxy.app.state, "PROVIDER_ROUTER", _FakeRouter(), raising=False)

    async def fake_readiness(self, spec):
        return RuntimeReadinessReport(runtime_id="internal_agent", ready=True, selected_runtime="internal_agent")

    class FakeRunner:
        def __init__(self, **kwargs):
            pass

        async def run(self, **kwargs):
            return {"summary": "Agent completed asynchronously", "judge": {"verdict": "APPROVED"}, "steps": []}

    monkeypatch.setattr("runtimes.adapters.internal_agent.InternalAgentAdapter.readiness_check", fake_readiness)
    monkeypatch.setattr("agent.loop.AgentRunner", FakeRunner)

    client = TestClient(proxy.app)
    # Use 5+ words with a code-op keyword so the trivial-message filter doesn't downgrade to regular chat
    response = client.post("/api/chat/send", json={"content": "Please implement this important new feature", "agent_mode": True})
    assert response.status_code == 202
    body = response.json()
    assert body["status"] in {"queued", "running"}
    assert body["job_id"]

    for _ in range(10):
        job_resp = client.get(f"/api/chat/agent-jobs/{body['job_id']}")
        assert job_resp.status_code == 200
        if job_resp.json()["status"] == "succeeded":
            break
        time.sleep(0.05)

    final_job = client.get(f"/api/chat/agent-jobs/{body['job_id']}").json()
    assert final_job["status"] == "succeeded"
    assert final_job["result"]["response"] == "Agent completed asynchronously"

    proxy.app.dependency_overrides.clear()


def test_agent_mode_returns_runtime_validation_errors(monkeypatch, tmp_path: Path):
    proxy.app.dependency_overrides[direct_chat._get_current_user] = _fake_user
    monkeypatch.setattr(direct_chat, "_direct_chat_store", AgentSessionStore(db_path=str(tmp_path / "chat2.db")))
    monkeypatch.setattr(direct_chat, "_agent_jobs", AgentJobManager())

    async def fake_readiness(self, spec):
        return RuntimeReadinessReport(
            runtime_id="internal_agent",
            ready=False,
            selected_runtime="internal_agent",
            summary="Missing task harness",
            issues=[],
        )

    monkeypatch.setattr("runtimes.adapters.internal_agent.InternalAgentAdapter.readiness_check", fake_readiness)

    client = TestClient(proxy.app)
    response = client.post("/api/chat/send", json={"content": "Please implement this important new feature", "agent_mode": True})
    assert response.status_code == 412
    assert response.json()["detail"]["ready"] is False

    proxy.app.dependency_overrides.clear()


def test_regular_chat_remains_sync_and_does_not_queue_job(monkeypatch, tmp_path: Path):
    proxy.app.dependency_overrides[direct_chat._get_current_user] = _fake_user
    monkeypatch.setattr(direct_chat, "_direct_chat_store", AgentSessionStore(db_path=str(tmp_path / "chat3.db")))
    job_manager = AgentJobManager()
    monkeypatch.setattr(direct_chat, "_agent_jobs", job_manager)

    class FakeRouter:
        providers = []

        async def chat_completion(self, payload):
            return _FakeChatResult("Direct response")

    monkeypatch.setattr(proxy.app.state, "PROVIDER_ROUTER", FakeRouter(), raising=False)

    client = TestClient(proxy.app)
    response = client.post("/api/chat/send", json={"content": "Hello", "agent_mode": False})
    assert response.status_code == 200
    assert response.json()["response"] == "Direct response"
    assert job_manager.list_jobs() == []

    proxy.app.dependency_overrides.clear()


def test_make_isolated_workspace_rejects_path_traversal(tmp_path: Path):
    with pytest.raises(ValueError):
        make_isolated_workspace(tmp_path, "../escape", "job-1")

    with pytest.raises(ValueError):
        make_isolated_workspace(tmp_path, "session-1", "../../escape")


def test_make_isolated_workspace_hashes_valid_identifiers(tmp_path: Path):
    workspace = make_isolated_workspace(tmp_path, "session-1", "job-1")

    assert workspace.parent.name != "session-1"
    assert workspace.name != "job-1"
    assert workspace.exists()


def test_agent_mode_github_preflight_missing_token(monkeypatch, tmp_path: Path):
    """
    Verifies that agent-mode preflight validation fails with a structured error when Git is present but no GitHub token is available.
    
    Posts to /api/chat/send with agent_mode=True while faking a present `git` binary and returning no GitHub token, and asserts the endpoint responds with HTTP 412, `detail["ready"] is False`, and one of the reported issue codes is `missing_github_token`.
    """
    proxy.app.dependency_overrides[direct_chat._get_current_user] = _fake_user
    monkeypatch.setattr(direct_chat, "_direct_chat_store", AgentSessionStore(db_path=str(tmp_path / "chat4.db")))
    monkeypatch.setattr(direct_chat, "_agent_jobs", AgentJobManager())
    monkeypatch.setattr(direct_chat, "_agent_workspace_root", tmp_path / "workspaces")

    # Ensure git binary appears present but no token is returned
    import shutil
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/git")
    async def fake_get_token(email):
        """
        Always indicate that no token exists for the provided email.
        
        This test stub simulates a token lookup that never finds a token.
        
        Returns:
            None: No token found for the provided email.
        """
        return None
    monkeypatch.setattr(direct_chat, "_get_github_token_for_user", fake_get_token)

    class _FakeProvider:
        priority = 1
        api_key = None
        normalized_base_url = "http://localhost:11434"
        def auth_headers(self) -> dict[str, str]:
            """
            Provide HTTP authentication headers required by the provider.
            
            Returns:
                dict: Mapping of header names to header values. Empty dict if no authentication is needed.
            """
            return {}

    class _FakeRouter:
        providers = (_FakeProvider(),)

    monkeypatch.setattr(proxy.app.state, "PROVIDER_ROUTER", _FakeRouter(), raising=False)

    client = TestClient(proxy.app)
    response = client.post("/api/chat/send", json={"content": "Please clone my repo and create a PR", "agent_mode": True})
    assert response.status_code == 412
    detail = response.json().get("detail")
    assert detail and detail.get("ready") is False
    issues = detail.get("issues") or []
    codes = {i.get("code") for i in issues}
    assert "missing_github_token" in codes

    proxy.app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_job_result_normalizes_and_exposes_final_message():
    """
    Verifies that AgentJobManager normalizes a job's final run summary into job.result["response"] and exposes it as as_dict()["final_message"].
    
    Creates a job, starts a runner that emits a heartbeat and returns a final textual summary, waits for the job to complete, and asserts the job succeeded and the final summary appears in both the job's result and its serialized representation.
    """
    import asyncio
    from agent.job_manager import AgentJobManager

    mgr = AgentJobManager()
    job = mgr.create_job(session_id="s1", instruction="do work")

    async def runner(heartbeat):
        """
        Emit an initial "planning" heartbeat and produce a final run summary.
        
        Parameters:
            heartbeat (Callable[[str, str], None]): Function to emit progress updates; called with (status, message).
        
        Returns:
            dict: Result with keys "summary" (final textual summary) and "steps" (list of step records).
        """
        heartbeat("planning", "planning")
        return {"summary": "Final textual summary", "steps": []}

    mgr.start_job(job.job_id, runner)

    for _ in range(200):
        if job.status in ("succeeded", "failed"):
            break
        await asyncio.sleep(0.01)

    assert job.status == "succeeded"
    assert isinstance(job.result, dict)
    assert job.result.get("response") == "Final textual summary"
    d = job.as_dict()
    assert d.get("final_message") == "Final textual summary"


@pytest.mark.asyncio
async def test_job_failure_structures_runtime_preflight(monkeypatch):
    """
    Validates that a runtime preflight failure raised during agent job execution is converted into a structured job error.
    
    Starts an AgentJobManager job whose runner immediately raises RuntimePreflightError and asserts the job transitions to "failed" with an error dict containing `"code": "runtime_preflight"` and a `"report"` key whose value is a dict.
    """
    from runtimes.base import RuntimePreflightError, RuntimeReadinessReport
    mgr = AgentJobManager()
    job = mgr.create_job(session_id="s2", instruction="run git ops")

    class DummyReport:
        def __init__(self):
            """
            Initialize a DummyReport describing an unavailable internal-agent runtime.
            
            Sets attributes that represent a runtime readiness failure.
            
            Attributes:
                runtime_id (str): Identifier of the runtime; "internal_agent".
                ready (bool): Readiness flag; False.
                selected_runtime (str): Chosen runtime identifier; "internal_agent".
                summary (str): Short explanation of the failure; "docker missing".
            """
            self.runtime_id = "internal_agent"
            self.ready = False
            self.selected_runtime = "internal_agent"
            self.summary = "docker missing"
        def as_dict(self):
            """
            Return this readiness report as a plain dictionary.
            
            Returns:
                dict: Dictionary with keys:
                    - runtime_id (str): Identifier of the runtime.
                    - ready (bool): Whether the runtime is ready.
                    - summary (str): Human-readable summary of the readiness state.
            """
            return {"runtime_id": self.runtime_id, "ready": self.ready, "summary": "docker missing"}

    async def runner(heartbeat):
        # Simulate runtime preflight failure thrown during execution
        """
        Simulated agent runner that immediately raises a runtime preflight error for the "internal_agent" runtime.
        
        Parameters:
            heartbeat (callable): Progress heartbeat callback; ignored by this simulated runner.
        
        Raises:
            RuntimePreflightError: Raised for runtime "internal_agent" with a report describing the readiness failure.
        """
        raise RuntimePreflightError("internal_agent", DummyReport())

    mgr.start_job(job.job_id, runner)

    for _ in range(200):
        if job.status in ("succeeded", "failed"):
            break
        await asyncio.sleep(0.01)

    assert job.status == "failed"
    assert isinstance(job.error, dict)
    assert job.error.get("code") == "runtime_preflight"
    assert "report" in job.error and isinstance(job.error["report"], dict)

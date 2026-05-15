from __future__ import annotations

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
    proxy.app.dependency_overrides[direct_chat._get_current_user] = _fake_user
    monkeypatch.setattr(direct_chat, "_direct_chat_store", AgentSessionStore(db_path=str(tmp_path / "chat4.db")))
    monkeypatch.setattr(direct_chat, "_agent_jobs", AgentJobManager())
    monkeypatch.setattr(direct_chat, "_agent_workspace_root", tmp_path / "workspaces")

    # Ensure git binary appears present but no token is returned
    import shutil
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/git")
    monkeypatch.setattr(direct_chat, "_get_github_token_for_user", lambda email: None)

    class _FakeProvider:
        priority = 1
        api_key = None
        normalized_base_url = "http://localhost:11434"
        def auth_headers(self) -> dict[str, str]:
            """
            Return authentication headers for the provider.
            
            Returns:
                dict[str, str]: Mapping of HTTP header names to values; empty if the provider requires no authentication.
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
    import asyncio
    from agent.job_manager import AgentJobManager

    mgr = AgentJobManager()
    job = mgr.create_job(session_id="s1", instruction="do work")

    async def runner(heartbeat):
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
async def test_job_failure_structures_runtime_preflight():
    import asyncio
    from agent.job_manager import AgentJobManager
    from runtimes.base import RuntimePreflightError
    mgr = AgentJobManager()
    job = mgr.create_job(session_id="s2", instruction="run git ops")

    class DummyReport:
        def __init__(self):
            """
            Initialize the report with defaults indicating the internal agent runtime is not ready.
            
            Sets:
                runtime_id: "internal_agent"
                ready: False
                selected_runtime: "internal_agent"
            """
            self.runtime_id = "internal_agent"
            self.ready = False
            self.selected_runtime = "internal_agent"
        def as_dict(self):
            return {"runtime_id": self.runtime_id, "ready": self.ready, "summary": "docker missing"}
        @property
        def summary(self):
            return "docker missing"

    async def runner(heartbeat):
        # Simulate runtime preflight failure thrown during execution
        """
        Simulates a runner that fails preflight by raising a RuntimePreflightError.
        
        This asynchronous runner always raises RuntimePreflightError for runtime "internal_agent"
        using a DummyReport instance.
        
        Parameters:
            heartbeat: Callable[[str, str], None] — progress callback invoked by runners (unused here).
        
        Raises:
            RuntimePreflightError: Indicates the runtime preflight failed with an attached report.
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

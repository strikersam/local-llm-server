from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

import direct_chat
import proxy
from agent.job_manager import AgentJobManager
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
    response = client.post("/api/chat/send", json={"content": "Implement feature", "agent_mode": True})
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
    response = client.post("/api/chat/send", json={"content": "Implement feature", "agent_mode": True})
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

    proxy.app.state.PROVIDER_ROUTER = FakeRouter()

    client = TestClient(proxy.app)
    response = client.post("/api/chat/send", json={"content": "Hello", "agent_mode": False})
    assert response.status_code == 200
    assert response.json()["response"] == "Direct response"
    assert job_manager.list_jobs() == []

    proxy.app.dependency_overrides.clear()

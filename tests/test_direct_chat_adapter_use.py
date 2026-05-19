import pytest
import time
from fastapi.testclient import TestClient
import proxy
import direct_chat
from agent.state import AgentSessionStore
from agent.job_manager import AgentJobManager
from direct_chat import UserInfo
from runtimes.manager import get_runtime_manager
from runtimes.base import TaskResult


def _fake_user():
    return UserInfo(id="user123", email="test@example.com")


def test_specialized_runtime_execution(monkeypatch, tmp_path):
    proxy.app.dependency_overrides[direct_chat._get_current_user] = _fake_user
    monkeypatch.setattr(direct_chat, "_direct_chat_store", AgentSessionStore(db_path=str(tmp_path / "chat_adapter.db")))
    monkeypatch.setattr(direct_chat, "_agent_jobs", AgentJobManager())

    # Mock doctor
    class FakeDoctor:
        def __init__(self, **kwargs): pass
        async def check_all(self, **kwargs):
            from agent.doctor import PreflightReport
            return PreflightReport(ready=True, summary="OK")
    monkeypatch.setattr("direct_chat.DirectChatDoctor", FakeDoctor)

    # Mock a specialized runtime
    class FakeAdapter:
        RUNTIME_ID = "specialized_v2"
        async def readiness_check(self, spec):
            from runtimes.base import RuntimeReadinessReport
            return RuntimeReadinessReport(runtime_id="specialized_v2", ready=True)
        async def execute(self, spec):
            return TaskResult(runtime_id="specialized_v2", task_id=spec.task_id, success=True, output="Specialized output")

    rm = get_runtime_manager()
    monkeypatch.setattr(rm, "select_runtime", lambda task_type, preferred_id=None: (FakeAdapter(), []))

    # Mock PROVIDER_ROUTER
    class _FakeRouter:
        providers = []
    proxy.app.state.PROVIDER_ROUTER = _FakeRouter()

    # Auth: patch proxy.verify_token (the local name imported via `from tokens import`)
    # AND add token to VALID_API_KEYS as belt-and-suspenders.
    # The JWT path sets email from the payload; we need it to match the job owner.
    monkeypatch.setattr(proxy, "verify_token", lambda token, **kwargs: {
        "sub": "user123", "email": "test@example.com", "name": "Test User", "role": "user"
    })
    monkeypatch.setattr(proxy, "VALID_API_KEYS", {"fake-token"})

    client = TestClient(proxy.app)
    session_id = "adapter-session"
    headers = {"Authorization": "Bearer fake-token"}

    response = client.post(
        "/api/chat/send",
        json={"content": "Use specialized tool", "agent_mode": True, "session_id": session_id},
        headers=headers,
    )
    assert response.status_code == 202

    # Poll until the specialized runtime result appears in the session
    max_wait = 10.0
    status_data = {}
    while max_wait > 0:
        resp = client.get(f"/api/chat/agent-status?session_id={session_id}", headers=headers)
        if resp.status_code == 200:
            status_data = resp.json()
            if status_data.get("latest_summary") == "Specialized output":
                break
        time.sleep(0.5)
        max_wait -= 0.5

    assert status_data.get("latest_summary") == "Specialized output", (
        f"Expected 'Specialized output', got status_data={status_data}"
    )

    proxy.app.dependency_overrides.clear()

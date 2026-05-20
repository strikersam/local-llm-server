import pytest
from fastapi.testclient import TestClient
import proxy
import direct_chat
from agent.state import AgentSessionStore
from agent.job_manager import AgentJobManager
from direct_chat import UserInfo
from agent.schemas import DirectChatState
import time

def _fake_user():
    return UserInfo(id="user123", email="test@example.com")

@pytest.fixture
def clean_store(tmp_path):
    return AgentSessionStore(db_path=str(tmp_path / "evolution.db"))

def test_intent_clarification(monkeypatch, clean_store):
    proxy.app.dependency_overrides[direct_chat._get_current_user] = _fake_user
    monkeypatch.setattr(direct_chat, "_direct_chat_store", clean_store)

    client = TestClient(proxy.app)
    headers = {"Authorization": "Bearer fake-token"}
    response = client.post("/api/chat/send", json={"content": "Fix it", "agent_mode": False}, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert "detail" in data["response"] or "provide" in data["response"]
    assert data["intent"] == "clarify"
    assert data["state"] == "needs_input"

def test_sticky_objective_memory(monkeypatch, clean_store):
    proxy.app.dependency_overrides[direct_chat._get_current_user] = _fake_user
    monkeypatch.setattr(direct_chat, "_direct_chat_store", clean_store)
    monkeypatch.setattr(direct_chat, "_agent_jobs", AgentJobManager())

    # Mock PROVIDER_ROUTER
    class _FakeProvider:
        priority = 1
        api_key = None
        normalized_base_url = "http://localhost:11434"
        def auth_headers(self) -> dict: return {}

    class _FakeRouter:
        providers = [_FakeProvider()]
    proxy.app.state.PROVIDER_ROUTER = _FakeRouter()

    # Mock doctor & readiness
    class FakeDoctor:
        def __init__(self, **kwargs): pass
        async def check_all(self, **kwargs):
            from agent.doctor import PreflightReport
            return PreflightReport(ready=True, summary="OK")
    monkeypatch.setattr("direct_chat.DirectChatDoctor", FakeDoctor)

    async def fake_readiness(self, spec):
        from runtimes.base import RuntimeReadinessReport
        return RuntimeReadinessReport(runtime_id="internal_agent", ready=True, selected_runtime="internal_agent")
    monkeypatch.setattr("runtimes.adapters.internal_agent.InternalAgentAdapter.readiness_check", fake_readiness)

    client = TestClient(proxy.app)
    headers = {"Authorization": "Bearer fake-token"}
    session_id = "sticky-eval"

    # turn 1
    client.post("/api/chat/send", json={"content": "Implement auth feature", "agent_mode": True, "session_id": session_id}, headers=headers)

    # turn 2 - should remember objective
    session = clean_store.get(session_id)
    assert session.active_objective == "Implement auth feature"

def test_humanized_momentum_status(monkeypatch, clean_store):
    proxy.app.dependency_overrides[direct_chat._get_current_user] = _fake_user
    monkeypatch.setattr(direct_chat, "_direct_chat_store", clean_store)
    mgr = AgentJobManager()
    monkeypatch.setattr(direct_chat, "_agent_jobs", mgr)

    # Bypass auth
    import proxy as proxy_mod
    monkeypatch.setattr(proxy_mod.JWTAuthMiddleware, "dispatch", lambda req, cn: cn(req))
    monkeypatch.setattr("tokens.verify_token", lambda token, **kwargs: {"id": "user123", "email": "test@example.com"})

    session_id = "momentum-eval"
    job = mgr.create_job(session_id=session_id, owner_id="test@example.com", instruction="test")
    job.status = "running"
    job.phase = "execution"
    # mock old update
    job.updated_at = "2024-01-01T00:00:00Z"
    job.progress_events.append({"timestamp": job.updated_at, "phase": "execution", "message": "Tool: run_command"})

    client = TestClient(proxy.app)
    # Need Authorization header for middleware bypass to work or just mock the state.user
    response = client.get(f"/api/chat/agent-status?session_id={session_id}", headers={"Authorization": "Bearer fake"})

    if response.status_code == 200:
        data = response.json()
        assert "Still" in data["humanized_progress"]

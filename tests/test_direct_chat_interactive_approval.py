import pytest
import asyncio
import httpx
from httpx import AsyncClient
import proxy
import direct_chat
from agent.state import AgentSessionStore
from agent.job_manager import AgentJobManager
from direct_chat import UserInfo
from agent.models import AgentPlan, AgentStep

def _fake_user():
    return UserInfo(id="user123", email="test@example.com")

@pytest.mark.asyncio
async def test_risky_plan_approval_gate(monkeypatch, tmp_path):
    # Setup
    monkeypatch.setenv("DIRECT_CHAT_STRICT_PREFLIGHT", "false")
    monkeypatch.setattr(direct_chat, "_direct_chat_store", AgentSessionStore(db_path=str(tmp_path / "chat_interactive.db")))
    monkeypatch.setattr(direct_chat, "_agent_jobs", AgentJobManager())

    # Bypass auth entirely
    def mock_verify(token, **kwargs):
        return {"sub": "user123", "email": "test@example.com", "name": "Test User", "role": "user"}
    monkeypatch.setattr("tokens.verify_token", mock_verify)
    monkeypatch.setattr("proxy.verify_token", mock_verify)
    monkeypatch.setattr("direct_chat.verify_token", mock_verify)

    # Mock doctor
    class FakeDoctor:
        def __init__(self, **kwargs): pass
        async def check_all(self, **kwargs):
            from agent.doctor import PreflightReport
            return PreflightReport(ready=True, summary="OK")
    monkeypatch.setattr("direct_chat.DirectChatDoctor", FakeDoctor)

    # Mock runner
    class FakeRunner:
        def __init__(self, **kwargs): pass
        async def plan(self, **kwargs):
            return AgentPlan(goal="Risky", steps=[AgentStep(id=1, description="rm -rf /", type="edit")], requires_risky_review=True)
        async def run(self, **kwargs):
            return {"summary": "Risky done"}

    monkeypatch.setattr("agent.loop.AgentRunner", FakeRunner)

    # Mock runtime manager to fallback to internal agent
    class FakeRuntimeMgr:
        def select_runtime(self, *args, **kwargs):
            return None, []
    monkeypatch.setattr("runtimes.manager.get_runtime_manager", lambda: FakeRuntimeMgr())

    # Mock PROVIDER_ROUTER
    class _FakeProvider:
        priority = 1
        api_key = None
        normalized_base_url = "http://localhost:11434"
        def auth_headers(self) -> dict: return {}

    class _FakeRouter:
        providers = [_FakeProvider()]
    proxy.app.state.PROVIDER_ROUTER = _FakeRouter()

    class _FakeWSMgr:
        async def validate_repo_ref(self, *args, **kwargs): return {"ok": True, "issues": []}
        def create_workspace(self, **kwargs):
            from types import SimpleNamespace
            return _FakeWSMgr()
        @property
        def root_path(self): return "/tmp/fake-ws"

    proxy.app.state.webui_workspaces = _FakeWSMgr()

    proxy.app.dependency_overrides[direct_chat._get_current_user] = _fake_user

    # Bypass JWTAuthMiddleware by adding token to VALID_API_KEYS
    monkeypatch.setattr(proxy, "VALID_API_KEYS", {"fake-token"})

    async with AsyncClient(transport=httpx.ASGITransport(app=proxy.app), base_url="http://test") as ac:
        session_id = "interactive-session"

        # Start the job
        # Use a keyword that triggers execution intent to be safe
        headers = {"Authorization": "Bearer fake-token"}
        response = await ac.post("/api/chat/send", json={
            "content": "Please fix the bugs in this risky plan",
            "agent_mode": True,
            "session_id": session_id
        }, headers=headers)
        assert response.status_code == 202

        # Wait for the job to reach needs_approval state
        max_wait = 15
        status_data = {}
        while max_wait > 0:
            status = await ac.get(f"/api/chat/agent-status?session_id={session_id}", headers=headers)
            if status.status_code == 200:
                status_data = status.json()
                if status_data.get("state") == "needs_approval":
                    break
                if status_data.get("state") == "failed_with_fix_hint":
                    pytest.fail(f"Job failed unexpectedly: {status_data.get('latest_error')}")
            await asyncio.sleep(0.5)
            max_wait -= 0.5

        if status_data.get("state") != "needs_approval":
            print(f"DEBUG: Final status_data: {status_data}")
            # Try to see if it failed
            job = direct_chat._agent_jobs.get_job(status_data.get("agents", [{}])[0].get("job_id"))
            if job and job.error:
                print(f"DEBUG: Job error: {job.error}")

        assert status_data.get("state") == "needs_approval", f"State was {status_data.get('state')} instead of needs_approval"

        # Resume with approval
        resume = await ac.post(f"/api/chat/resume/{session_id}", json={"action": "approve", "input": ""}, headers=headers)
        assert resume.status_code == 200

        # Verify it finishes
        max_wait = 10
        while max_wait > 0:
            status = await ac.get(f"/api/chat/agent-status?session_id={session_id}", headers=headers)
            if status.status_code == 200:
                status_data = status.json()
                if status_data.get("state") == "completed":
                    break
            await asyncio.sleep(0.5)
            max_wait -= 0.5

        assert status_data.get("state") == "completed"

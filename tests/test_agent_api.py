from fastapi.testclient import TestClient
from types import SimpleNamespace

import proxy
from admin_auth import AdminIdentity
from key_store import KeyStore


def test_openai_chat_completions_exact_output_short_circuits(monkeypatch):
    def fake_verify():
        return proxy.AuthContext(
            key="test-key",
            email="tester@example.com",
            department="engineering",
            key_id="kid_test",
            source="legacy",
        )

    proxy.app.dependency_overrides[proxy.verify_api_key] = fake_verify

    client = TestClient(proxy.app)
    resp = client.post(
        "/v1/chat/completions",
        json={
            "model": "qwen3-coder:30b",
            "messages": [{"role": "user", "content": "Reply with exactly: READY"}],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["choices"][0]["message"]["content"] == "READY"

    proxy.app.dependency_overrides.clear()


def test_openai_chat_completions_exact_output_streams(monkeypatch):
    def fake_verify():
        return proxy.AuthContext(
            key="test-key",
            email="tester@example.com",
            department="engineering",
            key_id="kid_test",
            source="legacy",
        )

    proxy.app.dependency_overrides[proxy.verify_api_key] = fake_verify

    client = TestClient(proxy.app)
    with client.stream(
        "POST",
        "/v1/chat/completions",
        json={
            "model": "qwen3-coder:30b",
            "stream": True,
            "messages": [{"role": "user", "content": "Reply with exactly: READY"}],
        },
    ) as resp:
        body = "".join(chunk for chunk in resp.iter_text())

    assert resp.status_code == 200
    assert '"content":"READY"' in body
    assert "data: [DONE]" in body

    proxy.app.dependency_overrides.clear()


def test_agent_session_endpoints_require_and_return_state(monkeypatch):
    def fake_verify():
        return proxy.AuthContext(
            key="test-key",
            email="tester@example.com",
            department="engineering",
            key_id="kid_test",
            source="legacy",
        )

    async def fake_run(**kwargs):
        return {
            "goal": kwargs["instruction"],
            "plan": {"goal": kwargs["instruction"], "steps": []},
            "steps": [],
            "commits": [],
            "summary": "ok",
        }

    proxy.app.dependency_overrides[proxy.verify_api_key] = fake_verify
    monkeypatch.setattr(proxy, "AGENT_RUNNER", type("Runner", (), {"run": staticmethod(fake_run)})())

    client = TestClient(proxy.app)

    create = client.post("/agent/sessions", json={"title": "Test Session"})
    assert create.status_code == 200
    session_id = create.json()["session_id"]

    fetch = client.get(f"/agent/sessions/{session_id}")
    assert fetch.status_code == 200
    assert fetch.json()["title"] == "Test Session"

    run = client.post(
        f"/agent/sessions/{session_id}/run",
        json={"instruction": "Do the thing", "auto_commit": False, "max_steps": 2},
    )
    assert run.status_code == 200
    assert run.json()["result"]["summary"] == "ok"

    proxy.app.dependency_overrides.clear()


def test_agent_session_run_reuses_bearer_key_for_same_origin_provider(monkeypatch, tmp_path):
    def fake_verify():
        return proxy.AuthContext(
            key="test-key",
            email="tester@example.com",
            department="engineering",
            key_id="kid_test",
            source="legacy",
        )

    captured: dict[str, object] = {}

    class FakeRunner:
        def __init__(
            self,
            *,
            ollama_base: str,
            workspace_root,
            provider_headers=None,
            provider_temperature=None,
            email=None,
            department=None,
            key_id=None,
        ) -> None:
            captured["ollama_base"] = ollama_base
            captured["workspace_root"] = workspace_root
            captured["provider_headers"] = provider_headers
            captured["provider_temperature"] = provider_temperature
            captured["email"] = email
            captured["department"] = department
            captured["key_id"] = key_id

        async def run(self, **kwargs):
            return {
                "goal": kwargs["instruction"],
                "plan": {"goal": kwargs["instruction"], "steps": []},
                "steps": [],
                "commits": [],
                "summary": "ok",
            }

    monkeypatch.setattr(proxy, "AgentRunner", FakeRunner)
    monkeypatch.setattr(
        proxy.WEBUI_PROVIDERS,
        "get_secret",
        lambda provider_id: SimpleNamespace(
            base_url="http://testserver/v1",
            api_key=None,
            default_model="qwen3-coder:30b",
            default_temperature=0.25,
        ),
    )
    monkeypatch.setattr(
        proxy.WEBUI_WORKSPACES,
        "get",
        lambda workspace_id: SimpleNamespace(path=str(tmp_path)),
    )
    proxy.app.dependency_overrides[proxy.verify_api_key] = fake_verify

    client = TestClient(proxy.app)
    create = client.post(
        "/agent/sessions",
        json={"title": "Test Session", "provider_id": "prov_proxy", "workspace_id": "ws_proxy"},
    )
    assert create.status_code == 200
    session_id = create.json()["session_id"]

    run = client.post(
        f"/agent/sessions/{session_id}/run",
        json={
            "instruction": "Do the thing",
            "provider_id": "prov_proxy",
            "workspace_id": "ws_proxy",
            "auto_commit": False,
            "max_steps": 2,
        },
    )
    assert run.status_code == 200
    assert run.json()["result"]["summary"] == "ok"
    assert captured["ollama_base"] == "http://testserver/v1"
    assert captured["provider_headers"] == {"Authorization": "Bearer test-key"}

    proxy.app.dependency_overrides.clear()


def test_agent_run_returns_structured_failure(monkeypatch):
    def fake_verify():
        return proxy.AuthContext(
            key="test-key",
            email="tester@example.com",
            department="engineering",
            key_id="kid_test",
            source="legacy",
        )

    async def fake_run(**kwargs):
        raise RuntimeError("planner backend unavailable")

    proxy.app.dependency_overrides[proxy.verify_api_key] = fake_verify
    monkeypatch.setattr(proxy, "AGENT_RUNNER", type("Runner", (), {"run": staticmethod(fake_run)})())

    client = TestClient(proxy.app)
    resp = client.post("/agent/run", json={"instruction": "Do the thing", "max_steps": 1})
    assert resp.status_code == 200
    assert resp.json()["result"]["status"] == "failed"
    assert "planner backend unavailable" in resp.json()["result"]["summary"]

    proxy.app.dependency_overrides.clear()


def test_admin_api_login_status_and_control(monkeypatch):
    monkeypatch.setattr(
        proxy.ADMIN_AUTH,
        "authenticate",
        lambda username, password: AdminIdentity(username=username or "swami", auth_source="windows"),
    )
    monkeypatch.setattr(
        proxy.SERVICE_MANAGER,
        "get_status",
        lambda: {
            "services": {
                "ollama": {"name": "ollama", "running": True, "pid": 101, "detail": "http://localhost:11434/api/tags"},
                "proxy": {"name": "proxy", "running": True, "pid": 202, "detail": "http://localhost:8000/health"},
                "tunnel": {"name": "tunnel", "running": True, "pid": 303, "detail": "https://demo.trycloudflare.com"},
            },
            "public_url": "https://demo.trycloudflare.com",
            "pid_file_present": True,
            "timestamp": 123,
        },
    )
    monkeypatch.setattr(
        proxy.SERVICE_MANAGER,
        "control",
        lambda action, target, current_proxy_pid=None: {"ok": True, "message": f"{action}:{target}"},
    )

    client = TestClient(proxy.app)
    login = client.post("/admin/api/login", json={"username": "swami", "password": "secret"})
    assert login.status_code == 200
    token = login.json()["token"]

    status = client.get("/admin/api/status", headers={"Authorization": f"Bearer {token}"})
    assert status.status_code == 200
    assert status.json()["public_url"] == "https://demo.trycloudflare.com"
    assert status.json()["admin"]["username"] == "swami"

    control = client.post(
        "/admin/api/control",
        headers={"Authorization": f"Bearer {token}"},
        json={"action": "restart", "target": "tunnel"},
    )
    assert control.status_code == 200
    assert control.json()["message"] == "restart:tunnel"


def test_admin_api_user_crud(monkeypatch, tmp_path):
    store = KeyStore(tmp_path / "keys.json")
    monkeypatch.setattr(proxy, "KEY_STORE", store)

    session = proxy.ADMIN_AUTH.sessions.create(AdminIdentity(username="swami", auth_source="windows"))
    auth_header = {"Authorization": f"Bearer {session.token}"}
    client = TestClient(proxy.app)

    create = client.post(
        "/admin/api/users",
        headers=auth_header,
        json={"email": "alice@example.com", "department": "engineering"},
    )
    assert create.status_code == 200
    payload = create.json()
    key_id = payload["record"]["key_id"]
    assert payload["api_key"].startswith("test-key-")

    listing = client.get("/admin/api/users", headers=auth_header)
    assert listing.status_code == 200
    assert listing.json()["count"] == 1

    update = client.patch(
        f"/admin/api/users/{key_id}",
        headers=auth_header,
        json={"email": "alice@company.com", "department": "research"},
    )
    assert update.status_code == 200
    assert update.json()["record"]["department"] == "research"

    rotate = client.post(f"/admin/api/users/{key_id}/rotate", headers=auth_header)
    assert rotate.status_code == 200
    assert rotate.json()["api_key"].startswith("test-key-")

    delete = client.delete(f"/admin/api/users/{key_id}", headers=auth_header)
    assert delete.status_code == 200
    assert delete.json()["ok"] is True

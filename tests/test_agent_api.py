from fastapi.testclient import TestClient

import proxy


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

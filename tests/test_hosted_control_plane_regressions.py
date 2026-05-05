"""Regression coverage for hosted control-plane routes and agent profile shape."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _auth_headers(client: TestClient) -> dict[str, str]:
    login = client.post(
        "/api/auth/login",
        json={"email": "admin@llmrelay.local", "password": "WikiAdmin2026!"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_backend_server_exposes_schedules_routes(client: TestClient) -> None:
    headers = _auth_headers(client)

    listed = client.get("/api/schedules/", headers=headers)
    assert listed.status_code == 200
    assert "schedules" in listed.json()

    legacy_listed = client.get("/agent/scheduler/jobs", headers=headers)
    assert legacy_listed.status_code == 200
    assert "jobs" in legacy_listed.json()

    created = client.post(
        "/api/schedules/",
        headers=headers,
        json={
            "name": "Hosted smoke",
            "cron": "0 8 * * *",
            "instruction": "Run hosted smoke checks",
            "approval_gate": False,
        },
    )
    assert created.status_code == 200
    payload = created.json()
    assert payload["name"] == "Hosted smoke"
    assert payload["status"] == "active"

    legacy_created = client.post(
        "/agent/scheduler/jobs",
        headers=headers,
        json={
            "name": "Hosted smoke legacy",
            "cron": "0 9 * * *",
            "instruction": "Run hosted smoke checks via legacy route",
        },
    )
    assert legacy_created.status_code == 200
    assert legacy_created.json()["name"] == "Hosted smoke legacy"


def test_backend_server_exposes_observability_savings_and_usage(client: TestClient) -> None:
    headers = _auth_headers(client)

    savings = client.get("/api/observability/savings", headers=headers)
    assert savings.status_code == 200
    savings_data = savings.json()
    assert "summary" in savings_data
    assert "time_series" in savings_data

    usage = client.get("/api/observability/usage", headers=headers)
    assert usage.status_code == 200
    usage_data = usage.json()
    assert "total_requests" in usage_data
    assert "total_tokens" in usage_data
    assert "by_model" in usage_data


def test_agent_profile_api_preserves_ui_fields(client: TestClient) -> None:
    headers = _auth_headers(client)
    payload = {
        "name": "Engineer",
        "role": "Engineer",
        "description": "Receives QA issue reports",
        "system_prompt": "You are Engineer.",
        "preferred_runtime": "hermes",
        "fallback_runtimes": ["opencode"],
        "task_specializations": ["code_review", "repo_editing"],
        "requires_approval": True,
        "cost_policy": "local_only",
    }

    created = client.post("/api/agents/", headers=headers, json=payload)
    assert created.status_code == 201
    body = created.json()
    agent_id = body["agent_id"]

    try:
        assert body["role"] == "Engineer"
        assert body["preferred_runtime"] == "hermes"
        assert body["runtime_id"] == "hermes"
        assert body["fallback_runtimes"] == ["opencode"]
        assert body["task_specializations"] == ["code_review", "repo_editing"]
        assert body["task_types"] == ["code_review", "repo_editing"]
        assert body["requires_approval"] is True

        fetched = client.get(f"/api/agents/{agent_id}", headers=headers)
        assert fetched.status_code == 200
        fetched_body = fetched.json()
        assert fetched_body["role"] == "Engineer"
        assert fetched_body["preferred_runtime"] == "hermes"
        assert fetched_body["task_specializations"] == ["code_review", "repo_editing"]
        assert fetched_body["fallback_runtimes"] == ["opencode"]
        assert fetched_body["requires_approval"] is True
    finally:
        client.delete(f"/api/agents/{agent_id}", headers=headers)

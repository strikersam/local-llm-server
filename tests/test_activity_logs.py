from __future__ import annotations

import logging

import backend.server as server


def _auth_headers(client) -> dict[str, str]:
    login = client.post(
        "/api/auth/login",
        json={"email": "admin@llmrelay.local", "password": "WikiAdmin2026!"},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_activity_endpoint_includes_recent_error_logs(client) -> None:
    server.clear_error_log_buffer()
    logging.getLogger("qwen-proxy").error("Synthetic activity log failure for regression test")

    response = client.get("/api/activity", headers=_auth_headers(client))

    assert response.status_code == 200, response.text
    messages = [entry.get("message") for entry in response.json()["activity"]]
    assert "Synthetic activity log failure for regression test" in messages

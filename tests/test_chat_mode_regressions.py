from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock


def _auth_headers(client) -> dict[str, str]:
    login = client.post(
        "/api/auth/login",
        json={"email": "admin@llmrelay.local", "password": "WikiAdmin2026!"},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_chat_send_keeps_complex_prompt_on_direct_path_when_agent_mode_is_off(
    client, monkeypatch
) -> None:
    direct_reply = AsyncMock(return_value="Direct answer")
    unexpected_agent = AsyncMock(side_effect=AssertionError("agent path should not run"))

    monkeypatch.setattr("backend.server.call_llm", direct_reply)
    monkeypatch.setattr("backend.server._run_agent_loop", unexpected_agent)

    response = client.post(
        "/api/chat/send",
        headers=_auth_headers(client),
        json={
            "session_id": "not-an-object-id",
            "agent_mode": False,
            "content": (
                "You are helping with a code-edit task. Given a React component that "
                "leaks requests on rapid navigation, propose the exact code changes to "
                "abort stale fetches, show the updated code snippet, and end with a "
                "conventional commit message."
            ),
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["response"] == "Direct answer"
    direct_reply.assert_awaited_once()
    unexpected_agent.assert_not_called()


def test_chat_send_uses_agent_path_only_when_agent_mode_is_enabled(
    client, monkeypatch
) -> None:
    direct_reply = AsyncMock(return_value="Direct answer")
    agent_reply = AsyncMock(return_value="Agent answer")

    monkeypatch.setattr("backend.server.call_llm", direct_reply)
    monkeypatch.setattr("backend.server._run_agent_loop", agent_reply)

    response = client.post(
        "/api/chat/send",
        headers=_auth_headers(client),
        json={
            "session_id": "not-an-object-id-2",
            "agent_mode": True,
            "content": "Plan the fix and edit the code.",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["response"] == "Agent answer"
    agent_reply.assert_awaited_once()
    direct_reply.assert_not_called()


def test_chat_send_falls_back_to_direct_answer_when_agent_mode_times_out(
    client, monkeypatch
) -> None:
    direct_reply = AsyncMock(return_value="Recovered direct answer")
    timed_out_agent = AsyncMock(side_effect=asyncio.TimeoutError())

    monkeypatch.setattr("backend.server.call_llm", direct_reply)
    monkeypatch.setattr("backend.server._run_agent_loop", timed_out_agent)

    response = client.post(
        "/api/chat/send",
        headers=_auth_headers(client),
        json={
            "session_id": "not-an-object-id-3",
            "agent_mode": True,
            "content": "Make the fix, add tests, and give me the commit message.",
        },
    )

    assert response.status_code == 200, response.text
    assert "Recovered direct answer" in response.json()["response"]
    timed_out_agent.assert_awaited_once()
    direct_reply.assert_awaited_once()

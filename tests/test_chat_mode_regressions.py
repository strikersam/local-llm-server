from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

from bson import ObjectId
from fastapi import HTTPException

import backend.server as server


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
    session_id = f"agent-mode-{uuid.uuid4()}"

    monkeypatch.setattr("backend.server.call_llm", direct_reply)
    monkeypatch.setattr("backend.server._run_agent_loop", agent_reply)

    response = client.post(
        "/api/chat/send",
        headers=_auth_headers(client),
        json={
            "session_id": session_id,
            "agent_mode": True,
            "content": "Plan the fix and edit the code.",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["response"] == "Agent answer"
    agent_reply.assert_awaited_once()
    direct_reply.assert_not_called()


def test_agent_status_endpoint_reports_live_progress_and_tool_calls(client, monkeypatch) -> None:
    session_id = f"agent-{uuid.uuid4()}"

    async def fake_agent_loop(*args, **kwargs):
        server.AGENT_EVENT_STORE.append_event(
            session_id,
            "step_start",
            {"goal": "Fix the tests", "steps": 2},
        )
        server.AGENT_EVENT_STORE.append_event(
            session_id,
            "step_start",
            {"step_id": 1, "description": "Inspect failing test output"},
        )
        server.AGENT_EVENT_STORE.append_event(
            session_id,
            "tool_call",
            {"call_id": "tool-1", "tool_name": "read_file", "args": {"path": "tests/test_app.py"}, "status": "running"},
        )
        server.AGENT_EVENT_STORE.append_event(
            session_id,
            "tool_result",
            {"call_id": "tool-1", "tool_name": "read_file", "status": "success", "output": "assert True"},
        )
        server.AGENT_EVENT_STORE.append_event(
            session_id,
            "assistant_message",
            {"summary": "Fixed the failing tests."},
        )
        return "Fixed the failing tests."

    monkeypatch.setattr("backend.server._run_agent_loop", fake_agent_loop)

    response = client.post(
        "/api/chat/send",
        headers=_auth_headers(client),
        json={
            "session_id": session_id,
            "agent_mode": True,
            "content": "Fix the failing tests and verify the result.",
        },
    )

    assert response.status_code == 200, response.text

    status_response = client.get(
        f"/api/agent/status?session_id={session_id}",
        headers=_auth_headers(client),
    )
    assert status_response.status_code == 200, status_response.text
    payload = status_response.json()
    assert payload["has_events"] is True
    assert any(agent["role"] == "planner" for agent in payload["agents"])
    assert any(agent["role"] == "implementer" for agent in payload["agents"])
    assert payload["tool_calls"][0]["tool_name"] == "read_file"
    assert payload["tool_calls"][0]["status"] == "success"
    assert payload["latest_summary"] == "Fixed the failing tests."


def test_agent_stream_endpoint_emits_server_sent_events(client) -> None:
    session_id = f"agent-{uuid.uuid4()}"
    headers = _auth_headers(client)
    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200, me.text
    user_id = str(me.json()["_id"])
    server.AGENT_EVENT_STORE.create_with_id(
        session_id=session_id,
        title="Live Stream",
        owner_id=user_id,
    )
    server.AGENT_EVENT_STORE.append_event(
        session_id,
        "tool_call",
        {"call_id": "tool-1", "tool_name": "read_file", "args": {"path": "README.md"}, "status": "running"},
    )

    response = asyncio.run(
        server.stream_agent_activity(session_id=session_id, user={"_id": user_id})
    )
    first_chunk = asyncio.run(response.body_iterator.__anext__())

    assert "Started read_file" in first_chunk


def test_chat_send_returns_safe_boundary_for_repo_editing_requests_when_agent_mode_is_off(
    client, monkeypatch
) -> None:
    unexpected_direct_call = AsyncMock(
        side_effect=AssertionError("direct llm path should not fabricate repo edits")
    )

    monkeypatch.setattr("backend.server.call_llm", unexpected_direct_call)

    response = client.post(
        "/api/chat/send",
        headers=_auth_headers(client),
        json={
            "session_id": "not-an-object-id-boundary",
            "agent_mode": False,
            "content": (
                "A production app has three regressions: a missing mounted router causing 404s, "
                "an invisible checkbox caused by CSS appearance:none, and a Docker image that forgot "
                "to copy a Python package. Provide a concrete multi-file fix plan, exact edits, tests "
                "to add, and a merge strategy."
            ),
        },
    )

    assert response.status_code == 200, response.text
    assert "needs Agent Mode" in response.json()["response"]
    assert response.json()["assistant_meta"]["recommended_mode"] == "agent"
    assert response.json()["assistant_meta"]["retryable_prompt"].startswith(
        "A production app has three regressions"
    )
    unexpected_direct_call.assert_not_called()


def test_chat_send_returns_agent_handoff_for_github_and_container_tasks_when_agent_mode_is_off(
    client, monkeypatch
) -> None:
    unexpected_direct_call = AsyncMock(
        side_effect=AssertionError("direct llm path should not attempt workspace actions")
    )

    monkeypatch.setattr("backend.server.call_llm", unexpected_direct_call)

    response = client.post(
        "/api/chat/send",
        headers=_auth_headers(client),
        json={
            "session_id": "not-an-object-id-github-container",
            "agent_mode": False,
            "content": (
                "Clone my GitHub repo, fix the Dockerfile so the Python package is copied, "
                "run tests, commit the changes, and open a pull request."
            ),
        },
    )

    assert response.status_code == 200, response.text
    meta = response.json()["assistant_meta"]
    assert meta["type"] == "agent_handoff"
    assert meta["recommended_mode"] == "agent"
    assert "github" in meta["reason_codes"]
    assert "runtime" in meta["reason_codes"]
    task_suggestion = next(
        suggestion
        for suggestion in meta["workflow_suggestions"]
        if suggestion["kind"] == "task"
    )
    assert task_suggestion["payload"]["task_type"] == "repository_change"
    assert task_suggestion["payload"]["requires_approval"] is True
    unexpected_direct_call.assert_not_called()


def test_chat_send_returns_schedule_suggestion_for_recurring_automation_requests(
    client, monkeypatch
) -> None:
    unexpected_direct_call = AsyncMock(
        side_effect=AssertionError("direct llm path should not attempt workspace actions")
    )

    monkeypatch.setattr("backend.server.call_llm", unexpected_direct_call)

    response = client.post(
        "/api/chat/send",
        headers=_auth_headers(client),
        json={
            "session_id": "not-an-object-id-recurring-github-container",
            "agent_mode": False,
            "content": (
                "Every day clone my GitHub repo, run tests, and open a pull request "
                "if the nightly verification fails."
            ),
        },
    )

    assert response.status_code == 200, response.text
    meta = response.json()["assistant_meta"]
    schedule_suggestion = next(
        suggestion
        for suggestion in meta["workflow_suggestions"]
        if suggestion["kind"] == "schedule"
    )
    assert schedule_suggestion["payload"]["cron"] == "0 9 * * *"
    assert schedule_suggestion["payload"]["approval_gate"] is True
    unexpected_direct_call.assert_not_called()


def test_chat_send_persists_agent_handoff_metadata_in_session_history(client, monkeypatch) -> None:
    unexpected_direct_call = AsyncMock(
        side_effect=AssertionError("direct llm path should not attempt workspace actions")
    )
    update_session = AsyncMock()
    session_id = ObjectId()

    monkeypatch.setattr("backend.server.call_llm", unexpected_direct_call)
    monkeypatch.setattr(
        "backend.server.db.chat_sessions.insert_one",
        AsyncMock(return_value=SimpleNamespace(inserted_id=session_id)),
    )
    monkeypatch.setattr(
        "backend.server.db.chat_sessions.find_one",
        AsyncMock(return_value={"messages": []}),
    )
    monkeypatch.setattr("backend.server.db.chat_sessions.update_one", update_session)
    headers = _auth_headers(client)

    response = client.post(
        "/api/chat/send",
        headers=headers,
        json={
            "agent_mode": False,
            "content": (
                "Clone my GitHub repo, fix the Dockerfile so the Python package is copied, "
                "run tests, commit the changes, and open a pull request."
            ),
        },
    )

    assert response.status_code == 200, response.text
    persisted_messages = update_session.await_args.args[1]["$set"]["messages"]
    assistant_message = persisted_messages[-1]
    assert assistant_message["assistant_meta"]["type"] == "agent_handoff"
    assert assistant_message["assistant_meta"]["recommended_mode"] == "agent"
    assert assistant_message["assistant_meta"]["workflow_suggestions"][0]["kind"] == "task"


def test_uuid_fallback_chat_session_can_be_reloaded_and_deleted(client, monkeypatch) -> None:
    direct_reply = AsyncMock(return_value="Docker explanation")

    monkeypatch.setattr("backend.server.call_llm", direct_reply)
    monkeypatch.setattr(
        "backend.server.db.chat_sessions.insert_one",
        AsyncMock(side_effect=RuntimeError("db unavailable")),
    )

    headers = _auth_headers(client)
    response = client.post(
        "/api/chat/send",
        headers=headers,
        json={
            "agent_mode": False,
            "content": "Explain why Docker COPY order affects rebuild speed.",
        },
    )

    assert response.status_code == 200, response.text
    session_id = response.json()["session_id"]
    uuid.UUID(session_id)

    session_response = client.get(f"/api/chat/sessions/{session_id}", headers=headers)
    assert session_response.status_code == 200, session_response.text
    payload = session_response.json()
    assert payload["_id"] == session_id
    assert payload["messages"][-1]["content"] == "Docker explanation"

    delete_response = client.delete(f"/api/chat/sessions/{session_id}", headers=headers)
    assert delete_response.status_code == 200, delete_response.text

    missing_response = client.get(f"/api/chat/sessions/{session_id}", headers=headers)
    assert missing_response.status_code == 404, missing_response.text


def test_chat_send_keeps_general_docker_explanation_on_direct_path_when_no_repo_action_is_requested(
    client, monkeypatch
) -> None:
    direct_reply = AsyncMock(return_value="Docker explanation")
    unexpected_agent = AsyncMock(side_effect=AssertionError("agent path should not run"))

    monkeypatch.setattr("backend.server.call_llm", direct_reply)
    monkeypatch.setattr("backend.server._run_agent_loop", unexpected_agent)

    response = client.post(
        "/api/chat/send",
        headers=_auth_headers(client),
        json={
            "session_id": "not-an-object-id-docker-advice",
            "agent_mode": False,
            "content": (
                "Explain why Docker COPY order affects Python dependency layer caching "
                "and how to speed up rebuilds."
            ),
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["response"] == "Docker explanation"
    assert response.json()["assistant_meta"] is None
    direct_reply.assert_awaited_once()
    unexpected_agent.assert_not_called()


def test_chat_send_keeps_explanatory_github_pr_guidance_on_direct_path(client, monkeypatch) -> None:
    direct_reply = AsyncMock(return_value="GitHub explanation")
    unexpected_agent = AsyncMock(side_effect=AssertionError("agent path should not run"))

    monkeypatch.setattr("backend.server.call_llm", direct_reply)
    monkeypatch.setattr("backend.server._run_agent_loop", unexpected_agent)

    response = client.post(
        "/api/chat/send",
        headers=_auth_headers(client),
        json={
            "session_id": "not-an-object-id-github-explanation",
            "agent_mode": False,
            "content": "Explain how to clone a repo and open a pull request safely.",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["response"] == "GitHub explanation"
    assert response.json()["assistant_meta"] is None
    direct_reply.assert_awaited_once()
    unexpected_agent.assert_not_called()


def test_chat_send_falls_back_to_direct_answer_when_agent_mode_times_out(
    client, monkeypatch
) -> None:
    direct_reply = AsyncMock(return_value="Recovered direct answer")
    timed_out_agent = AsyncMock(side_effect=asyncio.TimeoutError())
    session_id = f"agent-timeout-{uuid.uuid4()}"

    monkeypatch.setattr("backend.server.call_llm", direct_reply)
    monkeypatch.setattr("backend.server._run_agent_loop", timed_out_agent)

    response = client.post(
        "/api/chat/send",
        headers=_auth_headers(client),
        json={
            "session_id": session_id,
            "agent_mode": True,
            "content": "Make the fix, add tests, and give me the commit message.",
        },
    )

    assert response.status_code == 200, response.text
    assert "Recovered direct answer" in response.json()["response"]
    timed_out_agent.assert_awaited_once()
    direct_reply.assert_awaited_once()


def test_chat_send_uses_provider_default_model_for_agent_mode_when_model_is_omitted(
    client, monkeypatch
) -> None:
    captured: dict[str, str | None] = {}
    session_id = f"agent-default-model-{uuid.uuid4()}"

    async def fake_build_provider_router(**kwargs):
        return (
            SimpleNamespace(providers=[]),
            {"allow_commercial_fallback": True},
            {
                "default_model": "meta/llama-3.3-70b-instruct",
                "base_url": "https://integrate.api.nvidia.com/v1",
                "api_key": "test-key",
            },
        )

    async def fake_run_agent_loop(**kwargs):
        captured["requested_model"] = kwargs.get("requested_model")
        return "Agent answer"

    monkeypatch.setattr("backend.server.get_active_provider", AsyncMock(return_value=None))
    monkeypatch.setattr("backend.server._build_provider_router", fake_build_provider_router)
    monkeypatch.setattr("backend.server._run_agent_loop", fake_run_agent_loop)

    response = client.post(
        "/api/chat/send",
        headers=_auth_headers(client),
        json={
            "session_id": session_id,
            "agent_mode": True,
            "content": "Fix the endpoint and add a regression test.",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["response"] == "Agent answer"
    assert captured["requested_model"] == "meta/llama-3.3-70b-instruct"


def test_chat_send_timeout_fallback_retries_with_provider_default_model(
    client, monkeypatch
) -> None:
    session_id = f"agent-timeout-default-{uuid.uuid4()}"

    async def fake_build_provider_router(**kwargs):
        return (
            SimpleNamespace(providers=[]),
            {"allow_commercial_fallback": True},
            {
                "default_model": "meta/llama-3.3-70b-instruct",
                "base_url": "https://integrate.api.nvidia.com/v1",
                "api_key": "test-key",
            },
        )

    call_llm = AsyncMock(
        side_effect=[
            HTTPException(status_code=503, detail="bad explicit model"),
            "Recovered via provider default",
        ]
    )

    monkeypatch.setattr("backend.server.get_active_provider", AsyncMock(return_value=None))
    monkeypatch.setattr("backend.server._build_provider_router", fake_build_provider_router)
    monkeypatch.setattr(
        "backend.server._run_agent_loop",
        AsyncMock(side_effect=asyncio.TimeoutError()),
    )
    monkeypatch.setattr("backend.server.call_llm", call_llm)

    response = client.post(
        "/api/chat/send",
        headers=_auth_headers(client),
        json={
            "session_id": session_id,
            "agent_mode": True,
            "model": "qwen/qwen2.5-coder-32b-instruct",
            "content": "Make the fix and give me the commit message.",
        },
    )

    assert response.status_code == 200, response.text
    assert "Recovered via provider default" in response.json()["response"]
    assert call_llm.await_count == 2

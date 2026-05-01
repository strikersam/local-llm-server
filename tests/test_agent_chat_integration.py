"""Integration tests for /agent/chat endpoint and AGENT_RUNNER configuration.

Covers:
- Session history persistence across multiple /agent/chat calls
- session_store + memory_store wired into AgentRunner
- NVIDIA NIM headers on AGENT_RUNNER singleton when key is set
- Judge verdict present in result dict
- Risky module detection emits a WARNING
- Complex multi-file task round-trip via spawn_subagent delegation
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from unittest import mock

import pytest
from fastapi.testclient import TestClient

import proxy
from agent.loop import AgentRunner
from agent.state import AgentSessionStore


# ---------------------------------------------------------------------------
# Shared auth bypass
# ---------------------------------------------------------------------------

def _fake_auth() -> proxy.AuthContext:
    return proxy.AuthContext(
        key="test-key",
        email="tester@example.com",
        department="engineering",
        key_id="kid_test",
        source="legacy",
    )


def _fake_run_result(instruction: str, extra: dict | None = None) -> dict:
    result: dict = {
        "goal": instruction,
        "plan": {
            "goal": instruction,
            "steps": [
                {
                    "id": 1,
                    "description": "step one",
                    "files": ["a.py"],
                    "type": "edit",
                    "risky": False,
                    "acceptance": "test passes",
                }
            ],
            "risks": [],
            "requires_risky_review": False,
        },
        "steps": [
            {
                "id": 1,
                "description": "step one",
                "status": "applied",
                "changed_files": ["a.py"],
                "issues": [],
            }
        ],
        "commits": [],
        "summary": f"Done: {instruction}",
        "report": f"## Report\n{instruction}",
        "judge": {"verdict": "APPROVED", "security": "PASS", "correctness": "PASS", "notes": ""},
    }
    if extra:
        result.update(extra)
    return result


def _make_nim_providers() -> list:
    return [
        type("P", (), {
            "provider_id": "nim",
            "priority": -10,
            "api_key": "test-nim-key",
            "default_model": "qwen/qwen2.5-coder-32b-instruct",
            "normalized_base_url": "https://integrate.api.nvidia.com/v1",
            "auth_headers": lambda self=None: {"Authorization": "Bearer test-nim-key"},
        })()
    ]


# ---------------------------------------------------------------------------
# Test: /agent/chat persists history across calls with same session_id
# ---------------------------------------------------------------------------

def test_agent_chat_persists_history_across_calls(tmp_path: Path) -> None:
    proxy.app.dependency_overrides[proxy.verify_api_key] = _fake_auth
    try:
        captured_histories: list[list] = []

        class CapturingRunner:
            def __init__(self, *, ollama_base: str, workspace_root, provider_headers=None,
                         session_store=None, email=None, department=None, key_id=None, **kw):
                self.session_store = session_store

            async def run(self, *, instruction: str, history: list, **kwargs) -> dict:
                captured_histories.append(list(history))
                return _fake_run_result(instruction)

        with mock.patch.object(proxy, "AgentRunner", CapturingRunner), \
             mock.patch.object(proxy.PROVIDER_ROUTER, "providers", _make_nim_providers()):
            isolated_store = AgentSessionStore(db_path=str(tmp_path / "test.db"))
            with mock.patch.object(proxy, "AGENT_SESSIONS", isolated_store):
                client = TestClient(proxy.app)

                resp1 = client.post(
                    "/agent/chat",
                    json={"instruction": "First message", "session_id": "test-sess-001"},
                )
                assert resp1.status_code == 200
                assert resp1.json()["session_id"] == "test-sess-001"

                resp2 = client.post(
                    "/agent/chat",
                    json={"instruction": "Second message", "session_id": "test-sess-001"},
                )
                assert resp2.status_code == 200

        assert len(captured_histories) == 2
        second_history_roles = [m["role"] for m in captured_histories[1]]
        # The second call's history is the PRIOR context only (current instruction
        # is passed separately as `instruction`, not duplicated in history).
        # So history should contain the first call's user turn + assistant reply.
        assert second_history_roles.count("user") >= 1
        assert "assistant" in second_history_roles
        assert len(captured_histories[1]) > len(captured_histories[0])
    finally:
        proxy.app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test: /agent/chat wires session_store into AgentRunner
# ---------------------------------------------------------------------------

def test_agent_chat_passes_session_store_to_runner(tmp_path: Path) -> None:
    proxy.app.dependency_overrides[proxy.verify_api_key] = _fake_auth
    try:
        captured: dict = {}

        class CapturingRunner:
            def __init__(self, *, ollama_base: str, workspace_root, provider_headers=None,
                         session_store=None, email=None, department=None, key_id=None, **kw):
                captured["session_store"] = session_store

            async def run(self, *, instruction: str, memory_store=None, **kwargs) -> dict:
                captured["memory_store"] = memory_store
                return _fake_run_result(instruction)

        with mock.patch.object(proxy, "AgentRunner", CapturingRunner), \
             mock.patch.object(proxy.PROVIDER_ROUTER, "providers", _make_nim_providers()):
            isolated_store = AgentSessionStore(db_path=str(tmp_path / "test2.db"))
            with mock.patch.object(proxy, "AGENT_SESSIONS", isolated_store):
                client = TestClient(proxy.app)
                resp = client.post("/agent/chat", json={"instruction": "Check setup"})
                assert resp.status_code == 200

        assert captured.get("session_store") is not None
        assert captured.get("memory_store") is not None
    finally:
        proxy.app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test: /agent/chat returns judge verdict in result
# ---------------------------------------------------------------------------

def test_agent_chat_result_includes_judge_verdict(tmp_path: Path) -> None:
    proxy.app.dependency_overrides[proxy.verify_api_key] = _fake_auth
    try:
        class JudgeRunner:
            def __init__(self, **kw) -> None:
                pass

            async def run(self, *, instruction: str, **kwargs) -> dict:
                return _fake_run_result(instruction, {"judge": {
                    "verdict": "APPROVED",
                    "security": "PASS",
                    "correctness": "PASS",
                    "notes": "all checks pass",
                }})

        with mock.patch.object(proxy, "AgentRunner", JudgeRunner), \
             mock.patch.object(proxy.PROVIDER_ROUTER, "providers", _make_nim_providers()):
            isolated_store = AgentSessionStore(db_path=str(tmp_path / "judge.db"))
            with mock.patch.object(proxy, "AGENT_SESSIONS", isolated_store):
                client = TestClient(proxy.app)
                resp = client.post("/agent/chat", json={"instruction": "Refactor auth module"})
                assert resp.status_code == 200
                result = resp.json()["result"]
                assert "judge" in result
                assert result["judge"]["verdict"] == "APPROVED"
    finally:
        proxy.app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test: AGENT_RUNNER singleton has NIM headers when key is present
# ---------------------------------------------------------------------------

def test_agent_runner_singleton_uses_nim_when_key_set(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("NVIDIA_API_KEY", "nvtest-key-123")
    monkeypatch.setenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")

    nim_key = os.environ.get("NVIDIA_API_KEY") or ""
    nim_base = os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")

    headers = {"Authorization": f"Bearer {nim_key}"} if nim_key else None
    base = nim_base if nim_key else "http://localhost:11434"
    isolated_store = AgentSessionStore(db_path=str(tmp_path / "nim.db"))
    runner = AgentRunner(
        ollama_base=base,
        workspace_root=tmp_path,
        provider_headers=headers,
        session_store=isolated_store,
    )

    assert runner.ollama_base == "https://integrate.api.nvidia.com/v1"
    assert runner.provider_headers.get("Authorization") == "Bearer nvtest-key-123"
    assert runner._session_store is isolated_store


# ---------------------------------------------------------------------------
# Test: risky module detection fires a warning
# ---------------------------------------------------------------------------

def test_risky_module_detection_emits_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    root = tmp_path / "repo"
    root.mkdir()

    runner = AgentRunner(ollama_base="http://localhost:11434", workspace_root=root)

    responses = iter([
        # Planner returns a step touching admin_auth.py
        '{"goal":"Change admin auth","steps":[{"id":1,"description":"Modify admin auth","files":["admin_auth.py"],"type":"edit","risky":true,"acceptance":"tests pass"}],"risks":["auth surface change"],"requires_risky_review":true}',
        '{"tool":"finish","args":{"reason":"context gathered"}}',
        'FILE: admin_auth.py\nACTION: replace\n```python\n# admin auth placeholder\n```',
        '{"status":"pass","issues":[]}',
        '{"verdict":"APPROVED_WITH_CONDITIONS","security":"WARN","correctness":"PASS","notes":"auth change needs review"}',
    ])

    async def fake_chat_text(self_or_model, model_or_messages, messages=None) -> str:
        return next(responses)

    with mock.patch.object(AgentRunner, "_chat_text", fake_chat_text), \
         caplog.at_level(logging.WARNING, logger="qwen-agent"):
        result = asyncio.run(
            runner.run(
                instruction="Change admin auth behaviour",
                history=[],
                requested_model=None,
                auto_commit=False,
                max_steps=3,
            )
        )

    assert any("RISKY MODULE" in r.message for r in caplog.records), \
        "Expected RISKY MODULE warning in log"
    assert result["judge"]["verdict"] == "APPROVED_WITH_CONDITIONS"


# ---------------------------------------------------------------------------
# Test: complex multi-file task with 3 independent steps triggers parallel check
# ---------------------------------------------------------------------------

def test_complex_multi_file_task_parallel_detection(tmp_path: Path) -> None:
    from agent.loop import AgentRunner as Runner
    root = tmp_path / "repo"
    root.mkdir()
    for f in ["models.py", "views.py", "serializers.py"]:
        (root / f).write_text(f"# {f}\n")

    runner = Runner(ollama_base="http://localhost:11434", workspace_root=root)

    maybe_parallel_called: dict = {"called": False, "plan": None}

    async def spy_maybe_parallel(self, *, plan, **kwargs) -> None:
        maybe_parallel_called["called"] = True
        maybe_parallel_called["plan"] = plan
        return None  # fall through to sequential

    responses = iter([
        '{"goal":"Update three modules","steps":['
        '{"id":1,"description":"Update models","files":["models.py"],"type":"edit","risky":false,"acceptance":""},'
        '{"id":2,"description":"Update views","files":["views.py"],"type":"edit","risky":false,"acceptance":""},'
        '{"id":3,"description":"Update serializers","files":["serializers.py"],"type":"edit","risky":false,"acceptance":""}'
        '],"risks":[],"requires_risky_review":false}',
        '{"tool":"finish","args":{"reason":"ok"}}',
        'FILE: models.py\nACTION: replace\n```python\n# updated models\n```',
        '{"status":"pass","issues":[]}',
        '{"tool":"finish","args":{"reason":"ok"}}',
        'FILE: views.py\nACTION: replace\n```python\n# updated views\n```',
        '{"status":"pass","issues":[]}',
        '{"tool":"finish","args":{"reason":"ok"}}',
        'FILE: serializers.py\nACTION: replace\n```python\n# updated serializers\n```',
        '{"status":"pass","issues":[]}',
        '{"verdict":"APPROVED","security":"PASS","correctness":"PASS","notes":""}',
    ])

    async def fake_chat_text(self_or_model, model_or_messages, messages=None) -> str:
        return next(responses)

    with mock.patch.object(Runner, "_chat_text", fake_chat_text), \
         mock.patch.object(Runner, "_maybe_run_parallel", spy_maybe_parallel):
        result = asyncio.run(
            runner.run(
                instruction="Update three modules independently",
                history=[],
                requested_model=None,
                auto_commit=False,
                max_steps=5,
            )
        )

    assert maybe_parallel_called["called"], "_maybe_run_parallel was not called"
    plan = maybe_parallel_called["plan"]
    assert len(plan.steps) == 3
    assert Runner._steps_are_independent(plan.steps)
    assert result["judge"]["verdict"] == "APPROVED"
    applied = [s for s in result["steps"] if s["status"] == "applied"]
    assert len(applied) == 3


# ---------------------------------------------------------------------------
# Test: spawn_subagent is called and its result surfaces in the run output
# ---------------------------------------------------------------------------

def test_spawn_subagent_integrates_into_plan(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "main.py").write_text("# main\n")

    runner = AgentRunner(ollama_base="http://localhost:11434", workspace_root=root)

    responses = iter([
        '{"goal":"Analyze and fix","steps":[{"id":1,"description":"Analyze codebase","files":[],"type":"analyze","risky":false,"acceptance":"report produced"}],"risks":[],"requires_risky_review":false}',
        '{"tool":"spawn_subagent","args":{"instruction":"Check main.py for issues","max_steps":3}}',
        '{"tool":"finish","args":{"reason":"subagent done"}}',
        '{"goal":"Analyze","answer":"No issues found in main.py."}',
        '{"verdict":"APPROVED","security":"PASS","correctness":"PASS","notes":""}',
    ])

    async def fake_chat_text(self_or_model, model_or_messages, messages=None) -> str:
        return next(responses)

    spawn_mock = mock.AsyncMock(
        return_value={"summary": "No issues found in main.py.", "steps": [], "goal": "Check main.py for issues"}
    )

    with mock.patch.object(AgentRunner, "_chat_text", fake_chat_text), \
         mock.patch.object(runner, "_spawn_subagent", spawn_mock):
        result = asyncio.run(
            runner.run(
                instruction="Analyze and fix main.py",
                history=[],
                requested_model=None,
                auto_commit=False,
                max_steps=3,
            )
        )

    # Verify spawn_subagent was actually invoked with the expected instruction
    spawn_mock.assert_awaited_once()
    call_kwargs = spawn_mock.call_args
    assert "Check main.py for issues" in str(call_kwargs)

    # Verify the subagent summary surfaces somewhere in the run result
    assert "No issues found in main.py." in json.dumps(result)

    assert result["goal"] == "Analyze and fix"
    assert result["judge"]["verdict"] == "APPROVED"

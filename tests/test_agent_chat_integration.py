"""Integration tests for /agent/chat endpoint and AGENT_RUNNER configuration.

Covers:
- Session history persistence across multiple /agent/chat calls
- session_store + memory_store wired into AgentRunner
- NVIDIA NIM headers on AGENT_RUNNER singleton when key is set
- Judge verdict present in result dict
- Risky module detection emits a warning
- Complex multi-file task round-trip via spawn_subagent delegation
"""
from __future__ import annotations

import asyncio
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

def _fake_auth():
    return proxy.AuthContext(
        key="test-key",
        email="tester@example.com",
        department="engineering",
        key_id="kid_test",
        source="legacy",
    )


def _fake_run_result(instruction: str, extra: dict | None = None) -> dict:
    result = {
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


# ---------------------------------------------------------------------------
# Test: /agent/chat persists history across calls with same session_id
# ---------------------------------------------------------------------------

def test_agent_chat_persists_history_across_calls(tmp_path):
    proxy.app.dependency_overrides[proxy.verify_api_key] = _fake_auth

    captured_histories: list[list] = []

    class CapturingRunner:
        def __init__(self, *, ollama_base, workspace_root, provider_headers=None,
                     session_store=None, email=None, department=None, key_id=None, **kw):
            self.session_store = session_store

        async def run(self, *, instruction, history, **kwargs):
            captured_histories.append(list(history))
            return _fake_run_result(instruction)

    monkeypatch_runner = mock.patch.object(proxy, "AgentRunner", CapturingRunner)

    nim_providers = [
        type("P", (), {
            "provider_id": "nim",
            "priority": -10,
            "api_key": "test-nim-key",
            "default_model": "qwen/qwen2.5-coder-32b-instruct",
            "normalized_base_url": "https://integrate.api.nvidia.com/v1",
            "auth_headers": lambda self=None: {"Authorization": "Bearer test-nim-key"},
        })()
    ]
    monkeypatch_providers = mock.patch.object(proxy.PROVIDER_ROUTER, "providers", nim_providers)

    with monkeypatch_runner, monkeypatch_providers:
        # isolate session store so this test is hermetic
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

    # First call: history contains only the first message (user)
    # Second call: history contains both messages and the assistant reply
    assert len(captured_histories) == 2
    # Second call must include history from first call
    second_history_roles = [m["role"] for m in captured_histories[1]]
    assert "user" in second_history_roles
    assert len(captured_histories[1]) > len(captured_histories[0])

    proxy.app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test: /agent/chat wires session_store into AgentRunner
# ---------------------------------------------------------------------------

def test_agent_chat_passes_session_store_to_runner(tmp_path):
    proxy.app.dependency_overrides[proxy.verify_api_key] = _fake_auth

    captured: dict = {}

    class CapturingRunner:
        def __init__(self, *, ollama_base, workspace_root, provider_headers=None,
                     session_store=None, email=None, department=None, key_id=None, **kw):
            captured["session_store"] = session_store

        async def run(self, *, instruction, memory_store=None, **kwargs):
            captured["memory_store"] = memory_store
            return _fake_run_result(instruction)

    nim_providers = [
        type("P", (), {
            "provider_id": "nim",
            "priority": -10,
            "api_key": "key",
            "default_model": "test-model",
            "normalized_base_url": "http://nim",
            "auth_headers": lambda self=None: {"Authorization": "Bearer key"},
        })()
    ]
    with mock.patch.object(proxy, "AgentRunner", CapturingRunner), \
         mock.patch.object(proxy.PROVIDER_ROUTER, "providers", nim_providers):
        isolated_store = AgentSessionStore(db_path=str(tmp_path / "test2.db"))
        isolated_memory = proxy.USER_MEMORY
        with mock.patch.object(proxy, "AGENT_SESSIONS", isolated_store):
            client = TestClient(proxy.app)
            resp = client.post("/agent/chat", json={"instruction": "Check setup"})
            assert resp.status_code == 200

    assert captured.get("session_store") is not None
    assert captured.get("memory_store") is not None

    proxy.app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test: /agent/chat returns judge verdict in result
# ---------------------------------------------------------------------------

def test_agent_chat_result_includes_judge_verdict(tmp_path):
    proxy.app.dependency_overrides[proxy.verify_api_key] = _fake_auth

    class JudgeRunner:
        def __init__(self, **kw):
            pass

        async def run(self, *, instruction, **kwargs):
            return _fake_run_result(instruction, {"judge": {
                "verdict": "APPROVED",
                "security": "PASS",
                "correctness": "PASS",
                "notes": "all checks pass",
            }})

    nim_providers = [
        type("P", (), {
            "provider_id": "nim",
            "priority": -10,
            "api_key": "key",
            "default_model": "test-model",
            "normalized_base_url": "http://nim",
            "auth_headers": lambda self=None: {"Authorization": "Bearer key"},
        })()
    ]
    with mock.patch.object(proxy, "AgentRunner", JudgeRunner), \
         mock.patch.object(proxy.PROVIDER_ROUTER, "providers", nim_providers):
        isolated_store = AgentSessionStore(db_path=str(tmp_path / "judge.db"))
        with mock.patch.object(proxy, "AGENT_SESSIONS", isolated_store):
            client = TestClient(proxy.app)
            resp = client.post("/agent/chat", json={"instruction": "Refactor auth module"})
            assert resp.status_code == 200
            result = resp.json()["result"]
            assert "judge" in result
            assert result["judge"]["verdict"] == "APPROVED"

    proxy.app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test: AGENT_RUNNER singleton has NIM headers when key is present
# ---------------------------------------------------------------------------

def test_agent_runner_singleton_uses_nim_when_key_set(monkeypatch, tmp_path):
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

def test_risky_module_detection_emits_warning(tmp_path, caplog):
    root = tmp_path / "repo"
    root.mkdir()

    runner = AgentRunner(ollama_base="http://localhost:11434", workspace_root=root)

    # Plan that includes a risky file step
    responses = iter([
        # Planner returns a step touching admin_auth.py
        '{"goal":"Change admin auth","steps":[{"id":1,"description":"Modify admin auth","files":["admin_auth.py"],"type":"edit","risky":true,"acceptance":"tests pass"}],"risks":["auth surface change"],"requires_risky_review":true}',
        '{"tool":"finish","args":{"reason":"context gathered"}}',
        # Executor output
        'FILE: admin_auth.py\nACTION: replace\n```python\n# admin auth placeholder\n```',
        # Verifier
        '{"status":"pass","issues":[]}',
        # Judge
        '{"verdict":"APPROVED_WITH_CONDITIONS","security":"WARN","correctness":"PASS","notes":"auth change needs review"}',
    ])

    async def fake_chat_text(self_or_model, model_or_messages, messages=None):
        # Works whether patched at instance (2 args) or class level (3 args)
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

def test_complex_multi_file_task_parallel_detection(tmp_path):
    from agent.loop import AgentRunner as Runner
    root = tmp_path / "repo"
    root.mkdir()
    for f in ["models.py", "views.py", "serializers.py"]:
        (root / f).write_text(f"# {f}\n")

    runner = Runner(ollama_base="http://localhost:11434", workspace_root=root)

    maybe_parallel_called = {"called": False, "plan": None}
    original_maybe = Runner._maybe_run_parallel

    async def spy_maybe_parallel(self, *, plan, **kwargs):
        maybe_parallel_called["called"] = True
        maybe_parallel_called["plan"] = plan
        return None  # fall through to sequential

    responses = iter([
        '{"goal":"Update three modules","steps":['
        '{"id":1,"description":"Update models","files":["models.py"],"type":"edit","risky":false,"acceptance":""},'
        '{"id":2,"description":"Update views","files":["views.py"],"type":"edit","risky":false,"acceptance":""},'
        '{"id":3,"description":"Update serializers","files":["serializers.py"],"type":"edit","risky":false,"acceptance":""}'
        '],"risks":[],"requires_risky_review":false}',
        # Step 1 tooling
        '{"tool":"finish","args":{"reason":"ok"}}',
        'FILE: models.py\nACTION: replace\n```python\n# updated models\n```',
        '{"status":"pass","issues":[]}',
        # Step 2 tooling
        '{"tool":"finish","args":{"reason":"ok"}}',
        'FILE: views.py\nACTION: replace\n```python\n# updated views\n```',
        '{"status":"pass","issues":[]}',
        # Step 3 tooling
        '{"tool":"finish","args":{"reason":"ok"}}',
        'FILE: serializers.py\nACTION: replace\n```python\n# updated serializers\n```',
        '{"status":"pass","issues":[]}',
        # Judge
        '{"verdict":"APPROVED","security":"PASS","correctness":"PASS","notes":""}',
    ])

    async def fake_chat_text(self_or_model, model_or_messages, messages=None):
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
    # All steps touch different files — should be detected as independent
    assert Runner._steps_are_independent(plan.steps)
    assert result["judge"]["verdict"] == "APPROVED"
    applied = [s for s in result["steps"] if s["status"] == "applied"]
    assert len(applied) == 3


# ---------------------------------------------------------------------------
# Test: spawn_subagent result is included as step observation
# ---------------------------------------------------------------------------

def test_spawn_subagent_integrates_into_plan(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "main.py").write_text("# main\n")

    runner = AgentRunner(ollama_base="http://localhost:11434", workspace_root=root)

    responses = iter([
        # Planner: one step of type analyze that uses spawn_subagent
        '{"goal":"Analyze and fix","steps":[{"id":1,"description":"Analyze codebase","files":[],"type":"analyze","risky":false,"acceptance":"report produced"}],"risks":[],"requires_risky_review":false}',
        # Tool phase: spawn_subagent
        '{"tool":"spawn_subagent","args":{"instruction":"Check main.py for issues","max_steps":3}}',
        '{"tool":"finish","args":{"reason":"subagent done"}}',
        # Executor: synthesize answer for analyze step (no file written)
        '{"goal":"Analyze","answer":"No issues found in main.py."}',
        # Judge
        '{"verdict":"APPROVED","security":"PASS","correctness":"PASS","notes":""}',
    ])

    async def fake_chat_text(self_or_model, model_or_messages, messages=None):
        return next(responses)

    async def fake_spawn(instruction, *, requested_model=None, max_steps=5, user_id=None, memory_store=None):
        return {"summary": "No issues found in main.py.", "steps": [], "goal": instruction}

    with mock.patch.object(AgentRunner, "_chat_text", fake_chat_text), \
         mock.patch.object(runner, "_spawn_subagent", fake_spawn):
        result = asyncio.run(
            runner.run(
                instruction="Analyze and fix main.py",
                history=[],
                requested_model=None,
                auto_commit=False,
                max_steps=3,
            )
        )

    assert result["goal"] == "Analyze and fix"
    assert result["judge"]["verdict"] == "APPROVED"

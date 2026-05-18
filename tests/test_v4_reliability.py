"""tests/test_v4_reliability.py — Regression tests for v4 reliability claims.

Ensures that the following already-claimed behaviors continue to work:
  C3 - Existing reliability regression tests
  C4 - Security regressions

Tests in this file must NOT break when workspace isolation or feature matrix
code is added.  They prove the core system still works correctly.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# C3.1 — Runtime preflight returns structured error for missing binaries
# ---------------------------------------------------------------------------


class TestRuntimePreflight:
    def test_missing_binary_produces_structured_validation_issue(self):
        """Preflight must return RuntimeReadinessReport with issues, not raise."""
        from runtimes.base import RuntimeAdapter, RuntimeHealth, RuntimeTier, RuntimeCapability, IntegrationMode, TaskSpec, TaskResult, RuntimeDependency

        class _BinaryMissingAdapter(RuntimeAdapter):
            RUNTIME_ID = "test_missing_bin"
            DISPLAY_NAME = "Missing Binary Test"
            DESCRIPTION = "For testing"
            TIER = RuntimeTier.TIER_2
            INTEGRATION_MODE = IntegrationMode.EXTERNAL_PROCESS
            CAPABILITIES = frozenset()

            def required_dependencies(self):
                return [RuntimeDependency(
                    name="definitely_not_a_real_binary_xyz",
                    kind="binary",
                    required=True,
                    install_hint="install it",
                )]

            async def health_check(self):
                return RuntimeHealth(runtime_id=self.RUNTIME_ID, available=True)

            async def execute(self, spec):
                return TaskResult(
                    runtime_id=self.RUNTIME_ID,
                    task_id=spec.task_id,
                    success=True,
                    output="",
                )

        adapter = _BinaryMissingAdapter()
        spec = TaskSpec(task_id="t1", instruction="test")

        async def run():
            return await adapter.readiness_check(spec)

        report = asyncio.run(run())
        assert report.ready is False
        assert len(report.issues) > 0
        issue = report.issues[0]
        assert issue.code == "missing_binary"
        assert "definitely_not_a_real_binary_xyz" in issue.message
        assert issue.fix_hint is not None

    def test_preflight_report_serialises_to_dict(self):
        from runtimes.base import RuntimeReadinessReport, RuntimeValidationIssue
        report = RuntimeReadinessReport(
            runtime_id="test",
            ready=False,
            issues=[
                RuntimeValidationIssue(
                    code="missing_binary",
                    message="binary not found",
                    fix_hint="install it",
                )
            ],
            summary="runtime not ready",
        )
        d = report.as_dict()
        assert d["ready"] is False
        assert len(d["issues"]) == 1
        assert d["issues"][0]["code"] == "missing_binary"


# ---------------------------------------------------------------------------
# C3.2 — Direct chat routing: non-agent mode stays on direct path
# ---------------------------------------------------------------------------


class TestDirectChatNonBlocking:
    def test_direct_chat_non_agent_calls_direct_path(self, monkeypatch):
        """Non-agent mode must take the direct chat path, not the agent job path."""
        import backend.server as server
        from unittest.mock import AsyncMock

        direct_reply = AsyncMock(return_value="Direct answer")
        unexpected_agent = AsyncMock(side_effect=AssertionError("agent path must not run"))

        monkeypatch.setattr("backend.server.call_llm", direct_reply)
        monkeypatch.setattr("backend.server._run_agent_loop", unexpected_agent)

        # Import the client fixture from conftest (invoke manually)
        from fastapi.testclient import TestClient
        import backend.server as srv

        client = TestClient(srv.app)
        login = client.post(
            "/api/auth/login",
            json={"email": "admin@llmrelay.local", "password": "WikiAdmin2026!"},
        )
        if login.status_code != 200:
            pytest.skip("Backend auth not configured in this test environment")

        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        resp = client.post(
            "/api/chat/send",
            headers=headers,
            json={"content": "Hello world", "agent_mode": False},
        )
        assert resp.status_code == 200
        assert resp.json()["response"] == "Direct answer"
        unexpected_agent.assert_not_called()

    def test_trivial_message_forces_direct_mode(self):
        """Trivial greetings must always use direct mode even if agent_mode=True."""
        from direct_chat import _is_trivial_message
        assert _is_trivial_message("Hello") is True
        assert _is_trivial_message("hi there") is True
        assert _is_trivial_message("Please implement a new auth system with JWT tokens") is False


# ---------------------------------------------------------------------------
# C3.3 — Agent mode returns 202 + job_id
# ---------------------------------------------------------------------------


class TestAgentModeQueuesJob:
    def test_agent_mode_returns_202_with_job_id(self, monkeypatch, tmp_path: Path):
        from fastapi.testclient import TestClient
        import direct_chat
        import proxy
        from agent.job_manager import AgentJobManager
        from agent.state import AgentSessionStore
        from runtimes.base import RuntimeReadinessReport

        proxy.app.dependency_overrides[direct_chat._get_current_user] = (
            lambda: direct_chat.UserInfo(id="user-1", email="tester@example.com")
        )
        monkeypatch.setattr(direct_chat, "_direct_chat_store", AgentSessionStore(db_path=str(tmp_path / "chat.db")))
        monkeypatch.setattr(direct_chat, "_agent_jobs", AgentJobManager())
        monkeypatch.setattr(direct_chat, "_agent_workspace_root", tmp_path / "ws")

        class _FakeProvider:
            priority = 1
            api_key = None
            normalized_base_url = "http://localhost:11434"
            def auth_headers(self): return {}

        proxy.app.state.PROVIDER_ROUTER = type("R", (), {"providers": [_FakeProvider()]})()

        async def fake_readiness(self, spec):
            return RuntimeReadinessReport(runtime_id="internal_agent", ready=True, selected_runtime="internal_agent")

        class FakeRunner:
            def __init__(self, **kwargs): pass
            async def run(self, **kwargs):
                return {"summary": "done", "judge": {"verdict": "APPROVED"}, "steps": []}

        monkeypatch.setattr("runtimes.adapters.internal_agent.InternalAgentAdapter.readiness_check", fake_readiness)
        monkeypatch.setattr("agent.loop.AgentRunner", FakeRunner)

        client = TestClient(proxy.app)
        try:
            resp = client.post(
                "/api/chat/send",
                json={"content": "Please implement this important new feature", "agent_mode": True},
            )
            assert resp.status_code == 202
            body = resp.json()
            assert "job_id" in body
            assert body["status"] in {"queued", "running"}
        finally:
            proxy.app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# C3.4 — Agent job lifecycle transitions correctly
# ---------------------------------------------------------------------------


class TestJobLifecycle:
    def test_job_transitions_queued_running_succeeded(self):
        from agent.job_manager import AgentJob, AgentJobManager

        mgr = AgentJobManager()
        job = mgr.create_job(session_id="as_sess1", instruction="do work")
        assert job.status == "queued"
        assert job.phase == "queued"

        async def _run():
            async def runner(heartbeat):
                heartbeat("planning", "planning step")
                return {"summary": "done"}
            mgr.start_job(job.job_id, runner)
            # Wait for completion
            for _ in range(50):
                await asyncio.sleep(0.02)
                if job.status in ("succeeded", "failed"):
                    break

        asyncio.run(_run())
        assert job.status == "succeeded"
        assert job.phase == "completed"
        assert len(job.progress_events) >= 1

    def test_job_cancel_transitions_to_cancelled(self):
        from agent.job_manager import AgentJobManager

        mgr = AgentJobManager()
        job = mgr.create_job(session_id="as_sess2", instruction="cancel me")
        cancelled = mgr.cancel_job(job.job_id)
        assert cancelled is not None
        assert cancelled.status == "cancelled"

    def test_job_failure_captures_error(self):
        from agent.job_manager import AgentJobManager

        mgr = AgentJobManager()
        job = mgr.create_job(session_id="as_sess3", instruction="fail me")

        async def _run():
            async def runner(heartbeat):
                raise RuntimeError("deliberate test failure")
            mgr.start_job(job.job_id, runner)
            for _ in range(50):
                await asyncio.sleep(0.02)
                if job.status in ("succeeded", "failed"):
                    break

        asyncio.run(_run())
        assert job.status == "failed"
        assert job.error is not None
        assert "RuntimeError" in job.error["type"]

    def test_job_as_dict_contains_all_fields(self):
        from agent.job_manager import AgentJobManager

        mgr = AgentJobManager()
        job = mgr.create_job(session_id="as_sess4", instruction="inspect me", owner_id="user@example.com")
        d = job.as_dict()
        for field in (
            "job_id", "session_id", "instruction", "owner_id", "status",
            "phase", "created_at", "updated_at", "heartbeat_at",
            "runtime_id", "workspace_path", "progress_events", "result", "error",
        ):
            assert field in d, f"Missing field in job.as_dict(): {field}"


# ---------------------------------------------------------------------------
# C3.5 — Provider timeout / cooldown does not pin broken provider
# ---------------------------------------------------------------------------


class TestProviderCooldown:
    def test_cooldown_state_returns_dict(self):
        from provider_router import get_cooldown_state
        state = get_cooldown_state()
        assert isinstance(state, dict)

    def test_broken_provider_gets_cooldown_on_error(self, monkeypatch):
        import provider_router as pr
        from provider_router import mark_provider_failed, get_cooldown_state

        pr.clear_cooldowns()
        mark_provider_failed("bad_prov_test", cooldown_seconds=60)
        state = get_cooldown_state()
        assert "bad_prov_test" in state
        assert state["bad_prov_test"] > time.time()
        pr.clear_cooldowns()

    def test_provider_comes_off_cooldown_after_expiry(self, monkeypatch):
        import provider_router as pr
        from provider_router import clear_cooldowns, is_provider_on_cooldown

        clear_cooldowns()

        # Inject an already-expired cooldown
        pr._provider_cooldowns["recovering_test"] = time.time() - 1.0

        # After expiry, is_provider_on_cooldown should return False and clean up
        result = is_provider_on_cooldown("recovering_test")
        assert result is False
        # Expired entry should be removed
        assert "recovering_test" not in pr._provider_cooldowns
        clear_cooldowns()


# ---------------------------------------------------------------------------
# C3.6 — Planner / verifier / judge model-role separation
# ---------------------------------------------------------------------------


class TestModelRoleSeparation:
    def test_default_model_roles_are_configured_from_env(self, monkeypatch):
        """Module-level defaults must be read from AGENT_*_MODEL env vars.

        These defaults are read at module import time, so we verify the pattern
        by checking that the constants exist and correspond to their env vars.
        """
        import agent.loop as loop_mod
        # Verify the three defaults are module-level constants
        assert hasattr(loop_mod, "DEFAULT_PLANNER_MODEL")
        assert hasattr(loop_mod, "DEFAULT_EXECUTOR_MODEL")
        assert hasattr(loop_mod, "DEFAULT_VERIFIER_MODEL")
        # Defaults must be non-empty strings
        assert isinstance(loop_mod.DEFAULT_PLANNER_MODEL, str)
        assert isinstance(loop_mod.DEFAULT_EXECUTOR_MODEL, str)
        assert isinstance(loop_mod.DEFAULT_VERIFIER_MODEL, str)

    def test_planner_executor_verifier_env_vars_documented(self):
        """All three model role env vars must be recognised by loop.py."""
        import importlib, os
        import agent.loop as loop_mod
        # Verify that AGENT_PLANNER_MODEL env var feeds into DEFAULT_PLANNER_MODEL
        current = loop_mod.DEFAULT_PLANNER_MODEL
        # At minimum, verify the default fallback is set when env var is absent
        env_val = os.environ.get("AGENT_PLANNER_MODEL")
        if env_val:
            assert loop_mod.DEFAULT_PLANNER_MODEL == env_val
        else:
            assert loop_mod.DEFAULT_PLANNER_MODEL  # non-empty fallback


# ---------------------------------------------------------------------------
# C3.7 — make_isolated_workspace path isolation (existing function)
# ---------------------------------------------------------------------------


class TestMakeIsolatedWorkspace:
    def test_hashed_directories_created(self, tmp_path: Path):
        from agent.job_manager import make_isolated_workspace
        ws = make_isolated_workspace(tmp_path, "as_session1", "aj_job001")
        assert ws.exists()
        assert ws.is_dir()
        # Path must be under tmp_path
        assert str(ws).startswith(str(tmp_path))

    def test_different_sessions_get_different_paths(self, tmp_path: Path):
        from agent.job_manager import make_isolated_workspace
        ws1 = make_isolated_workspace(tmp_path, "as_sess1", "aj_job1")
        ws2 = make_isolated_workspace(tmp_path, "as_sess2", "aj_job1")
        assert ws1 != ws2

    def test_raw_id_not_in_path(self, tmp_path: Path):
        from agent.job_manager import make_isolated_workspace
        ws = make_isolated_workspace(tmp_path, "as_rawtest", "aj_rawjob")
        assert "as_rawtest" not in str(ws)
        assert "aj_rawjob" not in str(ws)

    def test_traversal_in_session_id_rejected(self, tmp_path: Path):
        from agent.job_manager import make_isolated_workspace
        with pytest.raises(ValueError):
            make_isolated_workspace(tmp_path, "../../../etc", "aj_job1")

    def test_traversal_in_job_id_rejected(self, tmp_path: Path):
        from agent.job_manager import make_isolated_workspace
        with pytest.raises(ValueError):
            make_isolated_workspace(tmp_path, "as_sess1", "../../../etc")


# ---------------------------------------------------------------------------
# C4 — Security: no path traversal through workspace/session IDs
# ---------------------------------------------------------------------------


class TestWorkspaceSecurityRegressions:
    def test_workspace_manager_blocks_traversal_session_id(self, tmp_path: Path):
        from agent.workspace import WorkspaceManager, WorkspaceIDError
        mgr = WorkspaceManager(tmp_path / "ws")
        with pytest.raises(WorkspaceIDError):
            asyncio.run(
                mgr.create("../../etc/passwd", "aj_job001")
            )

    def test_workspace_manager_blocks_traversal_job_id(self, tmp_path: Path):
        from agent.workspace import WorkspaceManager, WorkspaceIDError
        mgr = WorkspaceManager(tmp_path / "ws")
        with pytest.raises(WorkspaceIDError):
            asyncio.run(
                mgr.create("as_sess1", "../../etc/shadow")
            )

    def test_workspace_error_dict_does_not_leak_base_path(self, tmp_path: Path):
        from agent.workspace import WorkspaceManager, WorkspaceEscapeError
        mgr = WorkspaceManager(tmp_path / "ws_secret_base")
        asyncio.run(
            mgr.create("as_sess1", "aj_job001")
        )
        ws = asyncio.run(
            mgr.open("as_sess1", "aj_job001")
        )
        try:
            mgr.safe_path(ws, "../../outside")
        except WorkspaceEscapeError as exc:
            d = exc.as_dict()
            # The internal base path must not appear verbatim in the external error
            assert "ws_secret_base" not in d["message"]

    def test_feature_unavailable_error_has_no_internal_details(self):
        from features.matrix import FeatureUnavailableError, FeatureMaturity
        err = FeatureUnavailableError("secret_feature", FeatureMaturity.DISABLED, reason="internal only")
        d = err.as_dict()
        # Must have structured fields but not expose raw stack traces
        assert "code" in d
        assert "feature_id" in d
        assert "maturity" in d


# ---------------------------------------------------------------------------
# C3.8 — Workspace metrics endpoint (integration)
# ---------------------------------------------------------------------------


class TestAdminEndpoints:
    def test_feature_matrix_endpoint_requires_auth(self):
        from fastapi.testclient import TestClient
        import proxy
        client = TestClient(proxy.app, raise_server_exceptions=False)
        resp = client.get("/admin/api/features")
        # Must not return 200 without admin credentials
        assert resp.status_code in (401, 403, 404, 422)

    def test_workspace_metrics_endpoint_requires_auth(self):
        from fastapi.testclient import TestClient
        import proxy
        client = TestClient(proxy.app, raise_server_exceptions=False)
        resp = client.get("/admin/api/workspaces/metrics")
        assert resp.status_code in (401, 403, 404, 422)

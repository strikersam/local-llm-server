"""tests/test_workspace_isolation.py — Workspace isolation, path safety, and lifecycle tests.

Covers:
  C1 - Workspace isolation
  C4 - Security-oriented path traversal / symlink escape tests
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import pytest

from agent.workspace import (
    WorkspaceAccessDeniedError,
    WorkspaceEscapeError,
    WorkspaceIDError,
    WorkspaceLockError,
    WorkspaceManifest,
    WorkspaceManifestError,
    WorkspaceManager,
    WorkspaceNotFoundError,
    WorkspaceNotResumableError,
    WorkspaceStatus,
    _hash_component,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def run(coro):
    """Run a coroutine synchronously (test helper)."""
    return asyncio.run(coro)


@pytest.fixture()
def mgr(tmp_path: Path) -> WorkspaceManager:
    return WorkspaceManager(base_root=tmp_path / "workspaces", default_ttl_hours=1.0)


# ---------------------------------------------------------------------------
# A1 — Deterministic workspace roots
# ---------------------------------------------------------------------------


class TestDeterministicPaths:
    def test_unique_path_per_session_job(self, mgr: WorkspaceManager, tmp_path: Path):
        ws1 = run(mgr.create("as_aaa111", "aj_bbb222"))
        ws2 = run(mgr.create("as_xxx999", "aj_yyy888"))
        assert ws1.root != ws2.root, "Different session+job must produce different roots"

    def test_same_ids_produce_same_path(self, mgr: WorkspaceManager):
        ws1 = run(mgr.create("as_abc123", "aj_def456"))
        # Compute expected hash components
        sess_hash = _hash_component("as_abc123")
        job_hash = _hash_component("aj_def456")
        assert sess_hash in str(ws1.root), "Session hash must appear in root"
        assert job_hash in str(ws1.root), "Job hash must appear in root"

    def test_raw_id_not_in_path(self, mgr: WorkspaceManager):
        ws = run(mgr.create("as_abc123", "aj_def456"))
        assert "as_abc123" not in str(ws.root), "Raw session ID must not appear in path"
        assert "aj_def456" not in str(ws.root), "Raw job ID must not appear in path"

    def test_subdirectories_created(self, mgr: WorkspaceManager):
        ws = run(mgr.create("as_session1", "aj_job001"))
        assert ws.source.is_dir()
        assert ws.checkpoints.is_dir()
        assert ws.logs.is_dir()
        assert ws.artifacts.is_dir()
        assert ws.tmp.is_dir()

    def test_manifest_written(self, mgr: WorkspaceManager):
        ws = run(mgr.create("as_session1", "aj_job001"))
        manifest_path = ws.root / "workspace.json"
        assert manifest_path.exists()
        data = json.loads(manifest_path.read_text())
        assert data["session_id"] == "as_session1"
        assert data["job_id"] == "aj_job001"
        assert data["schema_version"] == "1"

    def test_different_jobs_same_session_isolated(self, mgr: WorkspaceManager):
        ws1 = run(mgr.create("as_shared", "aj_job001"))
        ws2 = run(mgr.create("as_shared", "aj_job002"))
        assert ws1.root != ws2.root
        # No path overlap for source trees
        assert ws2.source != ws1.source


# ---------------------------------------------------------------------------
# A2 — ID validation
# ---------------------------------------------------------------------------


class TestIDValidation:
    @pytest.mark.parametrize(
        "bad_id",
        [
            "",
            "a",  # too short
            "../etc/passwd",
            "../../root",
            "/absolute/path",
            "has space",
            "has\nnewline",
            "!invalid@chars",
            "a" * 65,  # too long
        ],
    )
    def test_invalid_session_id_rejected(self, mgr: WorkspaceManager, bad_id: str):
        with pytest.raises(WorkspaceIDError):
            run(mgr.create(bad_id, "aj_valid01"))

    @pytest.mark.parametrize(
        "bad_id",
        [
            "",
            "a",
            "../etc/passwd",
            "../../root",
            "/absolute",
            "has space",
            "a" * 65,
        ],
    )
    def test_invalid_job_id_rejected(self, mgr: WorkspaceManager, bad_id: str):
        with pytest.raises(WorkspaceIDError):
            run(mgr.create("as_valid01", bad_id))

    @pytest.mark.parametrize(
        "good_id",
        [
            "as_abc123",
            "aj_def-456",
            "session.v1",
            "AB",  # min 2 chars
            "a" * 64,  # max chars
        ],
    )
    def test_valid_ids_accepted(self, mgr: WorkspaceManager, good_id: str):
        ws = run(mgr.create(good_id, "aj_job001"))
        assert ws.session_id == good_id


# ---------------------------------------------------------------------------
# A2 — Path safety / traversal / symlink escape
# ---------------------------------------------------------------------------


class TestPathSafety:
    def test_traversal_in_relative_path_rejected(self, mgr: WorkspaceManager):
        ws = run(mgr.create("as_sess1", "aj_job001"))
        with pytest.raises(WorkspaceEscapeError):
            mgr.safe_path(ws, "../../etc/passwd")

    def test_absolute_path_escape_rejected(self, mgr: WorkspaceManager):
        ws = run(mgr.create("as_sess1", "aj_job001"))
        with pytest.raises(WorkspaceEscapeError):
            # Absolute path attempts to leave workspace
            mgr.safe_path(ws, "/etc/shadow")

    def test_null_byte_traversal_rejected(self, mgr: WorkspaceManager):
        ws = run(mgr.create("as_sess1", "aj_job001"))
        with pytest.raises((WorkspaceEscapeError, ValueError)):
            mgr.safe_path(ws, "file\x00../../etc/passwd")

    def test_dot_dot_at_root_rejected(self, mgr: WorkspaceManager):
        ws = run(mgr.create("as_sess1", "aj_job001"))
        with pytest.raises(WorkspaceEscapeError):
            mgr.safe_path(ws, "..")

    def test_symlink_escape_rejected(self, mgr: WorkspaceManager, tmp_path: Path):
        ws = run(mgr.create("as_sess1", "aj_job001"))
        # Create a symlink inside source/ pointing outside workspace root
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        (outside_dir / "secret.txt").write_text("secret")
        link = ws.source / "evil_link"
        link.symlink_to(outside_dir)
        # Accessing through the symlink should be rejected
        with pytest.raises(WorkspaceEscapeError):
            mgr.safe_path(ws, "evil_link/secret.txt")

    def test_valid_relative_path_accepted(self, mgr: WorkspaceManager):
        ws = run(mgr.create("as_sess1", "aj_job001"))
        (ws.source / "subdir").mkdir()
        safe = mgr.safe_path(ws, "subdir/file.py")
        assert safe.parent == ws.source / "subdir"

    def test_workspace_error_does_not_leak_internal_paths(self, mgr: WorkspaceManager):
        ws = run(mgr.create("as_sess1", "aj_job001"))
        try:
            mgr.safe_path(ws, "../../etc/passwd")
        except WorkspaceEscapeError as exc:
            msg = exc.as_dict()
            # Internal absolute paths must not appear in the external error dict
            assert str(mgr._base) not in msg["message"]


# ---------------------------------------------------------------------------
# A3 — Session/job ownership
# ---------------------------------------------------------------------------


class TestOwnershipBoundaries:
    def test_resume_correct_session_succeeds(self, mgr: WorkspaceManager):
        ws = run(mgr.create("as_ownerA", "aj_job001"))
        run(mgr.transition(ws, WorkspaceStatus.PAUSED))
        # Re-open clean instance
        mgr2 = WorkspaceManager(base_root=mgr._base, default_ttl_hours=1.0)
        resumed = run(mgr2.resume("as_ownerA", "aj_job001"))
        assert resumed.session_id == "as_ownerA"

    def test_assert_session_owns_raises_for_wrong_session(self, mgr: WorkspaceManager):
        ws = run(mgr.create("as_ownerA", "aj_job001"))
        with pytest.raises(WorkspaceAccessDeniedError):
            mgr.assert_session_owns(ws, "as_ownerB")

    def test_resume_wrong_session_rejected(self, mgr: WorkspaceManager):
        ws = run(mgr.create("as_ownerA", "aj_job001"))
        run(mgr.transition(ws, WorkspaceStatus.PAUSED))
        mgr2 = WorkspaceManager(base_root=mgr._base, default_ttl_hours=1.0)
        # Tamper: manually open with wrong session_id — should fail ID mismatch
        ws2 = run(mgr2.open("as_ownerA", "aj_job001"))
        with pytest.raises(WorkspaceAccessDeniedError):
            mgr2.assert_session_owns(ws2, "as_attacker")

    def test_no_cross_session_artifact_leakage(self, mgr: WorkspaceManager):
        ws1 = run(mgr.create("as_sess1", "aj_job001"))
        ws2 = run(mgr.create("as_sess2", "aj_job002"))
        (ws1.artifacts / "result.txt").write_text("session1 output")
        # ws2's artifact dir is empty and separate
        assert not (ws2.artifacts / "result.txt").exists()


# ---------------------------------------------------------------------------
# A3 — Concurrent lock guard
# ---------------------------------------------------------------------------


class TestConcurrencyLock:
    def test_acquire_lock_twice_raises(self, mgr: WorkspaceManager):
        async def _run():
            ws = await mgr.create("as_lock1", "aj_job001")
            await mgr.acquire_lock(ws)
            # Second acquire with very short timeout must fail
            mgr2 = WorkspaceManager(base_root=mgr._base, lock_timeout_sec=0.05)
            # Use same in-memory ws object (lock is on the Workspace instance)
            with pytest.raises(WorkspaceLockError):
                await mgr2.acquire_lock(ws)
            mgr.release_lock(ws)

        asyncio.run(_run())

    def test_lock_release_allows_reacquire(self, mgr: WorkspaceManager):
        async def _run():
            ws = await mgr.create("as_lock2", "aj_job002")
            await mgr.acquire_lock(ws)
            mgr.release_lock(ws)
            # Should be acquirable again
            await mgr.acquire_lock(ws)
            mgr.release_lock(ws)

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# A4 — Lifecycle states
# ---------------------------------------------------------------------------


class TestLifecycleStates:
    def test_initial_status_is_ready(self, mgr: WorkspaceManager):
        ws = run(mgr.create("as_lc1", "aj_job001"))
        assert ws.status == WorkspaceStatus.READY

    def test_transition_persists_to_manifest(self, mgr: WorkspaceManager):
        ws = run(mgr.create("as_lc1", "aj_job001"))
        run(mgr.transition(ws, WorkspaceStatus.ACTIVE))
        manifest_path = ws.root / "workspace.json"
        data = json.loads(manifest_path.read_text())
        assert data["status"] == "active"

    def test_resume_only_from_resumable_states(self, mgr: WorkspaceManager):
        ws = run(mgr.create("as_lc2", "aj_job001"))
        run(mgr.transition(ws, WorkspaceStatus.COMPLETED))
        # Create fresh manager to bypass in-memory cache
        mgr2 = WorkspaceManager(base_root=mgr._base, default_ttl_hours=1.0)
        with pytest.raises(WorkspaceNotResumableError):
            run(mgr2.resume("as_lc2", "aj_job001"))

    def test_terminal_states_set_cleanup_eligible(self, mgr: WorkspaceManager):
        ws = run(mgr.create("as_lc3", "aj_job001"))
        run(mgr.transition(ws, WorkspaceStatus.FAILED))
        assert ws.manifest.cleanup_eligible is True

    def test_failed_workspace_not_resumable(self, mgr: WorkspaceManager):
        ws = run(mgr.create("as_lc3", "aj_job002"))
        run(mgr.transition(ws, WorkspaceStatus.FAILED))
        mgr2 = WorkspaceManager(base_root=mgr._base, default_ttl_hours=1.0)
        with pytest.raises(WorkspaceNotResumableError):
            run(mgr2.resume("as_lc3", "aj_job002"))


# ---------------------------------------------------------------------------
# A4 — Cleanup respects active locks and TTL
# ---------------------------------------------------------------------------


class TestCleanup:
    def test_cleanup_removes_expired_workspace(self, mgr: WorkspaceManager):
        ws = run(mgr.create("as_clean1", "aj_job001", ttl_hours=-1.0))  # already expired
        run(mgr.transition(ws, WorkspaceStatus.COMPLETED))
        root = ws.root
        assert root.exists()
        result = run(mgr.cleanup_expired())
        assert result["cleaned"] >= 1
        assert not root.exists()

    def test_cleanup_skips_active_workspace(self, mgr: WorkspaceManager):
        ws = run(mgr.create("as_active1", "aj_job001", ttl_hours=-1.0))
        run(mgr.transition(ws, WorkspaceStatus.ACTIVE))
        root = ws.root
        result = run(mgr.cleanup_expired())
        assert result["skipped_active"] >= 1
        assert root.exists()

    def test_cleanup_dry_run_does_not_delete(self, mgr: WorkspaceManager):
        ws = run(mgr.create("as_dry1", "aj_job001", ttl_hours=-1.0))
        run(mgr.transition(ws, WorkspaceStatus.COMPLETED))
        root = ws.root
        result = run(mgr.cleanup_expired(dry_run=True))
        assert result["cleaned"] >= 1
        assert root.exists()  # not actually deleted

    def test_cleanup_respects_cleanup_after_in_future(self, mgr: WorkspaceManager):
        ws = run(mgr.create("as_future1", "aj_job001", ttl_hours=100.0))  # far future
        run(mgr.transition(ws, WorkspaceStatus.COMPLETED))
        root = ws.root
        result = run(mgr.cleanup_expired())
        assert root.exists()

    def test_clean_tmp_recreates_directory(self, mgr: WorkspaceManager):
        ws = run(mgr.create("as_tmp1", "aj_job001"))
        (ws.tmp / "scratch.txt").write_text("scratch")
        run(mgr.clean_tmp(ws))
        assert ws.tmp.is_dir()
        assert not (ws.tmp / "scratch.txt").exists()


# ---------------------------------------------------------------------------
# A5 — Manifest validation
# ---------------------------------------------------------------------------


class TestManifest:
    def test_manifest_fields_complete(self, mgr: WorkspaceManager):
        ws = run(mgr.create("as_mf1", "aj_job001", runtime_type="task_harness"))
        data = json.loads((ws.root / "workspace.json").read_text())
        for field in (
            "schema_version",
            "session_id",
            "job_id",
            "created_at",
            "updated_at",
            "last_heartbeat",
            "runtime_type",
            "status",
            "root",
            "source_path",
            "checkpoints_path",
            "logs_path",
            "artifacts_path",
            "tmp_path",
            "cleanup_eligible",
        ):
            assert field in data, f"Missing manifest field: {field}"
        assert data["runtime_type"] == "task_harness"

    def test_open_nonexistent_raises_not_found(self, mgr: WorkspaceManager):
        with pytest.raises(WorkspaceNotFoundError):
            run(mgr.open("as_ghost1", "aj_ghost001"))

    def test_corrupt_manifest_raises_manifest_error(self, mgr: WorkspaceManager, tmp_path: Path):
        ws = run(mgr.create("as_corrupt1", "aj_job001"))
        # Corrupt the manifest
        (ws.root / "workspace.json").write_text("{invalid json{{{{")
        mgr2 = WorkspaceManager(base_root=mgr._base, default_ttl_hours=1.0)
        mgr2._open.clear()
        with pytest.raises(WorkspaceManifestError):
            run(mgr2.open("as_corrupt1", "aj_job001"))

    def test_heartbeat_updates_timestamp(self, mgr: WorkspaceManager, monkeypatch):
        import agent.workspace as ws_mod
        ws = run(mgr.create("as_hb1", "aj_job001"))
        # Patch _iso_now to return a deterministically different value
        monkeypatch.setattr(ws_mod, "_iso_now", lambda: "2099-01-01T00:00:00Z")
        run(mgr.heartbeat(ws))
        assert ws.manifest.last_heartbeat == "2099-01-01T00:00:00Z"


# ---------------------------------------------------------------------------
# A6 — Workspace from env var / singleton
# ---------------------------------------------------------------------------


class TestSingleton:
    def test_get_workspace_manager_returns_same_instance(self, monkeypatch, tmp_path):
        from agent import workspace as ws_mod
        monkeypatch.setattr(ws_mod, "_default_manager", None)
        monkeypatch.setenv("AGENT_WORKSPACE_BASE", str(tmp_path / "wsbases"))
        mgr1 = ws_mod.get_workspace_manager()
        mgr2 = ws_mod.get_workspace_manager()
        assert mgr1 is mgr2

    def test_singleton_uses_env_base(self, monkeypatch, tmp_path):
        from agent import workspace as ws_mod
        base = str(tmp_path / "custom_base")
        monkeypatch.setattr(ws_mod, "_default_manager", None)
        monkeypatch.setenv("AGENT_WORKSPACE_BASE", base)
        mgr = ws_mod.get_workspace_manager()
        assert str(mgr._base) == str(Path(base).resolve())


# ---------------------------------------------------------------------------
# A7 — Structured error contracts
# ---------------------------------------------------------------------------


class TestStructuredErrors:
    def test_id_error_has_code_and_field(self):
        err = WorkspaceIDError("bad id", field="session_id")
        d = err.as_dict()
        assert d["code"] == "invalid_id"
        assert d["field"] == "session_id"
        assert "message" in d

    def test_not_found_error_has_code(self):
        err = WorkspaceNotFoundError("as_x", "aj_y")
        assert err.as_dict()["code"] == "workspace_not_found"

    def test_escape_error_has_code_no_internal_path(self):
        err = WorkspaceEscapeError("../../etc/passwd")
        d = err.as_dict()
        assert d["code"] == "workspace_escape"
        # Internal absolute paths must not leak
        assert "etc/passwd" not in d["message"]

    def test_access_denied_error_has_code(self):
        err = WorkspaceAccessDeniedError("as_a", "aj_b", "as_owner")
        assert err.as_dict()["code"] == "workspace_access_denied"

    def test_lock_error_has_code(self):
        err = WorkspaceLockError("aj_job")
        assert err.as_dict()["code"] == "workspace_locked"

    def test_manifest_error_has_code(self):
        err = WorkspaceManifestError("/path/to/manifest.json", "unexpected token")
        assert err.as_dict()["code"] == "workspace_manifest_corrupt"


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


class TestMetrics:
    def test_metrics_counts_by_status(self, mgr: WorkspaceManager):
        ws1 = run(mgr.create("as_m1", "aj_job001"))
        ws2 = run(mgr.create("as_m2", "aj_job002"))
        run(mgr.transition(ws2, WorkspaceStatus.COMPLETED))
        counts = mgr.metrics()
        assert counts.get("ready", 0) >= 1
        assert counts.get("completed", 0) >= 1

    def test_metrics_empty_base(self, tmp_path: Path):
        mgr = WorkspaceManager(base_root=tmp_path / "empty")
        assert mgr.metrics() == {}

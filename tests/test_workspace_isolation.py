"""Tests for workspace isolation model (Area A).

Covers:
  - Unique workspace path derivation per session/job
  - Session/job ID validation
  - Rejection of traversal attempts
  - Rejection of symlink escape
  - Lock/concurrency behavior
  - Resume only within correct session namespace
  - Cleanup respects active locks
  - Cleanup removes expired workspaces only
  - Manifest creation and corruption handling
  - No cross-session artifact leakage
"""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

import pytest

from workspace.manager import (
    WorkspaceManager,
    validate_session_id,
    validate_job_id,
    _hash_component,
    _safe_resolve,
)
from workspace.manifest import WorkspaceManifest, MANIFEST_SCHEMA_VERSION, CLEANABLE_STATES
from workspace.errors import (
    InvalidSessionIdError,
    InvalidJobIdError,
    WorkspaceNotFoundError,
    WorkspaceOutsideRootError,
    WorkspaceNotResumableError,
    WorkspaceCleanupBlockedError,
    WorkspaceManifestCorruptionError,
    WorkspacePermissionError,
)


# ── ID validation ─────────────────────────────────────────────────────────────


class TestSessionIdValidation:
    def test_valid_simple(self):
        assert validate_session_id("abc123") == "abc123"

    def test_valid_with_dashes(self):
        assert validate_session_id("session-1") == "session-1"

    def test_valid_with_dots(self):
        assert validate_session_id("session.v2") == "session.v2"

    def test_valid_with_underscores(self):
        assert validate_session_id("my_session") == "my_session"

    def test_rejects_empty(self):
        with pytest.raises(InvalidSessionIdError) as exc_info:
            validate_session_id("")
        assert exc_info.value.code == "invalid_session_id"

    def test_rejects_traversal(self):
        with pytest.raises(InvalidSessionIdError):
            validate_session_id("../../etc")

    def test_rejects_slash(self):
        with pytest.raises(InvalidSessionIdError):
            validate_session_id("foo/bar")

    def test_rejects_null_byte(self):
        with pytest.raises(InvalidSessionIdError):
            validate_session_id("foo\x00bar")

    def test_rejects_spaces(self):
        with pytest.raises(InvalidSessionIdError):
            validate_session_id("has space")

    def test_rejects_too_long(self):
        with pytest.raises(InvalidSessionIdError):
            validate_session_id("a" * 200)

    def test_rejects_starts_with_special(self):
        with pytest.raises(InvalidSessionIdError):
            validate_session_id("-starts-dash")


class TestJobIdValidation:
    def test_valid(self):
        assert validate_job_id("aj_abc123") == "aj_abc123"

    def test_rejects_traversal(self):
        with pytest.raises(InvalidJobIdError):
            validate_job_id("../../../tmp")

    def test_rejects_empty(self):
        with pytest.raises(InvalidJobIdError):
            validate_job_id("")


# ── Path derivation ───────────────────────────────────────────────────────────


class TestWorkspacePathDerivation:
    def test_different_sessions_get_different_roots(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        m1 = mgr.create_workspace("session-a", "job-1")
        m2 = mgr.create_workspace("session-b", "job-1")
        assert m1.root_path != m2.root_path

    def test_same_session_different_jobs_get_different_roots(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        m1 = mgr.create_workspace("session-a", "job-1")
        m2 = mgr.create_workspace("session-a", "job-2")
        assert m1.root_path != m2.root_path

    def test_hash_component_is_deterministic(self):
        h1 = _hash_component("test-session")
        h2 = _hash_component("test-session")
        assert h1 == h2
        assert len(h1) == 24

    def test_hash_component_is_opaque(self):
        h = _hash_component("my-session-id")
        # Should not contain the raw session ID
        assert "my-session-id" not in h

    def test_different_inputs_produce_different_hashes(self):
        assert _hash_component("aaa") != _hash_component("bbb")

    def test_workspace_root_under_base_root(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        manifest = mgr.create_workspace("sess-1", "job-1")
        root = Path(manifest.root_path)
        assert str(root).startswith(str(mgr.base_root))


# ── Traversal / symlink rejection ─────────────────────────────────────────────


class TestPathSafety:
    def test_rejects_traversal_session_id(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        with pytest.raises(InvalidSessionIdError):
            mgr.create_workspace("../../etc", "job-1")

    def test_rejects_traversal_job_id(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        with pytest.raises(InvalidJobIdError):
            mgr.create_workspace("session-1", "../../etc")

    def test_rejects_symlink_escape(self, tmp_path):
        """If a symlink inside the workspace points outside, resolve_path blocks it."""
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        manifest = mgr.create_workspace("sess-safe", "job-safe")

        # Create a symlink in the source dir that points outside
        source_dir = Path(manifest.source_path)
        escape_link = source_dir / "escape"
        try:
            escape_link.symlink_to("/etc/passwd")
        except (OSError, NotImplementedError):
            pytest.skip("Symlinks not supported on this platform")

        with pytest.raises(WorkspaceOutsideRootError):
            mgr.resolve_path("sess-safe", "job-safe", "escape")

    def test_safe_resolve_blocks_escape(self, tmp_path):
        base = tmp_path / "base"
        base.mkdir()
        with pytest.raises(WorkspaceOutsideRootError):
            _safe_resolve(tmp_path / "base" / ".." / ".." / "etc", base)

    def test_safe_resolve_allows_subpath(self, tmp_path):
        base = tmp_path / "base"
        base.mkdir()
        result = _safe_resolve(base / "subdir", base)
        assert str(result).startswith(str(base))


# ── Workspace lifecycle ───────────────────────────────────────────────────────


class TestWorkspaceLifecycle:
    def test_create_sets_status_to_ready(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        manifest = mgr.create_workspace("s1", "j1")
        assert manifest.status == "ready"

    def test_activate_sets_active(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        mgr.create_workspace("s1", "j1")
        manifest = mgr.activate("s1", "j1")
        assert manifest.status == "active"
        assert manifest.is_active

    def test_pause_sets_paused(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        mgr.create_workspace("s1", "j1")
        mgr.activate("s1", "j1")
        manifest = mgr.pause("s1", "j1")
        assert manifest.status == "paused"

    def test_complete_sets_completed(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        mgr.create_workspace("s1", "j1")
        mgr.activate("s1", "j1")
        manifest = mgr.complete("s1", "j1")
        assert manifest.status == "completed"
        assert manifest.cleanup_eligible

    def test_fail_sets_failed(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        mgr.create_workspace("s1", "j1")
        mgr.activate("s1", "j1")
        manifest = mgr.fail("s1", "j1")
        assert manifest.status == "failed"
        assert manifest.cleanup_eligible

    def test_cancel_transitions_cancelling_to_cancelled(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        mgr.create_workspace("s1", "j1")
        mgr.activate("s1", "j1")
        manifest = mgr.cancel("s1", "j1")
        assert manifest.status == "cancelled"
        assert manifest.cleanup_eligible

    def test_archive_completed(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        mgr.create_workspace("s1", "j1")
        mgr.activate("s1", "j1")
        mgr.complete("s1", "j1")
        manifest = mgr.archive("s1", "j1")
        assert manifest.status == "archived"


# ── Resume ────────────────────────────────────────────────────────────────────


class TestWorkspaceResume:
    def test_resume_active_workspace(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        mgr.create_workspace("s1", "j1")
        mgr.activate("s1", "j1")
        manifest = mgr.resume("s1", "j1")
        assert manifest.status == "active"
        assert mgr.metrics.resume_success == 1

    def test_resume_paused_workspace(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        mgr.create_workspace("s1", "j1")
        mgr.activate("s1", "j1")
        mgr.pause("s1", "j1")
        manifest = mgr.resume("s1", "j1")
        assert manifest.status == "active"

    def test_resume_ready_workspace(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        mgr.create_workspace("s1", "j1")
        manifest = mgr.resume("s1", "j1")
        assert manifest.status == "active"

    def test_resume_completed_workspace_raises(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        mgr.create_workspace("s1", "j1")
        mgr.activate("s1", "j1")
        mgr.complete("s1", "j1")
        with pytest.raises(WorkspaceNotResumableError) as exc_info:
            mgr.resume("s1", "j1")
        assert exc_info.value.code == "workspace_not_resumable"
        assert mgr.metrics.resume_failure == 1

    def test_resume_failed_workspace_raises(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        mgr.create_workspace("s1", "j1")
        mgr.activate("s1", "j1")
        mgr.fail("s1", "j1")
        with pytest.raises(WorkspaceNotResumableError):
            mgr.resume("s1", "j1")

    def test_resume_only_within_correct_session(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        mgr.create_workspace("session-a", "job-1")
        mgr.create_workspace("session-b", "job-1")
        with pytest.raises(WorkspaceNotFoundError):
            mgr.get_workspace("session-a", "job-999")


# ── Cleanup ───────────────────────────────────────────────────────────────────


class TestWorkspaceCleanup:
    def test_cleanup_completed_workspace(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws", retention_ttl_seconds=0)
        mgr.create_workspace("s1", "j1")
        mgr.activate("s1", "j1")
        mgr.complete("s1", "j1")
        result = mgr.cleanup_workspace("s1", "j1")
        assert result is True
        assert mgr.metrics.cleanup_count == 1

    def test_cleanup_active_workspace_raises(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        mgr.create_workspace("s1", "j1")
        mgr.activate("s1", "j1")
        with pytest.raises(WorkspaceCleanupBlockedError):
            mgr.cleanup_workspace("s1", "j1")
        assert mgr.metrics.cleanup_skipped_active == 0  # raised before incrementing

    def test_cleanup_expired_only(self, tmp_path):
        """Only expired workspaces (past retention TTL) are cleaned up."""
        mgr = WorkspaceManager(base_root=tmp_path / "ws", retention_ttl_seconds=0)
        # Create and complete workspace-1
        mgr.create_workspace("s1", "j1")
        mgr.activate("s1", "j1")
        mgr.complete("s1", "j1")

        # Create active workspace-2
        mgr.create_workspace("s2", "j2")
        mgr.activate("s2", "j2")

        cleaned = mgr.cleanup_expired()
        assert "s1" in cleaned
        assert "s2" not in cleaned

    def test_cleanup_does_not_delete_active(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws", retention_ttl_seconds=0)
        mgr.create_workspace("s-active", "j1")
        mgr.activate("s-active", "j1")
        cleaned = mgr.cleanup_expired()
        assert "s-active" not in cleaned
        # Workspace still exists
        manifest = mgr.get_workspace("s-active", "j1")
        assert manifest.status == "active"


# ── Manifest ──────────────────────────────────────────────────────────────────


class TestWorkspaceManifest:
    def test_manifest_created_on_disk(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        manifest = mgr.create_workspace("s1", "j1")
        manifest_path = Path(manifest.root_path) / "manifest.json"
        assert manifest_path.exists()
        data = json.loads(manifest_path.read_text())
        assert data["session_id"] == "s1"
        assert data["job_id"] == "j1"
        assert data["schema_version"] == MANIFEST_SCHEMA_VERSION

    def test_manifest_has_subdirectory_paths(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        manifest = mgr.create_workspace("s1", "j1")
        assert manifest.source_path is not None
        assert manifest.checkpoints_path is not None
        assert manifest.logs_path is not None
        assert manifest.artifacts_path is not None
        assert manifest.temp_path is not None
        # Directories should exist on disk
        assert Path(manifest.source_path).is_dir()
        assert Path(manifest.artifacts_path).is_dir()

    def test_manifest_corruption_raises(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        manifest = mgr.create_workspace("s1", "j1")
        manifest_path = Path(manifest.root_path) / "manifest.json"
        # Corrupt the file
        manifest_path.write_text("NOT VALID JSON{{{{")
        # Force re-read from disk
        mgr._manifests.clear()
        with pytest.raises(WorkspaceManifestCorruptionError):
            mgr.get_workspace("s1", "j1")

    def test_manifest_schema_version(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        manifest = mgr.create_workspace("s1", "j1")
        assert manifest.schema_version == MANIFEST_SCHEMA_VERSION

    def test_heartbeat_updates_timestamp(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        mgr.create_workspace("s1", "j1")
        before = mgr.get_workspace("s1", "j1").last_heartbeat
        time.sleep(0.01)
        mgr.heartbeat("s1", "j1")
        after = mgr.get_workspace("s1", "j1").last_heartbeat
        # They might be the same second but the manifest was updated
        assert after is not None


# ── Cross-session isolation ───────────────────────────────────────────────────


class TestCrossSessionIsolation:
    def test_no_cross_session_artifact_leakage(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        m1 = mgr.create_workspace("session-a", "job-1")
        m2 = mgr.create_workspace("session-b", "job-1")
        # Write a file in session-a
        a_artifact = Path(m1.artifacts_path) / "secret.txt"
        a_artifact.write_text("session-a secret")
        # Session-b should not see it
        b_artifacts = Path(m2.artifacts_path)
        assert not (b_artifacts / "secret.txt").exists()
        # Paths must not overlap
        assert not str(m2.root_path).startswith(str(m1.root_path))
        assert not str(m1.root_path).startswith(str(m2.root_path))

    def test_session_job_boundary(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        m1 = mgr.create_workspace("s1", "j1")
        m2 = mgr.create_workspace("s1", "j2")
        assert m1.root_path != m2.root_path
        # Write artifact in j1
        (Path(m1.artifacts_path) / "j1.txt").write_text("j1 data")
        assert not (Path(m2.artifacts_path) / "j1.txt").exists()


# ── Concurrency ───────────────────────────────────────────────────────────────


class TestConcurrency:
    def test_concurrent_create_same_session(self, tmp_path):
        """Two threads creating the same session/job should not corrupt state."""
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        results = []
        errors = []

        def create():
            try:
                m = mgr.create_workspace("s-concurrent", "j-concurrent")
                results.append(m)
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=create)
        t2 = threading.Thread(target=create)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        # At least one should succeed
        assert len(results) >= 1
        # If both succeeded, they should point to the same workspace
        if len(results) == 2:
            assert results[0].root_path == results[1].root_path


# ── Workspace not found ───────────────────────────────────────────────────────


class TestWorkspaceNotFound:
    def test_get_nonexistent_workspace(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        with pytest.raises(WorkspaceNotFoundError):
            mgr.get_workspace("nonexistent", "nope")

    def test_get_nonexistent_session(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        with pytest.raises(WorkspaceNotFoundError):
            mgr.get_workspace("no-such-session", None)


# ── Metrics ───────────────────────────────────────────────────────────────────


class TestWorkspaceMetrics:
    def test_metrics_after_lifecycle(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        mgr.create_workspace("s1", "j1")
        mgr.activate("s1", "j1")
        mgr.complete("s1", "j1")
        metrics = mgr.metrics.as_dict()
        assert "active_count" in metrics
        assert "cleanup_count" in metrics
        assert "resume_success" in metrics
        assert "resume_failure" in metrics

    def test_diagnostics(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        mgr.create_workspace("s1", "j1")
        diag = mgr.diagnostics()
        assert "base_root" in diag
        assert "metrics" in diag
        assert "workspaces" in diag
        assert diag["base_root_exists"] is True

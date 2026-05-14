"""Security-oriented tests for workspace isolation (Area C4).

Covers:
  - No path traversal through workspace/session IDs
  - No internal path leakage in external API error messages
  - Workspace hashing/canonicalization behavior
  - Cleanup and archive endpoints do not expose unrelated sessions
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from workspace.manager import WorkspaceManager, validate_session_id, validate_job_id, _hash_component, _safe_resolve
from workspace.errors import (
    InvalidSessionIdError,
    InvalidJobIdError,
    WorkspaceOutsideRootError,
    WorkspaceNotFoundError,
)


# ── Path traversal prevention ─────────────────────────────────────────────────


class TestPathTraversalPrevention:
    @pytest.mark.parametrize("malicious_id", [
        "../../etc/passwd",
        "..%2F..%2Fetc",
        "../",
        "..\\",
        "....//....//etc",
        "/absolute/path",
        "session/../../etc",
    ])
    def test_malicious_session_ids_rejected(self, malicious_id):
        with pytest.raises(InvalidSessionIdError):
            validate_session_id(malicious_id)

    @pytest.mark.parametrize("malicious_id", [
        "../../etc/passwd",
        "../tmp",
        "/absolute",
        "job/../../../etc",
    ])
    def test_malicious_job_ids_rejected(self, malicious_id):
        with pytest.raises(InvalidJobIdError):
            validate_job_id(malicious_id)

    def test_workspace_path_cannot_escape_root(self, tmp_path):
        base = tmp_path / "base"
        base.mkdir()
        # Direct path traversal attempt
        with pytest.raises(WorkspaceOutsideRootError):
            _safe_resolve(base / ".." / ".." / "etc" / "passwd", base)

    def test_workspace_manager_rejects_traversal_ids(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        with pytest.raises(InvalidSessionIdError):
            mgr.create_workspace("../../etc", "job-1")

    def test_double_dot_in_middle_rejected(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        with pytest.raises(InvalidSessionIdError):
            mgr.create_workspace("valid../escape", "job-1")


# ── No internal path leakage ─────────────────────────────────────────────────


class TestNoInternalPathLeakage:
    def test_error_messages_do_not_leak_full_paths(self, tmp_path):
        """WorkspaceNotFoundError should not expose the base root in error messages."""
        mgr = WorkspaceManager(base_root=tmp_path / "secret-root-xyz")
        try:
            mgr.get_workspace("nonexistent", None)
        except WorkspaceNotFoundError as exc:
            msg = str(exc)
            # Should not include the base root path
            assert "secret-root-xyz" not in msg

    def test_error_as_dict_has_no_path_fields(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        try:
            mgr.get_workspace("nonexistent", None)
        except WorkspaceNotFoundError as exc:
            d = exc.as_dict()
            assert "root_path" not in d
            assert "base_root" not in d
            # Only safe fields
            assert d["code"] == "workspace_not_found"

    def test_invalid_session_id_error_no_path_info(self):
        try:
            validate_session_id("../../etc")
        except InvalidSessionIdError as exc:
            d = exc.as_dict()
            assert "path" not in d
            assert d["code"] == "invalid_session_id"


# ── Workspace hashing/canonicalization ────────────────────────────────────────


class TestWorkspaceHashing:
    def test_hash_is_one_way(self):
        """The hash component should not be reversible to the original ID."""
        h = _hash_component("my-secret-session-id")
        assert "my-secret-session-id" not in h

    def test_hash_is_consistent(self):
        assert _hash_component("abc") == _hash_component("abc")

    def test_hash_length_is_fixed(self):
        assert len(_hash_component("short")) == 24
        assert len(_hash_component("a" * 1000)) == 24

    def test_workspace_root_is_canonical(self, tmp_path):
        """Workspace root path should be fully resolved (no . or ..)."""
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        manifest = mgr.create_workspace("test-session", "test-job")
        root = manifest.root_path
        # No .. or relative components
        assert ".." not in root
        assert Path(root).is_absolute()


# ── Cleanup isolation ─────────────────────────────────────────────────────────


class TestCleanupIsolation:
    def test_cleanup_does_not_expose_other_sessions(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws", retention_ttl_seconds=0)
        # Create two sessions
        mgr.create_workspace("session-a", "job-1")
        mgr.create_workspace("session-b", "job-2")

        mgr.activate("session-a", "job-1")
        mgr.complete("session-a", "job-1")

        # Clean up session-a
        cleaned = mgr.cleanup_expired()
        assert "session-a" in cleaned
        # Session-b should still exist
        manifest_b = mgr.get_workspace("session-b", "job-2")
        assert manifest_b.status == "ready"

    def test_cleanup_does_not_delete_across_sessions(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws", retention_ttl_seconds=0)
        m_a = mgr.create_workspace("s-alpha", "j-1")
        m_b = mgr.create_workspace("s-beta", "j-1")

        # Write artifacts in both
        (Path(m_a.artifacts_path) / "a.txt").write_text("alpha data")
        (Path(m_b.artifacts_path) / "b.txt").write_text("beta data")

        # Complete and clean alpha
        mgr.activate("s-alpha", "j-1")
        mgr.complete("s-alpha", "j-1")
        mgr.cleanup_workspace("s-alpha", "j-1")

        # Beta artifacts should still be there
        assert (Path(m_b.artifacts_path) / "b.txt").exists()


# ── Symlink attack prevention ─────────────────────────────────────────────────


class TestSymlinkAttackPrevention:
    def test_resolve_path_rejects_symlink_escape(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        manifest = mgr.create_workspace("s-symlink", "j-1")

        source_dir = Path(manifest.source_path)
        escape = source_dir / "escape_link"
        try:
            escape.symlink_to("/etc/passwd")
        except (OSError, NotImplementedError):
            pytest.skip("Symlinks not supported")

        with pytest.raises(WorkspaceOutsideRootError):
            mgr.resolve_path("s-symlink", "j-1", "escape_link")

    def test_resolve_path_allows_legitimate_subpaths(self, tmp_path):
        mgr = WorkspaceManager(base_root=tmp_path / "ws")
        manifest = mgr.create_workspace("s-legit", "j-1")

        result = mgr.resolve_path("s-legit", "j-1", "subdir/file.py")
        assert str(result).startswith(str(manifest.source_path))

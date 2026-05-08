"""workspace/manager.py — WorkspaceManager.

Provides strong isolated workspaces per session/job with:
  - Deterministic, validated workspace root derivation
  - Path safety (canonicalization, traversal rejection, symlink escape blocking)
  - Session/job ownership boundaries with locking
  - Workspace lifecycle management with retention/cleanup
  - Workspace manifest persistence
  - Structured, actionable errors
  - Workspace metrics
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import threading
import time
from pathlib import Path
from typing import Any

from workspace.errors import (
    InvalidJobIdError,
    InvalidSessionIdError,
    WorkspaceCleanupBlockedError,
    WorkspaceManifestCorruptionError,
    WorkspaceNotFoundError,
    WorkspaceOutsideRootError,
    WorkspaceNotResumableError,
    WorkspacePermissionError,
)
from workspace.manifest import (
    MANIFEST_SCHEMA_VERSION,
    CLEANABLE_STATES,
    RESUMABLE_STATES,
    WorkspaceManifest,
    WorkspaceStatusLiteral,
)

log = logging.getLogger("qwen-proxy")

# ── ID validation ─────────────────────────────────────────────────────────────

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def validate_session_id(session_id: str) -> str:
    """Validate and return a session ID, or raise InvalidSessionIdError."""
    if not _ID_RE.fullmatch(session_id):
        raise InvalidSessionIdError(session_id)
    return session_id


def validate_job_id(job_id: str) -> str:
    """Validate and return a job ID, or raise InvalidJobIdError."""
    if not _ID_RE.fullmatch(job_id):
        raise InvalidJobIdError(job_id)
    return job_id


# ── Path derivation ───────────────────────────────────────────────────────────

def _hash_component(value: str) -> str:
    """Derive a stable, opaque directory name from a validated ID.

    Using a truncated SHA-256 digest avoids exposing raw user IDs as
    directory names and prevents predictability attacks.
    """
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def _derive_workspace_root(base_root: Path, session_id: str, job_id: str | None = None) -> Path:
    """Derive the canonical, isolated workspace root directory.

    Layout: <base_root>/<session_hash>/<job_hash>  (or just <session_hash> when no job)
    """
    session_dir = _hash_component(session_id)
    if job_id:
        return (base_root / session_dir / _hash_component(job_id)).resolve()
    return (base_root / session_dir).resolve()


def _safe_resolve(path: Path, base_root: Path) -> Path:
    """Resolve *path* and verify it stays under *base_root*.

    Blocks symlink escape: the resolved path must have base_root as
    a parent (or be equal to it).
    """
    resolved = path.resolve()
    root_resolved = base_root.resolve()
    # Check that resolved is under root_resolved
    try:
        resolved.relative_to(root_resolved)
    except ValueError:
        raise WorkspaceOutsideRootError(str(resolved), str(root_resolved))
    return resolved


# ── Workspace subdirectories ─────────────────────────────────────────────────

_SUBDIRS = ("source", "checkpoints", "logs", "artifacts", "temp")


# ── Metrics ───────────────────────────────────────────────────────────────────


class WorkspaceMetrics:
    """Simple counters for workspace operations."""

    def __init__(self) -> None:
        self.active_count = 0
        self.expired_count = 0
        self.cleanup_count = 0
        self.cleanup_skipped_active = 0
        self.resume_success = 0
        self.resume_failure = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "active_count": self.active_count,
            "expired_count": self.expired_count,
            "cleanup_count": self.cleanup_count,
            "cleanup_skipped_active": self.cleanup_skipped_active,
            "resume_success": self.resume_success,
            "resume_failure": self.resume_failure,
        }


# ── WorkspaceManager ─────────────────────────────────────────────────────────


class WorkspaceManager:
    """First-class workspace isolation manager.

    Every session/job gets its own validated, isolated workspace root
    under a single configured base directory.  Paths are canonicalized
    and checked for traversal/symlink escape.  A structured manifest is
    maintained for each workspace.  Concurrency is guarded with locks.
    """

    def __init__(
        self,
        *,
        base_root: str | Path | None = None,
        retention_ttl_seconds: int = 86400 * 7,  # 7 days default
        cleanup_interval_seconds: int = 3600,  # 1 hour
    ) -> None:
        if base_root is None:
            base_root = os.environ.get(
                "WORKSPACE_BASE_ROOT", ".data/workspaces"
            )
        self._base_root = Path(base_root).resolve()
        self._retention_ttl = retention_ttl_seconds
        self._cleanup_interval = cleanup_interval_seconds
        self._metrics = WorkspaceMetrics()
        self._lock = threading.RLock()
        # session_id -> job_id -> WorkspaceManifest
        self._manifests: dict[str, dict[str | None, WorkspaceManifest]] = {}

    # ── Properties ─────────────────────────────────────────────────────────

    @property
    def base_root(self) -> Path:
        return self._base_root

    @property
    def retention_ttl_seconds(self) -> int:
        return self._retention_ttl

    @property
    def metrics(self) -> WorkspaceMetrics:
        return self._metrics

    # ── Workspace creation ─────────────────────────────────────────────────

    def create_workspace(
        self,
        session_id: str,
        job_id: str | None = None,
        runtime_type: str = "local",
        repo_url: str | None = None,
    ) -> WorkspaceManifest:
        """Create an isolated workspace for a session/job pair.

        Returns the workspace manifest.  Raises on invalid IDs or
        traversal/symlink attacks.
        """
        session_id = validate_session_id(session_id)
        if job_id is not None:
            job_id = validate_job_id(job_id)

        workspace_root = _derive_workspace_root(self._base_root, session_id, job_id)
        workspace_root = _safe_resolve(workspace_root, self._base_root)

        # Create directory structure
        with self._lock:
            try:
                workspace_root.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise WorkspacePermissionError(str(workspace_root), str(exc)) from exc

            subdirs: dict[str, Path] = {}
            for sub in _SUBDIRS:
                p = workspace_root / sub
                p.mkdir(parents=True, exist_ok=True)
                subdirs[sub] = p

            manifest = WorkspaceManifest(
                session_id=session_id,
                job_id=job_id,
                runtime_type=runtime_type,
                root_path=str(workspace_root),
                source_path=str(subdirs["source"]),
                checkpoints_path=str(subdirs["checkpoints"]),
                logs_path=str(subdirs["logs"]),
                artifacts_path=str(subdirs["artifacts"]),
                temp_path=str(subdirs["temp"]),
                repo_url=repo_url,
                status="creating",
                cleanup_eligible=False,
                schema_version=MANIFEST_SCHEMA_VERSION,
            )

            # Write manifest to disk
            self._write_manifest(manifest)
            manifest.update_status("ready")

            # Cache in memory
            self._manifests.setdefault(session_id, {})[job_id] = manifest
            self._metrics.active_count = self._count_active()
            self._write_manifest(manifest)

        log.info(
            "Workspace created: session=%s job=%s root=%s",
            session_id, job_id, workspace_root,
        )
        return manifest

    # ── Lookup ─────────────────────────────────────────────────────────────

    def get_workspace(
        self, session_id: str, job_id: str | None = None
    ) -> WorkspaceManifest:
        """Return the workspace manifest or raise WorkspaceNotFoundError."""
        session_id = validate_session_id(session_id)
        if job_id is not None:
            job_id = validate_job_id(job_id)

        with self._lock:
            # Try memory cache first
            session_manifests = self._manifests.get(session_id)
            if session_manifests:
                manifest = session_manifests.get(job_id)
                if manifest:
                    return manifest

            # Fall back to disk
            workspace_root = _derive_workspace_root(self._base_root, session_id, job_id)
            try:
                workspace_root = _safe_resolve(workspace_root, self._base_root)
            except WorkspaceOutsideRootError:
                raise WorkspaceNotFoundError(session_id, job_id)

            manifest_path = workspace_root / "manifest.json"
            if not manifest_path.exists():
                raise WorkspaceNotFoundError(session_id, job_id)

            manifest = self._read_manifest(manifest_path)
            # Verify ownership
            if manifest.session_id != session_id or manifest.job_id != job_id:
                raise WorkspaceNotFoundError(session_id, job_id)

            # Cache
            self._manifests.setdefault(session_id, {})[job_id] = manifest
            return manifest

    def list_workspaces(
        self, status: WorkspaceStatusLiteral | None = None
    ) -> list[WorkspaceManifest]:
        """List all known workspaces, optionally filtered by status."""
        with self._lock:
            results: list[WorkspaceManifest] = []
            for job_map in self._manifests.values():
                for manifest in job_map.values():
                    if status is None or manifest.status == status:
                        results.append(manifest)
            return results

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def activate(
        self, session_id: str, job_id: str | None = None
    ) -> WorkspaceManifest:
        """Mark a workspace as active (in-use)."""
        manifest = self.get_workspace(session_id, job_id)
        with self._lock:
            manifest.update_status("active")
            self._write_manifest(manifest)
            self._metrics.active_count = self._count_active()
        return manifest

    def pause(
        self, session_id: str, job_id: str | None = None
    ) -> WorkspaceManifest:
        """Pause a workspace (e.g. between agent steps)."""
        manifest = self.get_workspace(session_id, job_id)
        with self._lock:
            manifest.update_status("paused")
            self._write_manifest(manifest)
            self._metrics.active_count = self._count_active()
        return manifest

    def complete(
        self, session_id: str, job_id: str | None = None
    ) -> WorkspaceManifest:
        """Mark a workspace as completed."""
        manifest = self.get_workspace(session_id, job_id)
        with self._lock:
            manifest.update_status("completed")
            self._write_manifest(manifest)
            self._metrics.active_count = self._count_active()
        return manifest

    def fail(
        self, session_id: str, job_id: str | None = None
    ) -> WorkspaceManifest:
        """Mark a workspace as failed."""
        manifest = self.get_workspace(session_id, job_id)
        with self._lock:
            manifest.update_status("failed")
            self._write_manifest(manifest)
            self._metrics.active_count = self._count_active()
        return manifest

    def cancel(
        self, session_id: str, job_id: str | None = None
    ) -> WorkspaceManifest:
        """Mark a workspace as cancelled (via cancelling -> cancelled)."""
        manifest = self.get_workspace(session_id, job_id)
        with self._lock:
            manifest.update_status("cancelling")
            self._write_manifest(manifest)
            manifest.update_status("cancelled")
            self._write_manifest(manifest)
            self._metrics.active_count = self._count_active()
        return manifest

    def archive(
        self, session_id: str, job_id: str | None = None
    ) -> WorkspaceManifest:
        """Archive a completed/failed/cancelled workspace."""
        manifest = self.get_workspace(session_id, job_id)
        if manifest.status not in CLEANABLE_STATES:
            raise WorkspaceCleanupBlockedError(session_id, job_id)
        with self._lock:
            manifest.update_status("archived")
            self._write_manifest(manifest)
        return manifest

    # ── Resume ─────────────────────────────────────────────────────────────

    def resume(
        self, session_id: str, job_id: str | None = None
    ) -> WorkspaceManifest:
        """Resume a resumable workspace (only ready/active/paused)."""
        manifest = self.get_workspace(session_id, job_id)
        if not manifest.is_resumable:
            self._metrics.resume_failure += 1
            raise WorkspaceNotResumableError(session_id, manifest.status)
        with self._lock:
            manifest.update_status("active")
            manifest.heartbeat()
            self._write_manifest(manifest)
            self._metrics.resume_success += 1
            self._metrics.active_count = self._count_active()
        return manifest

    # ── Heartbeat ──────────────────────────────────────────────────────────

    def heartbeat(
        self, session_id: str, job_id: str | None = None
    ) -> WorkspaceManifest:
        """Touch the heartbeat on an active workspace."""
        manifest = self.get_workspace(session_id, job_id)
        with self._lock:
            manifest.heartbeat()
            self._write_manifest(manifest)
        return manifest

    # ── Cleanup ────────────────────────────────────────────────────────────

    def cleanup_expired(self) -> list[str]:
        """Remove workspaces that are cleanable AND past retention TTL.

        Only touches workspaces in completed/failed/cancelled/archived
        state that have not been heartbeat-ed within the retention window.
        Returns a list of cleaned session IDs.
        """
        cleaned: list[str] = []
        now = time.time()

        with self._lock:
            to_clean: list[tuple[str, str | None, WorkspaceManifest]] = []
            for session_id, job_map in list(self._manifests.items()):
                for job_id, manifest in list(job_map.items()):
                    if not manifest.cleanup_eligible:
                        continue
                    # Check heartbeat age
                    try:
                        ht = time.mktime(time.strptime(manifest.last_heartbeat, "%Y-%m-%dT%H:%M:%SZ"))
                    except (ValueError, OverflowError):
                        ht = 0
                    if (now - ht) < self._retention_ttl:
                        continue
                    to_clean.append((session_id, job_id, manifest))

            for session_id, job_id, manifest in to_clean:
                if manifest.is_active:
                    self._metrics.cleanup_skipped_active += 1
                    continue
                try:
                    manifest.update_status("cleaned")
                    self._remove_workspace_files(manifest)
                    cleaned.append(session_id)
                    self._metrics.cleanup_count += 1
                except Exception as exc:
                    log.warning(
                        "Failed to clean workspace session=%s job=%s: %s",
                        session_id, job_id, exc,
                    )

            self._metrics.expired_count = len(to_clean)
            self._metrics.active_count = self._count_active()

        return cleaned

    def cleanup_workspace(
        self, session_id: str, job_id: str | None = None
    ) -> bool:
        """Clean up a specific workspace if it is in a cleanable state.

        Returns True if cleaned, False if not cleanable.
        Raises WorkspaceCleanupBlockedError if the workspace is active.
        """
        manifest = self.get_workspace(session_id, job_id)
        if manifest.is_active:
            raise WorkspaceCleanupBlockedError(session_id, job_id)
        if manifest.status not in CLEANABLE_STATES:
            return False
        with self._lock:
            # Mark as cleaned first, then remove files.
            # After files are removed, we can no longer write the manifest.
            manifest.update_status("cleaned")
            self._remove_workspace_files(manifest)
            self._metrics.cleanup_count += 1
            self._metrics.active_count = self._count_active()
        return True

    # ── Path resolution helpers ────────────────────────────────────────────

    def resolve_path(
        self,
        session_id: str,
        job_id: str | None,
        subpath: str,
    ) -> Path:
        """Safely resolve a path inside a workspace's source directory.

        Rejects traversal attempts and symlink escapes.  Returns the
        canonical, validated path.
        """
        manifest = self.get_workspace(session_id, job_id)
        base = Path(manifest.source_path or manifest.root_path).resolve()
        # Join and resolve
        target = (base / subpath).resolve()
        # Verify it stays under the workspace root
        try:
            target.relative_to(base)
        except ValueError:
            raise WorkspaceOutsideRootError(str(target), str(base))
        return target

    # ── Internal helpers ───────────────────────────────────────────────────

    def _write_manifest(self, manifest: WorkspaceManifest) -> None:
        """Write manifest to disk atomically."""
        manifest_path = Path(manifest.root_path) / "manifest.json"
        try:
            tmp_path = manifest_path.with_suffix(".json.tmp")
            tmp_path.write_text(
                json.dumps(manifest.as_dict(), indent=2, sort_keys=True),
                encoding="utf-8",
            )
            tmp_path.replace(manifest_path)
        except OSError as exc:
            raise WorkspacePermissionError(str(manifest_path), str(exc)) from exc

    def _read_manifest(self, manifest_path: Path) -> WorkspaceManifest:
        """Read and validate a manifest from disk."""
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkspaceManifestCorruptionError(
                str(manifest_path), str(exc)
            ) from exc
        try:
            return WorkspaceManifest.model_validate(data)
        except Exception as exc:
            raise WorkspaceManifestCorruptionError(
                str(manifest_path), str(exc)
            ) from exc

    def _remove_workspace_files(self, manifest: WorkspaceManifest) -> None:
        """Remove workspace files on disk."""
        root = Path(manifest.root_path)
        if root.exists() and root.is_dir():
            try:
                # Check the path is still under base_root before removing
                _safe_resolve(root, self._base_root)
            except WorkspaceOutsideRootError:
                log.warning(
                    "Skipping cleanup of workspace %s — path escaped root",
                    root,
                )
                return
            shutil.rmtree(root, ignore_errors=True)

    def _count_active(self) -> int:
        """Count workspaces in an active state."""
        count = 0
        for job_map in self._manifests.values():
            for manifest in job_map.values():
                if manifest.is_active:
                    count += 1
        return count

    # ── Diagnostics ────────────────────────────────────────────────────────

    def diagnostics(self) -> dict[str, Any]:
        """Return a diagnostics snapshot combining workspace and runtime health."""
        return {
            "base_root": str(self._base_root),
            "base_root_exists": self._base_root.exists(),
            "retention_ttl_seconds": self._retention_ttl,
            "metrics": self._metrics.as_dict(),
            "workspaces": {
                "total": sum(len(m) for m in self._manifests.values()),
                "by_status": self._count_by_status(),
            },
        }

    def _count_by_status(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for job_map in self._manifests.values():
            for manifest in job_map.values():
                s = manifest.status
                counts[s] = counts.get(s, 0) + 1
        return counts

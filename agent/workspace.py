"""agent/workspace.py — Isolated workspace lifecycle management.

Every agent session/job gets its own deterministic workspace rooted under a
single configurable base directory.  Directory names are derived from a stable
SHA-256 hash of the opaque IDs — never from raw user-provided strings.

Directory layout per job::

    <base>/<session_hash>/<job_hash>/
        source/        work tree / files the agent reads and writes
        checkpoints/   durable state snapshots for resume
        logs/          per-job log files
        artifacts/     outputs the caller may retrieve
        tmp/           scratch space; always deleted on cleanup

Lifecycle states::

    creating → ready → active ↔ paused → completed
                                        → failed
                              → cancelling → cancelled
    (terminal states) → archived → cleaned

A workspace manifest (workspace.json) in the job root captures the full
lifecycle so cleanup and resume can operate safely.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

log = logging.getLogger("qwen-proxy")

# ---------------------------------------------------------------------------
# Module-level lock registry — shared across WorkspaceManager instances
# ---------------------------------------------------------------------------
# asyncio.Lock objects cannot cross process boundaries, but within a single
# process multiple WorkspaceManager instances (or cache-evict/reload) must
# share the same lock for a given workspace root so the exclusive-worker
# guarantee isn't broken.  A simple dict protected by the GIL is sufficient
# for the registry itself; the values are asyncio.Locks.
_WORKSPACE_LOCKS: dict[str, asyncio.Lock] = {}


def _get_workspace_lock(root: Path) -> asyncio.Lock:
    """Return the process-wide asyncio.Lock for *root*, creating it if needed."""
    key = str(root.resolve())
    if key not in _WORKSPACE_LOCKS:
        _WORKSPACE_LOCKS[key] = asyncio.Lock()
    return _WORKSPACE_LOCKS[key]

# ---------------------------------------------------------------------------
# ID validation
# ---------------------------------------------------------------------------

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,63}$")
_MANIFEST_NAME = "workspace.json"
_MANIFEST_SCHEMA_VERSION = "1"


def _validate_id(value: str, field_name: str) -> None:
    if not _ID_RE.fullmatch(value):
        raise WorkspaceIDError(
            f"Invalid {field_name} {value!r}: must be 2–64 alphanumeric/._- chars, "
            "starting with alphanumeric.",
            field=field_name,
        )


def _hash_component(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:24]


# ---------------------------------------------------------------------------
# Structured errors
# ---------------------------------------------------------------------------


class WorkspaceError(Exception):
    """Base class for all workspace errors."""

    code: str = "workspace_error"

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": str(self)}


class WorkspaceIDError(WorkspaceError):
    code = "invalid_id"

    def __init__(self, message: str, field: str = "") -> None:
        super().__init__(message)
        self.field = field

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": str(self), "field": self.field}


class WorkspaceNotFoundError(WorkspaceError):
    code = "workspace_not_found"

    def __init__(self, session_id: str, job_id: str) -> None:
        super().__init__(f"Workspace not found for session={session_id!r} job={job_id!r}")
        self.session_id = session_id
        self.job_id = job_id


class WorkspaceEscapeError(WorkspaceError):
    code = "workspace_escape"

    def __init__(self, path: str) -> None:
        super().__init__(f"Path {path!r} escapes the allowed workspace root")
        self.path = path

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": "Path traversal outside workspace root rejected"}


class WorkspaceAccessDeniedError(WorkspaceError):
    code = "workspace_access_denied"

    def __init__(self, session_id: str, job_id: str, owner_session: str) -> None:
        super().__init__(
            f"Session {session_id!r} cannot access workspace owned by {owner_session!r} "
            f"(job={job_id!r})"
        )
        self.session_id = session_id
        self.job_id = job_id
        self.owner_session = owner_session


class WorkspaceNotResumableError(WorkspaceError):
    code = "workspace_not_resumable"

    def __init__(self, job_id: str, status: str) -> None:
        super().__init__(
            f"Workspace for job={job_id!r} is in status={status!r} and cannot be resumed"
        )
        self.job_id = job_id
        self.status = status


class WorkspaceLockError(WorkspaceError):
    code = "workspace_locked"

    def __init__(self, job_id: str) -> None:
        super().__init__(f"Workspace for job={job_id!r} is locked by an active worker")
        self.job_id = job_id


class WorkspaceManifestError(WorkspaceError):
    code = "workspace_manifest_corrupt"

    def __init__(self, path: str, reason: str) -> None:
        super().__init__(f"Workspace manifest at {path!r} is corrupt: {reason}")
        self.path = path
        self.reason = reason


# ---------------------------------------------------------------------------
# Lifecycle states
# ---------------------------------------------------------------------------


class WorkspaceStatus(str, Enum):
    CREATING = "creating"
    READY = "ready"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"
    CLEANED = "cleaned"


_RESUMABLE_STATES = frozenset({WorkspaceStatus.READY, WorkspaceStatus.PAUSED})
_TERMINAL_STATES = frozenset(
    {
        WorkspaceStatus.COMPLETED,
        WorkspaceStatus.FAILED,
        WorkspaceStatus.CANCELLED,
        WorkspaceStatus.ARCHIVED,
        WorkspaceStatus.CLEANED,
    }
)
_ACTIVE_STATES = frozenset({WorkspaceStatus.CREATING, WorkspaceStatus.ACTIVE})


# ---------------------------------------------------------------------------
# Manifest model
# ---------------------------------------------------------------------------


class WorkspaceManifest(BaseModel):
    schema_version: str = _MANIFEST_SCHEMA_VERSION
    session_id: str
    job_id: str
    created_at: str
    updated_at: str
    last_heartbeat: str
    runtime_type: str = "internal_agent"
    status: WorkspaceStatus = WorkspaceStatus.CREATING
    root: str
    source_path: str
    checkpoints_path: str
    logs_path: str
    artifacts_path: str
    tmp_path: str
    source_repo: str | None = None
    cleanup_eligible: bool = False
    cleanup_after: str | None = None
    ttl_hours: float = 24.0
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Workspace descriptor (in-memory view after open/create)
# ---------------------------------------------------------------------------


@dataclass
class Workspace:
    manifest: WorkspaceManifest
    root: Path
    source: Path
    checkpoints: Path
    logs: Path
    artifacts: Path
    tmp: Path
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    def safe_path(self, relative: str) -> Path:
        """Resolve *relative* inside source dir and reject traversal/symlink escapes."""
        if ".." in relative:
            raise WorkspaceEscapeError(relative) from None
        source_abs = self.source.resolve()
        candidate = (source_abs / relative.lstrip("/").lstrip("\\")).resolve()
        try:
            if os.path.commonpath([str(source_abs), str(candidate)]) != str(source_abs):
                raise WorkspaceEscapeError(relative) from None
        except ValueError:
            raise WorkspaceEscapeError(relative) from None
        return candidate

    @property
    def session_id(self) -> str:
        return self.manifest.session_id

    @property
    def job_id(self) -> str:
        return self.manifest.job_id

    @property
    def status(self) -> WorkspaceStatus:
        return self.manifest.status


# ---------------------------------------------------------------------------
# WorkspaceManager
# ---------------------------------------------------------------------------


class WorkspaceManager:
    """Create, open, and lifecycle-manage per-job isolated workspaces.

    All workspaces live under *base_root*.  Directory names are SHA-256 hashes
    of the (session_id, job_id) pair — never raw user-supplied strings.

    Usage::

        mgr = WorkspaceManager(base_root=Path("/data/workspaces"))
        ws  = await mgr.create(session_id="as_abc123", job_id="aj_def456")
        # ... do work in ws.source ...
        await mgr.transition(ws, WorkspaceStatus.COMPLETED)
        await mgr.cleanup_expired()
    """

    def __init__(
        self,
        base_root: Path | str,
        default_ttl_hours: float = 24.0,
        lock_timeout_sec: float = 30.0,
    ) -> None:
        self._base = Path(base_root).resolve()
        self._default_ttl_hours = default_ttl_hours
        self._lock_timeout = lock_timeout_sec
        # session_id -> job_id -> Workspace (in-memory registry of open workspaces)
        self._open: dict[str, dict[str, Workspace]] = {}
        self._registry_lock = asyncio.Lock()

    # ── Creation ───────────────────────────────────────────────────────────────

    async def create(
        self,
        session_id: str,
        job_id: str,
        *,
        runtime_type: str = "internal_agent",
        source_repo: str | None = None,
        metadata: dict[str, Any] | None = None,
        ttl_hours: float | None = None,
    ) -> Workspace:
        """Create and return a new workspace in READY state.

        Raises :exc:`WorkspaceIDError` if either ID is invalid.
        """
        _validate_id(session_id, "session_id")
        _validate_id(job_id, "job_id")

        root = self._make_root(session_id, job_id)
        self._assert_within_base(root)

        now = _iso_now()
        effective_ttl = ttl_hours if ttl_hours is not None else self._default_ttl_hours

        source = root / "source"
        checkpoints = root / "checkpoints"
        logs_dir = root / "logs"
        artifacts = root / "artifacts"
        tmp = root / "tmp"

        def _claim_and_create_dirs() -> None:
            # Atomically claim the root directory — exist_ok=False raises
            # FileExistsError if another coroutine or process already created it,
            # eliminating the TOCTOU window of the old preflight-check approach.
            try:
                root.mkdir(parents=True, exist_ok=False)
            except FileExistsError as exc:
                raise WorkspaceError(
                    f"Workspace already exists for session={session_id!r} job={job_id!r}"
                ) from exc
            for d in (source, checkpoints, logs_dir, artifacts, tmp):
                d.mkdir(exist_ok=False)

        await asyncio.to_thread(_claim_and_create_dirs)

        manifest = WorkspaceManifest(
            session_id=session_id,
            job_id=job_id,
            created_at=now,
            updated_at=now,
            last_heartbeat=now,
            runtime_type=runtime_type,
            status=WorkspaceStatus.READY,
            root=str(root),
            source_path=str(source),
            checkpoints_path=str(checkpoints),
            logs_path=str(logs_dir),
            artifacts_path=str(artifacts),
            tmp_path=str(tmp),
            source_repo=source_repo,
            cleanup_eligible=False,
            cleanup_after=None,
            ttl_hours=effective_ttl,
            metadata=metadata or {},
        )
        await asyncio.to_thread(_write_manifest, root, manifest)
        ws = _ws_from_manifest(manifest, root, source, checkpoints, logs_dir, artifacts, tmp)

        async with self._registry_lock:
            self._open.setdefault(session_id, {})[job_id] = ws

        log.info("Workspace created: session=%s job=%s root=%s", session_id, job_id, root)
        return ws

    # ── Open existing ──────────────────────────────────────────────────────────

    async def open(self, session_id: str, job_id: str) -> Workspace:
        """Open an existing workspace from disk.

        Raises :exc:`WorkspaceNotFoundError` if the directory/manifest is absent.
        Raises :exc:`WorkspaceManifestError` if the manifest cannot be parsed.
        """
        _validate_id(session_id, "session_id")
        _validate_id(job_id, "job_id")

        async with self._registry_lock:
            cached = self._open.get(session_id, {}).get(job_id)

        if cached is not None:
            # Validate stale-cache: exists() check is outside the lock to avoid
            # blocking the event loop while holding _registry_lock.
            if await asyncio.to_thread(cached.root.exists):
                return cached
            # Directory was deleted (e.g. by cleanup_expired) — evict stale handle.
            async with self._registry_lock:
                self._open.get(session_id, {}).pop(job_id, None)
            raise WorkspaceNotFoundError(session_id, job_id)

        root = self._make_root(session_id, job_id)
        self._assert_within_base(root)

        if not await asyncio.to_thread(root.exists):
            raise WorkspaceNotFoundError(session_id, job_id)

        manifest = await asyncio.to_thread(_read_manifest, root, session_id, job_id)
        ws = _load_workspace(root, manifest)

        async with self._registry_lock:
            self._open.setdefault(session_id, {})[job_id] = ws

        return ws

    # ── Resume ─────────────────────────────────────────────────────────────────

    async def resume(self, session_id: str, job_id: str) -> Workspace:
        """Open a workspace for resumption.

        Only READY or PAUSED workspaces may be resumed.
        The session_id must match the workspace's recorded session_id.
        """
        ws = await self.open(session_id, job_id)

        if ws.manifest.session_id != session_id:
            raise WorkspaceAccessDeniedError(session_id, job_id, ws.manifest.session_id)

        if ws.status not in _RESUMABLE_STATES:
            raise WorkspaceNotResumableError(job_id, ws.status.value)

        await self.transition(ws, WorkspaceStatus.ACTIVE)
        return ws

    # ── Access validation ─────────────────────────────────────────────────────

    def assert_session_owns(self, ws: Workspace, requesting_session_id: str) -> None:
        """Raise :exc:`WorkspaceAccessDeniedError` if *requesting_session_id* doesn't own *ws*."""
        if ws.manifest.session_id != requesting_session_id:
            raise WorkspaceAccessDeniedError(
                requesting_session_id, ws.job_id, ws.manifest.session_id
            )

    def safe_path(self, ws: Workspace, relative: str) -> Path:
        """Resolve *relative* within *ws*.source and reject traversal/symlink escapes.

        After resolve() all symlinks are followed, so symlink-based escapes are
        caught by the relative_to() check.  Absolute paths passed as *relative*
        are also caught because Path(source) / "/abs" == Path("/abs").
        """
        if ".." in relative:
            raise WorkspaceEscapeError(relative) from None
        source_abs = ws.source.resolve()
        candidate = (source_abs / relative.lstrip("/").lstrip("\\")).resolve()
        try:
            if os.path.commonpath([str(source_abs), str(candidate)]) != str(source_abs):
                raise WorkspaceEscapeError(relative) from None
        except ValueError:
            raise WorkspaceEscapeError(relative) from None
        return candidate

    # ── Lifecycle transitions ──────────────────────────────────────────────────

    async def transition(self, ws: Workspace, new_status: WorkspaceStatus) -> None:
        """Update *ws* status and persist the manifest."""
        now = _iso_now()
        ws.manifest.status = new_status
        ws.manifest.updated_at = now
        ws.manifest.last_heartbeat = now
        if new_status in _TERMINAL_STATES:
            ws.manifest.cleanup_eligible = True
            # Anchor TTL clock to the moment the workspace enters a terminal state.
            ws.manifest.cleanup_after = _iso_offset_hours(ws.manifest.ttl_hours)
        await asyncio.to_thread(_write_manifest, ws.root, ws.manifest)
        log.debug(
            "Workspace transition: session=%s job=%s status=%s",
            ws.session_id,
            ws.job_id,
            new_status.value,
        )

    async def heartbeat(self, ws: Workspace) -> None:
        """Update last_heartbeat timestamp and persist."""
        ws.manifest.last_heartbeat = _iso_now()
        await asyncio.to_thread(_write_manifest, ws.root, ws.manifest)

    # ── Lock ──────────────────────────────────────────────────────────────────

    async def acquire_lock(self, ws: Workspace) -> None:
        """Acquire the exclusive async lock for *ws*.

        Raises :exc:`WorkspaceLockError` if the lock is already held and cannot
        be acquired within *lock_timeout_sec*.
        """
        try:
            await asyncio.wait_for(ws._lock.acquire(), timeout=self._lock_timeout)
        except asyncio.TimeoutError:
            raise WorkspaceLockError(ws.job_id)

    def release_lock(self, ws: Workspace) -> None:
        if ws._lock.locked():
            ws._lock.release()

    # ── Cleanup ───────────────────────────────────────────────────────────────

    async def cleanup_expired(self, *, dry_run: bool = False) -> dict[str, int]:
        """Remove expired workspaces that are cleanup_eligible and past cleanup_after.

        Active workspaces are never deleted.  Returns a summary dict with counts.
        Delegates all blocking filesystem I/O to a thread pool.
        """
        return await asyncio.to_thread(self._cleanup_expired_sync, dry_run)

    def _cleanup_expired_sync(self, dry_run: bool = False) -> dict[str, int]:
        now_epoch = time.time()
        cleaned = 0
        skipped_active = 0
        errors = 0

        if not self._base.exists():
            return {"cleaned": 0, "skipped_active": 0, "errors": 0}

        for session_dir in self._base.iterdir():
            if not session_dir.is_dir():
                continue
            for job_dir in session_dir.iterdir():
                if not job_dir.is_dir():
                    continue
                manifest_path = job_dir / _MANIFEST_NAME
                if not manifest_path.exists():
                    continue
                try:
                    manifest = WorkspaceManifest.model_validate_json(
                        manifest_path.read_text(encoding="utf-8")
                    )
                except Exception as exc:
                    log.debug("Skipping workspace with invalid manifest %s: %s", manifest_path, exc)
                    continue

                if manifest.status in _ACTIVE_STATES:
                    skipped_active += 1
                    continue

                if not manifest.cleanup_eligible:
                    continue

                if manifest.cleanup_after:
                    try:
                        cutoff = _parse_iso(manifest.cleanup_after)
                    except Exception:
                        cutoff = 0.0
                    if now_epoch < cutoff:
                        continue

                try:
                    if not dry_run:
                        shutil.rmtree(job_dir)
                        # Remove session dir if now empty
                        try:
                            session_dir.rmdir()
                        except OSError:
                            pass
                    cleaned += 1
                except Exception as exc:
                    log.warning("Workspace cleanup error for %s: %s", job_dir, exc)
                    errors += 1

        return {"cleaned": cleaned, "skipped_active": skipped_active, "errors": errors}

    async def clean_tmp(self, ws: Workspace) -> None:
        """Remove and recreate the tmp directory for *ws*."""
        def _do() -> None:
            if ws.tmp.exists():
                shutil.rmtree(ws.tmp, ignore_errors=True)
            ws.tmp.mkdir(parents=True, exist_ok=True)

        await asyncio.to_thread(_do)

    # ── Metrics ───────────────────────────────────────────────────────────────

    def metrics(self) -> dict[str, int]:
        """Return counts of workspaces by status (scans disk, sync).

        Call ``await asyncio.to_thread(mgr.metrics)`` from async code.
        """
        counts: dict[str, int] = {}
        if not self._base.exists():
            return counts
        for session_dir in self._base.iterdir():
            if not session_dir.is_dir():
                continue
            for job_dir in session_dir.iterdir():
                manifest_path = job_dir / _MANIFEST_NAME
                if not manifest_path.exists():
                    continue
                try:
                    m = WorkspaceManifest.model_validate_json(
                        manifest_path.read_text(encoding="utf-8")
                    )
                    counts[m.status.value] = counts.get(m.status.value, 0) + 1
                except Exception as exc:
                    log.debug("Skipping workspace with invalid manifest %s: %s", manifest_path, exc)
                    counts["corrupt"] = counts.get("corrupt", 0) + 1
        return counts

    # ── Internals ─────────────────────────────────────────────────────────────

    def _make_root(self, session_id: str, job_id: str) -> Path:
        session_hash = _hash_component(session_id)
        job_hash = _hash_component(job_id)
        return self._base / session_hash / job_hash

    def _assert_within_base(self, path: Path) -> None:
        resolved = path.resolve()
        if self._base not in resolved.parents and resolved != self._base:
            raise WorkspaceEscapeError(str(path))


# ---------------------------------------------------------------------------
# Module-level singleton (configured from env)
# ---------------------------------------------------------------------------

_default_manager: WorkspaceManager | None = None


def get_workspace_manager() -> WorkspaceManager:
    global _default_manager
    if _default_manager is None:
        base = os.environ.get("AGENT_WORKSPACE_BASE") or os.environ.get(
            "AGENT_WORKSPACE_ROOT", str(Path(__file__).resolve().parent.parent / ".workspaces")
        )
        ttl = float(os.environ.get("WORKSPACE_TTL_HOURS", "24"))
        _default_manager = WorkspaceManager(base_root=base, default_ttl_hours=ttl)
    return _default_manager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _iso_offset_hours(hours: float) -> str:
    future = time.gmtime(time.time() + hours * 3600)
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", future)


def _parse_iso(ts: str) -> float:
    import datetime
    dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return dt.timestamp()


def _write_manifest(root: Path, manifest: WorkspaceManifest) -> None:
    # Write to a uniquely named temp file then atomically rename.
    # Using a unique name avoids races when heartbeat/transition/second manager
    # writes concurrently to the same workspace.json.tmp path.
    with tempfile.NamedTemporaryFile(
        "w",
        dir=root,
        prefix=f"{_MANIFEST_NAME}.",
        suffix=".tmp",
        delete=False,
        encoding="utf-8",
    ) as fh:
        fh.write(manifest.model_dump_json(indent=2))
        tmp = Path(fh.name)
    tmp.replace(root / _MANIFEST_NAME)


def _read_manifest(root: Path, session_id: str, job_id: str) -> WorkspaceManifest:
    manifest_path = root / _MANIFEST_NAME
    if not manifest_path.exists():
        raise WorkspaceNotFoundError(session_id, job_id)
    try:
        return WorkspaceManifest.model_validate_json(
            manifest_path.read_text(encoding="utf-8")
        )
    except Exception as exc:
        raise WorkspaceManifestError(str(manifest_path), str(exc)) from exc


def _ws_from_manifest(
    manifest: WorkspaceManifest,
    root: Path,
    source: Path,
    checkpoints: Path,
    logs_dir: Path,
    artifacts: Path,
    tmp: Path,
) -> Workspace:
    return Workspace(
        manifest=manifest,
        root=root,
        source=source,
        checkpoints=checkpoints,
        logs=logs_dir,
        artifacts=artifacts,
        tmp=tmp,
        _lock=_get_workspace_lock(root),
    )


def _load_workspace(root: Path, manifest: WorkspaceManifest) -> Workspace:
    return Workspace(
        manifest=manifest,
        root=root,
        source=root / "source",
        checkpoints=root / "checkpoints",
        logs=root / "logs",
        artifacts=root / "artifacts",
        tmp=root / "tmp",
        _lock=_get_workspace_lock(root),
    )

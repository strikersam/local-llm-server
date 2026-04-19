"""workflow/artifact_store.py — Durable artifact persistence.

Artifacts are stored in two places:
  1. Filesystem  — the actual content at a deterministic path under
                   <artifacts_root>/<run_id>/<name>
  2. SQLite DB   — a metadata row per artifact (id, run_id, name, path,
                   content_hash, size_bytes, created_at)

This dual approach means:
  - Content is git-trackable and human-inspectable without a DB query.
  - The metadata table enables fast listing and queryability.
  - Resumability: after a server restart, the metadata can be
    reconstructed from the filesystem if needed (re-index path exists).

Usage::

    store = ArtifactStore()
    art = store.persist(run_id="wf_abc123", phase="context", name="context.md",
                        content="# Context\\n...")
    retrieved = store.get_content(art.artifact_id)
    listed = store.list_for_run("wf_abc123")
"""
from __future__ import annotations

import hashlib
import logging
import os
import secrets
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from workflow.models import Artifact

log = logging.getLogger("crispy-artifact-store")

_DEFAULT_ARTIFACTS_ROOT = os.environ.get(
    "CRISPY_ARTIFACTS_ROOT", ".data/workflow/artifacts"
)
_DEFAULT_DB_PATH = os.environ.get("CRISPY_WORKFLOW_DB", ".data/workflow/workflow.db")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class ArtifactStore:
    """Store and retrieve workflow artifacts (markdown files + JSON results).

    Thread-safe via a reentrant lock wrapping all SQLite writes.
    """

    def __init__(
        self,
        *,
        artifacts_root: str | Path | None = None,
        db_path: str | Path | None = None,
    ) -> None:
        self._root = Path(artifacts_root or _DEFAULT_ARTIFACTS_ROOT)
        self._db_path = str(Path(db_path or _DEFAULT_DB_PATH))
        self._lock = threading.RLock()
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._root.mkdir(parents=True, exist_ok=True)
        self._init_db()
        log.info(
            "ArtifactStore ready: root=%s db=%s", self._root, self._db_path
        )

    # ── Internal ─────────────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS artifacts (
                    artifact_id  TEXT PRIMARY KEY,
                    run_id       TEXT NOT NULL,
                    phase        TEXT NOT NULL,
                    name         TEXT NOT NULL,
                    path         TEXT NOT NULL,
                    content_hash TEXT NOT NULL DEFAULT '',
                    size_bytes   INTEGER NOT NULL DEFAULT 0,
                    created_at   TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_art_run ON artifacts (run_id)"
            )
            conn.commit()

    def _run_dir(self, run_id: str) -> Path:
        d = self._root / run_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    @staticmethod
    def _hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _row_to_artifact(self, row: sqlite3.Row) -> Artifact:
        return Artifact(
            artifact_id=row["artifact_id"],
            run_id=row["run_id"],
            phase=row["phase"],
            name=row["name"],
            path=row["path"],
            content_hash=row["content_hash"],
            size_bytes=row["size_bytes"],
            created_at=row["created_at"],
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def persist(
        self,
        *,
        run_id: str,
        phase: str,
        name: str,
        content: str,
        artifact_id: str | None = None,
    ) -> Artifact:
        """Write *content* to disk and record metadata in SQLite.

        If an artifact with the same (run_id, name) already exists, it is
        overwritten (idempotent re-runs).

        Returns the persisted :class:`Artifact`.
        """
        file_path = self._run_dir(run_id) / name
        file_path.write_text(content, encoding="utf-8")
        content_hash = self._hash(content)
        size_bytes = file_path.stat().st_size
        art_id = artifact_id or ("art_" + secrets.token_hex(6))
        now = _now()

        with self._lock:
            with self._connect() as conn:
                # Upsert: overwrite if same (run_id, name) exists.
                existing = conn.execute(
                    "SELECT artifact_id FROM artifacts WHERE run_id=? AND name=?",
                    (run_id, name),
                ).fetchone()
                if existing:
                    art_id = existing["artifact_id"]
                    conn.execute(
                        """
                        UPDATE artifacts
                        SET phase=?, path=?, content_hash=?, size_bytes=?, created_at=?
                        WHERE artifact_id=?
                        """,
                        (phase, str(file_path), content_hash, size_bytes, now, art_id),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO artifacts
                            (artifact_id, run_id, phase, name, path, content_hash,
                             size_bytes, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            art_id,
                            run_id,
                            phase,
                            name,
                            str(file_path),
                            content_hash,
                            size_bytes,
                            now,
                        ),
                    )
                conn.commit()

        art = Artifact(
            artifact_id=art_id,
            run_id=run_id,
            phase=phase,
            name=name,
            path=str(file_path),
            content_hash=content_hash,
            size_bytes=size_bytes,
            created_at=now,
        )
        log.debug("Artifact persisted: run=%s name=%s size=%d", run_id, name, size_bytes)
        return art

    def get_content(self, artifact_id: str) -> str | None:
        """Return the raw text content of an artifact, or None if missing."""
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT path FROM artifacts WHERE artifact_id=?", (artifact_id,)
                ).fetchone()
        if row is None:
            return None
        try:
            return Path(row["path"]).read_text(encoding="utf-8")
        except FileNotFoundError:
            log.warning("Artifact file missing on disk: %s", row["path"])
            return None

    def get_by_name(self, run_id: str, name: str) -> Artifact | None:
        """Return the Artifact for (run_id, name), or None."""
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM artifacts WHERE run_id=? AND name=?",
                    (run_id, name),
                ).fetchone()
        if row is None:
            return None
        return self._row_to_artifact(row)

    def get(self, artifact_id: str) -> Artifact | None:
        """Return the Artifact by its ID, or None."""
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM artifacts WHERE artifact_id=?", (artifact_id,)
                ).fetchone()
        if row is None:
            return None
        return self._row_to_artifact(row)

    def list_for_run(self, run_id: str) -> list[Artifact]:
        """Return all artifacts for a run, ordered by creation time."""
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT * FROM artifacts WHERE run_id=? ORDER BY created_at",
                    (run_id,),
                ).fetchall()
        return [self._row_to_artifact(r) for r in rows]

    def delete_run_artifacts(self, run_id: str) -> int:
        """Delete all artifacts (disk + DB) for a run. Returns count deleted."""
        arts = self.list_for_run(run_id)
        deleted = 0
        for art in arts:
            try:
                Path(art.path).unlink(missing_ok=True)
            except Exception as exc:
                log.warning("Could not delete artifact file %s: %s", art.path, exc)
            deleted += 1
        with self._lock:
            with self._connect() as conn:
                conn.execute("DELETE FROM artifacts WHERE run_id=?", (run_id,))
                conn.commit()
        return deleted

    def content_by_name(self, run_id: str, name: str) -> str | None:
        """Convenience: return file content for (run_id, name), or None."""
        art = self.get_by_name(run_id, name)
        if art is None:
            return None
        return self.get_content(art.artifact_id)

    def as_index(self, run_id: str) -> list[dict[str, Any]]:
        """Return a lightweight index of all artifacts for a run (no content)."""
        return [
            {
                "artifact_id": a.artifact_id,
                "phase": a.phase,
                "name": a.name,
                "size_bytes": a.size_bytes,
                "created_at": a.created_at,
            }
            for a in self.list_for_run(run_id)
        ]

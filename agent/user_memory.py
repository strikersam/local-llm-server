"""Per-user key/value memory store backed by SQLite.

Allows agents to persist and recall facts about a user across sessions and
server restarts.  Keyed by user_id (email) + an arbitrary string key.
"""
from __future__ import annotations

import logging
import os
import sqlite3
import threading
import time
from pathlib import Path

log = logging.getLogger("qwen-agent")

_DEFAULT_DB = ".data/agent.db"


class UserMemoryStore:
    """Persistent key/value store scoped per user.

    Thread-safe; uses a single SQLite file shared with ``AgentSessionStore``
    (separate table).  The database path is resolved from the ``AGENT_DB_PATH``
    environment variable, falling back to ``.data/agent.db``.
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        path = Path(db_path or os.environ.get("AGENT_DB_PATH") or _DEFAULT_DB)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = str(path)
        self._lock = threading.RLock()
        self._init_db()

    # ── internals ────────────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_memories (
                    user_id    TEXT NOT NULL,
                    key        TEXT NOT NULL,
                    value      TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, key)
                )
                """
            )
            conn.commit()

    # ── public API ────────────────────────────────────────────────────────────

    def save(self, user_id: str, key: str, value: str) -> None:
        """Upsert a memory entry for *user_id*."""
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO user_memories (user_id, key, value, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, key) DO UPDATE
                    SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (user_id, key, value, now),
            )
            conn.commit()
        log.debug("memory saved: user=%s key=%s", user_id, key)

    def recall(self, user_id: str, key: str) -> str | None:
        """Return the stored value for *key*, or ``None`` if not found."""
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM user_memories WHERE user_id = ? AND key = ?",
                (user_id, key),
            ).fetchone()
            return row["value"] if row else None

    def recall_all(self, user_id: str) -> dict[str, str]:
        """Return all stored key/value pairs for *user_id*."""
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT key, value FROM user_memories WHERE user_id = ?",
                (user_id,),
            ).fetchall()
            return {row["key"]: row["value"] for row in rows}

    def delete(self, user_id: str, key: str) -> bool:
        """Delete a memory entry.  Returns ``True`` if a row was removed."""
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM user_memories WHERE user_id = ? AND key = ?",
                (user_id, key),
            )
            conn.commit()
            return cur.rowcount > 0

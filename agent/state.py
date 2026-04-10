from __future__ import annotations

import json
import logging
import os
import secrets
import sqlite3
import threading
import time
from pathlib import Path

from agent.models import AgentPlan, AgentSession, AgentSessionMessage

log = logging.getLogger("qwen-agent")

_DEFAULT_DB = ".data/agent.db"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class AgentSessionStore:
    """SQLite-backed session store.

    Sessions and their message history are persisted to a SQLite database so
    they survive server restarts.  An in-memory dict is kept as a fast cache;
    every mutation is written through to the DB atomically.

    The database path is resolved from the ``AGENT_DB_PATH`` environment
    variable, falling back to ``.data/agent.db`` (shared with
    ``UserMemoryStore``).
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        path = Path(db_path or os.environ.get("AGENT_DB_PATH") or _DEFAULT_DB)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = str(path)
        self._lock = threading.RLock()
        self._init_db()
        self._sessions: dict[str, AgentSession] = self._load_all()
        log.info("AgentSessionStore loaded %d session(s) from %s", len(self._sessions), self._db_path)

    # ── internals ────────────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_sessions (
                    session_id   TEXT PRIMARY KEY,
                    title        TEXT NOT NULL,
                    provider_id  TEXT,
                    workspace_id TEXT,
                    created_at   TEXT NOT NULL,
                    updated_at   TEXT NOT NULL,
                    last_plan    TEXT,
                    last_result  TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS session_messages (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL REFERENCES agent_sessions(session_id),
                    role       TEXT NOT NULL,
                    content    TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _load_all(self) -> dict[str, AgentSession]:
        sessions: dict[str, AgentSession] = {}
        with self._connect() as conn:
            for row in conn.execute("SELECT * FROM agent_sessions").fetchall():
                msgs = conn.execute(
                    "SELECT role, content FROM session_messages WHERE session_id = ? ORDER BY id",
                    (row["session_id"],),
                ).fetchall()
                sessions[row["session_id"]] = AgentSession(
                    session_id=row["session_id"],
                    title=row["title"],
                    provider_id=row["provider_id"],
                    workspace_id=row["workspace_id"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    history=[AgentSessionMessage(role=m["role"], content=m["content"]) for m in msgs],
                    last_plan=json.loads(row["last_plan"]) if row["last_plan"] else None,
                    last_result=json.loads(row["last_result"]) if row["last_result"] else None,
                )
        return sessions

    def _db_upsert_session(self, conn: sqlite3.Connection, session: AgentSession) -> None:
        conn.execute(
            """
            INSERT OR REPLACE INTO agent_sessions
                (session_id, title, provider_id, workspace_id, created_at, updated_at, last_plan, last_result)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session.session_id,
                session.title,
                session.provider_id,
                session.workspace_id,
                session.created_at,
                session.updated_at,
                json.dumps(session.last_plan.model_dump()) if session.last_plan else None,
                json.dumps(session.last_result) if session.last_result else None,
            ),
        )

    # ── public API ────────────────────────────────────────────────────────────

    def create(
        self,
        *,
        title: str | None = None,
        provider_id: str | None = None,
        workspace_id: str | None = None,
    ) -> AgentSession:
        session_id = "as_" + secrets.token_hex(8)
        now = _now()
        session = AgentSession(
            session_id=session_id,
            title=title or "Coding Agent Session",
            provider_id=provider_id,
            workspace_id=workspace_id,
            created_at=now,
            updated_at=now,
            history=[],
            last_plan=None,
            last_result=None,
        )
        with self._lock:
            self._sessions[session_id] = session
            with self._connect() as conn:
                self._db_upsert_session(conn, session)
                conn.commit()
        return session

    def get(self, session_id: str) -> AgentSession | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            return AgentSession.model_validate(session.model_dump())

    def append_message(self, session_id: str, role: str, content: str) -> AgentSession:
        with self._lock:
            session = self._sessions[session_id]
            session.history.append(AgentSessionMessage(role=role, content=content))
            session.updated_at = _now()
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO session_messages (session_id, role, content) VALUES (?, ?, ?)",
                    (session_id, role, content),
                )
                conn.execute(
                    "UPDATE agent_sessions SET updated_at = ? WHERE session_id = ?",
                    (session.updated_at, session_id),
                )
                conn.commit()
            return AgentSession.model_validate(session.model_dump())

    def update_result(self, session_id: str, plan: AgentPlan | dict, result: dict) -> AgentSession:
        with self._lock:
            session = self._sessions[session_id]
            session.last_plan = plan if isinstance(plan, AgentPlan) else AgentPlan.model_validate(plan)
            session.last_result = result
            session.updated_at = _now()
            with self._connect() as conn:
                conn.execute(
                    """
                    UPDATE agent_sessions
                    SET updated_at = ?, last_plan = ?, last_result = ?
                    WHERE session_id = ?
                    """,
                    (
                        session.updated_at,
                        json.dumps(session.last_plan.model_dump()),
                        json.dumps(result),
                        session_id,
                    ),
                )
                conn.commit()
            return AgentSession.model_validate(session.model_dump())

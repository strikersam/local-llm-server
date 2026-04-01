from __future__ import annotations

import secrets
import threading
import time

from agent.models import AgentPlan, AgentSession, AgentSessionMessage


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class AgentSessionStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._sessions: dict[str, AgentSession] = {}

    def create(self, title: str | None = None) -> AgentSession:
        session_id = "as_" + secrets.token_hex(8)
        now = _now()
        session = AgentSession(
            session_id=session_id,
            title=title or "Coding Agent Session",
            created_at=now,
            updated_at=now,
            history=[],
            last_plan=None,
            last_result=None,
        )
        with self._lock:
            self._sessions[session_id] = session
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
            return AgentSession.model_validate(session.model_dump())

    def update_result(self, session_id: str, plan: AgentPlan | dict, result: dict) -> AgentSession:
        with self._lock:
            session = self._sessions[session_id]
            session.last_plan = plan if isinstance(plan, AgentPlan) else AgentPlan.model_validate(plan)
            session.last_result = result
            session.updated_at = _now()
            return AgentSession.model_validate(session.model_dump())

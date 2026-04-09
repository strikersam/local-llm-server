"""Tests for the persistent memory features:
- UserMemoryStore (user profile key/value store)
- AgentSessionStore SQLite persistence (sessions survive restart)
"""
from __future__ import annotations

import pytest

from agent.user_memory import UserMemoryStore
from agent.state import AgentSessionStore


# ── UserMemoryStore ───────────────────────────────────────────────────────────

class TestUserMemoryStore:
    def test_save_and_recall(self, tmp_path):
        store = UserMemoryStore(db_path=tmp_path / "mem.db")
        store.save("alice@example.com", "preferred_language", "Python")
        assert store.recall("alice@example.com", "preferred_language") == "Python"

    def test_recall_missing_key_returns_none(self, tmp_path):
        store = UserMemoryStore(db_path=tmp_path / "mem.db")
        assert store.recall("alice@example.com", "nonexistent") is None

    def test_save_overwrites_existing(self, tmp_path):
        store = UserMemoryStore(db_path=tmp_path / "mem.db")
        store.save("alice@example.com", "style", "PEP8")
        store.save("alice@example.com", "style", "Google")
        assert store.recall("alice@example.com", "style") == "Google"

    def test_recall_all_returns_all_keys(self, tmp_path):
        store = UserMemoryStore(db_path=tmp_path / "mem.db")
        store.save("bob@example.com", "k1", "v1")
        store.save("bob@example.com", "k2", "v2")
        result = store.recall_all("bob@example.com")
        assert result == {"k1": "v1", "k2": "v2"}

    def test_recall_all_empty_for_unknown_user(self, tmp_path):
        store = UserMemoryStore(db_path=tmp_path / "mem.db")
        assert store.recall_all("nobody@example.com") == {}

    def test_memories_are_user_scoped(self, tmp_path):
        store = UserMemoryStore(db_path=tmp_path / "mem.db")
        store.save("alice@example.com", "theme", "dark")
        store.save("bob@example.com", "theme", "light")
        assert store.recall("alice@example.com", "theme") == "dark"
        assert store.recall("bob@example.com", "theme") == "light"

    def test_delete_removes_entry(self, tmp_path):
        store = UserMemoryStore(db_path=tmp_path / "mem.db")
        store.save("alice@example.com", "key", "val")
        assert store.delete("alice@example.com", "key") is True
        assert store.recall("alice@example.com", "key") is None

    def test_delete_nonexistent_returns_false(self, tmp_path):
        store = UserMemoryStore(db_path=tmp_path / "mem.db")
        assert store.delete("alice@example.com", "ghost") is False

    def test_persists_across_instances(self, tmp_path):
        db = tmp_path / "mem.db"
        store1 = UserMemoryStore(db_path=db)
        store1.save("alice@example.com", "note", "remember this")

        store2 = UserMemoryStore(db_path=db)
        assert store2.recall("alice@example.com", "note") == "remember this"


# ── AgentSessionStore persistence ────────────────────────────────────────────

class TestAgentSessionStorePersistence:
    def test_session_survives_restart(self, tmp_path):
        db = tmp_path / "sessions.db"
        store1 = AgentSessionStore(db_path=db)
        session = store1.create(title="My Session")
        store1.append_message(session.session_id, "user", "hello")
        store1.append_message(session.session_id, "assistant", "hi there")

        # Simulate a restart by creating a new store backed by the same DB.
        store2 = AgentSessionStore(db_path=db)
        loaded = store2.get(session.session_id)
        assert loaded is not None
        assert loaded.title == "My Session"
        assert len(loaded.history) == 2
        assert loaded.history[0].role == "user"
        assert loaded.history[0].content == "hello"
        assert loaded.history[1].role == "assistant"
        assert loaded.history[1].content == "hi there"

    def test_multiple_sessions_all_restored(self, tmp_path):
        db = tmp_path / "sessions.db"
        store1 = AgentSessionStore(db_path=db)
        s1 = store1.create(title="Session A")
        s2 = store1.create(title="Session B")
        store1.append_message(s1.session_id, "user", "msg-a")
        store1.append_message(s2.session_id, "user", "msg-b")

        store2 = AgentSessionStore(db_path=db)
        assert store2.get(s1.session_id) is not None
        assert store2.get(s2.session_id) is not None

    def test_update_result_persisted(self, tmp_path):
        db = tmp_path / "sessions.db"
        store1 = AgentSessionStore(db_path=db)
        session = store1.create(title="Result Session")
        plan = {"goal": "do stuff", "steps": []}
        store1.update_result(session.session_id, plan=plan, result={"summary": "done"})

        store2 = AgentSessionStore(db_path=db)
        loaded = store2.get(session.session_id)
        assert loaded is not None
        assert loaded.last_result == {"summary": "done"}
        assert loaded.last_plan is not None
        assert loaded.last_plan.goal == "do stuff"

    def test_unknown_session_returns_none(self, tmp_path):
        store = AgentSessionStore(db_path=tmp_path / "sessions.db")
        assert store.get("as_nonexistent") is None

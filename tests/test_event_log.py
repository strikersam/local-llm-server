from __future__ import annotations

"""Tests for the append-only event log in AgentSessionStore.

Covers:
- append_event stores events with correct position/type/payload
- get_events retrieves positional slices
- event_count increments correctly on the session
- Multiple sessions are isolated
"""

from pathlib import Path

from agent.state import AgentSessionStore


def _store(tmp_path: Path) -> AgentSessionStore:
    return AgentSessionStore(db_path=tmp_path / "test.db")


# ---------------------------------------------------------------------------
# append_event
# ---------------------------------------------------------------------------

def test_append_event_stores_and_increments_count(tmp_path: Path):
    store = _store(tmp_path)
    session = store.create(title="test")

    store.append_event(session.session_id, "user_message", {"instruction": "hello"})
    store.append_event(session.session_id, "step_start", {"step_id": 1})

    refreshed = store.get(session.session_id)
    assert refreshed.event_count == 2


def test_append_event_positions_are_monotonic(tmp_path: Path):
    store = _store(tmp_path)
    session = store.create(title="test")

    store.append_event(session.session_id, "user_message", {"x": 1})
    store.append_event(session.session_id, "tool_call", {"x": 2})
    store.append_event(session.session_id, "tool_result", {"x": 3})

    events = store.get_events(session.session_id)
    positions = [e.position for e in events]
    assert positions == [0, 1, 2]


def test_append_event_payload_roundtrips(tmp_path: Path):
    store = _store(tmp_path)
    session = store.create(title="test")
    payload = {"goal": "fix bug", "files": ["a.py", "b.py"], "score": 42}

    store.append_event(session.session_id, "step_complete", payload)
    events = store.get_events(session.session_id)

    assert len(events) == 1
    assert events[0].payload == payload
    assert events[0].event_type == "step_complete"


# ---------------------------------------------------------------------------
# get_events — positional slicing
# ---------------------------------------------------------------------------

def test_get_events_from_position(tmp_path: Path):
    store = _store(tmp_path)
    session = store.create(title="test")

    for i in range(5):
        store.append_event(session.session_id, "user_message", {"i": i})

    # Slice from position 2
    events = store.get_events(session.session_id, from_position=2)
    assert len(events) == 3
    assert events[0].position == 2
    assert events[-1].position == 4


def test_get_events_limit(tmp_path: Path):
    store = _store(tmp_path)
    session = store.create(title="test")

    for i in range(10):
        store.append_event(session.session_id, "tool_call", {"i": i})

    events = store.get_events(session.session_id, limit=3)
    assert len(events) == 3


def test_get_events_empty_session(tmp_path: Path):
    store = _store(tmp_path)
    session = store.create(title="empty")
    events = store.get_events(session.session_id)
    assert events == []


# ---------------------------------------------------------------------------
# Session isolation
# ---------------------------------------------------------------------------

def test_events_are_isolated_per_session(tmp_path: Path):
    store = _store(tmp_path)
    s1 = store.create(title="session1")
    s2 = store.create(title="session2")

    store.append_event(s1.session_id, "user_message", {"msg": "s1"})
    store.append_event(s2.session_id, "user_message", {"msg": "s2"})
    store.append_event(s1.session_id, "step_start", {"msg": "s1-2"})

    e1 = store.get_events(s1.session_id)
    e2 = store.get_events(s2.session_id)

    assert len(e1) == 2
    assert len(e2) == 1
    assert e2[0].payload["msg"] == "s2"


# ---------------------------------------------------------------------------
# Persistence across store restarts
# ---------------------------------------------------------------------------

def test_events_survive_store_restart(tmp_path: Path):
    db = tmp_path / "persist.db"
    store1 = AgentSessionStore(db_path=db)
    session = store1.create(title="persist-test")
    store1.append_event(session.session_id, "user_message", {"hello": True})
    store1.append_event(session.session_id, "step_complete", {"done": True})

    # Re-open the same DB
    store2 = AgentSessionStore(db_path=db)
    events = store2.get_events(session.session_id)
    assert len(events) == 2
    assert events[0].payload == {"hello": True}
    assert events[1].payload == {"done": True}

    refreshed = store2.get(session.session_id)
    assert refreshed.event_count == 2

"""Tests for agent/memory.py — Session Memory Snapshots."""
from pathlib import Path

import pytest

from agent.memory import SessionMemory


def test_snapshot_and_restore(tmp_path: Path):
    mem = SessionMemory(storage_dir=tmp_path)
    state = {"history": [{"role": "user", "content": "hello"}], "step": 3}
    mem.snapshot("as_test1", state)

    restored = mem.restore("as_test1")
    assert restored == state


def test_restore_missing_returns_none(tmp_path: Path):
    mem = SessionMemory(storage_dir=tmp_path)
    assert mem.restore("nonexistent") is None


def test_list_snapshots(tmp_path: Path):
    mem = SessionMemory(storage_dir=tmp_path)
    mem.snapshot("as_aaa", {"x": 1})
    mem.snapshot("as_bbb", {"x": 2})

    snapshots = mem.list_snapshots()
    ids = [s["session_id"] for s in snapshots]
    assert "as_aaa" in ids
    assert "as_bbb" in ids


def test_delete_snapshot(tmp_path: Path):
    mem = SessionMemory(storage_dir=tmp_path)
    mem.snapshot("as_del", {"x": 1})
    assert mem.restore("as_del") is not None

    deleted = mem.delete("as_del")
    assert deleted is True
    assert mem.restore("as_del") is None


def test_delete_nonexistent_returns_false(tmp_path: Path):
    mem = SessionMemory(storage_dir=tmp_path)
    assert mem.delete("nope") is False


def test_snapshot_overwrites(tmp_path: Path):
    mem = SessionMemory(storage_dir=tmp_path)
    mem.snapshot("as_over", {"v": 1})
    mem.snapshot("as_over", {"v": 2})
    assert mem.restore("as_over") == {"v": 2}


def test_session_id_sanitisation(tmp_path: Path):
    mem = SessionMemory(storage_dir=tmp_path)
    # IDs with special chars should not create path traversal
    mem.snapshot("../evil", {"x": 1})
    snaps = mem.list_snapshots()
    for s in snaps:
        assert ".." not in Path(s["path"]).name

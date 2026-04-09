"""Tests for agent/watchdog.py — Resource Watchdog."""
from pathlib import Path

import pytest

from agent.watchdog import ResourceWatchdog, WatchEvent


def test_watch_and_list():
    wd = ResourceWatchdog()
    res = wd.watch(name="health", kind="url", target="http://localhost:9999/health")
    resources = wd.list()
    assert any(r.resource_id == res.resource_id for r in resources)


def test_unwatch():
    wd = ResourceWatchdog()
    res = wd.watch(name="x", kind="file", target="/tmp/x.txt")
    assert wd.unwatch(res.resource_id) is True
    assert not any(r.resource_id == res.resource_id for r in wd.list())


def test_unwatch_nonexistent():
    wd = ResourceWatchdog()
    assert wd.unwatch("res_nope") is False


def test_check_once_file_change(tmp_path: Path):
    events: list[WatchEvent] = []
    wd = ResourceWatchdog(on_change=events.append)

    f = tmp_path / "watched.txt"
    f.write_text("v1", encoding="utf-8")

    res = wd.watch(name="f", kind="file", target=str(f))
    # First check — establishes baseline, no event (hash was None)
    event1 = wd.check_once(res.resource_id)
    assert event1 is not None  # first time: None → hash is a change

    # Modify the file
    f.write_text("v2", encoding="utf-8")
    event2 = wd.check_once(res.resource_id)
    assert event2 is not None
    assert event2.old_hash != event2.new_hash


def test_check_once_no_change(tmp_path: Path):
    wd = ResourceWatchdog()
    f = tmp_path / "stable.txt"
    f.write_text("unchanged", encoding="utf-8")

    res = wd.watch(name="stable", kind="file", target=str(f))
    wd.check_once(res.resource_id)  # prime the hash
    event = wd.check_once(res.resource_id)  # same content
    assert event is None


def test_check_once_missing_file_returns_none():
    wd = ResourceWatchdog()
    res = wd.watch(name="missing", kind="file", target="/nonexistent/path/file.txt")
    event = wd.check_once(res.resource_id)
    assert event is None


def test_as_dict():
    wd = ResourceWatchdog()
    res = wd.watch(name="n", kind="url", target="http://x.com", action="notify")
    d = res.as_dict()
    assert "resource_id" in d
    assert d["action"] == "notify"


def test_trigger_count_increments(tmp_path: Path):
    wd = ResourceWatchdog()
    f = tmp_path / "cnt.txt"
    f.write_text("a", encoding="utf-8")
    res = wd.watch(name="cnt", kind="file", target=str(f))
    wd.check_once(res.resource_id)  # first change (None → hash)

    f.write_text("b", encoding="utf-8")
    wd.check_once(res.resource_id)

    f.write_text("c", encoding="utf-8")
    wd.check_once(res.resource_id)

    updated = wd.list()[0]
    assert updated.trigger_count >= 2

"""tests/test_quick_note.py — Unit tests for agent/quick_note.py."""
from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agent.quick_note import QuickNote, QuickNoteQueue, _fetch_text, process_note


# ── QuickNoteQueue ────────────────────────────────────────────────────────────

def test_add_creates_pending_note(tmp_path: Path) -> None:
    q = QuickNoteQueue(queue_file=tmp_path / "q.json")
    note = q.add("https://example.com/feature")
    assert note.status == "pending"
    assert note.url == "https://example.com/feature"
    assert note.note_id.startswith("note_")


def test_add_persists_to_file(tmp_path: Path) -> None:
    q = QuickNoteQueue(queue_file=tmp_path / "q.json")
    q.add("https://example.com")
    data = json.loads((tmp_path / "q.json").read_text())
    assert len(data["notes"]) == 1


def test_next_pending_claims_note(tmp_path: Path) -> None:
    q = QuickNoteQueue(queue_file=tmp_path / "q.json")
    q.add("https://example.com/a")
    q.add("https://example.com/b")
    note = q.next_pending()
    assert note is not None
    assert note.status == "processing"
    assert note.url == "https://example.com/a"  # FIFO


def test_next_pending_returns_none_when_empty(tmp_path: Path) -> None:
    q = QuickNoteQueue(queue_file=tmp_path / "q.json")
    assert q.next_pending() is None


def test_mark_done(tmp_path: Path) -> None:
    q = QuickNoteQueue(queue_file=tmp_path / "q.json")
    note = q.add("https://example.com")
    q.next_pending()
    q.mark_done(note.note_id)
    notes = q.list_all()
    assert notes[0].status == "done"
    assert notes[0].processed_at is not None


def test_mark_failed(tmp_path: Path) -> None:
    q = QuickNoteQueue(queue_file=tmp_path / "q.json")
    note = q.add("https://example.com")
    q.next_pending()
    q.mark_failed(note.note_id, "network error")
    notes = q.list_all()
    assert notes[0].status == "failed"
    assert "network error" in notes[0].error


def test_list_all_returns_all(tmp_path: Path) -> None:
    q = QuickNoteQueue(queue_file=tmp_path / "q.json")
    q.add("https://a.com")
    q.add("https://b.com")
    assert len(q.list_all()) == 2


def test_queue_survives_reload(tmp_path: Path) -> None:
    path = tmp_path / "q.json"
    q1 = QuickNoteQueue(queue_file=path)
    q1.add("https://example.com/persist")
    q2 = QuickNoteQueue(queue_file=path)
    notes = q2.list_all()
    assert len(notes) == 1
    assert notes[0].url == "https://example.com/persist"


# ── process_note ──────────────────────────────────────────────────────────────

def _make_note() -> QuickNote:
    return QuickNote(
        note_id="note_abc123",
        url="https://example.com/feature",
        added_at="2026-01-01T00:00:00Z",
        status="processing",
    )


def test_process_note_success(tmp_path: Path) -> None:
    q = QuickNoteQueue(queue_file=tmp_path / "q.json")
    note = q.add("https://example.com")
    note = q.next_pending()

    with (
        patch("agent.quick_note._fetch_text", return_value="Build a health endpoint"),
        patch("agent.quick_note._run") as mock_run,
        patch("subprocess.run") as mock_subprocess,
    ):
        mock_run.return_value = ""
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="1 file changed", stderr="")
        process_note(note, q, repo_root=tmp_path)

    assert q.list_all()[0].status == "done"


def test_process_note_marks_failed_on_fetch_error(tmp_path: Path) -> None:
    q = QuickNoteQueue(queue_file=tmp_path / "q.json")
    note = q.add("https://example.com")
    note = q.next_pending()

    with patch("agent.quick_note._fetch_text", side_effect=RuntimeError("timeout")):
        process_note(note, q, repo_root=tmp_path)

    assert q.list_all()[0].status == "failed"
    assert "timeout" in q.list_all()[0].error


def test_process_note_no_commit_when_nothing_changed(tmp_path: Path) -> None:
    q = QuickNoteQueue(queue_file=tmp_path / "q.json")
    note = q.add("https://example.com")
    note = q.next_pending()

    with (
        patch("agent.quick_note._fetch_text", return_value="content"),
        patch("agent.quick_note._run"),
        patch("subprocess.run") as mock_subprocess,
    ):
        mock_subprocess.return_value = MagicMock(
            returncode=1, stdout="nothing to commit", stderr=""
        )
        process_note(note, q, repo_root=tmp_path)

    assert q.list_all()[0].status == "done"



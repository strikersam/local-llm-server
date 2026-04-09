"""Tests for agent/commit_tracker.py — AI Commit Attribution."""
import subprocess
from pathlib import Path

import pytest

from agent.commit_tracker import CommitAttribution, CommitTracker


def _init_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True, capture_output=True)
    # Disable signing so tests work in environments with mandatory commit signing
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "gpg.format", "openpgp"], cwd=tmp_path, check=True, capture_output=True)
    return tmp_path


def test_build_trailer_args():
    attr = CommitAttribution(session_id="as_abc", model="qwen3:30b")
    tracker = CommitTracker()
    args = tracker.build_trailer_args(attr)
    assert any("Agent-Session: as_abc" in a for a in args)
    assert any("Agent-Model: qwen3:30b" in a for a in args)
    assert any("Agent-Tool:" in a for a in args)
    assert any("Agent-Timestamp:" in a for a in args)


def test_attribution_timestamp_auto():
    attr = CommitAttribution(session_id="s", model="m")
    assert attr.timestamp != ""


def test_commit_attributed(tmp_path: Path):
    repo = _init_repo(tmp_path)
    tracker = CommitTracker(repo_root=repo)

    f = repo / "hello.txt"
    f.write_text("hello\n", encoding="utf-8")
    attr = CommitAttribution(session_id="as_xyz", model="qwen3:30b")
    sha = tracker.commit(files=["hello.txt"], message="test: attributed commit", attribution=attr)
    assert sha is not None
    assert len(sha) == 40


def test_log_returns_entries(tmp_path: Path):
    repo = _init_repo(tmp_path)
    tracker = CommitTracker(repo_root=repo)

    f = repo / "a.txt"
    f.write_text("a\n", encoding="utf-8")
    attr = CommitAttribution(session_id="as_log1", model="m1")
    tracker.commit(files=["a.txt"], message="first", attribution=attr)

    entries = tracker.log(limit=5)
    assert isinstance(entries, list)
    assert len(entries) >= 1


def test_commit_failure_returns_none(tmp_path: Path):
    """Attempting to commit when no files staged returns None gracefully."""
    repo = _init_repo(tmp_path)
    tracker = CommitTracker(repo_root=repo)
    attr = CommitAttribution(session_id="s", model="m")
    # No files exist — commit should fail gracefully
    sha = tracker.commit(files=["nonexistent.txt"], message="fail", attribution=attr)
    assert sha is None

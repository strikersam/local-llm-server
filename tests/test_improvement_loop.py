"""Tests for agent/improvement_loop.py"""
from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# Override the autouse conftest fixture that requires backend.server dependencies
# not available in the lightweight test environment for these unit tests.
@pytest.fixture(autouse=True)
def setup_database_moks(monkeypatch):  # noqa: PT004
    pass


from agent.improvement_loop import (
    DetectedIssue,
    ImprovementLoop,
    ImprovementLoopState,
    IssueCategory,
    IssueSeverity,
    get_improvement_loop,
    set_improvement_loop,
)


@pytest.fixture
def tmp_loop(tmp_path: Path) -> ImprovementLoop:
    """ImprovementLoop with a temp repo root and no _on_task callback."""
    return ImprovementLoop(repo_root=tmp_path, on_task=None, scan_interval_hours=24)


def test_detected_issue_to_instruction():
    issue = DetectedIssue(
        issue_id="tf_abc123",
        category=IssueCategory.TEST_FAILURE,
        severity=IssueSeverity.HIGH,
        title="Failing test: test_foo",
        description="test_foo failed",
        file_path="tests/test_foo.py",
    )
    inst = issue.to_instruction()
    assert "test_failure" in inst
    assert "Failing test: test_foo" in inst
    assert "tests/test_foo.py" in inst
    assert "docs/changelog.md" in inst


def test_detected_issue_as_dict():
    issue = DetectedIssue(
        issue_id="mt_deadbeef",
        category=IssueCategory.MISSING_TEST,
        severity=IssueSeverity.LOW,
        title="No coverage: foo.py",
        description="foo.py has no test",
    )
    d = issue.as_dict()
    assert d["issue_id"] == "mt_deadbeef"
    assert d["category"] == IssueCategory.MISSING_TEST
    assert d["resolved"] is False


def test_improvement_loop_state_round_trip(tmp_path: Path):
    state_file = tmp_path / ".claude" / "state" / "improvement-state.json"
    loop = ImprovementLoop(repo_root=tmp_path, scan_interval_hours=24)

    # Manually register an issue and save
    issue = DetectedIssue(
        issue_id="td_1234",
        category=IssueCategory.TODO_FIXME,
        severity=IssueSeverity.MEDIUM,
        title="FIXME in foo.py:12",
        description="Found FIXME",
    )
    loop._register_issue(issue)

    # Re-load from disk
    loop2 = ImprovementLoop(repo_root=tmp_path, scan_interval_hours=24)
    state = loop2.get_status()
    assert any(i["issue_id"] == "td_1234" for i in state["active_issues"])


def test_mark_resolved(tmp_loop: ImprovementLoop):
    issue = DetectedIssue(
        issue_id="tf_resolve_me",
        category=IssueCategory.TEST_FAILURE,
        severity=IssueSeverity.HIGH,
        title="Failing test: test_x",
        description="test_x fails",
    )
    tmp_loop._register_issue(issue)

    assert tmp_loop.mark_resolved("tf_resolve_me") is True
    assert tmp_loop.mark_resolved("nonexistent_id") is False

    status = tmp_loop.get_status()
    assert not any(i["issue_id"] == "tf_resolve_me" for i in status["active_issues"])
    assert any(i["issue_id"] == "tf_resolve_me" for i in status["resolved_issues"])
    assert status["issues_resolved"] == 1


def test_filter_new_issues_deduplicates(tmp_loop: ImprovementLoop):
    issue = DetectedIssue(
        issue_id="mt_dup",
        category=IssueCategory.MISSING_TEST,
        severity=IssueSeverity.LOW,
        title="No coverage: bar.py",
        description="bar.py has no test",
    )
    tmp_loop._register_issue(issue)

    # Same title again — should be filtered out
    duplicate = DetectedIssue(
        issue_id="mt_different_id",
        category=IssueCategory.MISSING_TEST,
        severity=IssueSeverity.LOW,
        title="No coverage: bar.py",  # same title
        description="bar.py still has no test",
    )
    new_issues = tmp_loop._filter_new_issues([duplicate])
    assert new_issues == []


def test_schedule_fix_calls_on_task(tmp_path: Path):
    calls: list[dict] = []

    def capture(**kwargs):
        calls.append(kwargs)

    loop = ImprovementLoop(repo_root=tmp_path, on_task=capture, scan_interval_hours=24)
    issue = DetectedIssue(
        issue_id="tf_sched",
        category=IssueCategory.TEST_FAILURE,
        severity=IssueSeverity.HIGH,
        title="Failing test: test_y",
        description="test_y fails",
    )
    loop._schedule_fix(issue)
    assert len(calls) == 1
    assert "fix:tf_sched" in calls[0]["name"]
    assert "auto-improvement" in calls[0]["tags"]


def test_schedule_fix_no_callback(tmp_loop: ImprovementLoop):
    """Should not raise even with no on_task callback."""
    issue = DetectedIssue(
        issue_id="tf_noop",
        category=IssueCategory.TEST_FAILURE,
        severity=IssueSeverity.HIGH,
        title="Test failure",
        description="desc",
    )
    tmp_loop._schedule_fix(issue)  # should be a no-op


def test_scan_todo_fixme_empty(tmp_path: Path):
    """In an empty tmp dir, grep returns nothing — no issues."""
    (tmp_path / "sample.py").write_text("x = 1\n")
    loop = ImprovementLoop(repo_root=tmp_path, scan_interval_hours=24)
    issues = loop._scan_todo_fixme()
    assert issues == []


def test_scan_todo_fixme_finds_marker(tmp_path: Path):
    (tmp_path / "sample.py").write_text("# FIXME: this is broken\nx = 1\n")
    loop = ImprovementLoop(repo_root=tmp_path, scan_interval_hours=24)
    issues = loop._scan_todo_fixme()
    assert len(issues) >= 1
    assert issues[0].category == IssueCategory.TODO_FIXME


def test_singleton_round_trip():
    orig = get_improvement_loop()
    loop = ImprovementLoop(scan_interval_hours=24)
    set_improvement_loop(loop)
    assert get_improvement_loop() is loop
    # Restore original
    set_improvement_loop(orig)


def test_get_status_is_dict(tmp_loop: ImprovementLoop):
    status = tmp_loop.get_status()
    assert isinstance(status, dict)
    for key in ("active_issues", "resolved_issues", "scan_count", "issues_detected"):
        assert key in status

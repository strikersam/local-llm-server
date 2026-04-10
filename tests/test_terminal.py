"""Tests for agent/terminal.py — Terminal Panel."""
from agent.terminal import TerminalPanel, TerminalSnapshot


def test_snapshot_returns_snapshot():
    panel = TerminalPanel()
    snap = panel.snapshot()
    assert isinstance(snap, TerminalSnapshot)
    assert isinstance(snap.lines, list)
    assert snap.cols > 0
    assert snap.rows > 0


def test_snapshot_source():
    panel = TerminalPanel()
    snap = panel.snapshot()
    # Either tmux or fallback — both are valid
    assert snap.source in ("tmux", "fallback")


def test_run_and_capture_echo():
    panel = TerminalPanel()
    result = panel.run_and_capture(["echo", "hello world"])
    assert result["returncode"] == 0
    assert "hello world" in result["stdout"]


def test_run_and_capture_stderr():
    panel = TerminalPanel()
    result = panel.run_and_capture(["ls", "/nonexistent_path_xyz"])
    assert result["returncode"] != 0
    assert result["stderr"] != "" or result["stdout"] != ""


def test_run_and_capture_timeout():
    panel = TerminalPanel()
    result = panel.run_and_capture(["sleep", "10"], timeout=1)
    assert result["returncode"] == -1
    assert "timeout" in result["stderr"]


def test_run_and_capture_unknown_cmd():
    panel = TerminalPanel()
    result = panel.run_and_capture(["__no_such_cmd_xyz__"])
    assert result["returncode"] == -1


def test_as_dict():
    panel = TerminalPanel()
    snap = panel.snapshot()
    d = snap.as_dict()
    assert "lines" in d
    assert "cols" in d
    assert "source" in d

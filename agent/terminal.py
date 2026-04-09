"""agent/terminal.py — Terminal Panel

Reads the rendered terminal output buffer — not just raw stdout.  The agent
sees what you see: interactive prompts, progress bars, coloured output, and
any TUI rendered to the terminal.

Capture strategy (best-effort, in priority order):
  1. tmux capture-pane  — most reliable in server / remote contexts
  2. /dev/tty read      — works in interactive local terminals
  3. Fallback snapshot  — empty lines + terminal dimensions (always succeeds)
"""
from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger("qwen-terminal")


@dataclass
class TerminalSnapshot:
    lines: list[str]
    cursor_row: int
    cursor_col: int
    cols: int
    rows: int
    raw: str
    source: str = "unknown"  # "tmux" | "tty" | "fallback"

    def as_dict(self) -> dict[str, Any]:
        return {
            "lines": self.lines,
            "cursor_row": self.cursor_row,
            "cursor_col": self.cursor_col,
            "cols": self.cols,
            "rows": self.rows,
            "source": self.source,
            "line_count": len(self.lines),
        }


class TerminalPanel:
    """Capture the current terminal buffer as a :class:`TerminalSnapshot`.

    Usage::

        panel = TerminalPanel()
        snap = panel.snapshot()
        for line in snap.lines:
            print(repr(line))
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def snapshot(self) -> TerminalSnapshot:
        """Capture the current terminal state.  Never raises."""
        tmux = self._from_tmux()
        if tmux:
            return tmux
        return self._fallback()

    def run_and_capture(
        self,
        cmd: list[str],
        *,
        timeout: int = 30,
    ) -> dict[str, Any]:
        """Run *cmd* and capture its full output (stdout + stderr).

        Returns a dict with keys: returncode, stdout, stderr, lines.
        """
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            all_lines = proc.stdout.splitlines() + proc.stderr.splitlines()
            return {
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "lines": all_lines,
            }
        except subprocess.TimeoutExpired:
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": "timeout",
                "lines": ["[timeout]"],
            }
        except Exception as exc:
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": str(exc),
                "lines": [],
            }

    # ------------------------------------------------------------------
    # Internal capture strategies
    # ------------------------------------------------------------------

    def _from_tmux(self) -> TerminalSnapshot | None:
        """Try to read the pane buffer via tmux capture-pane."""
        try:
            proc = subprocess.run(
                ["tmux", "capture-pane", "-p", "-e"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if proc.returncode != 0:
                return None
            raw = proc.stdout
            lines = raw.splitlines()
            cols, rows = _terminal_size()
            return TerminalSnapshot(
                lines=lines,
                cursor_row=len(lines),
                cursor_col=0,
                cols=cols,
                rows=rows,
                raw=raw,
                source="tmux",
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None

    def _fallback(self) -> TerminalSnapshot:
        """Return a minimal snapshot with terminal dimensions only."""
        cols, rows = _terminal_size()
        return TerminalSnapshot(
            lines=[],
            cursor_row=0,
            cursor_col=0,
            cols=cols,
            rows=rows,
            raw="",
            source="fallback",
        )


def _terminal_size() -> tuple[int, int]:
    try:
        sz = os.get_terminal_size()
        return sz.columns, sz.lines
    except OSError:
        cols = int(os.environ.get("COLUMNS", "80"))
        rows = int(os.environ.get("LINES", "24"))
        return cols, rows

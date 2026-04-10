"""agent/commit_tracker.py — AI Commit Attribution

Tags git commits with metadata identifying the agent session that made them,
so every AI-generated code change is traceable back to the session, model,
and timestamp that produced it.

Trailers added to each attributed commit::

    Agent-Session: as_abc123
    Agent-Model:   qwen3-coder:30b
    Agent-Tool:    llm-relay
    Agent-Timestamp: 2026-04-09T12:34:56Z
"""
from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger("qwen-commit-tracker")


@dataclass
class CommitAttribution:
    session_id: str
    model: str
    timestamp: str = ""
    tool: str = "llm-relay"

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class CommitTracker:
    """Create git commits enriched with agent-session attribution trailers.

    Usage::

        tracker = CommitTracker(repo_root="/path/to/repo")
        sha = tracker.commit(
            files=["src/main.py"],
            message="feat: improve routing",
            attribution=CommitAttribution(session_id="as_abc", model="qwen3-coder:30b"),
        )
        history = tracker.log(limit=5)
    """

    def __init__(self, repo_root: str | Path | None = None) -> None:
        self.repo_root = Path(repo_root) if repo_root else Path.cwd()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_trailer_args(self, attribution: CommitAttribution) -> list[str]:
        """Return ``--trailer`` arguments ready to append to a ``git commit`` call."""
        return [
            "--trailer", f"Agent-Session: {attribution.session_id}",
            "--trailer", f"Agent-Model: {attribution.model}",
            "--trailer", f"Agent-Tool: {attribution.tool}",
            "--trailer", f"Agent-Timestamp: {attribution.timestamp}",
        ]

    def commit(
        self,
        *,
        files: list[str],
        message: str,
        attribution: CommitAttribution,
    ) -> str | None:
        """Stage *files* and create an attributed commit.

        Returns the commit SHA on success, or *None* on failure.
        """
        try:
            subprocess.run(
                ["git", "add", *files],
                cwd=self.repo_root,
                check=True,
                capture_output=True,
                text=True,
            )
            trailer_args = self.build_trailer_args(attribution)
            subprocess.run(
                ["git", "commit", "-m", message, *trailer_args],
                cwd=self.repo_root,
                check=True,
                capture_output=True,
                text=True,
            )
            proc = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_root,
                check=True,
                capture_output=True,
                text=True,
            )
            sha = proc.stdout.strip()
            log.info(
                "Attributed commit %s: session=%s model=%s",
                sha,
                attribution.session_id,
                attribution.model,
            )
            return sha
        except subprocess.CalledProcessError as exc:
            log.warning(
                "Attributed commit failed: %s",
                exc.stderr.strip() if exc.stderr else exc,
            )
            return None

    def log(self, limit: int = 10) -> list[dict[str, Any]]:
        """Return recent commits with agent attribution trailers parsed out."""
        try:
            proc = subprocess.run(
                ["git", "log", f"-{limit}", "--format=%x00%H|%s|%b"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
            )
            entries: list[dict[str, Any]] = []
            for block in proc.stdout.split("\x00"):
                lines = block.strip().split("\n")
                if not lines or not lines[0].strip():
                    continue
                first = lines[0].split("|", 2)
                sha = first[0] if first else ""
                subject = first[1] if len(first) > 1 else ""
                body_lines = lines[1:] if len(lines) > 1 else []
                trailers: dict[str, str] = {}
                for line in body_lines:
                    if ": " in line and line.startswith("Agent-"):
                        k, _, v = line.partition(": ")
                        trailers[k] = v.strip()
                entries.append(
                    {
                        "sha": sha,
                        "subject": subject,
                        "agent_trailers": trailers,
                    }
                )
            return entries
        except Exception as exc:
            log.warning("commit_tracker.log failed: %s", exc)
            return []

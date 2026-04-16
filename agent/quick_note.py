"""agent/quick_note.py — iPhone Quick Note integration.

Persistent URL queue + background processor.  Every QUICK_NOTE_INTERVAL_HOURS
hours the processor picks the next pending URL, fetches its content, runs
Claude Code to implement it, then commits and pushes to QUICK_NOTE_PUSH_BRANCH.

iPhone Shortcut → POST /v1/quick-notes  → queue  → processor → git push
"""
from __future__ import annotations

import json
import logging
import os
import re
import secrets
import subprocess
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import httpx

log = logging.getLogger("qwen-proxy")

_REPO_ROOT = Path(__file__).parent.parent
_QUEUE_FILE = _REPO_ROOT / "tasks" / "quick_notes.json"

PUSH_BRANCH = os.environ.get("QUICK_NOTE_PUSH_BRANCH", "master")
INTERVAL_HOURS = int(os.environ.get("QUICK_NOTE_INTERVAL_HOURS", "4"))


@dataclass
class QuickNote:
    note_id: str
    url: str
    added_at: str
    status: str = "pending"   # pending | processing | done | failed
    processed_at: str | None = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class QuickNoteQueue:
    """Thread-safe, file-backed queue for iPhone quick-note URLs."""

    def __init__(self, queue_file: Path = _QUEUE_FILE) -> None:
        self._file = queue_file
        self._lock = threading.Lock()
        self._file.parent.mkdir(parents=True, exist_ok=True)
        if not self._file.exists():
            self._write({"notes": []})

    def add(self, url: str) -> QuickNote:
        note = QuickNote(
            note_id="note_" + secrets.token_hex(6),
            url=url,
            added_at=_now(),
        )
        with self._lock:
            data = self._read()
            data["notes"].append(note.as_dict())
            self._write(data)
        log.info("QuickNote queued: %s -> %s", note.note_id, url)
        return note

    def next_pending(self) -> QuickNote | None:
        """Atomically claim the oldest pending note (sets it to 'processing')."""
        with self._lock:
            data = self._read()
            for item in data["notes"]:
                if item["status"] == "pending":
                    item["status"] = "processing"
                    self._write(data)
                    return QuickNote(**item)
        return None

    def mark_done(self, note_id: str) -> None:
        self._update(note_id, status="done", processed_at=_now())

    def mark_failed(self, note_id: str, error: str) -> None:
        self._update(note_id, status="failed", processed_at=_now(), error=error[:500])

    def list_all(self) -> list[QuickNote]:
        with self._lock:
            return [QuickNote(**item) for item in self._read()["notes"]]

    # ── internal ─────────────────────────────────────────────────────────────────

    def _update(self, note_id: str, **fields: Any) -> None:
        with self._lock:
            data = self._read()
            for item in data["notes"]:
                if item["note_id"] == note_id:
                    item.update(fields)
                    break
            self._write(data)

    def _read(self) -> dict:
        try:
            return json.loads(self._file.read_text())
        except (json.JSONDecodeError, FileNotFoundError):
            return {"notes": []}

    def _write(self, data: dict) -> None:
        self._file.write_text(json.dumps(data, indent=2))


# ── URL fetching ──────────────────────────────────────────────────────────────

def _fetch_text(url: str, max_chars: int = 8000) -> str:
    """GET *url* and return plain text (HTML tags stripped, max *max_chars*)."""
    headers = {"User-Agent": "QuickNote-Bot/1.0 (local-llm-server)"}
    with httpx.Client(follow_redirects=True, timeout=30) as client:
        resp = client.get(url, headers=headers)
        resp.raise_for_status()
    text = resp.text
    if "html" in resp.headers.get("content-type", "").lower():
        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


# ── Note processor ────────────────────────────────────────────────────────────

def _run(cmd: list[str], *, cwd: Path, timeout: int = 60) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd), timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout)[:500])
    return result.stdout


def process_note(
    note: QuickNote,
    queue: QuickNoteQueue,
    repo_root: Path = _REPO_ROOT,
    push_branch: str = PUSH_BRANCH,
) -> None:
    """Fetch URL, run Claude Code to implement, commit and push."""
    log.info("QuickNote processing: %s (%s)", note.note_id, note.url)
    try:
        content = _fetch_text(note.url)

        instruction = (
            "Implement the following feature or change in this codebase. "
            "Read the source material carefully and make all necessary code changes. "
            "Do NOT run git commands — the system will commit and push after you finish.\n\n"
            f"Source URL: {note.url}\n\n"
            f"Content:\n{content}"
        )

        _run(
            ["claude", "--print", "--dangerously-skip-permissions", instruction],
            cwd=repo_root,
            timeout=3600,
        )

        _run(["git", "add", "-A"], cwd=repo_root)

        commit_result = subprocess.run(
            ["git", "commit", "-m", f"feat: implement quick note from {note.url[:60]}"],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
        committed = commit_result.returncode == 0
        if not committed and "nothing to commit" not in commit_result.stdout + commit_result.stderr:
            raise RuntimeError(commit_result.stderr[:500])

        if committed:
            _run(["git", "push", "-u", "origin", push_branch], cwd=repo_root, timeout=120)
            log.info("QuickNote %s pushed to %s", note.note_id, push_branch)
        else:
            log.info("QuickNote %s: no changes to commit", note.note_id)

        queue.mark_done(note.note_id)

    except Exception as exc:
        log.error("QuickNote %s failed: %s", note.note_id, exc)
        queue.mark_failed(note.note_id, str(exc))


# ── Background processor ──────────────────────────────────────────────────────

def start_processor(
    queue: QuickNoteQueue,
    repo_root: Path = _REPO_ROOT,
    push_branch: str = PUSH_BRANCH,
    interval_hours: int = INTERVAL_HOURS,
) -> None:
    """Start a daemon thread that processes one queued note every *interval_hours*."""
    interval_secs = interval_hours * 3600

    def _loop() -> None:
        log.info("QuickNote processor started (interval=%dh, branch=%s)", interval_hours, push_branch)
        while True:
            try:
                note = queue.next_pending()
                if note:
                    process_note(note, queue, repo_root, push_branch)
                else:
                    log.debug("QuickNote: queue empty")
            except Exception as exc:
                log.error("QuickNote processor error: %s", exc)
            time.sleep(interval_secs)

    threading.Thread(target=_loop, name="quick-note-processor", daemon=True).start()


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

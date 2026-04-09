"""agent/memory.py — Session Memory Snapshots

Persists agent session state to disk so agents can resume from exactly where
they left off after a restart — no external database required.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

log = logging.getLogger("qwen-memory")

DEFAULT_MEMORY_DIR = ".agent_memory"


class SessionMemory:
    """Save and restore agent state snapshots to/from a local directory.

    Usage::

        mem = SessionMemory()
        mem.snapshot("as_abc123", {"history": [...], "last_plan": ...})
        state = mem.restore("as_abc123")   # dict or None if not found
    """

    def __init__(self, storage_dir: str | Path | None = None) -> None:
        self.storage_dir = Path(storage_dir or DEFAULT_MEMORY_DIR)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def snapshot(self, session_id: str, state: dict[str, Any]) -> Path:
        """Persist *state* to disk under *session_id*. Returns the file path."""
        data = {
            "session_id": session_id,
            "saved_at": _now(),
            "state": state,
        }
        path = self._path(session_id)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        log.debug("Memory snapshot saved: session=%s path=%s", session_id, path)
        return path

    def restore(self, session_id: str) -> dict[str, Any] | None:
        """Load a saved snapshot. Returns the state dict or *None* if absent."""
        path = self._path(session_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get("state")
        except (json.JSONDecodeError, KeyError) as exc:
            log.warning("Corrupt memory snapshot %s: %s", path, exc)
            return None

    def list_snapshots(self) -> list[dict[str, Any]]:
        """Return metadata for all saved snapshots (session_id, saved_at, path)."""
        results: list[dict[str, Any]] = []
        for p in sorted(self.storage_dir.glob("*.json")):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                results.append(
                    {
                        "session_id": data.get("session_id", p.stem),
                        "saved_at": data.get("saved_at"),
                        "path": str(p),
                    }
                )
            except (json.JSONDecodeError, KeyError):
                continue
        return results

    def delete(self, session_id: str) -> bool:
        """Delete a snapshot. Returns *True* if the file existed."""
        path = self._path(session_id)
        if path.exists():
            path.unlink()
            log.debug("Memory snapshot deleted: session=%s", session_id)
            return True
        return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _path(self, session_id: str) -> Path:
        # Sanitise session_id to a safe filename component.
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)
        return self.storage_dir / f"{safe}.json"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

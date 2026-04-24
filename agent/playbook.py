"""agent/playbook.py — Automation Playbooks

Pre-defined, named multi-step automation scripts.  Invoke a playbook by
name; each step's instruction is executed in sequence.  Steps can chain
context (results of step N feed into step N+1 via history).

Playbooks can be registered programmatically or loaded from JSON files in a
directory.
"""
from __future__ import annotations

import json
import logging
import secrets
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger("qwen-playbook")


@dataclass
class PlaybookStep:
    step_id: int
    description: str
    instruction: str
    model: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "description": self.description,
            "instruction": self.instruction,
            "model": self.model,
        }


@dataclass
class Playbook:
    playbook_id: str
    name: str
    description: str
    steps: list[PlaybookStep]
    created_at: str
    tags: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "playbook_id": self.playbook_id,
            "name": self.name,
            "description": self.description,
            "steps": [s.as_dict() for s in self.steps],
            "created_at": self.created_at,
            "tags": self.tags,
        }


@dataclass
class PlaybookRun:
    run_id: str
    playbook_id: str
    playbook_name: str
    started_at: str
    finished_at: str | None = None
    step_results: list[dict[str, Any]] = field(default_factory=list)
    created_task_ids: list[str] = field(default_factory=list)
    status: str = "pending"  # pending | running | done | failed

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "playbook_id": self.playbook_id,
            "playbook_name": self.playbook_name,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "step_results": self.step_results,
            "created_task_ids": self.created_task_ids,
            "status": self.status,
        }


class PlaybookLibrary:
    """Store, search, and execute named automation playbooks.

    Usage::

        lib = PlaybookLibrary()
        pb = lib.register(
            name="daily-review",
            description="Lint wiki then summarise open issues",
            steps=[
                {"description": "Lint", "instruction": "Run wiki lint"},
                {"description": "Summarise", "instruction": "Summarise open issues"},
            ],
        )
        run = lib.start_run(pb.playbook_id)
        # … execute each step …
        lib.finish_run(run.run_id, step_results=[...])
    """

    def __init__(self, library_dir: str | Path | None = None) -> None:
        self._playbooks: dict[str, Playbook] = {}
        self._runs: dict[str, PlaybookRun] = {}
        if library_dir:
            self._load_dir(Path(library_dir))

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        *,
        name: str,
        description: str,
        steps: list[dict[str, Any]],
        tags: list[str] | None = None,
        playbook_id: str | None = None,
    ) -> Playbook:
        pb = Playbook(
            playbook_id=playbook_id or ("pb_" + secrets.token_hex(6)),
            name=name,
            description=description,
            tags=tags or [],
            created_at=_now(),
            steps=[
                PlaybookStep(
                    step_id=i + 1,
                    description=s.get("description", f"Step {i + 1}"),
                    instruction=s["instruction"],
                    model=s.get("model"),
                )
                for i, s in enumerate(steps)
            ],
        )
        self._playbooks[pb.playbook_id] = pb
        log.info("Playbook registered: id=%s name=%r steps=%d", pb.playbook_id, name, len(pb.steps))
        return pb

    def _load_dir(self, directory: Path) -> None:
        for p in directory.glob("*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                self.register(
                    name=data["name"],
                    description=data.get("description", ""),
                    steps=data.get("steps", []),
                    tags=data.get("tags", []),
                    playbook_id=data.get("playbook_id"),
                )
                log.info("Loaded playbook %r from %s", data["name"], p)
            except Exception as exc:
                log.warning("Could not load playbook %s: %s", p, exc)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get(self, playbook_id: str) -> Playbook | None:
        return self._playbooks.get(playbook_id)

    def list(self, tag: str | None = None) -> list[Playbook]:
        pbs = list(self._playbooks.values())
        if tag:
            pbs = [p for p in pbs if tag in p.tags]
        return pbs

    def delete(self, playbook_id: str) -> bool:
        return bool(self._playbooks.pop(playbook_id, None))

    # ------------------------------------------------------------------
    # Run lifecycle
    # ------------------------------------------------------------------

    def start_run(self, playbook_id: str) -> PlaybookRun:
        pb = self._playbooks.get(playbook_id)
        if not pb:
            raise KeyError(f"Playbook {playbook_id!r} not found")
        run = PlaybookRun(
            run_id="run_" + secrets.token_hex(6),
            playbook_id=playbook_id,
            playbook_name=pb.name,
            started_at=_now(),
            status="running",
        )
        self._runs[run.run_id] = run
        return run

    def finish_run(
        self,
        run_id: str,
        step_results: list[dict[str, Any]],
        *,
        created_task_ids: list[str] | None = None,
        status: str = "done",
    ) -> PlaybookRun:
        run = self._runs[run_id]
        run.step_results = step_results
        run.created_task_ids = list(created_task_ids or run.created_task_ids)
        run.finished_at = _now()
        run.status = status
        return run

    def get_run(self, run_id: str) -> PlaybookRun | None:
        return self._runs.get(run_id)

    def list_runs(self, playbook_id: str | None = None) -> list[PlaybookRun]:
        runs = list(self._runs.values())
        if playbook_id:
            runs = [r for r in runs if r.playbook_id == playbook_id]
        return runs


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

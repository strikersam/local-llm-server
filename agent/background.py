"""agent/background.py — Background Agent

An always-on worker thread that processes tasks submitted from webhooks,
the scheduler, or the resource watchdog — without needing a user to open
a chat window.

Typical use: wire the scheduler's on_fire callback to BackgroundAgent.submit()
so scheduled jobs are automatically dispatched to the agent pipeline.
"""
from __future__ import annotations

import logging
import queue
import secrets
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

log = logging.getLogger("qwen-background")


@dataclass
class BackgroundTask:
    task_id: str
    kind: str  # "webhook" | "scheduled" | "watchdog" | "manual"
    payload: dict[str, Any]
    created_at: str
    status: str = "pending"  # pending | running | done | failed
    result: Any = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "kind": self.kind,
            "payload": self.payload,
            "created_at": self.created_at,
            "status": self.status,
            "result": self.result,
            "error": self.error,
        }


class BackgroundAgent:
    """Always-on worker that drains a task queue on a daemon thread.

    Usage::

        agent = BackgroundAgent(on_task_complete=notify_telegram)
        agent.start()
        agent.submit(BackgroundTask(
            task_id=secrets.token_hex(8),
            kind="webhook",
            payload={"instruction": "Run tests and report failures"},
            created_at=...,
        ))
    """

    def __init__(
        self,
        *,
        on_task_complete: Callable[[BackgroundTask], None] | None = None,
    ) -> None:
        self._queue: queue.Queue[BackgroundTask] = queue.Queue()
        self._on_task_complete = on_task_complete
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._tasks: dict[str, BackgroundTask] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def submit(self, task: BackgroundTask) -> BackgroundTask:
        """Enqueue *task* for processing. Returns the task (with task_id set)."""
        self._tasks[task.task_id] = task
        self._queue.put(task)
        log.info("Background task submitted: id=%s kind=%s", task.task_id, task.kind)
        return task

    def create_and_submit(
        self,
        kind: str,
        payload: dict[str, Any],
    ) -> BackgroundTask:
        """Convenience: create a task and submit it in one call."""
        task = BackgroundTask(
            task_id="bg_" + secrets.token_hex(6),
            kind=kind,
            payload=payload,
            created_at=_now(),
        )
        return self.submit(task)

    def get_task(self, task_id: str) -> BackgroundTask | None:
        return self._tasks.get(task_id)

    def list_tasks(self, status: str | None = None) -> list[BackgroundTask]:
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return tasks

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="background-agent",
        )
        self._thread.start()
        log.info("BackgroundAgent worker started")

    def stop(self, timeout: float = 10.0) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=timeout)

    @property
    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    # ------------------------------------------------------------------
    # Worker loop
    # ------------------------------------------------------------------

    def _worker_loop(self) -> None:
        while not self._stop.is_set():
            try:
                task = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue
            self._handle(task)

    def _handle(self, task: BackgroundTask) -> None:
        task.status = "running"
        log.info("Processing background task %s (%s)", task.task_id, task.kind)
        try:
            result = self._process(task)
            task.result = result
            task.status = "done"
        except Exception as exc:
            log.error("Background task %s failed: %s", task.task_id, exc)
            task.error = str(exc)
            task.status = "failed"
        finally:
            self._queue.task_done()
            if self._on_task_complete:
                try:
                    self._on_task_complete(task)
                except Exception as exc:
                    log.warning("on_task_complete callback raised: %s", exc)

    def _process(self, task: BackgroundTask) -> Any:
        """Default handler — override in subclasses or patch for custom dispatch."""
        log.debug("Background task processed (stub): %s", task.kind)
        return {"dispatched": True, "kind": task.kind, "payload_keys": list(task.payload)}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

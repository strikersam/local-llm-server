"""Background dispatcher for task execution."""

from __future__ import annotations

import asyncio
import logging

from tasks.service import TaskExecutionCoordinator
from tasks.store import TaskStore, get_task_store

log = logging.getLogger("qwen-proxy")


class TaskDispatcher:
    """Polls for queued task work and executes it through the coordinator."""

    def __init__(
        self,
        *,
        workspace_root: str,
        poll_interval_s: float = 5.0,
        store: TaskStore | None = None,
        coordinator: TaskExecutionCoordinator | None = None,
    ) -> None:
        self.workspace_root = workspace_root
        self.poll_interval_s = poll_interval_s
        self.store = store or get_task_store()
        self.coordinator = coordinator or TaskExecutionCoordinator(store=self.store, workspace_root=workspace_root)
        self._stop = False

    async def run_forever(self) -> None:
        log.info(
            "TaskDispatcher started (poll_interval=%.1fs, workspace=%s)",
            self.poll_interval_s,
            self.workspace_root,
        )
        while not self._stop:
            try:
                await self._poll_and_execute()
            except Exception as exc:  # pragma: no cover - defensive loop logging
                log.error("TaskDispatcher error: %s", exc, exc_info=True)
            await asyncio.sleep(self.poll_interval_s)

    async def _poll_and_execute(self) -> None:
        tasks = await self.store.list_pending(limit=5)
        for task in tasks:
            await self._execute_task(task.task_id)

    async def _execute_task(self, task_id: str) -> None:
        log.info("Executing task %s", task_id)
        await self.coordinator.execute(task_id)

    def stop(self) -> None:
        self._stop = True
        log.info("TaskDispatcher stopped")

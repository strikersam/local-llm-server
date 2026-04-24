"""tasks/dispatcher.py — Background task dispatcher

Polls the task store for TODO tasks and submits them to the BackgroundAgent
for automatic execution by AgentRunner.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from agent.loop import AgentRunner
from tasks.store import get_task_store, TaskStatus

log = logging.getLogger("qwen-proxy")


class TaskDispatcher:
    """Polls task store and executes TODO tasks via AgentRunner."""

    def __init__(
        self,
        *,
        ollama_base: str,
        workspace_root: str,
        poll_interval_s: float = 5.0,
    ) -> None:
        self.ollama_base = ollama_base
        self.workspace_root = workspace_root
        self.poll_interval_s = poll_interval_s
        self._stop = False

    async def run_forever(self) -> None:
        """Poll and execute tasks indefinitely."""
        log.info(
            "TaskDispatcher started (poll_interval=%.1fs, workspace=%s)",
            self.poll_interval_s,
            self.workspace_root,
        )
        while not self._stop:
            try:
                await self._poll_and_execute()
            except Exception as exc:
                log.error("TaskDispatcher error: %s", exc, exc_info=True)
            await asyncio.sleep(self.poll_interval_s)

    async def _poll_and_execute(self) -> None:
        """Poll for TODO tasks and execute each one."""
        store = get_task_store()
        tasks = await store.list_all(status=TaskStatus.TODO, limit=5)

        if not tasks:
            return

        log.debug("Found %d TODO task(s)", len(tasks))
        for task in tasks:
            await self._execute_task(task)

    async def _execute_task(self, task: Any) -> None:
        """Execute a single task via AgentRunner."""
        log.info("Executing task %s: %s", task.task_id, task.title)

        task.status = TaskStatus.IN_PROGRESS
        await get_task_store().update(task)

        try:
            runner = AgentRunner(
                ollama_base=self.ollama_base,
                workspace_root=self.workspace_root,
            )
            result = await runner.run(
                instruction=task.prompt or task.title,
                history=[],
                requested_model=task.model_preference,
                auto_commit=True,
                max_steps=10,
                user_id=task.owner_id,
            )

            task.status = TaskStatus.DONE
            task.result = result.get("summary") or result
            log.info("Task %s completed: %s", task.task_id, result.get("summary"))

        except Exception as exc:
            log.error("Task %s failed: %s", task.task_id, exc, exc_info=True)
            task.status = TaskStatus.FAILED
            task.error = str(exc)

        await get_task_store().update(task)

    def stop(self) -> None:
        """Stop the dispatcher."""
        self._stop = True
        log.info("TaskDispatcher stopped")

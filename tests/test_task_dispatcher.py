from __future__ import annotations

import asyncio

import pytest

from tasks.dispatcher import TaskDispatcher
from tasks.models import Task


class _PendingStore:
    def __init__(self, tasks: list[Task]) -> None:
        self._tasks = tasks

    async def list_pending(self, *, limit: int = 50) -> list[Task]:
        return self._tasks[:limit]


class _BlockingCoordinator:
    def __init__(self, expected: int) -> None:
        self.expected = expected
        self.started: list[str] = []
        self.finished: list[str] = []
        self.release = asyncio.Event()
        self.all_started = asyncio.Event()

    async def execute(self, task_id: str):
        self.started.append(task_id)
        if len(self.started) >= self.expected:
            self.all_started.set()
        await self.release.wait()
        self.finished.append(task_id)


@pytest.mark.asyncio
async def test_dispatcher_executes_pending_tasks_concurrently() -> None:
    pending = [
        Task(owner_id="owner@example.com", task_id=f"task-{idx}", title=f"Task {idx}")
        for idx in range(3)
    ]
    coordinator = _BlockingCoordinator(expected=len(pending))
    dispatcher = TaskDispatcher(
        workspace_root=".",
        store=_PendingStore(pending),
        coordinator=coordinator,
        max_concurrency=len(pending),
    )

    poll = asyncio.create_task(dispatcher._poll_and_execute())

    await asyncio.wait_for(coordinator.all_started.wait(), timeout=0.2)
    assert set(coordinator.started) == {task.task_id for task in pending}

    coordinator.release.set()
    await asyncio.wait_for(poll, timeout=0.2)
    assert set(coordinator.finished) == {task.task_id for task in pending}

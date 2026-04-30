from __future__ import annotations

import os

import pytest

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("JWT_SECRET", "test-secret-for-tests-only")
os.environ.setdefault("ADMIN_EMAIL", "admin@test.local")
os.environ.setdefault("ADMIN_PASSWORD", "TestPassword1!")

import backend.server as server  # noqa: E402


class _StubRuntimeRegistry:
    def ids(self) -> list[str]:
        return ["hermes"]


class _StubRuntimeManager:
    def __init__(self) -> None:
        self._registry = _StubRuntimeRegistry()
        self.started = 0
        self.stopped = 0

    async def start(self) -> None:
        self.started += 1

    async def stop(self) -> None:
        self.stopped += 1


class _StubTaskDispatcher:
    def __init__(self, *, workspace_root: str, poll_interval_s: float) -> None:
        self.workspace_root = workspace_root
        self.poll_interval_s = poll_interval_s
        self.stop_called = 0

    async def run_forever(self) -> None:
        return None

    def stop(self) -> None:
        self.stop_called += 1


class _StubTask:
    def __init__(self, coro) -> None:
        self._coro = coro
        self.cancel_called = 0

    def cancel(self) -> None:
        self.cancel_called += 1

    def __await__(self):
        return self._coro.__await__()


@pytest.mark.anyio
async def test_backend_lifespan_starts_runtime_manager_and_dispatcher(monkeypatch):
    manager = _StubRuntimeManager()
    dispatchers: list[_StubTaskDispatcher] = []
    created_tasks: list[_StubTask] = []

    async def fake_ensure_bootstrap() -> None:
        return None

    def fake_dispatcher(*, workspace_root: str, poll_interval_s: float) -> _StubTaskDispatcher:
        dispatcher = _StubTaskDispatcher(
            workspace_root=workspace_root,
            poll_interval_s=poll_interval_s,
        )
        dispatchers.append(dispatcher)
        return dispatcher

    def fake_create_task(coro):
        task = _StubTask(coro)
        created_tasks.append(task)
        return task

    monkeypatch.setattr(server, "ensure_bootstrap", fake_ensure_bootstrap)
    monkeypatch.setattr(server, "get_runtime_manager", lambda: manager)
    monkeypatch.setattr(server, "TaskDispatcher", fake_dispatcher)
    monkeypatch.setattr(server.asyncio, "create_task", fake_create_task)

    lifecycle = server.lifespan(server.app)
    await lifecycle.__aenter__()

    assert manager.started == 1
    assert len(dispatchers) == 1
    assert dispatchers[0].workspace_root == str(server.ROOT_DIR)
    assert dispatchers[0].poll_interval_s == 10.0
    assert len(created_tasks) == 1

    await lifecycle.__aexit__(None, None, None)

    assert dispatchers[0].stop_called == 1
    assert created_tasks[0].cancel_called == 1
    assert manager.stopped == 1

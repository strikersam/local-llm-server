from __future__ import annotations

from types import SimpleNamespace

import pytest

from runtimes.control import start_runtime, stop_runtime


class _StubManager:
    def __init__(self, available: bool) -> None:
        self.available = available

    def get_runtime(self, runtime_id: str):
        return {
            "runtime_id": runtime_id,
            "health": {
                "runtime_id": runtime_id,
                "available": self.available,
            },
        }


@pytest.mark.anyio
async def test_start_runtime_returns_remote_managed_when_runtime_is_reachable(monkeypatch):
    def fake_run(*args, **kwargs):
        raise FileNotFoundError()

    monkeypatch.setattr("runtimes.control.subprocess.run", fake_run)
    monkeypatch.setattr("runtimes.control.get_runtime_manager", lambda: _StubManager(True))

    result = await start_runtime("hermes")

    assert result["status"] == "remote_managed"
    assert result["remote_managed"] is True


@pytest.mark.anyio
async def test_stop_runtime_returns_remote_managed_on_remote_only_docker_error(monkeypatch):
    def fake_run(*args, **kwargs):
        raise __import__("subprocess").CalledProcessError(
            1,
            args[0],
            stderr=b"Docker lifecycle control is only available when running locally",
        )

    monkeypatch.setattr("runtimes.control.subprocess.run", fake_run)
    monkeypatch.setattr("runtimes.control.get_runtime_manager", lambda: _StubManager(True))

    result = await stop_runtime("hermes")

    assert result["status"] == "remote_managed"
    assert result["remote_managed"] is True
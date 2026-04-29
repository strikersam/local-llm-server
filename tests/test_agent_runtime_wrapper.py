from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient


def _load_agent_runtime_module():
    module_path = Path(__file__).resolve().parent.parent / "docker" / "agent_runtime.py"
    spec = importlib.util.spec_from_file_location("test_agent_runtime_wrapper_module", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_wrapper_exposes_hermes_task_endpoints(monkeypatch):
    module = _load_agent_runtime_module()

    async def fake_chat_with_ollama(**kwargs):
        return {"message": {"content": "runtime ok"}}, kwargs["model"]

    monkeypatch.setattr(module, "_chat_with_ollama", fake_chat_with_ollama)
    module.TASK_RESULTS.clear()

    client = TestClient(module.app)
    response = client.post(
        "/tasks",
        json={
            "task_id": "task-123",
            "instruction": "Verify runtime execution",
            "model": "qwen3-coder:30b",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "done"
    assert response.json()["output"] == "runtime ok"

    lookup = client.get("/tasks/task-123")
    assert lookup.status_code == 200
    assert lookup.json()["output"] == "runtime ok"


def test_wrapper_exposes_opencode_run_endpoint(monkeypatch):
    module = _load_agent_runtime_module()

    async def fake_chat_with_ollama(**kwargs):
        return {"message": {"content": "run ok"}}, kwargs["model"]

    monkeypatch.setattr(module, "_chat_with_ollama", fake_chat_with_ollama)
    module.TASK_RESULTS.clear()

    client = TestClient(module.app)
    response = client.post(
        "/run",
        json={
            "instruction": "Summarize the repo",
            "model": "qwen3-coder:30b",
            "task_id": "run-123",
        },
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["output"] == "run ok"
    assert module.TASK_RESULTS["run-123"]["output"] == "run ok"


def test_wrapper_falls_back_to_installed_model(monkeypatch):
    module = _load_agent_runtime_module()

    class _FakeResponse:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self._payload = payload
            self.text = str(payload)

        def json(self):
            return self._payload

        def raise_for_status(self):
            if self.status_code >= 400:
                raise module.httpx.HTTPStatusError(
                    "error",
                    request=None,
                    response=self,
                )

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            self.post_calls = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url):
            assert url.endswith("/api/tags")
            if "host.docker.internal" in url:
                return _FakeResponse(
                    200,
                    {"models": [{"name": "gemma4:latest"}]},
                )
            return _FakeResponse(200, {"models": []})

        async def post(self, url, json):
            self.post_calls += 1
            if self.post_calls == 1:
                return _FakeResponse(404, {"error": "model not found"})
            assert json["model"] == "gemma4:latest"
            return _FakeResponse(200, {"message": {"content": "fallback ok"}})

    monkeypatch.setattr(module.httpx, "AsyncClient", _FakeClient)

    data, model = asyncio.run(
        module._chat_with_ollama(
            instruction="hello",
            model="qwen3-coder:30b",
        )
    )

    assert model == "gemma4:latest"
    assert data["message"]["content"] == "fallback ok"

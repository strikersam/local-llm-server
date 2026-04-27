from __future__ import annotations

# Regression tests for docker-compose validation and /agent/coordinate API compatibility.
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import proxy

ROOT = Path(__file__).resolve().parents[1]


def _auth_override() -> proxy.AuthContext:
    return proxy.AuthContext(
        key="test-key",
        email="tester@example.com",
        department="engineering",
        key_id="kid_test",
        source="legacy",
    )


def test_docker_compose_yaml_is_valid_and_has_expected_healthchecks() -> None:
    yaml = pytest.importorskip("yaml")
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    assert isinstance(compose, dict)
    assert "services" in compose

    services = compose["services"]
    ollama_hc = services["ollama"]["healthcheck"]["test"]
    # Accept both the legacy ["CMD", "ollama", "list"] format and the newer
    # CMD-SHELL curl-based format introduced for better Docker portability.
    if isinstance(ollama_hc, list):
        joined_hc = " ".join(ollama_hc)
    else:
        joined_hc = str(ollama_hc)
    assert "ollama" in joined_hc or "11434" in joined_hc, (
        f"Unexpected ollama healthcheck: {ollama_hc!r}"
    )

    proxy_health = services["proxy"]["healthcheck"]["test"]
    joined = (
        " ".join(proxy_health) if isinstance(proxy_health, list) else str(proxy_health)
    )
    assert "/live" in joined


def test_docker_compose_has_no_circular_depends_on() -> None:
    yaml = pytest.importorskip("yaml")
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    services: dict = compose.get("services", {})

    graph: dict[str, list[str]] = {}
    for service_name, service_cfg in services.items():
        deps = service_cfg.get("depends_on", {})
        if isinstance(deps, dict):
            graph[service_name] = list(deps.keys())
        elif isinstance(deps, list):
            graph[service_name] = deps
        else:
            graph[service_name] = []

    visiting: set[str] = set()
    visited: set[str] = set()

    def _visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for nxt in graph.get(node, []):
            if nxt in graph and _visit(nxt):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    has_cycle = any(_visit(node) for node in graph)
    assert has_cycle is False


def test_coordinate_dependency_aware_tasks_succeed_with_dependencies(monkeypatch):
    class FakeRunner:
        def __init__(self, **kwargs):
            pass

        async def run(self, **kwargs):
            return {
                "goal": kwargs["instruction"],
                "plan": {"goal": kwargs["instruction"], "steps": []},
                "steps": [],
                "commits": [],
                "summary": f"ok:{kwargs['instruction']}",
            }

    monkeypatch.setattr("agent.coordinator.AgentRunner", FakeRunner)
    proxy.app.dependency_overrides[proxy.verify_api_key] = _auth_override
    client = TestClient(proxy.app)

    resp = client.post(
        "/agent/coordinate",
        json={
            "goal": "ship feature",
            "max_concurrent": 2,
            "agents": [
                {"agent_id": "planner", "capabilities": ["planning", "general"]},
                {"agent_id": "coder", "capabilities": ["code"]},
            ],
            "tasks": [
                {
                    "task_id": "plan",
                    "instruction": "plan first",
                    "task_type": "planning",
                },
                {
                    "task_id": "code",
                    "instruction": "code second",
                    "task_type": "code",
                    "dependencies": ["plan"],
                },
            ],
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert [w["status"] for w in data["workers"]] == ["ok", "ok"]
    proxy.app.dependency_overrides.clear()


def test_coordinate_dependency_aware_tasks_block_missing_dependencies():
    proxy.app.dependency_overrides[proxy.verify_api_key] = _auth_override
    client = TestClient(proxy.app)

    resp = client.post(
        "/agent/coordinate",
        json={
            "goal": "ship feature",
            "agents": [{"agent_id": "worker", "capabilities": ["general"]}],
            "tasks": [
                {
                    "task_id": "blocked",
                    "instruction": "cannot run",
                    "dependencies": ["missing"],
                }
            ],
        },
    )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["workers"][0]["status"] == "blocked"
    assert "missing" in payload["workers"][0]["error"]
    proxy.app.dependency_overrides.clear()


def test_coordinate_legacy_workers_flow_remains_backward_compatible(monkeypatch):
    class _Result:
        def as_dict(self):
            return {
                "goal": "legacy",
                "workers": [{"worker_id": "w1", "status": "ok"}],
                "completed_at": "2026-01-01T00:00:00Z",
                "total_duration_s": 0.1,
                "summary": "legacy-ok",
            }

    class _Coordinator:
        async def run(
            self,
            goal,
            specs,
            max_concurrent=3,
            email=None,
            department=None,
            key_id=None,
        ):
            assert goal == "legacy"
            assert len(specs) == 1
            assert specs[0].instruction == "do legacy work"
            return _Result()

    monkeypatch.setattr(proxy, "COORDINATOR", _Coordinator())
    proxy.app.dependency_overrides[proxy.verify_api_key] = _auth_override
    client = TestClient(proxy.app)

    resp = client.post(
        "/agent/coordinate",
        json={
            "goal": "legacy",
            "workers": [
                {"worker_id": "w1", "instruction": "do legacy work", "max_steps": 2}
            ],
        },
    )

    assert resp.status_code == 200
    assert resp.json()["summary"] == "legacy-ok"
    proxy.app.dependency_overrides.clear()

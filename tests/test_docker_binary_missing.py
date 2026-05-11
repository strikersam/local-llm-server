import asyncio
import pytest
from runtimes.adapters.docker_agent import DockerAgentAdapter


@pytest.mark.asyncio
async def test_docker_binary_missing(monkeypatch):
    import shutil
    monkeypatch.setattr(shutil, 'which', lambda name: None)
    adapter = DockerAgentAdapter()
    health = await adapter.health_check()
    assert health.available is False
    assert "docker" in (health.error or "").lower()

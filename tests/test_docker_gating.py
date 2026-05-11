import asyncio
import pytest
from runtimes.adapters.docker_agent import DockerAgentAdapter


@pytest.mark.asyncio
async def test_docker_health_unavailable(monkeypatch):
    # Simulate docker binary failing by making create_subprocess_exec return a proc with returncode != 0
    class FakeProc:
        def __init__(self):
            self.returncode = 1
            self._stdout = b""
            self._stderr = b"docker not found"
        async def communicate(self):
            """
            Return captured stdout and stderr bytes as a (stdout, stderr) tuple.
            
            Returns:
                tuple[bytes, bytes]: A 2-tuple where the first element is stdout bytes and the second element is stderr bytes.
            """
            return (self._stdout, self._stderr)

    async def fake_create(*args, **kwargs):
        """
        Create and return a fake subprocess-like object used for testing.
        
        Returns:
            FakeProc: An instance that mimics a subprocess with predefined `returncode`, `_stdout`, `_stderr`, and an async `communicate()` method. The function accepts any arguments but ignores them.
        """
        return FakeProc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)
    adapter = DockerAgentAdapter()
    health = await adapter.health_check()
    assert health.available is False
    assert health.runtime_id == adapter.RUNTIME_ID

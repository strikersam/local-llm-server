import asyncio
import pytest
from runtimes.adapters.docker_agent import DockerAgentAdapter


@pytest.mark.asyncio
async def test_docker_health_unavailable(monkeypatch):
    # Simulate docker binary failing by making create_subprocess_exec return a proc with returncode != 0
    class FakeProc:
        def __init__(self):
            """
            Initialize a fake subprocess result representing a failed Docker invocation.
            
            Sets:
                returncode (int): Exit code 1 indicating failure.
                _stdout (bytes): Empty standard output.
                _stderr (bytes): Standard error bytes containing b"docker not found".
            """
            self.returncode = 1
            self._stdout = b""
            self._stderr = b"docker not found"
        async def communicate(self):
            """
            Provide captured stdout and stderr from the fake subprocess.
            
            Returns:
                tuple[bytes, bytes]: A tuple (stdout, stderr) containing the subprocess output and error streams as raw bytes.
            """
            return (self._stdout, self._stderr)

    async def fake_create(*args, **kwargs):
        """
        Create and return a fake subprocess-like object that simulates a failed Docker process.
        
        The function ignores any positional or keyword arguments.
        
        Returns:
            FakeProc: A `FakeProc` instance with `returncode == 1` and an async `communicate()` that returns `(b'', b'docker not found')`.
        """
        return FakeProc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)
    adapter = DockerAgentAdapter()
    health = await adapter.health_check()
    assert health.available is False
    assert health.runtime_id == adapter.RUNTIME_ID

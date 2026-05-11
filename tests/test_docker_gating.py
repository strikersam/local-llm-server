import asyncio
import pytest
from runtimes.adapters.docker_agent import DockerAgentAdapter


@pytest.mark.asyncio
async def test_docker_health_unavailable(monkeypatch):
    # Simulate docker binary failing by making create_subprocess_exec return a proc with returncode != 0
    import shutil
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/docker" if cmd == "docker" else None)

    class FakeProc:
        def __init__(self):
            """
            Create a fake subprocess result that simulates a failed Docker invocation.
            
            Sets the following attributes:
            - returncode: 1 (indicates failure)
            - _stdout: b"" (empty standard output)
            - _stderr: b"docker not found" (standard error bytes)
            """
            self.returncode = 1
            self._stdout = b""
            self._stderr = b"docker not found"
        async def communicate(self):
            """
            Return captured stdout and stderr from the fake subprocess.
            
            Returns:
                tuple[bytes, bytes]: A tuple (stdout, stderr) containing the subprocess output and error streams as raw bytes.
            """
            return (self._stdout, self._stderr)

    async def fake_create(*args, **kwargs):
        """
        Create and return a fake subprocess-like object that simulates a failed Docker process.
        
        This function ignores all positional and keyword arguments and returns a FakeProc instance whose
        `returncode` is 1 and whose async `communicate()` method returns `(b'', b'docker not found')`.
        
        Returns:
            FakeProc: A subprocess-like object representing a failed Docker invocation.
        """
        return FakeProc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)
    adapter = DockerAgentAdapter()
    health = await adapter.health_check()
    assert health.available is False
    assert health.runtime_id == adapter.RUNTIME_ID

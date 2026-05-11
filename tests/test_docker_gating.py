import asyncio
import pytest
from runtimes.adapters.docker_agent import DockerAgentAdapter


@pytest.mark.asyncio
async def test_docker_health_available(monkeypatch):
    """
    Verify that DockerAgentAdapter reports Docker as available when the 'docker' executable is present and a `docker version` subprocess exits successfully.
    """
    import shutil
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/docker" if cmd == "docker" else None)

    class FakeProc:
        returncode = 0
        async def communicate(self):
            """
            Simulate a subprocess's communicate() result that reports a Docker version.
            
            Returns:
                tuple[bytes, bytes]: (stdout, stderr) where stdout is b"Docker version 24.0.0" and stderr is b"".
            """
            return b"Docker version 24.0.0", b""

    async def fake_create(*args, **kwargs):
        """
        Return a fake subprocess-like object used to simulate asyncio.create_subprocess_exec in tests.
        
        Returns:
            FakeProc: Instance with a `returncode` attribute and an async `communicate()` method.
        """
        return FakeProc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)
    adapter = DockerAgentAdapter()
    health = await adapter.health_check()
    assert health.available is True
    assert health.runtime_id == adapter.RUNTIME_ID
    # details should contain the configured image
    assert "image" in health.details


@pytest.mark.asyncio
async def test_docker_health_available_reports_image_in_details(monkeypatch):
    """details['image'] reflects the configured docker image."""
    import shutil
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/docker")

    class FakeProc:
        returncode = 0
        async def communicate(self):
            """
            Return empty stdout and stderr for a fake subprocess communicate call.
            
            Returns:
                tuple(bytes, bytes): A tuple `(stdout, stderr)` where both elements are empty `bytes` objects.
            """
            return b"", b""

    async def fake_create(*args, **kwargs):
        """
        Return a fake subprocess-like object used to simulate asyncio.create_subprocess_exec in tests.
        
        Returns:
            FakeProc: Instance with a `returncode` attribute and an async `communicate()` method.
        """
        return FakeProc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)
    custom_image = "my-custom-runtime:v2"
    adapter = DockerAgentAdapter(config={"image": custom_image})
    health = await adapter.health_check()
    assert health.available is True
    assert health.details.get("image") == custom_image


@pytest.mark.asyncio
async def test_docker_health_exception_returns_unavailable(monkeypatch):
    """
    Verify that DockerAgentAdapter.health_check marks Docker unavailable and records an error when subprocess creation raises an exception.
    
    This test monkeypatches shutil.which to simulate the docker binary being present and replaces asyncio.create_subprocess_exec with a coroutine that raises OSError("subprocess spawn failed"). It then asserts that the returned health object has available == False and an error set.
    """
    import shutil
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/docker")

    async def fake_create(*args, **kwargs):
        """
        Mock async subprocess creator that always raises an OSError to simulate a subprocess spawn failure.
        
        Raises:
            OSError: Always raised with message "subprocess spawn failed" to indicate the subprocess could not be spawned.
        """
        raise OSError("subprocess spawn failed")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)
    adapter = DockerAgentAdapter()
    health = await adapter.health_check()
    assert health.available is False
    assert health.error is not None


@pytest.mark.asyncio
async def test_docker_health_unavailable(monkeypatch):
    # Simulate docker binary failing by making create_subprocess_exec return a proc with returncode != 0
    import shutil
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/docker" if cmd == "docker" else None)

    class FakeProc:
        def __init__(self):
            """
            Initialize a fake subprocess result representing a failed Docker invocation.
            
            Sets attributes:
                returncode: 1 (failure)
                _stdout: b""
                _stderr: b"docker not found"
            """
            self.returncode = 1
            self._stdout = b""
            self._stderr = b"docker not found"
        async def communicate(self):
            """
            Return captured stdout and stderr from the fake subprocess.
            
            Returns:
                tuple[bytes, bytes]: (stdout, stderr) as raw bytes.
            """
            return (self._stdout, self._stderr)

    async def fake_create(*args, **kwargs):
        """
        Create a fake subprocess-like object that simulates a Docker process failure.
        
        Returns:
            FakeProc: Instance whose `returncode` is 1 and whose async `communicate()` returns `(b'', b'docker not found')`.
        """
        return FakeProc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)
    adapter = DockerAgentAdapter()
    health = await adapter.health_check()
    assert health.available is False
    assert health.runtime_id == adapter.RUNTIME_ID

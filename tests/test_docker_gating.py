import asyncio
import pytest
from runtimes.adapters.docker_agent import DockerAgentAdapter


@pytest.mark.asyncio
async def test_docker_health_available(monkeypatch):
    """When docker binary is found and 'docker version' returns 0, health is available=True."""
    import shutil
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/docker" if cmd == "docker" else None)

    class FakeProc:
        returncode = 0
        async def communicate(self):
            return b"Docker version 24.0.0", b""

    async def fake_create(*args, **kwargs):
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
            return b"", b""

    async def fake_create(*args, **kwargs):
        return FakeProc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)
    custom_image = "my-custom-runtime:v2"
    adapter = DockerAgentAdapter(config={"image": custom_image})
    health = await adapter.health_check()
    assert health.available is True
    assert health.details.get("image") == custom_image


@pytest.mark.asyncio
async def test_docker_health_exception_returns_unavailable(monkeypatch):
    """If create_subprocess_exec raises, health_check returns available=False."""
    import shutil
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/docker")

    async def fake_create(*args, **kwargs):
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

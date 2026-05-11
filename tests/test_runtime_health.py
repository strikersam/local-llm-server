from __future__ import annotations

import asyncio
import pytest

from runtimes.adapters.internal_agent import InternalAgentAdapter


def test_internal_agent_health_reports_unavailable_when_ollama_unreachable(monkeypatch):
    # Ensure no NVIDIA key present
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("NVidiaApiKey", raising=False)
    # Point OLLAMA_BASE to a localhost URL that will not respond in tests
    monkeypatch.setenv("OLLAMA_BASE", "http://127.0.0.1:59999")

    # Force httpx.get to raise to simulate unreachable service
    import httpx

    def fake_get(url, timeout=1.0):
        """
        Simulates an HTTP GET request that always fails with a connection error.
        
        Parameters:
            url (str): The target URL for the simulated request.
            timeout (float): The request timeout in seconds (ignored).
        
        Raises:
            httpx.ConnectError: Always raised to simulate a failed connection.
        """
        raise httpx.ConnectError("failed to connect")

    monkeypatch.setattr(httpx, "get", fake_get)

    adapter = InternalAgentAdapter(config={})
    result = asyncio.run(adapter.health_check())
    assert result.available is False
    assert (result.error and "Ollama" in result.error) or (result.details is not None)


@pytest.mark.asyncio
async def test_internal_agent_health_available_with_nvidia_key(monkeypatch):
    """When NVIDIA_API_KEY is set, health_check returns available=True with nvidia-nim provider."""
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-FAKE_KEY")
    monkeypatch.delenv("NVidiaApiKey", raising=False)

    adapter = InternalAgentAdapter(config={})
    result = await adapter.health_check()
    assert result.available is True
    assert result.runtime_id == "internal_agent"
    assert result.details.get("provider") == "nvidia-nim"


@pytest.mark.asyncio
async def test_internal_agent_health_available_when_ollama_reachable(monkeypatch):
    """When no NVIDIA key but Ollama responds 200, health_check returns available=True."""
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("NVidiaApiKey", raising=False)
    monkeypatch.setenv("OLLAMA_BASE", "http://127.0.0.1:11434")

    import httpx

    class FakeResponse:
        status_code = 200

    class FakeAsyncClient:
        async def __aenter__(self):
            """
            Enter the asynchronous context manager and make the adapter available to the surrounding `async with` block.
            
            Returns:
                self: The adapter instance to be used inside the `async with` block.
            """
            return self
        async def __aexit__(self, *args):
            """
            Async context manager exit hook that performs no cleanup.
            
            Does nothing and does not suppress exceptions raised within the context.
            """
            pass
        async def get(self, url, timeout=None):
            """
            Return a FakeResponse that simulates the result of an HTTP GET request.
            
            Parameters:
                url (str): The request URL (ignored by the fake client).
                timeout (float | None): Optional request timeout in seconds (ignored by the fake client).
            
            Returns:
                FakeResponse: A fake response object representing the HTTP GET result.
            """
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", lambda: FakeAsyncClient())
    adapter = InternalAgentAdapter(config={})
    result = await adapter.health_check()
    assert result.available is True
    assert result.details.get("provider") == "ollama"


@pytest.mark.asyncio
async def test_internal_agent_health_unavailable_error_message(monkeypatch):
    """When Ollama probe fails, error message contains 'Ollama'."""
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("NVidiaApiKey", raising=False)
    monkeypatch.setenv("OLLAMA_BASE", "http://127.0.0.1:59999")

    import httpx

    class FakeAsyncClient:
        async def __aenter__(self):
            """
            Enter the asynchronous context manager and make the adapter available to the surrounding `async with` block.
            
            Returns:
                self: The adapter instance to be used inside the `async with` block.
            """
            return self
        async def __aexit__(self, *args):
            """
            Async context manager exit hook that performs no cleanup.
            
            Does nothing and does not suppress exceptions raised within the context.
            """
            pass
        async def get(self, url, timeout=None):
            """
            Simulated HTTP GET that always fails with a connection error to emulate an unreachable service.
            
            Parameters:
                url (str): The request URL that would be contacted.
                timeout (float | None): Optional request timeout in seconds.
            
            Raises:
                httpx.ConnectError: Always raised with message "refused" to simulate a refused connection.
            """
            raise httpx.ConnectError("refused")

    monkeypatch.setattr(httpx, "AsyncClient", lambda: FakeAsyncClient())
    adapter = InternalAgentAdapter(config={})
    result = await adapter.health_check()
    assert result.available is False
    assert result.error is not None
    assert "Ollama" in result.error


def test_internal_agent_required_dependencies_no_harness(monkeypatch):
    """When task harness is not required, required_dependencies returns empty list."""
    monkeypatch.delenv("TASK_HARNESS_REQUIRED", raising=False)
    adapter = InternalAgentAdapter(config={"task_harness_required": False})
    deps = adapter.required_dependencies()
    assert deps == []


def test_internal_agent_required_dependencies_with_harness(monkeypatch):
    """When task harness is required, required_dependencies returns a list with one dep."""
    adapter = InternalAgentAdapter(config={"task_harness_required": True})
    deps = adapter.required_dependencies()
    assert len(deps) == 1
    assert deps[0].name == "task-harness"
    assert deps[0].config_var == "TASK_HARNESS_BIN"


def test_internal_agent_required_dependencies_env_var(monkeypatch):
    """TASK_HARNESS_REQUIRED env var controls dependency list."""
    monkeypatch.setenv("TASK_HARNESS_REQUIRED", "true")
    adapter = InternalAgentAdapter(config={})
    deps = adapter.required_dependencies()
    assert len(deps) == 1

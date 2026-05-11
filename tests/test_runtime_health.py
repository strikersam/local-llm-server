from __future__ import annotations

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
        Simulates an HTTP GET that always fails to connect.
        
        This helper is intended for tests: calling it raises an httpx.ConnectError to emulate an unreachable HTTP service.
        
        Parameters:
            url (str): The requested URL (ignored; included for signature compatibility).
            timeout (float): Request timeout in seconds (ignored).
        
        Raises:
            httpx.ConnectError: Always raised with message "failed to connect".
        """
        raise httpx.ConnectError("failed to connect")

    monkeypatch.setattr(httpx, "get", fake_get)

    adapter = InternalAgentAdapter(config={})
    import asyncio
    result = asyncio.run(adapter.health_check())
    assert result.available is False
    assert (result.error and "Ollama" in result.error) or (result.details is not None)

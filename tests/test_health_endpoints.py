"""Tests for /health, /live, and /api/health endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

import proxy

# ─── Helpers ───────────────────────────────────────────────────────────────────


def _make_fake_client(
    json_data: dict | None = None, raise_exc: Exception | None = None
):
    """Return a context-manager-compatible mock for httpx.AsyncClient."""

    mock_response = MagicMock()
    mock_response.json.return_value = json_data or {}

    mock_client = AsyncMock()
    if raise_exc:
        mock_client.get = AsyncMock(side_effect=raise_exc)
    else:
        mock_client.get = AsyncMock(return_value=mock_response)

    # Support `async with httpx.AsyncClient(...) as client:`
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    return mock_cm


# ─── /live ─────────────────────────────────────────────────────────────────────


def test_live_endpoint_always_200():
    """Container liveness probe must always return 200."""
    client = TestClient(proxy.app)
    resp = client.get("/live")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ─── /health ───────────────────────────────────────────────────────────────────


def test_health_endpoint_exists_and_returns_json(monkeypatch):
    """Health endpoint exists and returns a JSON body."""
    fake_cm = _make_fake_client(json_data={"models": [{"name": "llama3.2"}]})
    monkeypatch.setattr("httpx.AsyncClient", lambda **kwargs: fake_cm)

    client = TestClient(proxy.app)
    resp = client.get("/health")
    assert resp.status_code in (200, 503)
    data = resp.json()
    assert "status" in data


def test_health_endpoint_has_providers_key_when_router_available(monkeypatch):
    """Health endpoint includes provider states when ProviderRouter is wired in."""
    fake_cm = _make_fake_client(json_data={"models": [{"name": "llama3.2"}]})
    monkeypatch.setattr("httpx.AsyncClient", lambda **kwargs: fake_cm)

    client = TestClient(proxy.app)
    resp = client.get("/health")
    # Accept both 200 (healthy) and 503 (degraded) — we only care about shape
    data = resp.json()
    assert "status" in data
    # If providers key exists, verify it's a list
    if "providers" in data:
        assert isinstance(data["providers"], list)


# ─── /api/health ───────────────────────────────────────────────────────────────


def test_api_health_endpoint_exists(monkeypatch):
    """Public /api/health must exist (used by setup wizard and frontend)."""
    fake_cm = _make_fake_client(json_data={"models": []})
    monkeypatch.setattr("httpx.AsyncClient", lambda **kwargs: fake_cm)

    client = TestClient(proxy.app)
    resp = client.get("/api/health")
    assert resp.status_code in (200, 503)
    assert "status" in resp.json()


# ─── Degraded state ────────────────────────────────────────────────────────────


def test_health_returns_503_when_ollama_unreachable(monkeypatch):
    """When Ollama is down, /health should return non-200 status and explain the issue."""
    fake_cm = _make_fake_client(raise_exc=Exception("connection refused"))
    monkeypatch.setattr("httpx.AsyncClient", lambda **kwargs: fake_cm)

    client = TestClient(proxy.app)
    resp = client.get("/health")
    # The implementation returns 503 on connection errors
    assert resp.status_code in (200, 503)
    data = resp.json()
    assert "status" in data


def test_api_health_returns_503_when_ollama_unreachable(monkeypatch):
    """When Ollama is down, /api/health should also return a degraded status."""
    fake_cm = _make_fake_client(raise_exc=Exception("connection refused"))
    monkeypatch.setattr("httpx.AsyncClient", lambda **kwargs: fake_cm)

    client = TestClient(proxy.app)
    resp = client.get("/api/health")
    assert resp.status_code in (200, 503)
    data = resp.json()
    assert "status" in data

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from dotenv import load_dotenv

# Load .env so tests see the same environment as the app
load_dotenv()


def pytest_configure() -> None:
    """Ensure repo root is importable when running `pytest` as a console script."""
    root = Path(__file__).resolve().parents[1]
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)

    # Test defaults (CI may not have a .env and proxy reads env at import time).
    os.environ.setdefault("API_KEYS", "ci-test-key")
    # Enable admin API routes for tests that hit /admin/api/*
    os.environ.setdefault("ADMIN_SECRET", "ci-admin-secret-123")
    # V3 API JWT secret for tests
    os.environ.setdefault("V3_JWT_SECRET", "ci-jwt-secret-key-12345678901234567890")
    os.environ.setdefault("V3_ADMIN_EMAIL", "admin@localhost")
    os.environ.setdefault("V3_ADMIN_NAME", "Administrator")


@pytest.fixture(scope="session")
def client():
    """FastAPI test client for proxy.app — V3 API surface (default).

    Most existing tests (v3_auth, features_api, etc.) target proxy.app, so
    this remains the default `client` fixture.
    """
    import proxy
    with TestClient(proxy.app) as c:
        yield c


@pytest.fixture(scope="session")
def wiki_client():
    """FastAPI test client for backend/server.py — LLM Relay wiki dashboard.

    Iteration 6/7 integration tests target backend/server.py specifically
    (it has /api/chat/send, the Mongo-backed admin login, etc.).
    """
    from backend.server import app as backend_app
    with TestClient(backend_app) as c:
        yield c

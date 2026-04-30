from __future__ import annotations

import os

# Pin test credentials before load_dotenv() so the real .env cannot override
# these values during test runs. seed_admin will sync the DB to match.
os.environ.setdefault("ADMIN_EMAIL", "admin@llmrelay.local")
os.environ.setdefault("ADMIN_PASSWORD", "WikiAdmin2026!")
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

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
    os.environ.setdefault("JWT_SECRET", "ci-jwt-secret-key-12345678901234567890")
    os.environ.setdefault("V3_ADMIN_EMAIL", "admin@llmrelay.local")
    os.environ.setdefault("V3_ADMIN_NAME", "Administrator")


@pytest.fixture(autouse=True)
def reset_provider_cooldowns():
    """Reset cross-request provider cooldown state before every test.

    Without this, a test that triggers a provider failure (and thus a cooldown)
    would pollute subsequent tests that use the same provider_id.
    """
    from provider_router import clear_cooldowns

    clear_cooldowns()
    yield
    clear_cooldowns()


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

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


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


@pytest.fixture
def client() -> TestClient:
    """FastAPI test client for integration tests."""
    import proxy
    return TestClient(proxy.app)

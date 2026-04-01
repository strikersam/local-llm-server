from __future__ import annotations

import os
import sys
from pathlib import Path


# Test defaults (CI may not have a .env)
os.environ.setdefault("API_KEYS", "ci-test-key")
# Enable admin endpoints for tests that exercise /admin/api/*
os.environ.setdefault("ADMIN_SECRET", "ci-admin-secret-123")


def pytest_configure() -> None:
    """Ensure repo root is importable under pytest's importlib mode."""
    root = Path(__file__).resolve().parents[1]
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)

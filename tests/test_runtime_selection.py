from __future__ import annotations
import os
from runtimes.manager import get_runtime_manager


def test_default_preferred_runtime_is_internal(monkeypatch):
    # Ensure AGENT_MODE_DOCKER not set
    monkeypatch.delenv("AGENT_MODE_DOCKER", raising=False)
    monkeypatch.delenv("RUNTIME_DEFAULT", raising=False)
    mgr = get_runtime_manager()
    policy = mgr.get_policy()
    assert policy["preferred_runtime_id"] == "internal_agent"

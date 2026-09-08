"""tests/test_brain_config_store.py — BrainConfigStore unit tests.

Pins the contract from docs/plans/db-brain-switcher.md §4:

  * get/set round-trip — a PATCH'd config is returned by the next get.
  * Cache invalidation — invalidate() forces the next get to re-read.
  * Sqlite mirror — when Mongo is unavailable, the mirror serves reads.
  * Defaults — a fresh store returns the safe default (no DB doc yet).
  * Never raises — store errors fall back to the safe default.

All tests patch ``backend.server.get_db`` with a MagicMock so no live Mongo
is required. The sqlite mirror uses a temp ``SQLITE_DB_PATH`` so each test
gets a clean slate.
"""
from __future__ import annotations

import asyncio
import os
import sqlite3
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch as mock_patch

import pytest

from packages.ai.brain_config import (
    BrainConfig,
    BrainConfigPatch,
    BrainConfigStore,
    SAFE_DEFAULT_MODEL,
    default_brain_config,
    get_brain_config,
    invalidate_brain_config_cache,
    resolve_agent_generation_sync,
    resolve_role_model_sync,
    set_brain_config,
)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro) if asyncio.get_event_loop().is_running() else asyncio.run(coro)


@pytest.fixture(autouse=True)
def _isolated_store(monkeypatch, tmp_path):
    """Force a fresh BrainConfigStore singleton per test + a temp sqlite mirror."""
    import packages.ai.brain_config as mod
    monkeypatch.setattr(mod, "_store", None)
    monkeypatch.setenv("SQLITE_DB_PATH", str(tmp_path / "test.db"))
    # Clear env vars that would change role resolution.
    for v in ("AGENT_PLANNER_MODEL", "AGENT_EXECUTOR_MODEL", "AGENT_VERIFIER_MODEL", "AGENT_JUDGE_MODEL", "NVIDIA_DEFAULT_MODEL"):
        monkeypatch.delenv(v, raising=False)
    yield


# ── Defaults ────────────────────────────────────────────────────────────────


def test_get_returns_safe_default_when_no_doc(monkeypatch):
    """A fresh store with no Mongo doc and no mirror returns the safe default."""
    # No cloud provider keys present → the recommended-chain fallback resolves
    # to the safe NIM default (this test pins that floor deterministically).
    for env_var in ("CEREBRAS_API_KEY", "GROQ_API_KEY", "NVIDIA_API_KEY"):
        monkeypatch.delenv(env_var, raising=False)
    db = MagicMock()
    db.app_settings = MagicMock()
    db.app_settings.find_one = AsyncMock(return_value=None)

    with mock_patch("backend.server.get_db", return_value=db):
        cfg = asyncio.run(get_brain_config())

    assert cfg.primary_provider == "nvidia"
    assert cfg.planner_model == SAFE_DEFAULT_MODEL
    assert cfg.executor_model == SAFE_DEFAULT_MODEL
    assert cfg.verifier_model == SAFE_DEFAULT_MODEL
    assert cfg.judge_model == SAFE_DEFAULT_MODEL
    assert cfg.updated_at == ""  # never applied


def test_default_brain_config_is_safe():
    cfg = default_brain_config()
    assert cfg.primary_provider == "nvidia"
    # The safe default follows the catalogue; a literal here went stale when a
    # live probe proved z-ai/glm-5.2 dead on 2026-08-28.
    from packages.ai.brain_config import SAFE_DEFAULT_MODEL

    assert cfg.planner_model == SAFE_DEFAULT_MODEL


def test_recommended_config_prefers_nvidia_when_key_present(monkeypatch):
    """PR #1046: NVIDIA leads the priority chain. With an NVIDIA key set (and
    no saved doc), nvidia is the recommended provider — not cerebras."""
    from packages.ai.brain_config import PROVIDER_PRESETS, recommended_brain_config

    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test")
    monkeypatch.setenv("CEREBRAS_API_KEY", "csk-test")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    cfg = recommended_brain_config()
    assert cfg.primary_provider == "nvidia"
    assert cfg.planner_model == PROVIDER_PRESETS["nvidia"]["planner"]
    assert cfg.executor_model == PROVIDER_PRESETS["nvidia"]["executor"]


def test_recommended_config_priority_cerebras_without_nvidia(monkeypatch):
    """PR #1046: when no NVIDIA key, cerebras is next in the chain."""
    from packages.ai.brain_config import recommended_brain_config

    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.setenv("CEREBRAS_API_KEY", "csk-test")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    cfg = recommended_brain_config()
    assert cfg.primary_provider == "cerebras"


def test_recommended_config_falls_back_to_nvidia_default_with_no_cloud_keys(monkeypatch):
    """No cloud keys → the safe NIM default (never an unreachable local Ollama)."""
    from packages.ai.brain_config import recommended_brain_config

    for env_var in ("CEREBRAS_API_KEY", "GROQ_API_KEY", "NVIDIA_API_KEY"):
        monkeypatch.delenv(env_var, raising=False)
    cfg = recommended_brain_config()
    assert cfg.primary_provider == "nvidia"
    assert cfg.planner_model == SAFE_DEFAULT_MODEL


# ── Round-trip ──────────────────────────────────────────────────────────────


def test_set_then_get_round_trips(monkeypatch):
    """A PATCH persists + the next get returns the applied config."""
    captured = {}

    class _FakeCollection:
        async def find_one(self, q):
            return captured.get("doc")

        async def update_one(self, q, update, upsert=False):
            captured["doc"] = dict(update["$set"])
            captured["doc"]["_id"] = q["_id"]
            return SimpleNamespace(matched_count=1, upserted_id=None)

    db = MagicMock()
    db.app_settings = _FakeCollection()

    with mock_patch("backend.server.get_db", return_value=db):
        cfg_patch = BrainConfigPatch(
            primary_provider="cerebras",
            planner_model="qwen-3-coder-480b",
            executor_model="qwen-3-coder-480b",
            verifier_model="llama-3.3-70b",
            judge_model="llama-3.3-70b",
        )
        applied = asyncio.run(set_brain_config(cfg_patch, actor="admin@example.com"))
        # Invalidate cache to force a re-read.
        invalidate_brain_config_cache()
        got = asyncio.run(get_brain_config())

    assert applied.primary_provider == "cerebras"
    assert applied.planner_model == "qwen-3-coder-480b"
    assert applied.updated_by == "admin@example.com"
    assert applied.updated_at  # ISO timestamp
    assert got.primary_provider == applied.primary_provider
    assert got.planner_model == applied.planner_model
    assert got.updated_by == "admin@example.com"


def test_patch_merges_partial_update(monkeypatch):
    """A partial PATCH only touches the supplied fields; others stay."""
    existing_doc = {
        "_id": "brain_config",
        "primary_provider": "cerebras",
        "planner_model": "qwen-3-coder-480b",
        "executor_model": "qwen-3-coder-480b",
        "verifier_model": "llama-3.3-70b",
        "judge_model": "llama-3.3-70b",
        "max_tokens": 4096,
        "updated_at": "2026-06-26T00:00:00Z",
        "updated_by": "admin@example.com",
    }
    captured = {}

    class _FakeCollection:
        async def find_one(self, q):
            return captured.get("doc", existing_doc)

        async def update_one(self, q, update, upsert=False):
            captured["doc"] = dict(update["$set"])
            captured["doc"]["_id"] = q["_id"]
            return SimpleNamespace(matched_count=1, upserted_id=None)

    db = MagicMock()
    db.app_settings = _FakeCollection()

    with mock_patch("backend.server.get_db", return_value=db):
        # Only touch executor_model.
        cfg_patch = BrainConfigPatch(executor_model="llama-3.3-70b")
        applied = asyncio.run(set_brain_config(cfg_patch, actor="admin2@example.com"))

    assert applied.executor_model == "llama-3.3-70b"
    # Untouched fields preserved.
    assert applied.primary_provider == "cerebras"
    assert applied.planner_model == "qwen-3-coder-480b"
    assert applied.verifier_model == "llama-3.3-70b"
    assert applied.judge_model == "llama-3.3-70b"


# ── Agent generation params (max_tokens + request_timeout_sec) ───────────────


def test_generation_defaults_when_no_config(monkeypatch):
    """Cold cache + no env → safe defaults (4096 tokens, 120s)."""
    import packages.ai.brain_config as mod
    monkeypatch.setattr(mod, "_store", None)
    for v in ("AGENT_MAX_OUTPUT_TOKENS", "AGENT_REQUEST_TIMEOUT_SEC"):
        monkeypatch.delenv(v, raising=False)
    assert resolve_agent_generation_sync() == (4096, 120)


def test_generation_reads_env_on_cold_cache(monkeypatch):
    import packages.ai.brain_config as mod
    monkeypatch.setattr(mod, "_store", None)
    monkeypatch.setenv("AGENT_MAX_OUTPUT_TOKENS", "2048")
    monkeypatch.setenv("AGENT_REQUEST_TIMEOUT_SEC", "90")
    assert resolve_agent_generation_sync() == (2048, 90)


def test_generation_env_is_clamped(monkeypatch):
    import packages.ai.brain_config as mod
    monkeypatch.setattr(mod, "_store", None)
    monkeypatch.setenv("AGENT_MAX_OUTPUT_TOKENS", "999999")  # over cap → 32768
    monkeypatch.setenv("AGENT_REQUEST_TIMEOUT_SEC", "5")     # under floor → 15
    assert resolve_agent_generation_sync() == (32768, 15)


def test_generation_prefers_fresh_brainconfig_cache(monkeypatch):
    """A fresh BrainConfig cache wins over env — the UI value takes effect."""
    import time as _t
    import packages.ai.brain_config as mod
    store = BrainConfigStore()
    store._cache = BrainConfig(max_tokens=8000, request_timeout_sec=300)
    store._cache_at = _t.monotonic()
    monkeypatch.setattr(mod, "_store", store)
    monkeypatch.setenv("AGENT_MAX_OUTPUT_TOKENS", "2048")  # must be ignored
    assert resolve_agent_generation_sync() == (8000, 300)


def test_patch_round_trips_request_timeout_sec(monkeypatch):
    """The new UI field persists through a PATCH and is served on the next get."""
    existing_doc = {
        "_id": "brain_config",
        "primary_provider": "cerebras",
        "planner_model": "qwen-3-coder-480b",
        "executor_model": "qwen-3-coder-480b",
        "verifier_model": "llama-3.3-70b",
        "judge_model": "llama-3.3-70b",
        "max_tokens": 4096,
    }
    captured = {}

    class _FakeCollection:
        async def find_one(self, q):
            return captured.get("doc", existing_doc)

        async def update_one(self, q, update, upsert=False):
            captured["doc"] = dict(update["$set"])
            captured["doc"]["_id"] = q["_id"]
            return SimpleNamespace(matched_count=1, upserted_id=None)

    db = MagicMock()
    db.app_settings = _FakeCollection()
    with mock_patch("backend.server.get_db", return_value=db):
        applied = asyncio.run(
            set_brain_config(BrainConfigPatch(request_timeout_sec=240), actor="a@x.com")
        )
    assert applied.request_timeout_sec == 240
    assert applied.max_tokens == 4096  # untouched


# ── Cache invalidation ──────────────────────────────────────────────────────


def test_invalidate_forces_reread(monkeypatch):
    """invalidate() clears the cache so the next get re-reads from storage."""
    call_count = {"n": 0}

    class _FakeCollection:
        async def find_one(self, q):
            call_count["n"] += 1
            return None

    db = MagicMock()
    db.app_settings = _FakeCollection()

    with mock_patch("backend.server.get_db", return_value=db):
        asyncio.run(get_brain_config())
        asyncio.run(get_brain_config())  # cache hit — should NOT re-read
        invalidate_brain_config_cache()
        asyncio.run(get_brain_config())  # cache cleared — re-reads

    assert call_count["n"] == 2  # initial + post-invalidate


# ── Sqlite mirror ──────────────────────────────────────────────────────────


def test_sqlite_mirror_serves_when_mongo_unavailable(monkeypatch):
    """When Mongo raises, the sqlite mirror serves reads."""
    cfg = BrainConfig(
        primary_provider="groq",
        planner_model="groq-planner",
        executor_model="groq-executor",
        verifier_model="groq-verifier",
        judge_model="groq-judge",
        updated_at="2026-06-26T00:00:00Z",
        updated_by="mirror-test",
    )

    # Persist directly via the mirror.
    store = BrainConfigStore()
    store._save_sqlite_mirror(cfg)

    # Now make Mongo blow up.
    db = MagicMock()
    db.app_settings = MagicMock()
    db.app_settings.find_one = AsyncMock(side_effect=RuntimeError("mongo down"))

    with mock_patch("backend.server.get_db", return_value=db):
        got = asyncio.run(store.get_brain_config())

    assert got.primary_provider == "groq"
    assert got.planner_model == "groq-planner"
    assert got.updated_by == "mirror-test"


def test_sqlite_mirror_round_trips_through_set(monkeypatch, tmp_path):
    """set_brain_config writes to both Mongo AND the sqlite mirror."""
    # Isolate the sqlite mirror AND reset the module-level singleton so this
    # test does NOT pollute the production mirror (`.data/agency.db_brain.db`)
    # or leak a cached config with ``updated_at`` set into later tests.
    import packages.ai.brain_config as _bcs
    monkeypatch.setattr(_bcs, "_store", None)
    monkeypatch.setenv("SQLITE_DB_PATH", str(tmp_path / "test.db"))

    class _FakeCollection:
        async def find_one(self, q):
            return None

        async def update_one(self, q, update, upsert=False):
            return SimpleNamespace(matched_count=1, upserted_id=None)

    db = MagicMock()
    db.app_settings = _FakeCollection()

    with mock_patch("backend.server.get_db", return_value=db):
        asyncio.run(set_brain_config(
            BrainConfigPatch(primary_provider="ollama", executor_model="qwen3-coder:30b"),
            actor="test",
        ))
        invalidate_brain_config_cache()
        # Now Mongo goes away — sqlite mirror must still serve.
        db2 = MagicMock()
        db2.app_settings = MagicMock()
        db2.app_settings.find_one = AsyncMock(side_effect=RuntimeError("mongo down"))
        with mock_patch("backend.server.get_db", return_value=db2):
            got = asyncio.run(get_brain_config())

    assert got.primary_provider == "ollama"
    assert got.executor_model == "qwen3-coder:30b"


# ── Never raises ────────────────────────────────────────────────────────────


def test_get_never_raises_on_total_failure(monkeypatch):
    """If both Mongo AND sqlite fail, the store returns the safe default."""
    # Clear cloud provider keys so the recommended chain falls to the safe default.
    for env_var in ("CEREBRAS_API_KEY", "GROQ_API_KEY", "NVIDIA_API_KEY"):
        monkeypatch.delenv(env_var, raising=False)

    db = MagicMock()
    db.app_settings = MagicMock()
    db.app_settings.find_one = AsyncMock(side_effect=RuntimeError("mongo down"))

    # Point sqlite path at a non-existent directory we can't write to.
    monkeypatch.setattr(
        "packages.ai.brain_config.BrainConfigStore._mirror_db_path",
        lambda self: "/nonexistent-dir/test.db",
    )

    with mock_patch("backend.server.get_db", return_value=db):
        cfg = asyncio.run(get_brain_config())

    assert cfg.primary_provider == "nvidia"
    assert cfg.planner_model == SAFE_DEFAULT_MODEL


# ── Role resolver ───────────────────────────────────────────────────────────


def test_resolve_role_model_precedence_requested_wins(monkeypatch):
    """An explicit ``requested`` value always wins."""
    assert resolve_role_model_sync("planner", "custom-model") == "custom-model"


def test_resolve_role_model_precedence_env_var(monkeypatch):
    """With no cache and no requested, the env var wins."""
    monkeypatch.setenv("AGENT_PLANNER_MODEL", "env-planner")
    invalidate_brain_config_cache()
    assert resolve_role_model_sync("planner") == "env-planner"


def test_resolve_role_model_precedence_safe_default(monkeypatch):
    """With nothing set, the safe default is returned."""
    invalidate_brain_config_cache()
    assert resolve_role_model_sync("executor") == SAFE_DEFAULT_MODEL


def test_resolve_role_model_db_overrides_env(monkeypatch):
    """A DB-stored config (cache fresh) wins over the env var."""
    monkeypatch.setenv("AGENT_PLANNER_MODEL", "env-planner")
    # Prime the cache with a DB config.
    import packages.ai.brain_config as mod
    cfg = BrainConfig(
        primary_provider="cerebras",
        planner_model="db-planner",
        executor_model="db-executor",
        verifier_model="db-verifier",
        judge_model="db-judge",
        updated_at="2026-06-26T00:00:00Z",
        updated_by="test",
    )
    if mod._store is None:
        mod._store = BrainConfigStore()
    mod._store._cache = cfg
    # Monotonic time so the cache is considered fresh.
    import time
    mod._store._cache_at = time.monotonic()

    assert resolve_role_model_sync("planner") == "db-planner"
    assert resolve_role_model_sync("executor") == "db-executor"

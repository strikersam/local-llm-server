"""Ollama model availability check with TTL cache.

Keeps a short-lived cache of which models are currently loaded in Ollama so the
router can skip models that aren't available instead of forwarding a request that
will fail.

The check is synchronous and uses a TTL cache (default 60 s) so most calls
return immediately from memory.  A stale or failed check returns an empty set
which disables availability filtering — routing continues normally.

Configuration:
    ROUTER_HEALTH_CHECK_ENABLED  true/false  (default: true)
    ROUTER_HEALTH_CACHE_TTL      seconds     (default: 60)
    OLLAMA_BASE / OLLAMA_BASE_URL base URL  (default: http://localhost:11434)
    ROUTER_HEALTH_CONNECT_TIMEOUT seconds   (default: 10 — time to wait for Ollama to accept TCP;
                                              raise when loading large models)
"""

from __future__ import annotations

import logging
import os
import time

import httpx

log = logging.getLogger("qwen-proxy")

# ── Cache ─────────────────────────────────────────────────────────────────────

_cache_ts: float = 0.0
_cache_models: set[str] = set()
_SENTINEL = object()          # marks "never fetched" vs "fetched empty"
_ever_fetched: bool = False


def _ttl() -> float:
    try:
        return float(os.environ.get("ROUTER_HEALTH_CACHE_TTL") or "60")
    except ValueError:
        return 60.0


def _enabled() -> bool:
    return os.environ.get("ROUTER_HEALTH_CHECK_ENABLED", "true").strip().lower() in (
        "1", "true", "yes",
    )


def get_available_models() -> set[str]:
    """Return the set of model names currently present in Ollama.

    Returns an empty set when:
    - health checks are disabled (``ROUTER_HEALTH_CHECK_ENABLED=false``)
    - Ollama is unreachable (silently degrades — routing still works)

    An empty return value means "no availability filtering" — the router
    treats all registered models as candidates.
    """
    global _cache_ts, _cache_models, _ever_fetched

    if not _enabled():
        return set()

    now = time.monotonic()
    if _ever_fetched and (now - _cache_ts) < _ttl():
        return _cache_models

    base = (
        os.environ.get("OLLAMA_BASE")
        or os.environ.get("OLLAMA_BASE_URL")
        or "http://localhost:11434"
    ).rstrip("/")
    try:
        connect_timeout = float(os.environ.get("ROUTER_HEALTH_CONNECT_TIMEOUT") or "10")
    except ValueError:
        connect_timeout = 10.0
    try:
        with httpx.Client(timeout=httpx.Timeout(connect_timeout + 5.0, connect=connect_timeout)) as client:
            resp = client.get(f"{base}/api/tags")
            resp.raise_for_status()
            data = resp.json()

        names: set[str] = set()
        for m in data.get("models") or []:
            if isinstance(m, dict):
                name = m.get("name") or ""
                if name:
                    names.add(name)
                    # Also add the short name without digest tag, e.g. "qwen3-coder:30b"
                    # Ollama sometimes returns "qwen3-coder:30b-q4_K_M"; keep base tag too
                    tag_colon = name.rfind(":")
                    if tag_colon != -1:
                        base_tag = name[:tag_colon]
                        names.add(base_tag)

        _cache_models = names
        _cache_ts = now
        _ever_fetched = True
        log.debug("Health check: %d models available in Ollama", len(names))
        return names

    except Exception as exc:
        log.debug("Ollama health check skipped (%s) — availability filtering disabled", exc)
        # Don't overwrite a good cached value with a failure
        if _ever_fetched:
            return _cache_models
        return set()


def invalidate_cache() -> None:
    """Force the next call to re-probe Ollama (useful in tests)."""
    global _ever_fetched
    _ever_fetched = False


def is_model_available(model: str) -> bool:
    """Return True if *model* is in the Ollama tag list (or health checks off)."""
    available = get_available_models()
    if not available:          # empty = no filtering
        return True
    # Exact match
    if model in available:
        return True
    # Allow prefix match: "qwen3-coder:30b" matches "qwen3-coder:30b-q4_K_M"
    return any(a.startswith(model) or model.startswith(a) for a in available)

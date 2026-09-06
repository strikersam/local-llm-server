"""Per-model cost attribution for the LLM provider router.

Maintains in-memory per-model token and cost aggregates so operators can see
which models are consuming the most spend.  The store is best-effort (no
persistence across restarts, no locking) and is never on the critical path —
all accounting is fire-and-forget.

Cost table (USD per million tokens) is approximate and covers the free/low-cost
providers this platform uses.  Operators can override via ``MODEL_COST_INPUT``
and ``MODEL_COST_OUTPUT`` env vars (comma-separated ``model_id=price`` pairs).

Usage:
    from packages.ai.cost_tracker import record_usage, get_stats, clear_stats

    record_usage("gpt-4o-mini", provider_id="openai", prompt_tokens=1200, completion_tokens=80)
    stats = get_stats()  # {"gpt-4o-mini": {"calls": 1, "prompt_tokens": 1200, ...}}
"""
from __future__ import annotations

import logging
import os
from collections import defaultdict
from typing import Any

log = logging.getLogger("llm-cost-tracker")

# ── Per-million-token cost table (USD) ────────────────────────────────────────
# Pricing as of 2026-09-06; free-tier providers are listed at $0.00.
# Anthropic source: platform.claude.com/docs/en/about-claude/pricing
_DEFAULT_COST_TABLE: dict[str, tuple[float, float]] = {
    # (input_per_M, output_per_M)
    # --- NVIDIA NIM (free tier) ---
    "meta/llama-4-maverick-17b-128e-instruct": (0.0, 0.0),
    "meta/llama-4-scout-17b-16e-instruct": (0.0, 0.0),
    "meta/llama-3.3-70b-instruct": (0.0, 0.0),
    "nvidia/llama-3.1-nemotron-70b-instruct": (0.0, 0.0),
    "deepseek-ai/deepseek-r1": (0.0, 0.0),
    "z-ai/glm-5.2": (0.0, 0.0),
    "nvidia/nemotron-3-super-120b-a12b": (0.0, 0.0),
    # DeepSeek V4 Pro — live in NIM catalog Aug 2026 (free tier).
    "deepseek-ai/deepseek-v4-pro": (0.0, 0.0),
    # --- Cerebras (free/paid tier) ---
    # Probed 2026-08-29: this account's catalogue is exactly these two. The
    # three ids that were here — qwen-3-coder-480b, llama-3.3-70b,
    # llama-3.1-8b — all answer 404.
    # gpt-oss-120B — Cerebras's 120B OSS model, ~3000 tok/s (Aug 2026).
    "gpt-oss-120b": (0.85, 1.20),
    # Rate not established: the account returns 402, so nothing has been
    # billed to read a rate off. Zero matches every other free-tier entry here
    # and the documented default for an unlisted model, so it adds no claim.
    "gemma-4-31b": (0.0, 0.0),
    # --- Groq (free/paid tier) ---
    "llama-3.3-70b-versatile": (0.0, 0.0),
    "deepseek-r1-distill-llama-70b": (0.0, 0.0),
    "llama-3.1-8b-instant": (0.0, 0.0),
    # Kimi K2 on Groq — Moonshot AI MoE, ~1M context (Aug 2026).
    "moonshotai/kimi-k2-instruct": (0.0, 0.0),
    # Qwen3 32B on Groq — strong coder, free tier (Aug 2026).
    "qwen-qwq-32b": (0.0, 0.0),
    # --- Anthropic (paid) — Claude 5 family + Sonnet 4.x / Opus 4.x ---
    # Prices verified from platform.claude.com/docs/en/about-claude/pricing 2026-09-06.
    "claude-opus-5": (5.0, 25.0),          # Opus 5 — $5/$25 per MTok
    "claude-sonnet-5": (2.0, 10.0),        # Sonnet 5 — $2/$10 per MTok (introductory price made permanent 2026-09-01)
    "claude-sonnet-5-20260501": (2.0, 10.0),
    "claude-fable-5": (10.0, 50.0),        # Fable 5 — $10/$50 per MTok (gated flagship)
    "claude-fable-5-1": (10.0, 50.0),      # Fable 5.1 — $10/$50, cache reads 0.025x base
    "claude-mythos-5": (10.0, 50.0),       # Mythos 5 — same as Fable 5 (restricted)
    "claude-mythos-5-1": (10.0, 50.0),     # Mythos 5.1 — released 2026-09-01 (restricted)
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-opus-4-8": (5.0, 25.0),        # Opus 4.8 — $5/$25 per MTok (same tier as Opus 5)
    "claude-opus-4-7": (5.0, 25.0),        # Opus 4.7 — $5/$25 per MTok
    "claude-opus-4-6": (5.0, 25.0),        # Opus 4.6 — $5/$25 per MTok
    "claude-haiku-4-5-20251001": (1.0, 5.0),
    "claude-haiku-4-5": (1.0, 5.0),        # Haiku 4.5 — $1/$5 per MTok
    "claude-3-5-sonnet-20241022": (3.0, 15.0),
    "claude-3-5-haiku-20241022": (0.8, 4.0),
    # --- OpenAI (paid) — GPT-5.6 family (GA July 9 2026) + legacy ---
    "gpt-5.6-sol": (5.0, 30.0),            # Sol: complex reasoning/coding, o3 successor
    "gpt-5.6-terra": (1.5, 7.5),           # Terra: balanced/lower cost
    "gpt-5.6-luna": (0.5, 2.0),            # Luna: fast/high-volume
    "gpt-4o": (2.5, 10.0),
    "gpt-4o-mini": (0.15, 0.6),
    "o1": (15.0, 60.0),
    "o3": (10.0, 40.0),                    # Deprecating late August 2026; migrate to gpt-5.6-sol
    "o3-mini": (1.1, 4.4),
    # --- North Mini Code (local/OpenRouter free) ---
    "north-mini-code-1.0": (0.0, 0.0),
    "cohere/north-mini-code:free": (0.0, 0.0),
    # --- DeepSeek ---
    "deepseek-chat": (0.27, 1.10),
    "deepseek-coder": (0.27, 1.10),
}


def _load_env_overrides() -> dict[str, tuple[float, float]]:
    """Parse MODEL_COST_INPUT / MODEL_COST_OUTPUT env overrides.

    Format: ``MODEL_COST_INPUT=gpt-4o=2.5,gpt-4o-mini=0.15``
            ``MODEL_COST_OUTPUT=gpt-4o=10.0,gpt-4o-mini=0.6``
    """
    overrides: dict[str, tuple[float, float]] = {}
    try:
        raw_in = os.environ.get("MODEL_COST_INPUT", "")
        raw_out = os.environ.get("MODEL_COST_OUTPUT", "")
        in_map: dict[str, float] = {}
        out_map: dict[str, float] = {}
        for pair in raw_in.split(","):
            pair = pair.strip()
            if "=" in pair:
                k, v = pair.split("=", 1)
                in_map[k.strip()] = float(v.strip())
        for pair in raw_out.split(","):
            pair = pair.strip()
            if "=" in pair:
                k, v = pair.split("=", 1)
                out_map[k.strip()] = float(v.strip())
        for model in set(in_map) | set(out_map):
            overrides[model] = (in_map.get(model, 0.0), out_map.get(model, 0.0))
    except Exception as exc:
        log.debug("MODEL_COST env override parse error (ignored): %s", exc)
    return overrides


def _build_cost_table() -> dict[str, tuple[float, float]]:
    table = dict(_DEFAULT_COST_TABLE)
    table.update(_load_env_overrides())
    return table


_COST_TABLE: dict[str, tuple[float, float]] = _build_cost_table()


def cost_for_tokens(
    model: str, prompt_tokens: int, completion_tokens: int
) -> float:
    """Return the USD cost for (prompt_tokens, completion_tokens) on *model*.

    Returns 0.0 for unknown / free-tier models.  Calculation:
      cost = (prompt_tokens * input_$/M + completion_tokens * output_$/M) / 1_000_000
    """
    costs = _COST_TABLE.get(model)
    if costs is None:
        # Fuzzy fallback: check if any key is a prefix / suffix match
        model_lower = model.lower()
        for key, val in _COST_TABLE.items():
            if key.lower() in model_lower or model_lower in key.lower():
                costs = val
                break
    if costs is None:
        return 0.0
    input_per_m, output_per_m = costs
    return (prompt_tokens * input_per_m + completion_tokens * output_per_m) / 1_000_000.0


# ── Aggregate store ───────────────────────────────────────────────────────────
# Dict[model_id, Dict[field, value]]; no locking (best-effort counters).

_stats: dict[str, dict[str, Any]] = defaultdict(
    lambda: {
        "calls": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "estimated_cost_usd": 0.0,
        "providers": set(),
    }
)
# Per-task-category breakdown (e.g. "code_generation", "reasoning",
# "fast_response" — see router/classifier.py). Populated only for callers
# that pass ``tag``; existing untagged calls roll up under "untagged" so
# totals still reconcile against get_stats()["totals"].
_tag_stats: dict[str, dict[str, Any]] = defaultdict(
    lambda: {"calls": 0, "total_tokens": 0, "estimated_cost_usd": 0.0}
)
_total_calls: int = 0
_total_cost_usd: float = 0.0


def record_usage(
    model: str,
    *,
    provider_id: str = "",
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    tag: str = "untagged",
) -> None:
    """Record token usage for *model* (fire-and-forget, never raises).

    ``tag`` is a coarse task-category label (see router/classifier.py's
    ``classify_task()``) used to break down spend by kind of work, not just
    by model — callers that don't have a category default to "untagged".
    """
    global _total_calls, _total_cost_usd
    try:
        cost = cost_for_tokens(model, prompt_tokens, completion_tokens)
        entry = _stats[model]
        entry["calls"] += 1
        entry["prompt_tokens"] += prompt_tokens
        entry["completion_tokens"] += completion_tokens
        entry["total_tokens"] += prompt_tokens + completion_tokens
        entry["estimated_cost_usd"] += cost
        if provider_id:
            entry["providers"].add(provider_id)
        tag_entry = _tag_stats[tag or "untagged"]
        tag_entry["calls"] += 1
        tag_entry["total_tokens"] += prompt_tokens + completion_tokens
        tag_entry["estimated_cost_usd"] += cost
        _total_calls += 1
        _total_cost_usd += cost
    except Exception as exc:
        log.debug("cost_tracker.record_usage error (ignored): %s", exc)


def get_stats() -> dict[str, Any]:
    """Return a JSON-serialisable snapshot of per-model cost attribution."""
    result: dict[str, Any] = {}
    for model, entry in _stats.items():
        result[model] = {
            "calls": entry["calls"],
            "prompt_tokens": entry["prompt_tokens"],
            "completion_tokens": entry["completion_tokens"],
            "total_tokens": entry["total_tokens"],
            "estimated_cost_usd": round(entry["estimated_cost_usd"], 6),
            "providers": sorted(entry["providers"]),
        }
    by_tag = {
        tag: {
            "calls": entry["calls"],
            "total_tokens": entry["total_tokens"],
            "estimated_cost_usd": round(entry["estimated_cost_usd"], 6),
        }
        for tag, entry in _tag_stats.items()
    }
    return {
        "models": result,
        "by_tag": by_tag,
        "totals": {
            "calls": _total_calls,
            "estimated_cost_usd": round(_total_cost_usd, 6),
        },
    }


def clear_stats() -> None:
    """Reset all aggregates (intended for testing)."""
    global _total_calls, _total_cost_usd
    _stats.clear()
    _tag_stats.clear()
    _total_calls = 0
    _total_cost_usd = 0.0


def get_cost_table() -> dict[str, dict[str, float]]:
    """Return the active cost table as a JSON-serialisable dict."""
    return {
        model: {"input_per_million_usd": inp, "output_per_million_usd": out}
        for model, (inp, out) in _COST_TABLE.items()
    }

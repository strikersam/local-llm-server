"""Model capability registry.

Defines the known local models, their strengths, and context limits.
The router uses this to select the best model for a task category.

Extend via ROUTER_EXTRA_MODELS env var (see .env.example) without touching code.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class ModelCapability:
    name: str
    strengths: list[str]
    context_window: int
    type: str          # "coder" | "reasoning" | "general"
    cost_tier: int     # 1=lightest, 2=medium, 3=heaviest (relative resource use)
    tags: list[str] = field(default_factory=list)


# ── Built-in registry ──────────────────────────────────────────────────────────
# Keyed by the Ollama model name (same value you pass to /v1/chat/completions).

_DEFAULT_REGISTRY: dict[str, ModelCapability] = {
    "qwen3-coder:30b": ModelCapability(
        name="qwen3-coder:30b",
        strengths=["code_generation", "code_debugging", "code_review", "tool_use",
                   "long_context", "data_analysis", "conversation"],
        context_window=32768,
        type="coder",
        cost_tier=2,
    ),
    "deepseek-r1:32b": ModelCapability(
        name="deepseek-r1:32b",
        strengths=["reasoning", "analysis", "planning", "math", "complex_tasks", "data_analysis"],
        context_window=32768,
        type="reasoning",
        cost_tier=3,
    ),
    "deepseek-r1:32b-16k": ModelCapability(
        name="deepseek-r1:32b-16k",
        strengths=["reasoning", "analysis", "planning", "math", "complex_tasks", "data_analysis"],
        context_window=16384,
        type="reasoning",
        cost_tier=3,
    ),
    "deepseek-r1:671b": ModelCapability(
        name="deepseek-r1:671b",
        strengths=["reasoning", "analysis", "planning", "math", "complex_tasks", "data_analysis"],
        context_window=131072,
        type="reasoning",
        cost_tier=3,
        tags=["flagship"],
    ),
    "qwen3-coder:7b": ModelCapability(
        name="qwen3-coder:7b",
        # Preferred for fast_response — smallest registered coder model
        strengths=["code_generation", "code_debugging", "tool_use", "fast_response", "conversation"],
        context_window=32768,
        type="coder",
        cost_tier=1,
        tags=["lightweight"],
    ),
    # ── Gemma 4 (Google, April 2026) ─────────────────────────────────────────
    # Interleaved-attention architecture; strong multimodal + code + tool-use.
    "gemma4:27b": ModelCapability(
        name="gemma4:27b",
        strengths=["code_generation", "code_debugging", "code_review", "tool_use",
                   "reasoning", "analysis", "long_context", "conversation"],
        context_window=128000,
        type="general",
        cost_tier=2,
        tags=["multimodal", "google", "gemma4"],
    ),
    "gemma4:9b": ModelCapability(
        name="gemma4:9b",
        strengths=["code_generation", "code_debugging", "tool_use",
                   "conversation", "fast_response"],
        context_window=128000,
        type="general",
        cost_tier=1,
        tags=["multimodal", "google", "gemma4", "lightweight"],
    ),
    "gemma4:2b": ModelCapability(
        name="gemma4:2b",
        strengths=["conversation", "fast_response"],
        context_window=32768,
        type="general",
        cost_tier=1,
        tags=["google", "gemma4", "ultra-fast"],
    ),
    # ── Qwen3-Coder 235B (Qwen3 family, 2025) ────────────────────────────────
    # Flagship Qwen3-Coder variant; MoE architecture; best-in-class for code.
    "qwen3-coder:235b": ModelCapability(
        name="qwen3-coder:235b",
        strengths=["code_generation", "code_debugging", "code_review", "tool_use",
                   "long_context", "reasoning", "data_analysis", "complex_tasks"],
        context_window=131072,
        type="coder",
        cost_tier=3,
        tags=["qwen3", "flagship", "moe"],
    ),
    # ── Llama 4 (Meta, April 2025) ───────────────────────────────────────────
    # Scout: 17Bx16E MoE, 10M context; Maverick: 17Bx128E, 1M context.
    "llama4-maverick:17b": ModelCapability(
        name="llama4-maverick:17b",
        strengths=["code_generation", "code_debugging", "code_review", "tool_use",
                   "reasoning", "analysis", "long_context", "conversation", "data_analysis"],
        context_window=1048576,
        type="general",
        cost_tier=2,
        tags=["llama4", "meta", "moe", "multimodal"],
    ),
    "llama4-scout:17b": ModelCapability(
        name="llama4-scout:17b",
        strengths=["code_generation", "code_debugging", "tool_use",
                   "conversation", "fast_response", "data_analysis"],
        context_window=10485760,
        type="general",
        cost_tier=1,
        tags=["llama4", "meta", "moe", "multimodal", "lightweight"],
    ),
    # ── DeepSeek V3 (Dec 2024) ────────────────────────────────────────────────
    # 685B MoE model; strong code + reasoning; lower cost than R1.
    "deepseek-v3:685b": ModelCapability(
        name="deepseek-v3:685b",
        strengths=["code_generation", "code_debugging", "code_review", "tool_use",
                   "reasoning", "analysis", "planning", "long_context", "data_analysis",
                   "conversation"],
        context_window=131072,
        type="coder",
        cost_tier=2,
        tags=["deepseek", "moe", "flagship"],
    ),
    # ── Claude aliases ────────────────────────────────────────────────────────
    "claude-3-5-sonnet-20241022": ModelCapability(
        name="claude-3-5-sonnet-20241022",
        strengths=["code_generation", "code_debugging", "code_review", "tool_use", "long_context", "conversation"],
        context_window=32768,
        type="coder",
        cost_tier=2,
        tags=["alias"],
    ),
    "claude-3-opus-20240229": ModelCapability(
        name="claude-3-opus-20240229",
        strengths=["reasoning", "analysis", "planning", "math", "complex_tasks"],
        context_window=32768,
        type="reasoning",
        cost_tier=3,
        tags=["alias"],
    ),
    "qwen3.6:35b": ModelCapability(
        name="qwen3.6:35b",
        strengths=["code_generation", "code_debugging", "code_review", "tool_use",
                   "reasoning", "analysis", "long_context", "conversation", "multimodal"],
        context_window=128000,
        type="general",
        cost_tier=2,
        tags=["qwen3.6", "moe", "multimodal"],
    ),
}


def get_registry() -> dict[str, ModelCapability]:
    """Return model registry, extended with ROUTER_EXTRA_MODELS env entries.

    ROUTER_EXTRA_MODELS format (comma-separated):
        model_name:type:strength1+strength2+strength3

    Example::
        ROUTER_EXTRA_MODELS=my-model:7b:coder:code_generation+tool_use,llama3:8b:general:conversation
    """
    registry = dict(_DEFAULT_REGISTRY)

    raw = os.environ.get("ROUTER_EXTRA_MODELS", "").strip()
    if raw:
        for entry in raw.split(","):
            parts = entry.strip().split(":", 2)
            if len(parts) == 3:
                name, mtype, strengths_raw = parts
                name = name.strip()
                mtype = mtype.strip()
                strengths = [s.strip() for s in strengths_raw.strip().split("+") if s.strip()]
                if name and strengths:
                    registry[name] = ModelCapability(
                        name=name,
                        strengths=strengths,
                        context_window=32768,
                        type=mtype,
                        cost_tier=2,
                    )

    # Hook MODEL_MAP so aliases appear in registry natively
    raw_map = os.environ.get("MODEL_MAP", "").strip()
    if raw_map:
        for pair in raw_map.split(","):
            pair = pair.strip()
            if ":" in pair:
                src, dst = pair.split(":", 1)
                src, dst = src.strip(), dst.strip()
                if src and dst and dst in registry:
                    registry[src] = ModelCapability(
                        name=src,
                        strengths=registry[dst].strengths,
                        context_window=registry[dst].context_window,
                        type=registry[dst].type,
                        cost_tier=registry[dst].cost_tier,
                        tags=["alias"]
                    )

    return registry


def best_model_for(category: str, registry: dict[str, ModelCapability] | None = None) -> str:
    """Return the name of the best model for a given task category.

    Falls back to AGENT_EXECUTOR_MODEL env var, then 'qwen3-coder:30b'.
    """
    if registry is None:
        registry = get_registry()

    # Models that have the category in strengths, sorted by cost_tier desc
    # (prefer the most capable model within the category)
    candidates = [
        cap for cap in registry.values()
        if category in cap.strengths
    ]
    if candidates:
        candidates.sort(key=lambda c: c.cost_tier, reverse=True)
        return candidates[0].name

    return os.environ.get("AGENT_EXECUTOR_MODEL", "qwen3-coder:30b")

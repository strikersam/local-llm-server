"""
Map each local Ollama model name to a commercial API reference price (USD per 1M tokens).
Used only for *estimated* savings vs paying that commercial API — not actual billing.

Override defaults with COMMERCIAL_EQUIVALENT_PRICES_FILE (JSON) or inline JSON in
COMMERCIAL_EQUIVALENT_PRICES_JSON.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CommercialEquivalent:
    commercial_name: str
    input_per_million_usd: float
    output_per_million_usd: float


def _load_from_env() -> dict[str, CommercialEquivalent]:
    defaults: dict[str, CommercialEquivalent] = {
        # ── Reference cloud SKUs — 2026 equivalence map ──────────────────────────
        # Open model → closest closed equivalent for savings estimation.
        # Pricing: DeepSeek API (deepseek.com), Anthropic API (anthropic.com).
        # Update when vendors change pricing.

        # Executor / coding specialist  →  Claude Sonnet 4.6 class
        # (practical match: 80–90% on SWE-bench, coding, and daily driver tasks)
        "qwen3-coder:30b": CommercialEquivalent(
            commercial_name="Claude Sonnet 4.6 / GPT-4.1 class (reference)",
            input_per_million_usd=3.0,
            output_per_million_usd=15.0,
        ),

        # Planner / reasoning specialist  →  DeepSeek R1 API (official)
        # (R1 API is itself cheap; savings vs Claude Opus 4.6 are much larger)
        "deepseek-r1:32b": CommercialEquivalent(
            commercial_name="DeepSeek R1 API / Claude Opus 4.6 class (reference)",
            input_per_million_usd=0.55,
            output_per_million_usd=2.19,
        ),

        # Heavy flagship (404 GB)  →  DeepSeek R1 API full scale
        "deepseek-r1:671b": CommercialEquivalent(
            commercial_name="DeepSeek R1 API (full) / Claude Opus 4.6 class",
            input_per_million_usd=0.55,
            output_per_million_usd=2.19,
        ),

        # Lightweight / fallback  →  Claude Haiku class
        "qwen3-coder:7b": CommercialEquivalent(
            commercial_name="Claude Haiku 4.5 class (reference)",
            input_per_million_usd=0.80,
            output_per_million_usd=4.0,
        ),

        # Optional 32B Qwen2.5-Coder pull  →  GPT-4.1-mini class
        "qwen2.5-coder:32b": CommercialEquivalent(
            commercial_name="GPT-4.1-mini / Claude Sonnet 4.6 class (reference)",
            input_per_million_usd=0.40,
            output_per_million_usd=1.60,
        ),

        # ── 2026 open-source additions ────────────────────────────────────────
        # MiniMax M2.5 — 229B sparse MoE (10B active), community Q4_K_M GGUF
        # Reference: MiniMax M2.5 API ($0.10/$0.55 per M tokens per minimax.io)
        "frob/minimax-m2.5:230b-a10b-q4_K_M": CommercialEquivalent(
            commercial_name="MiniMax M2.5 API / GPT-4.1 class (reference)",
            input_per_million_usd=0.10,
            output_per_million_usd=0.55,
        ),

        # DeepSeek V3.2 — 685B MoE, cloud-proxy via Ollama
        # Reference: DeepSeek V3 API ($0.27/$1.10 per M tokens per deepseek.com)
        "deepseek-v3.2:cloud": CommercialEquivalent(
            commercial_name="DeepSeek V3.2 API / GPT-4.1 class (reference)",
            input_per_million_usd=0.27,
            output_per_million_usd=1.10,
        ),

        # MiniMax M2.7 — cloud-proxy only (open weights not yet released)
        # Reference: MiniMax M2.7 API pricing (minimax.io)
        "minimax-m2.7:cloud": CommercialEquivalent(
            commercial_name="MiniMax M2.7 API (cloud proxy reference)",
            input_per_million_usd=0.10,
            output_per_million_usd=0.55,
        ),

        # GLM-5 — 744B MoE (40B active), cloud-proxy via Ollama
        # Reference: GLM-5 API ($0.14/$0.14 per M tokens per z.ai)
        "glm-5:cloud": CommercialEquivalent(
            commercial_name="GLM-5 API / GPT-4.1 class (reference)",
            input_per_million_usd=0.14,
            output_per_million_usd=0.14,
        ),
    }

    merged: dict[str, CommercialEquivalent] = dict(defaults)

    path_raw = os.environ.get("COMMERCIAL_EQUIVALENT_PRICES_FILE", "").strip()
    if path_raw:
        p = Path(path_raw)
        if p.is_file():
            merged.update(_parse_mapping(json.loads(p.read_text(encoding="utf-8"))))

    inline = os.environ.get("COMMERCIAL_EQUIVALENT_PRICES_JSON", "").strip()
    if inline:
        merged.update(_parse_mapping(json.loads(inline)))

    return merged


def _parse_mapping(obj: Any) -> dict[str, CommercialEquivalent]:
    out: dict[str, CommercialEquivalent] = {}
    if not isinstance(obj, dict):
        return out
    for model, spec in obj.items():
        if not isinstance(model, str) or not isinstance(spec, dict):
            continue
        name = spec.get("commercial_name")
        inp = spec.get("input_per_million_usd")
        outp = spec.get("output_per_million_usd")
        if not isinstance(name, str) or not isinstance(inp, (int, float)) or not isinstance(outp, (int, float)):
            continue
        out[model] = CommercialEquivalent(
            commercial_name=name,
            input_per_million_usd=float(inp),
            output_per_million_usd=float(outp),
        )
    return out


_PRICES: dict[str, CommercialEquivalent] | None = None


def get_prices() -> dict[str, CommercialEquivalent]:
    global _PRICES
    if _PRICES is None:
        _PRICES = _load_from_env()
    return _PRICES


def estimate_commercial_equivalent_usd(model: str | None, prompt_tokens: int, completion_tokens: int) -> tuple[float, CommercialEquivalent | None]:
    if not model:
        return 0.0, None
    eq = get_prices().get(model)
    if not eq:
        return 0.0, None
    cost = (prompt_tokens / 1_000_000.0) * eq.input_per_million_usd + (completion_tokens / 1_000_000.0) * eq.output_per_million_usd
    return cost, eq

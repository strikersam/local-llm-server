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
        # Reference cloud SKUs (update when vendors change pricing).
        "deepseek-r1:671b": CommercialEquivalent(
            commercial_name="DeepSeek R1 (API)",
            input_per_million_usd=0.55,
            output_per_million_usd=2.19,
        ),
        "deepseek-r1:32b": CommercialEquivalent(
            commercial_name="DeepSeek R1 (API)",
            input_per_million_usd=0.55,
            output_per_million_usd=2.19,
        ),
        "qwen3-coder:30b": CommercialEquivalent(
            commercial_name="Qwen3-Coder / GPT-4.1 class (reference)",
            input_per_million_usd=2.0,
            output_per_million_usd=8.0,
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

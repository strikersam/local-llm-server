"""Model pricing for the cost-aware routing evaluation.

Rates are first-party Anthropic API list prices in USD per 1,000,000 tokens,
current as of 2026-09. They are the *published* rates, not a live lookup — verify
against https://www.anthropic.com/pricing before quoting a dollar figure, and
override per deploy via ``set_price`` if your account is billed differently.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPrice:
    """Per-token price for one model, in USD per 1,000,000 tokens."""

    input_per_mtok: float
    output_per_mtok: float


# Keyed by the short tier name used in the subagent frontmatter (`model: haiku`
# etc.), not the dated model id, so the eval speaks the same language as the
# `.claude/agents/*.md` files it measures.
MODEL_PRICING: dict[str, ModelPrice] = {
    "haiku": ModelPrice(input_per_mtok=1.00, output_per_mtok=5.00),
    "sonnet": ModelPrice(input_per_mtok=2.00, output_per_mtok=10.00),
    "opus": ModelPrice(input_per_mtok=5.00, output_per_mtok=25.00),
}


def set_price(tier: str, input_per_mtok: float, output_per_mtok: float) -> None:
    """Override the price for a tier (e.g. a discounted or partner rate)."""
    MODEL_PRICING[tier] = ModelPrice(input_per_mtok, output_per_mtok)


def token_cost(tier: str, input_tokens: int, output_tokens: int) -> float:
    """USD cost of one model call. Raises KeyError on an unknown tier."""
    price = MODEL_PRICING[tier]
    return (
        input_tokens * price.input_per_mtok / 1_000_000
        + output_tokens * price.output_per_mtok / 1_000_000
    )

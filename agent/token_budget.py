"""agent/token_budget.py — Per-Session Token Spend Caps

Track token usage per session or per agent run and raise an error when a
configured budget ceiling is hit. Prevents runaway cloud API costs.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger("qwen-budget")

# Rough heuristic used when the model does not return usage metadata
_CHARS_PER_TOKEN = 4


class BudgetExceededError(Exception):
    """Raised when a token spend cap is hit."""


@dataclass
class BudgetUsage:
    session_id: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cap: int = 0  # 0 means unlimited

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def remaining(self) -> int:
        if self.cap == 0:
            return -1  # unlimited
        return max(0, self.cap - self.total_tokens)

    @property
    def exceeded(self) -> bool:
        return self.cap > 0 and self.total_tokens >= self.cap

    def as_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cap": self.cap,
            "remaining": self.remaining,
            "exceeded": self.exceeded,
        }


class TokenBudget:
    """Track and enforce per-session or per-agent token budgets.

    Usage::

        budget = TokenBudget()
        budget.set_cap("as_abc123", cap=50_000)
        budget.record("as_abc123", prompt_tokens=120, completion_tokens=80)
        budget.check("as_abc123")  # raises BudgetExceededError if over cap
    """

    def __init__(self) -> None:
        self._usage: dict[str, BudgetUsage] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_cap(self, session_id: str, cap: int) -> BudgetUsage:
        """Set (or update) the token cap for *session_id*."""
        usage = self._usage.setdefault(
            session_id,
            BudgetUsage(session_id=session_id, cap=cap),
        )
        usage.cap = cap
        log.debug("Budget cap set: session=%s cap=%d", session_id, cap)
        return usage

    def record(
        self,
        session_id: str,
        *,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        response_text: str | None = None,
    ) -> BudgetUsage:
        """Add token counts for *session_id*.

        If *response_text* is given and counts are zero, estimates from chars.
        """
        usage = self._usage.setdefault(
            session_id,
            BudgetUsage(session_id=session_id),
        )
        if prompt_tokens == 0 and completion_tokens == 0 and response_text:
            completion_tokens = len(response_text) // _CHARS_PER_TOKEN
        usage.prompt_tokens += prompt_tokens
        usage.completion_tokens += completion_tokens
        log.debug(
            "Budget record: session=%s +p=%d +c=%d total=%d cap=%d",
            session_id,
            prompt_tokens,
            completion_tokens,
            usage.total_tokens,
            usage.cap,
        )
        return usage

    def check(self, session_id: str) -> None:
        """Raise :class:`BudgetExceededError` if the session has exceeded its cap."""
        usage = self._usage.get(session_id)
        if usage and usage.exceeded:
            raise BudgetExceededError(
                f"Token budget exceeded for session {session_id!r}: "
                f"{usage.total_tokens}/{usage.cap} tokens used."
            )

    def get(self, session_id: str) -> BudgetUsage | None:
        return self._usage.get(session_id)

    def reset(self, session_id: str) -> None:
        """Reset usage counters for *session_id* (cap is preserved)."""
        usage = self._usage.get(session_id)
        if usage:
            cap = usage.cap
            self._usage[session_id] = BudgetUsage(session_id=session_id, cap=cap)

    def list_all(self) -> list[BudgetUsage]:
        return list(self._usage.values())

"""agent/context.py — Smart Context Compression

Three strategies for keeping conversations within model token limits:
  reactive  — drop oldest non-system messages until under threshold
  micro     — remove exact-duplicate and near-empty messages
  inspect   — return statistics without modifying the history
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

log = logging.getLogger("qwen-context")

ContextMessage = dict[str, str]  # {"role": ..., "content": ...}
Strategy = Literal["reactive", "micro", "inspect"]

# Rough heuristic: 4 chars ≈ 1 token (good enough for budget checks)
_CHARS_PER_TOKEN = 4


def _estimate_tokens(messages: list[ContextMessage]) -> int:
    total = sum(len(m.get("content", "")) for m in messages)
    return total // _CHARS_PER_TOKEN


@dataclass
class ContextStats:
    message_count: int
    estimated_tokens: int
    oldest_role: str
    newest_role: str

    def as_dict(self) -> dict[str, object]:
        return {
            "message_count": self.message_count,
            "estimated_tokens": self.estimated_tokens,
            "oldest_role": self.oldest_role,
            "newest_role": self.newest_role,
        }


class ContextCompressor:
    """Compress conversation history when it approaches the token limit.

    Usage::

        cc = ContextCompressor(token_threshold=4096)
        if cc.needs_compression(messages):
            messages = cc.compress(messages, strategy="reactive")
        stats = cc.inspect(messages)
    """

    DEFAULT_TOKEN_THRESHOLD = 6_000

    def __init__(self, token_threshold: int | None = None) -> None:
        self.token_threshold = token_threshold or self.DEFAULT_TOKEN_THRESHOLD

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compress(
        self,
        messages: list[ContextMessage],
        strategy: Strategy = "reactive",
    ) -> list[ContextMessage]:
        """Return a (possibly shorter) copy of *messages* using *strategy*.

        ``inspect`` never modifies — call :meth:`inspect` for stats instead.
        """
        if strategy == "reactive":
            return self._reactive(messages)
        if strategy == "micro":
            return self._micro(messages)
        if strategy == "inspect":
            return list(messages)
        raise ValueError(f"Unknown strategy: {strategy!r}. Use 'reactive', 'micro', or 'inspect'.")

    def inspect(self, messages: list[ContextMessage]) -> ContextStats:
        """Return token usage stats without modifying *messages*."""
        if not messages:
            return ContextStats(0, 0, "", "")
        return ContextStats(
            message_count=len(messages),
            estimated_tokens=_estimate_tokens(messages),
            oldest_role=messages[0].get("role", ""),
            newest_role=messages[-1].get("role", ""),
        )

    def needs_compression(self, messages: list[ContextMessage]) -> bool:
        """Return *True* when estimated token count exceeds the threshold."""
        return _estimate_tokens(messages) >= self.token_threshold

    # ------------------------------------------------------------------
    # Strategies
    # ------------------------------------------------------------------

    def _reactive(self, messages: list[ContextMessage]) -> list[ContextMessage]:
        """Drop the oldest non-system messages until under the token threshold."""
        result = list(messages)
        while _estimate_tokens(result) >= self.token_threshold and len(result) > 1:
            # Prefer dropping the oldest non-system message
            for i, m in enumerate(result):
                if m.get("role") != "system":
                    result.pop(i)
                    break
            else:
                # Only system messages remain — drop the oldest
                result.pop(0)
        log.debug(
            "reactive compress: %d → %d messages (%d tokens)",
            len(messages),
            len(result),
            _estimate_tokens(result),
        )
        return result

    def _micro(self, messages: list[ContextMessage]) -> list[ContextMessage]:
        """Remove exact-duplicate and near-empty messages."""
        seen: set[str] = set()
        result: list[ContextMessage] = []
        for m in messages:
            content = m.get("content", "")
            if len(content.strip()) < 3:
                continue  # near-empty filler
            key = f"{m.get('role')}:{content.strip()}"
            if key in seen:
                continue  # exact duplicate
            seen.add(key)
            result.append(m)
        log.debug(
            "micro compress: %d → %d messages",
            len(messages),
            len(result),
        )
        return result

from __future__ import annotations

"""Context management for agent sessions.

Implements the three context-engineering strategies from Anthropic's
"Scaling Managed Agents: Decoupling the brain from the hands" (April 2026):

1. Observation masking  — keep tool-call records visible but truncate/hide
   the *content* of old tool outputs so the context window stays lean.

2. Context compaction  — when conversation history grows past a threshold,
   summarise the old portion into a single system note so the LLM retains
   the gist without burning tokens on verbatim repetition.

3. Just-in-time retrieval cue  — the ContextManager signals when the harness
   should switch from full-file reads to targeted head/search queries.

Anthropic's key insight: the harness—not the model—owns context-window
management.  As models get more capable the harness should *stop* doing
orchestration work, but it should *keep* doing context engineering.
"""

import logging
from typing import Any

log = logging.getLogger("qwen-agent")

# ---------------------------------------------------------------------------
# Tunables (can be overridden via constructor for testing)
# ---------------------------------------------------------------------------
_DEFAULT_MASK_AFTER = 4      # Keep last N observations fully; mask earlier ones
_DEFAULT_MASK_CONTENT_LIMIT = 300   # chars to keep from a masked observation result
_DEFAULT_COMPACT_AFTER = 16  # Compact history when it exceeds this many messages
_DEFAULT_JIT_FILE_LIMIT = 80  # Lines — switch to head_file below this threshold hint


class ContextManager:
    """Manages context window state for a single agent run.

    The Brain (LLM) stays stateless across tool calls; the ContextManager is
    the harness component that curates what the Brain actually sees.
    """

    def __init__(
        self,
        *,
        mask_after: int = _DEFAULT_MASK_AFTER,
        mask_content_limit: int = _DEFAULT_MASK_CONTENT_LIMIT,
        compact_after: int = _DEFAULT_COMPACT_AFTER,
        jit_file_limit: int = _DEFAULT_JIT_FILE_LIMIT,
    ) -> None:
        self.mask_after = mask_after
        self.mask_content_limit = mask_content_limit
        self.compact_after = compact_after
        self.jit_file_limit = jit_file_limit

    # ------------------------------------------------------------------
    # Observation masking
    # ------------------------------------------------------------------

    def mask_observations(
        self, observations: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Return a copy of *observations* with old tool outputs truncated.

        JetBrains Junie (cited in the Anthropic managed-agents article) uses
        this pattern to keep tool *calls* visible (so the model knows what it
        already tried) while dropping bulky *results* that are no longer needed
        for the current decision.

        The last ``self.mask_after`` observations are passed through verbatim;
        earlier ones have their ``result`` field replaced with a short summary.
        """
        if len(observations) <= self.mask_after:
            return list(observations)

        masked: list[dict[str, Any]] = []
        cutoff = len(observations) - self.mask_after

        for i, obs in enumerate(observations):
            if i < cutoff:
                result = obs.get("result", "")
                summary = self._summarise_result(result)
                masked.append(
                    {
                        "tool": obs.get("tool", "unknown"),
                        "args": obs.get("args", {}),
                        "result": summary,
                        "_masked": True,
                    }
                )
            else:
                masked.append(dict(obs))

        return masked

    def _summarise_result(self, result: Any) -> str:
        """Produce a short, token-efficient representation of a tool result."""
        if isinstance(result, str):
            if len(result) <= self.mask_content_limit:
                return result
            return result[: self.mask_content_limit] + " … [masked]"
        if isinstance(result, list):
            return f"[list: {len(result)} items — masked]"
        if isinstance(result, dict):
            keys = list(result.keys())[:5]
            return f"[dict keys={keys} — masked]"
        return f"[{type(result).__name__} — masked]"

    # ------------------------------------------------------------------
    # Context compaction
    # ------------------------------------------------------------------

    def needs_compaction(self, history: list[dict[str, Any]]) -> bool:
        """True when the history is long enough to warrant compaction."""
        return len(history) > self.compact_after

    def compact_history(
        self,
        history: list[dict[str, Any]],
        *,
        compaction_summary: str,
    ) -> list[dict[str, Any]]:
        """Replace the old portion of *history* with a single compaction note.

        The compaction summary (produced by asking the LLM to summarise the
        session so far) is injected as a system message.  The most recent
        ``self.mask_after * 2`` messages are kept verbatim so the model has
        immediate context; everything older is replaced.

        This mirrors the Claude Code compaction strategy described in the
        Anthropic engineering blog: preserve architectural decisions, discard
        redundant tool outputs.
        """
        keep_tail = self.mask_after * 2
        if len(history) <= keep_tail:
            return list(history)

        recent = history[-keep_tail:]
        compacted: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "[Context compacted — earlier session summary]\n\n"
                    + compaction_summary
                ),
            },
            *recent,
        ]
        log.debug(
            "context_manager: compacted %d → %d messages",
            len(history),
            len(compacted),
        )
        return compacted

    # ------------------------------------------------------------------
    # Just-in-time retrieval hint
    # ------------------------------------------------------------------

    def prefer_partial_read(self, file_size_hint: int | None) -> bool:
        """True when the harness should use head_file instead of read_file.

        When a file is known to be large (line count above the JIT threshold),
        the harness should request only the first N lines and let the model
        decide whether it needs more.  This avoids bloating the context window
        with irrelevant file content.

        Pass ``None`` if the file size is unknown; conservatively returns False.
        """
        if file_size_hint is None:
            return False
        return file_size_hint > self.jit_file_limit

    # ------------------------------------------------------------------
    # Condensed step summary (sub-agent delegation)
    # ------------------------------------------------------------------

    @staticmethod
    def condense_step_result(result: dict[str, Any], max_chars: int = 2000) -> dict[str, Any]:
        """Trim a step result so sub-agent outputs stay within ~1-2k tokens.

        The Anthropic managed-agents article recommends that sub-agents return
        condensed summaries (1 000–2 000 tokens) rather than full execution
        transcripts, to keep the orchestrator's context lean.
        """
        condensed = dict(result)

        # Trim the observations list — keep only the last few entries
        observations = condensed.get("observations", [])
        if len(observations) > 3:
            condensed["observations"] = observations[-3:]
            condensed["_observations_truncated"] = len(observations) - 3

        # Trim any large string fields
        for key in ("summary", "reason", "output"):
            if isinstance(condensed.get(key), str) and len(condensed[key]) > max_chars:
                condensed[key] = condensed[key][:max_chars] + " … [truncated]"

        return condensed

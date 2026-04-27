"""runtimes/registry.py — RuntimeCapabilityRegistry.

Maps task types and required capabilities to the best-fit runtime.
Acts as the decision table for RuntimeRoutingPolicyEngine.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from runtimes.base import RuntimeCapability, RuntimeTier

if TYPE_CHECKING:
    from runtimes.base import RuntimeAdapter

log = logging.getLogger("qwen-proxy")

# ── Task-type → required capability mapping ───────────────────────────────────

TASK_CAPABILITY_MAP: dict[str, list[RuntimeCapability]] = {
    "code_generation":  [RuntimeCapability.CODE_GENERATION, RuntimeCapability.FILE_READ_WRITE],
    "code_review":      [RuntimeCapability.CODE_REVIEW],
    "repo_editing":     [RuntimeCapability.REPO_EDITING, RuntimeCapability.GIT_OPERATIONS],
    "git_operations":   [RuntimeCapability.GIT_OPERATIONS],
    "reasoning":        [],  # any runtime can handle reasoning
    "general":          [],
    "agent_delegation": [RuntimeCapability.AGENT_DELEGATION],
    "scheduled":        [RuntimeCapability.SCHEDULED_TASKS],
    "web_browse":       [RuntimeCapability.WEB_BROWSE],
    "shell_exec":       [RuntimeCapability.SHELL_EXEC],
    "tool_use":         [RuntimeCapability.TOOL_USE],
}

# Tier ordering for preference: FIRST_CLASS > TIER_2 > TIER_3 > EXPERIMENTAL
_TIER_ORDER = [
    RuntimeTier.FIRST_CLASS,
    RuntimeTier.TIER_2,
    RuntimeTier.TIER_3,
    RuntimeTier.EXPERIMENTAL,
]


class RuntimeCapabilityRegistry:
    """Maintains the catalogue of registered adapters and answers
    'which runtimes can handle task X?' queries.
    """

    def __init__(self) -> None:
        self._adapters: dict[str, "RuntimeAdapter"] = {}

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, adapter: "RuntimeAdapter") -> None:
        if not adapter.RUNTIME_ID:
            raise ValueError(f"Adapter {adapter!r} has no RUNTIME_ID set")
        if adapter.RUNTIME_ID in self._adapters:
            log.warning("Runtime %s already registered; replacing", adapter.RUNTIME_ID)
        self._adapters[adapter.RUNTIME_ID] = adapter
        log.info("Registered runtime %s (tier=%s)", adapter.RUNTIME_ID, adapter.TIER.value)

    def unregister(self, runtime_id: str) -> None:
        self._adapters.pop(runtime_id, None)

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get(self, runtime_id: str) -> "RuntimeAdapter | None":
        return self._adapters.get(runtime_id)

    def all(self) -> list["RuntimeAdapter"]:
        return list(self._adapters.values())

    def ids(self) -> list[str]:
        return list(self._adapters.keys())

    # ── Capability query ──────────────────────────────────────────────────────

    def capable_of(
        self,
        task_type: str,
        required_capabilities: list[RuntimeCapability] | None = None,
    ) -> list["RuntimeAdapter"]:
        """Return all adapters that can handle *task_type*, ordered by tier."""
        needed = list(required_capabilities or TASK_CAPABILITY_MAP.get(task_type, []))
        candidates = [
            a for a in self._adapters.values()
            if all(a.supports(cap) for cap in needed)
        ]
        # Sort by tier preference, then alphabetically for stability
        candidates.sort(
            key=lambda a: (
                _TIER_ORDER.index(a.TIER) if a.TIER in _TIER_ORDER else 99,
                a.RUNTIME_ID,
            )
        )
        return candidates

    def best_for(
        self,
        task_type: str,
        preferred_runtime_id: str | None = None,
        required_capabilities: list[RuntimeCapability] | None = None,
    ) -> "RuntimeAdapter | None":
        """Return the single best adapter for *task_type*.

        If *preferred_runtime_id* is set and capable, it wins regardless of tier.
        Otherwise falls back to the highest-tier capable adapter.
        """
        capable = self.capable_of(task_type, required_capabilities)
        if not capable:
            return None
        if preferred_runtime_id:
            for a in capable:
                if a.RUNTIME_ID == preferred_runtime_id:
                    return a
        return capable[0]  # highest tier first

    def as_list(self) -> list[dict]:
        return [a.as_dict() for a in self._adapters.values()]

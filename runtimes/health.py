"""runtimes/health.py — RuntimeHealthService.

Periodically polls all registered runtimes for health and caches the
results.  Exposes get_health(runtime_id) for instant access without
blocking.  Also implements circuit-breaker logic: a runtime that fails
N consecutive checks is marked OPEN (unhealthy) and skipped by the
routing engine until it recovers.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from runtimes.base import RuntimeHealth

if TYPE_CHECKING:
    from runtimes.registry import RuntimeCapabilityRegistry

log = logging.getLogger("qwen-proxy")

# ── Circuit-breaker constants ─────────────────────────────────────────────────
CB_FAILURE_THRESHOLD = 3    # consecutive failures → OPEN
CB_RECOVERY_SEC      = 60   # seconds before attempting recovery from OPEN


@dataclass
class CircuitState:
    runtime_id: str
    consecutive_failures: int = 0
    open_since: float | None = None   # epoch time when circuit opened

    @property
    def is_open(self) -> bool:
        if self.open_since is None:
            return False
        # Allow probing after recovery window
        return (time.monotonic() - self.open_since) < CB_RECOVERY_SEC

    def record_success(self) -> None:
        self.consecutive_failures = 0
        self.open_since = None

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        if self.consecutive_failures >= CB_FAILURE_THRESHOLD:
            if self.open_since is None:
                self.open_since = time.monotonic()
                log.warning("Circuit OPEN for runtime %s after %d failures",
                            self.runtime_id, self.consecutive_failures)


class RuntimeHealthService:
    """Async health polling service for all registered runtimes."""

    def __init__(
        self,
        registry: "RuntimeCapabilityRegistry",
        poll_interval_sec: int = 30,
    ) -> None:
        self._registry = registry
        self._poll_interval = poll_interval_sec
        self._cache: dict[str, RuntimeHealth] = {}
        self._circuits: dict[str, CircuitState] = {}
        self._task: asyncio.Task | None = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the background polling loop."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._poll_loop())
            log.info("RuntimeHealthService started (interval=%ds)", self._poll_interval)

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    # ── Public API ────────────────────────────────────────────────────────────

    def get_health(self, runtime_id: str) -> RuntimeHealth | None:
        """Return the last-known health for *runtime_id* (may be stale)."""
        return self._cache.get(runtime_id)

    def is_available(self, runtime_id: str) -> bool:
        """Return True if the runtime is available (not circuit-open)."""
        circuit = self._circuits.get(runtime_id)
        if circuit and circuit.is_open:
            return False
        h = self._cache.get(runtime_id)
        return h.available if h else True  # optimistic until first check

    def all_health(self) -> list[dict]:
        """Return health snapshots for all known runtimes."""
        return [
            {
                **h.as_dict(),
                "circuit_open": self._circuits.get(h.runtime_id, CircuitState(h.runtime_id)).is_open,
            }
            for h in self._cache.values()
        ]

    async def verify_all(self) -> list[dict]:
        """Force an immediate health check of all runtimes and return results."""
        await self._poll_all()
        return self.all_health()

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _poll_loop(self) -> None:
        while True:
            await self._poll_all()
            await asyncio.sleep(self._poll_interval)

    async def _poll_all(self) -> None:
        adapters = self._registry.all()
        tasks = [self._poll_one(a.RUNTIME_ID) for a in adapters]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _poll_one(self, runtime_id: str) -> None:
        adapter = self._registry.get(runtime_id)
        if adapter is None:
            return
        circuit = self._circuits.setdefault(runtime_id, CircuitState(runtime_id))
        # If circuit is open and not yet past recovery window, skip the check
        # unless the window has passed (then do a probe check)
        if circuit.is_open:
            return
        try:
            health = await asyncio.wait_for(adapter.health_check(), timeout=10.0)
            self._cache[runtime_id] = health
            if health.available:
                circuit.record_success()
            else:
                circuit.record_failure()
        except Exception as exc:
            log.debug("Health check failed for %s: %s", runtime_id, exc)
            circuit.record_failure()
            self._cache[runtime_id] = RuntimeHealth(
                runtime_id=runtime_id,
                available=False,
                error=str(exc),
            )

"""agent/log_monitor.py — Application Log Monitor

Captures ERROR/CRITICAL log records emitted by the running proxy and turns
them into self-healing fix tasks.  Works by attaching a custom
``logging.Handler`` to the root logger at startup.

Rate-limiting:
  - At most one task per unique error signature per hour.
  - Signature = sha256(logger_name + message[:120]).
  - A separate IGNORED_LOGGERS set suppresses noisy, non-actionable loggers.

Usage (called once at startup in proxy.py)::

    monitor = LogMonitor()
    monitor.attach()

The monitor is also a singleton so any module can call
``get_log_monitor()`` to retrieve it.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import time
import threading
from typing import Any

log = logging.getLogger("qwen-proxy")

# Loggers that emit errors we don't want to auto-fix (too noisy or not actionable).
IGNORED_LOGGERS: frozenset[str] = frozenset(
    {
        "uvicorn.error",
        "uvicorn.access",
        "httpx",
        "httpcore",
        "asyncio",
        "multipart",
        "qwen-proxy",        # avoid self-feeding: our own logger errors are already tracked
    }
)

# Don't create a task for the same error within this window.
COOLDOWN_SECONDS: int = 3600  # 1 hour


class _ErrorCaptureHandler(logging.Handler):
    """Logging handler that forwards ERROR/CRITICAL records to LogMonitor."""

    def __init__(self, monitor: "LogMonitor") -> None:
        super().__init__(level=logging.ERROR)
        self._monitor = monitor

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
            self._monitor._on_log_error(record.name, record.levelname, message)
        except Exception:
            pass  # never let the logging handler raise


class LogMonitor:
    """Attach to the root logger and forward errors to the self-healing agent.

    Usage::

        monitor = LogMonitor()
        monitor.attach()
    """

    def __init__(self) -> None:
        self._handler: _ErrorCaptureHandler | None = None
        self._cooldowns: dict[str, float] = {}  # sig → last_task_time
        self._lock = threading.Lock()
        self._task_count = 0

    # ── Public API ────────────────────────────────────────────────────────────

    def attach(self) -> None:
        """Register the error capture handler on the root logger."""
        if self._handler is not None:
            return
        self._handler = _ErrorCaptureHandler(self)
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        self._handler.setFormatter(formatter)
        logging.getLogger().addHandler(self._handler)
        log.info("LogMonitor attached — backend errors will auto-create fix tasks")

    def detach(self) -> None:
        if self._handler:
            logging.getLogger().removeHandler(self._handler)
            self._handler = None

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "attached": self._handler is not None,
                "tasks_created": self._task_count,
                "active_cooldowns": len(self._cooldowns),
            }

    # ── Internal ──────────────────────────────────────────────────────────────

    def _on_log_error(self, logger_name: str, level: str, message: str) -> None:
        if logger_name in IGNORED_LOGGERS:
            return
        if "LogMonitor" in (message or ""):
            return
        sig = _sig(logger_name, message)
        now = time.monotonic()
        # _NEVER_SEEN sentinel is negative so that `now - sentinel` is always > COOLDOWN,
        # meaning the very first occurrence of an error is never blocked.
        _NEVER_SEEN = -(COOLDOWN_SECONDS + 1)

        with self._lock:
            last = self._cooldowns.get(sig, _NEVER_SEEN)
            if now - last < COOLDOWN_SECONDS:
                return
            self._cooldowns[sig] = now
            self._task_count += 1

        title = f"Backend {level}: {logger_name} — {message[:80]}"
        description = (
            f"The server emitted a `{level}` log entry from `{logger_name}`.\n\n"
            f"**Full message:**\n```\n{message[:2000]}\n```\n\n"
            "Please investigate the root cause and apply the minimum fix."
        )
        # Run async dispatch from sync logging handler via thread-safe scheduling.
        _dispatch_async(title, description)
        log.debug("LogMonitor: created fix task for %s (sig=%s)", logger_name, sig[:8])


def _sig(logger_name: str, message: str) -> str:
    raw = f"{logger_name}:{message[:120]}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _dispatch_async(title: str, description: str) -> None:
    """Fire-and-forget: schedule a self-healing task from any thread."""
    from agent.self_healing import get_self_healing_agent

    healer = get_self_healing_agent()
    if not healer:
        return

    async def _run():
        await healer.on_manual_report(title, description, severity="medium")

    # If there's a running event loop (typical in uvicorn), schedule there.
    # Otherwise use asyncio.run() in a fresh thread.
    try:
        loop = asyncio.get_running_loop()
        loop.call_soon_threadsafe(lambda: loop.create_task(_run()))
    except RuntimeError:
        threading.Thread(target=asyncio.run, args=(_run(),), daemon=True).start()


# ── Singleton ─────────────────────────────────────────────────────────────────

_monitor_instance: LogMonitor | None = None


def set_log_monitor(instance: LogMonitor) -> None:
    global _monitor_instance
    _monitor_instance = instance


def get_log_monitor() -> LogMonitor | None:
    return _monitor_instance

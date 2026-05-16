"""agent/error_interceptor.py — HTTP Error Interceptor Middleware

FastAPI/Starlette middleware that catches unhandled 500 responses and turns
them into self-healing fix tasks.

Rate-limited: at most one task per unique exception signature per hour so a
crashing endpoint doesn't flood the task queue.

Usage (added in proxy.py)::

    from agent.error_interceptor import ErrorInterceptorMiddleware
    app.add_middleware(ErrorInterceptorMiddleware)
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import time
import traceback
import threading
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

log = logging.getLogger("qwen-proxy")

COOLDOWN_SECONDS: int = 3600  # deduplicate identical errors within 1 hour


class ErrorInterceptorMiddleware(BaseHTTPMiddleware):
    """Catch 5xx responses and auto-create fix tasks via the self-healing agent.

    Errors with the same signature (method + path + exception type) are
    rate-limited to one task per COOLDOWN_SECONDS to prevent task flooding.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._cooldowns: dict[str, float] = {}
        self._lock = threading.Lock()
        self._intercepted = 0

    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            response = await call_next(request)
        except Exception as exc:
            tb = traceback.format_exc()
            self._handle_exception(request, exc, tb)
            raise

        if response.status_code >= 500:
            self._handle_5xx(request, response.status_code)

        return response

    # ── Internal ──────────────────────────────────────────────────────────────

    def _handle_exception(self, request: Request, exc: Exception, tb: str) -> None:
        method = request.method
        path = request.url.path
        exc_type = type(exc).__name__
        sig = _sig(f"{method}:{path}:{exc_type}")
        if not self._should_create_task(sig):
            return

        title = f"Unhandled exception on {method} {path}: {exc_type}"
        description = (
            f"An unhandled `{exc_type}` exception was raised while handling "
            f"`{method} {path}`.\n\n"
            f"**Error:** {exc}\n\n"
            f"**Traceback:**\n```\n{tb[:3000]}\n```\n\n"
            "Please fix the root cause. Add error handling only if the error "
            "cannot be prevented — don't silence exceptions."
        )
        _dispatch_async(title, description, severity="high")
        self._intercepted += 1

    def _handle_5xx(self, request: Request, status_code: int) -> None:
        method = request.method
        path = request.url.path
        sig = _sig(f"{method}:{path}:{status_code}")
        if not self._should_create_task(sig):
            return

        title = f"HTTP {status_code} on {method} {path}"
        description = (
            f"The endpoint `{method} {path}` returned HTTP {status_code}.\n\n"
            "This may indicate an unhandled error or a missing dependency. "
            "Investigate the server logs and fix the underlying issue."
        )
        _dispatch_async(title, description, severity="medium")
        self._intercepted += 1

    def _should_create_task(self, sig: str) -> bool:
        now = time.monotonic()
        with self._lock:
            last = self._cooldowns.get(sig, 0.0)
            if now - last < COOLDOWN_SECONDS:
                return False
            self._cooldowns[sig] = now
        return True

    def get_stats(self) -> dict[str, Any]:
        return {
            "intercepted_errors": self._intercepted,
            "active_cooldowns": len(self._cooldowns),
        }


def _sig(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _dispatch_async(title: str, description: str, severity: str = "medium") -> None:
    from agent.self_healing import get_self_healing_agent

    healer = get_self_healing_agent()
    if not healer:
        return

    async def _run():
        await healer.on_manual_report(title, description, severity=severity)

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_run())
    except RuntimeError:
        threading.Thread(target=asyncio.run, args=(_run(),), daemon=True).start()

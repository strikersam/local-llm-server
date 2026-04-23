"""runtimes/adapters/hermes.py — Hermes Agent adapter (FIRST CLASS).

Hermes Agent (https://github.com/NousResearch/hermes-agent) is the
primary autonomous runtime.  It runs as a sidecar process and exposes
an HTTP API that we call for task execution.

Integration mode: SIDECAR (managed subprocess + HTTP API)
Tier: FIRST CLASS

Key capabilities:
  - Self-improving skill loop
  - Cron/scheduled tasks
  - Subagent delegation
  - MCP connectivity
  - Autonomous/recurring tasks
  - Agent memory/session continuity
  - Local-first model usage

Configuration (env vars or constructor config dict):
  HERMES_BASE_URL    — Base URL of the running Hermes server (default: http://localhost:8100)
  HERMES_API_KEY     — Optional API key for Hermes HTTP API
  HERMES_TIMEOUT_SEC — Default timeout for task execution (default: 300)
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

import httpx

from runtimes.base import (
    IntegrationMode,
    RuntimeAdapter,
    RuntimeCapability,
    RuntimeExecutionError,
    RuntimeHealth,
    RuntimeTier,
    RuntimeUnavailableError,
    TaskResult,
    TaskSpec,
)

log = logging.getLogger("runtime.hermes")


class HermesAdapter(RuntimeAdapter):
    """Adapter for Hermes Agent — FIRST CLASS autonomous runtime."""

    RUNTIME_ID      = "hermes"
    DISPLAY_NAME    = "Hermes Agent"
    DESCRIPTION     = (
        "NousResearch Hermes Agent — autonomous self-improving agent with "
        "MCP connectivity, scheduled tasks, subagent delegation, and "
        "local-first model usage."
    )
    TIER            = RuntimeTier.FIRST_CLASS
    INTEGRATION_MODE = IntegrationMode.SIDECAR
    DOCS_URL        = "https://github.com/NousResearch/hermes-agent"
    CAPABILITIES    = frozenset({
        RuntimeCapability.CODE_GENERATION,
        RuntimeCapability.CODE_REVIEW,
        RuntimeCapability.FILE_READ_WRITE,
        RuntimeCapability.TOOL_USE,
        RuntimeCapability.AGENT_DELEGATION,
        RuntimeCapability.SCHEDULED_TASKS,
        RuntimeCapability.MEMORY_SESSIONS,
        RuntimeCapability.MCP_CONNECTIVITY,
        RuntimeCapability.STREAM_OUTPUT,
        RuntimeCapability.AUTONOMOUS_LOOP,
        RuntimeCapability.SHELL_EXEC,
        RuntimeCapability.WEB_BROWSE,
    })

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._base_url = (
            config.get("base_url") if config else None
        ) or os.environ.get("HERMES_BASE_URL", "http://localhost:8100")
        self._api_key = (
            config.get("api_key") if config else None
        ) or os.environ.get("HERMES_API_KEY", "")
        self._timeout = int(
            (config.get("timeout_sec") if config else None)
            or os.environ.get("HERMES_TIMEOUT_SEC", "300")
        )

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            h["Authorization"] = f"Bearer {self._api_key}"
        return h

    # ── Health ────────────────────────────────────────────────────────────────

    async def health_check(self) -> RuntimeHealth:
        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{self._base_url}/health",
                    headers=self._headers(),
                )
            latency_ms = (time.monotonic() - t0) * 1000
            if resp.status_code == 200:
                data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                return RuntimeHealth(
                    runtime_id=self.RUNTIME_ID,
                    available=True,
                    version=data.get("version"),
                    latency_ms=round(latency_ms, 1),
                    details=data,
                )
            return RuntimeHealth(
                runtime_id=self.RUNTIME_ID,
                available=False,
                error=f"HTTP {resp.status_code}",
            )
        except Exception as exc:
            return RuntimeHealth(
                runtime_id=self.RUNTIME_ID,
                available=False,
                error=str(exc),
            )

    # ── Execution ─────────────────────────────────────────────────────────────

    async def execute(self, spec: TaskSpec) -> TaskResult:
        """Submit task to Hermes via its /tasks endpoint."""
        payload: dict[str, Any] = {
            "task_id": spec.task_id,
            "instruction": spec.instruction,
            "task_type": spec.task_type,
            "timeout_sec": spec.timeout_sec,
            "context": spec.context,
        }
        if spec.workspace_path:
            payload["workspace_path"] = spec.workspace_path
        if spec.model_preference:
            payload["model"] = spec.model_preference
        if spec.tool_allowlist is not None:
            payload["tool_allowlist"] = spec.tool_allowlist

        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(
                timeout=float(spec.timeout_sec + 10)
            ) as client:
                resp = await client.post(
                    f"{self._base_url}/tasks",
                    json=payload,
                    headers=self._headers(),
                )
        except httpx.ConnectError as exc:
            raise RuntimeUnavailableError(self.RUNTIME_ID, f"Cannot connect to Hermes at {self._base_url}: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise RuntimeExecutionError(self.RUNTIME_ID, f"Timeout executing task {spec.task_id}", spec.task_id) from exc

        elapsed_ms = (time.monotonic() - t0) * 1000

        if resp.status_code not in (200, 201, 202):
            detail = _safe_detail(resp)
            raise RuntimeExecutionError(
                self.RUNTIME_ID,
                f"Hermes returned HTTP {resp.status_code}: {detail}",
                spec.task_id,
            )

        data = resp.json()

        # Hermes may return immediately (async task) or with full result.
        # If async, poll for completion.
        if data.get("status") in ("queued", "running"):
            data = await self._poll_task(client, data["task_id"], spec.timeout_sec)

        return TaskResult(
            runtime_id=self.RUNTIME_ID,
            task_id=spec.task_id,
            success=data.get("success", data.get("status") == "done"),
            output=data.get("output", data.get("result", "")),
            artifacts=data.get("artifacts", []),
            tool_calls=data.get("tool_calls", []),
            model_used=data.get("model_used"),
            provider_used=data.get("provider_used", "local"),
            tokens_used=data.get("tokens_used"),
            cost_usd=data.get("cost_usd"),
            execution_time_ms=elapsed_ms,
            metadata=data.get("metadata", {}),
        )

    async def _poll_task(
        self,
        client: httpx.AsyncClient,
        hermes_task_id: str,
        timeout_sec: int,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            await asyncio.sleep(2.0)
            resp = await client.get(
                f"{self._base_url}/tasks/{hermes_task_id}",
                headers=self._headers(),
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") not in ("queued", "running"):
                    return data
        raise RuntimeExecutionError(
            self.RUNTIME_ID,
            f"Timeout polling Hermes task {hermes_task_id}",
            hermes_task_id,
        )


# ── Utility ────────────────────────────────────────────────────────────────────

def _safe_detail(resp: httpx.Response) -> str:
    try:
        d = resp.json()
        return d.get("detail", str(d))
    except Exception:
        return resp.text[:200]

"""runtimes/adapters/openhands.py — OpenHands adapter (TIER 2, EXPERIMENTAL).

OpenHands (https://github.com/All-Hands-AI/OpenHands) is a powerful
open-source coding agent.  Integration is via its REST API.  Marked
EXPERIMENTAL due to heavyweight Docker deployment requirements.

Integration mode: EXTERNAL_PROCESS (Docker-based, user must run separately)
Tier: TIER_2 / EXPERIMENTAL

Configuration:
  OPENHANDS_BASE_URL  — Base URL of the OpenHands server (default: http://localhost:3000)
  OPENHANDS_API_KEY   — Optional API key
"""

from __future__ import annotations

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

log = logging.getLogger("runtime.openhands")

_EXPERIMENTAL_NOTE = (
    "OpenHands requires a separately running Docker container. "
    "Start with: docker run -it --rm -e SANDBOX_RUNTIME_CONTAINER_IMAGE=docker.all-hands.dev/all-hands-ai/runtime:0.38-nikolaik "
    "-v /var/run/docker.sock:/var/run/docker.sock -p 3000:3000 docker.all-hands.dev/all-hands-ai/openhands:0.38"
)


class OpenHandsAdapter(RuntimeAdapter):
    """Adapter for OpenHands — TIER 2 / EXPERIMENTAL coding agent.

    NOTE: OpenHands must be running as a separate Docker container.
    This adapter communicates with it via its REST API.
    """

    RUNTIME_ID      = "openhands"
    DISPLAY_NAME    = "OpenHands (Experimental)"
    DESCRIPTION     = (
        "All-Hands-AI OpenHands — Docker-based open-source coding agent. "
        "EXPERIMENTAL: requires separately running Docker container. "
        + _EXPERIMENTAL_NOTE
    )
    TIER            = RuntimeTier.EXPERIMENTAL
    INTEGRATION_MODE = IntegrationMode.EXTERNAL_PROCESS
    DOCS_URL        = "https://github.com/All-Hands-AI/OpenHands"
    CAPABILITIES    = frozenset({
        RuntimeCapability.CODE_GENERATION,
        RuntimeCapability.CODE_REVIEW,
        RuntimeCapability.REPO_EDITING,
        RuntimeCapability.GIT_OPERATIONS,
        RuntimeCapability.FILE_READ_WRITE,
        RuntimeCapability.TOOL_USE,
        RuntimeCapability.SHELL_EXEC,
        RuntimeCapability.WEB_BROWSE,
        RuntimeCapability.MULTI_FILE_EDIT,
        RuntimeCapability.AUTONOMOUS_LOOP,
    })

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._base_url = (
            (config or {}).get("base_url")
            or os.environ.get("OPENHANDS_BASE_URL", "http://localhost:3000")
        )
        self._api_key = (
            (config or {}).get("api_key")
            or os.environ.get("OPENHANDS_API_KEY", "")
        )

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            h["Authorization"] = f"Bearer {self._api_key}"
        return h

    async def health_check(self) -> RuntimeHealth:
        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._base_url}/api/options/config", headers=self._headers())
            latency_ms = (time.monotonic() - t0) * 1000
            available = resp.status_code == 200
            return RuntimeHealth(
                runtime_id=self.RUNTIME_ID,
                available=available,
                latency_ms=round(latency_ms, 1),
                error=None if available else f"HTTP {resp.status_code}",
                details={"note": "EXPERIMENTAL - requires Docker"},
            )
        except Exception as exc:
            return RuntimeHealth(
                runtime_id=self.RUNTIME_ID,
                available=False,
                error=str(exc),
                details={"note": _EXPERIMENTAL_NOTE},
            )

    async def execute(self, spec: TaskSpec) -> TaskResult:
        """Create a conversation in OpenHands and poll for completion."""
        # OpenHands v0.38+ API: POST /api/conversations
        payload: dict[str, Any] = {
            "initial_message": spec.instruction,
            "runtime": "docker",
        }
        if spec.model_preference:
            payload["llm_model"] = spec.model_preference
        if spec.workspace_path:
            payload["workspace_mount_path"] = spec.workspace_path

        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=float(spec.timeout_sec + 10)) as client:
                resp = await client.post(
                    f"{self._base_url}/api/conversations",
                    json=payload,
                    headers=self._headers(),
                )
                if resp.status_code not in (200, 201):
                    raise RuntimeExecutionError(
                        self.RUNTIME_ID,
                        f"HTTP {resp.status_code}: {resp.text[:200]}",
                        spec.task_id,
                    )
                conv = resp.json()
                conv_id = conv.get("conversation_id") or conv.get("id")
                if not conv_id:
                    raise RuntimeExecutionError(
                        self.RUNTIME_ID, "No conversation_id in response", spec.task_id
                    )

                # Poll for completion
                import asyncio
                deadline = time.monotonic() + spec.timeout_sec
                while time.monotonic() < deadline:
                    await asyncio.sleep(3.0)
                    status_resp = await client.get(
                        f"{self._base_url}/api/conversations/{conv_id}",
                        headers=self._headers(),
                    )
                    if status_resp.status_code == 200:
                        status_data = status_resp.json()
                        if status_data.get("state") in ("finished", "error", "stopped"):
                            elapsed_ms = (time.monotonic() - t0) * 1000
                            success = status_data.get("state") == "finished"
                            return TaskResult(
                                runtime_id=self.RUNTIME_ID,
                                task_id=spec.task_id,
                                success=success,
                                output=status_data.get("last_message", ""),
                                model_used=spec.model_preference,
                                provider_used="local",
                                execution_time_ms=elapsed_ms,
                                metadata={
                                    "conversation_id": conv_id,
                                    "state": status_data.get("state"),
                                    "note": "EXPERIMENTAL",
                                },
                            )
        except (RuntimeUnavailableError, RuntimeExecutionError):
            raise
        except httpx.ConnectError as exc:
            raise RuntimeUnavailableError(self.RUNTIME_ID, f"Cannot connect: {exc}") from exc

        raise RuntimeExecutionError(
            self.RUNTIME_ID, f"Timeout after {spec.timeout_sec}s", spec.task_id
        )

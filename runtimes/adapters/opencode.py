"""runtimes/adapters/opencode.py — OpenCode adapter (FIRST CLASS for coding).

OpenCode (https://github.com/sst/opencode) is the primary coding runtime.
It runs as an external CLI process (or server) and is best-in-class for:
  - Repository work
  - Code analysis and generation
  - Local-first model usage
  - Built-in agent modes

Integration mode: SIDECAR (managed subprocess, stdin/stdout or HTTP API)
Tier: FIRST CLASS (for coding tasks)

Configuration:
  OPENCODE_BIN      — Path to opencode binary (default: opencode)
  OPENCODE_BASE_URL — HTTP API URL if running in server mode (optional)
  OPENCODE_MODEL    — Default model to use (default: env AGENT_EXECUTOR_MODEL)
  OPENCODE_WORKSPACE — Default workspace root (default: .)
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
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

log = logging.getLogger("runtime.opencode")


class OpenCodeAdapter(RuntimeAdapter):
    """Adapter for OpenCode — FIRST CLASS coding runtime."""

    RUNTIME_ID      = "opencode"
    DISPLAY_NAME    = "OpenCode"
    DESCRIPTION     = (
        "SST OpenCode — local-first coding agent with repo-aware editing, "
        "code analysis, code generation, and built-in agent modes."
    )
    TIER            = RuntimeTier.FIRST_CLASS
    INTEGRATION_MODE = IntegrationMode.SIDECAR
    DOCS_URL        = "https://github.com/sst/opencode"
    CAPABILITIES    = frozenset({
        RuntimeCapability.CODE_GENERATION,
        RuntimeCapability.CODE_REVIEW,
        RuntimeCapability.REPO_EDITING,
        RuntimeCapability.GIT_OPERATIONS,
        RuntimeCapability.FILE_READ_WRITE,
        RuntimeCapability.TOOL_USE,
        RuntimeCapability.STREAM_OUTPUT,
        RuntimeCapability.MULTI_FILE_EDIT,
        RuntimeCapability.SHELL_EXEC,
    })

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._bin = (config or {}).get("bin") or os.environ.get("OPENCODE_BIN", "opencode")
        self._base_url = (config or {}).get("base_url") or os.environ.get("OPENCODE_BASE_URL", "")
        self._default_model = (config or {}).get("model") or os.environ.get(
            "OPENCODE_MODEL", os.environ.get("AGENT_EXECUTOR_MODEL", "qwen3-coder:30b")
        )
        self._workspace = (config or {}).get("workspace") or os.environ.get("OPENCODE_WORKSPACE", ".")

    # ── Health ────────────────────────────────────────────────────────────────

    async def health_check(self) -> RuntimeHealth:
        # If HTTP API mode is configured, check that first
        if self._base_url:
            return await self._health_via_http()

        # Otherwise verify the binary is available
        t0 = time.monotonic()
        bin_path = shutil.which(self._bin)
        if bin_path is None:
            return RuntimeHealth(
                runtime_id=self.RUNTIME_ID,
                available=False,
                error=f"Binary '{self._bin}' not found in PATH",
            )

        # Run `opencode --version` to verify it works
        try:
            proc = await asyncio.create_subprocess_exec(
                bin_path, "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
            version = stdout.decode().strip().split("\n")[0]
            latency_ms = (time.monotonic() - t0) * 1000
            return RuntimeHealth(
                runtime_id=self.RUNTIME_ID,
                available=True,
                version=version or "unknown",
                latency_ms=round(latency_ms, 1),
                details={"bin_path": bin_path},
            )
        except Exception as exc:
            return RuntimeHealth(
                runtime_id=self.RUNTIME_ID,
                available=False,
                error=str(exc),
            )

    async def _health_via_http(self) -> RuntimeHealth:
        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._base_url}/health")
            latency_ms = (time.monotonic() - t0) * 1000
            return RuntimeHealth(
                runtime_id=self.RUNTIME_ID,
                available=resp.status_code == 200,
                latency_ms=round(latency_ms, 1),
                error=None if resp.status_code == 200 else f"HTTP {resp.status_code}",
            )
        except Exception as exc:
            return RuntimeHealth(runtime_id=self.RUNTIME_ID, available=False, error=str(exc))

    # ── Execution ─────────────────────────────────────────────────────────────

    async def execute(self, spec: TaskSpec) -> TaskResult:
        """Execute via OpenCode CLI: `opencode run --json <instruction>`."""
        if self._base_url:
            return await self._execute_via_http(spec)
        return await self._execute_via_cli(spec)

    async def _execute_via_cli(self, spec: TaskSpec) -> TaskResult:
        bin_path = shutil.which(self._bin)
        if not bin_path:
            raise RuntimeUnavailableError(self.RUNTIME_ID, f"Binary '{self._bin}' not found")

        workspace = spec.workspace_path or self._workspace
        model = spec.model_preference or self._default_model
        cmd = [
            bin_path, "run",
            "--model", model,
            "--workspace", workspace,
            "--json",
            "--",
            spec.instruction,
        ]

        t0 = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=float(spec.timeout_sec)
            )
        except asyncio.TimeoutError as exc:
            raise RuntimeExecutionError(
                self.RUNTIME_ID, f"Timeout after {spec.timeout_sec}s", spec.task_id
            ) from exc
        except Exception as exc:
            raise RuntimeExecutionError(self.RUNTIME_ID, str(exc), spec.task_id) from exc

        elapsed_ms = (time.monotonic() - t0) * 1000
        success = proc.returncode == 0
        output = stdout.decode(errors="replace").strip()
        if not success and not output:
            output = stderr.decode(errors="replace").strip()

        return TaskResult(
            runtime_id=self.RUNTIME_ID,
            task_id=spec.task_id,
            success=success,
            output=output,
            model_used=model,
            provider_used="local",
            execution_time_ms=elapsed_ms,
            metadata={"returncode": proc.returncode},
        )

    async def _execute_via_http(self, spec: TaskSpec) -> TaskResult:
        payload = {
            "instruction": spec.instruction,
            "model": spec.model_preference or self._default_model,
            "workspace": spec.workspace_path or self._workspace,
            "task_id": spec.task_id,
        }
        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=float(spec.timeout_sec + 10)) as client:
                resp = await client.post(f"{self._base_url}/run", json=payload)
        except httpx.ConnectError as exc:
            raise RuntimeUnavailableError(self.RUNTIME_ID, str(exc)) from exc

        elapsed_ms = (time.monotonic() - t0) * 1000
        if resp.status_code not in (200, 201):
            raise RuntimeExecutionError(
                self.RUNTIME_ID, f"HTTP {resp.status_code}", spec.task_id
            )
        data = resp.json()
        return TaskResult(
            runtime_id=self.RUNTIME_ID,
            task_id=spec.task_id,
            success=data.get("success", True),
            output=data.get("output", ""),
            artifacts=data.get("artifacts", []),
            model_used=data.get("model_used", spec.model_preference),
            provider_used="local",
            execution_time_ms=elapsed_ms,
        )

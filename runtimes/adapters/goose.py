"""runtimes/adapters/goose.py — Goose adapter (TIER 2).

Goose (https://github.com/block/goose) is a general-purpose local
runtime with extensible tool integrations.  Runs as a managed subprocess.

Integration mode: SIDECAR
Tier: TIER_2

Configuration:
  GOOSE_BIN        — Path to goose binary (default: goose)
  GOOSE_MODEL      — Default model (default: qwen3-coder:14b)
  GOOSE_PROFILE    — Goose profile name (default: default)
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
    RuntimeDependency,
    RuntimeExecutionError,
    RuntimeHealth,
    RuntimeTier,
    RuntimeUnavailableError,
    TaskResult,
    TaskSpec,
)

log = logging.getLogger("runtime.goose")


class GooseAdapter(RuntimeAdapter):
    """Adapter for Goose — TIER 2 general-purpose local runtime."""

    RUNTIME_ID      = "goose"
    DISPLAY_NAME    = "Goose"
    DESCRIPTION     = (
        "Block Goose — general-purpose local AI agent with extensible "
        "tool integrations, CLI/API interface, and local model support."
    )
    TIER            = RuntimeTier.TIER_2
    INTEGRATION_MODE = IntegrationMode.SIDECAR
    DOCS_URL        = "https://github.com/block/goose"
    CAPABILITIES    = frozenset({
        RuntimeCapability.CODE_GENERATION,
        RuntimeCapability.CODE_REVIEW,
        RuntimeCapability.FILE_READ_WRITE,
        RuntimeCapability.TOOL_USE,
        RuntimeCapability.SHELL_EXEC,
        RuntimeCapability.STREAM_OUTPUT,
    })

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._base_url = (config or {}).get("base_url") or os.environ.get("GOOSE_BASE_URL", "")
        self._bin = (config or {}).get("bin") or os.environ.get("GOOSE_BIN", "goose")
        self._model = (config or {}).get("model") or os.environ.get("GOOSE_MODEL", "qwen3-coder:14b")
        self._profile = (config or {}).get("profile") or os.environ.get("GOOSE_PROFILE", "default")

    def required_dependencies(self) -> list[RuntimeDependency]:
        return [
            RuntimeDependency(
                name="goose",
                config_var="GOOSE_BIN",
                install_hint="Install Goose and set GOOSE_BIN if needed.",
            )
        ] if not self._base_url else []

    async def health_check(self) -> RuntimeHealth:
        if self._base_url:
            return await self._health_via_http()
        return await self._health_via_cli()

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

    async def _health_via_cli(self) -> RuntimeHealth:
        t0 = time.monotonic()
        bin_path = shutil.which(self._bin)
        if not bin_path:
            return RuntimeHealth(
                runtime_id=self.RUNTIME_ID,
                available=False,
                error=f"Binary '{self._bin}' not found in PATH",
            )
        try:
            proc = await asyncio.create_subprocess_exec(
                bin_path, "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
            latency_ms = (time.monotonic() - t0) * 1000
            return RuntimeHealth(
                runtime_id=self.RUNTIME_ID,
                available=True,
                version=stdout.decode().strip().split("\n")[0] or "unknown",
                latency_ms=round(latency_ms, 1),
                details={"bin_path": bin_path, "profile": self._profile},
            )
        except Exception as exc:
            return RuntimeHealth(runtime_id=self.RUNTIME_ID, available=False, error=str(exc))

    async def execute(self, spec: TaskSpec) -> TaskResult:
        bin_path = shutil.which(self._bin)
        if not bin_path:
            raise RuntimeUnavailableError(self.RUNTIME_ID, f"Binary '{self._bin}' not found")

        workspace = spec.workspace_path or "."
        cmd = [
            bin_path, "run",
            "--profile", self._profile,
            "--model", spec.model_preference or self._model,
            "--text", spec.instruction,
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
            raise RuntimeExecutionError(self.RUNTIME_ID, f"Timeout after {spec.timeout_sec}s", spec.task_id) from exc

        elapsed_ms = (time.monotonic() - t0) * 1000
        success = proc.returncode == 0
        output = stdout.decode(errors="replace").strip() or stderr.decode(errors="replace").strip()

        return TaskResult(
            runtime_id=self.RUNTIME_ID,
            task_id=spec.task_id,
            success=success,
            output=output,
            model_used=spec.model_preference or self._model,
            provider_used="local",
            execution_time_ms=elapsed_ms,
        )

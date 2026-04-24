"""runtimes/adapters/aider.py — Aider adapter (TIER 3 — specialized).

Aider (https://github.com/Aider-AI/aider) is a git-aware, repo-aware
code editing backend.  Best used for targeted file edits with git commit.
Not intended as the main orchestration engine.

Integration mode: EXTERNAL_PROCESS (CLI subprocess)
Tier: TIER_3

Configuration:
  AIDER_BIN         — Path to aider binary (default: aider)
  AIDER_MODEL       — Default model (default: ollama/qwen3-coder:14b)
  AIDER_NO_AUTO_COMMIT — If "true", skip auto-commit (default: false)
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

log = logging.getLogger("runtime.aider")


class AiderAdapter(RuntimeAdapter):
    """Adapter for Aider — TIER 3 specialized git-aware code editor."""

    RUNTIME_ID      = "aider"
    DISPLAY_NAME    = "Aider"
    DESCRIPTION     = (
        "Aider-AI Aider — git-aware, repo-aware code editing backend. "
        "Best for targeted file edits with automatic git commits. "
        "Not recommended as a general orchestration engine."
    )
    TIER            = RuntimeTier.TIER_3
    INTEGRATION_MODE = IntegrationMode.EXTERNAL_PROCESS
    DOCS_URL        = "https://github.com/Aider-AI/aider"
    CAPABILITIES    = frozenset({
        RuntimeCapability.CODE_GENERATION,
        RuntimeCapability.REPO_EDITING,
        RuntimeCapability.GIT_OPERATIONS,
        RuntimeCapability.FILE_READ_WRITE,
        RuntimeCapability.MULTI_FILE_EDIT,
    })

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._base_url = (config or {}).get("base_url") or os.environ.get("AIDER_BASE_URL", "")
        self._bin = (config or {}).get("bin") or os.environ.get("AIDER_BIN", "aider")
        self._model = (
            (config or {}).get("model")
            or os.environ.get("AIDER_MODEL", "ollama/qwen3-coder:14b")
        )
        self._no_auto_commit = (
            str((config or {}).get("no_auto_commit", os.environ.get("AIDER_NO_AUTO_COMMIT", "false"))).lower()
            == "true"
        )

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
                error=f"Binary '{self._bin}' not found in PATH. Install with: pip install aider-chat",
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
                details={"bin_path": bin_path, "model": self._model},
            )
        except Exception as exc:
            return RuntimeHealth(runtime_id=self.RUNTIME_ID, available=False, error=str(exc))

    async def execute(self, spec: TaskSpec) -> TaskResult:
        """Run aider non-interactively via `--message` flag."""
        bin_path = shutil.which(self._bin)
        if not bin_path:
            raise RuntimeUnavailableError(self.RUNTIME_ID, f"Binary '{self._bin}' not found")

        workspace = spec.workspace_path or "."
        model = spec.model_preference or self._model

        cmd = [
            bin_path,
            "--model", model,
            "--no-pretty",
            "--yes",          # auto-confirm file edits
            "--message", spec.instruction,
        ]
        if self._no_auto_commit:
            cmd.append("--no-auto-commits")

        # If specific files are in context, pass them
        files = spec.context.get("files", [])
        if isinstance(files, list):
            cmd.extend(files)

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

        return TaskResult(
            runtime_id=self.RUNTIME_ID,
            task_id=spec.task_id,
            success=success,
            output=output,
            model_used=model,
            provider_used="local",
            execution_time_ms=elapsed_ms,
            metadata={
                "returncode": proc.returncode,
                "stderr": stderr.decode(errors="replace").strip()[:500],
            },
        )

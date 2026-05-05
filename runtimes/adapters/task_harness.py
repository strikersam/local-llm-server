"""runtimes/adapters/task_harness.py — external task harness adapter.

Compatible CLI harnesses can expose non-interactive `run --json` and
`run --ndjson` entrypoints. This adapter bridges those long-running,
multi-file workflows into the runtime manager without requiring a managed
service process.

Integration mode: EXTERNAL_PROCESS (CLI subprocess)
Tier: TIER_2 (supported CLI bridge; deeper server/session integration can come later)

Configuration:
  TASK_HARNESS_BIN              — Path to the compatible harness binary
  TASK_HARNESS_MODEL            — Default model for `--model`
  TASK_HARNESS_PROVIDER         — Default provider for `--provider`
  TASK_HARNESS_PROVIDER_PROFILE — Default provider profile for `--provider-profile`
  TASK_HARNESS_WORKSPACE        — Default workspace root (default: .)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import time
from typing import Any, AsyncIterator

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

log = logging.getLogger("runtime.task_harness")


class TaskHarnessAdapter(RuntimeAdapter):
    """Adapter for a compatible external task harness."""

    RUNTIME_ID = "task_harness"
    DISPLAY_NAME = "Task Harness"
    DESCRIPTION = (
        "Compatible external task harness for multi-file coding, repo workflows, "
        "delegation, streaming output, and long-running agent tasks."
    )
    TIER = RuntimeTier.TIER_2
    INTEGRATION_MODE = IntegrationMode.EXTERNAL_PROCESS
    DOCS_URL = ""
    CAPABILITIES = frozenset({
        RuntimeCapability.CODE_GENERATION,
        RuntimeCapability.CODE_REVIEW,
        RuntimeCapability.REPO_EDITING,
        RuntimeCapability.GIT_OPERATIONS,
        RuntimeCapability.FILE_READ_WRITE,
        RuntimeCapability.TOOL_USE,
        RuntimeCapability.WEB_BROWSE,
        RuntimeCapability.SHELL_EXEC,
        RuntimeCapability.AGENT_DELEGATION,
        RuntimeCapability.SCHEDULED_TASKS,
        RuntimeCapability.MEMORY_SESSIONS,
        RuntimeCapability.MCP_CONNECTIVITY,
        RuntimeCapability.STREAM_OUTPUT,
        RuntimeCapability.MULTI_FILE_EDIT,
        RuntimeCapability.AUTONOMOUS_LOOP,
    })

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        cfg = config or {}
        self._bin = cfg.get("bin") or os.environ.get("TASK_HARNESS_BIN", "task-harness")
        self._model = cfg.get("model") or os.environ.get("TASK_HARNESS_MODEL", "")
        self._provider = cfg.get("provider") or os.environ.get("TASK_HARNESS_PROVIDER", "")
        self._provider_profile = cfg.get("provider_profile") or os.environ.get(
            "TASK_HARNESS_PROVIDER_PROFILE", ""
        )
        self._workspace = cfg.get("workspace") or os.environ.get("TASK_HARNESS_WORKSPACE", ".")

    async def health_check(self) -> RuntimeHealth:
        t0 = time.monotonic()
        bin_path = shutil.which(self._bin)
        if not bin_path:
            return RuntimeHealth(
                runtime_id=self.RUNTIME_ID,
                available=False,
                error=(
                    f"Binary '{self._bin}' not found in PATH. Install a compatible harness "
                    "and point TASK_HARNESS_BIN at it."
                ),
            )
        try:
            proc = await asyncio.create_subprocess_exec(
                bin_path,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5.0)
            output = stdout.decode(errors="replace").strip() or stderr.decode(errors="replace").strip()
            latency_ms = (time.monotonic() - t0) * 1000
            return RuntimeHealth(
                runtime_id=self.RUNTIME_ID,
                available=proc.returncode == 0,
                version=(output.splitlines()[0] if output else "unknown"),
                latency_ms=round(latency_ms, 1),
                error=None if proc.returncode == 0 else output or f"exit {proc.returncode}",
                details={"bin_path": bin_path},
            )
        except Exception as exc:
            return RuntimeHealth(
                runtime_id=self.RUNTIME_ID,
                available=False,
                error=str(exc),
            )

    async def execute(self, spec: TaskSpec) -> TaskResult:
        bin_path = shutil.which(self._bin)
        if not bin_path:
            raise RuntimeUnavailableError(self.RUNTIME_ID, f"Binary '{self._bin}' not found")

        workspace = spec.workspace_path or self._workspace
        command = self._build_command(
            bin_path,
            workspace=workspace,
            model=spec.model_preference or self._model or None,
            provider=spec.provider_preference or self._provider or None,
            provider_profile=str(spec.context.get("provider_profile") or self._provider_profile or "") or None,
            ndjson=False,
            instruction=spec.instruction,
        )

        t0 = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=float(spec.timeout_sec))
        except asyncio.TimeoutError as exc:
            raise RuntimeExecutionError(
                self.RUNTIME_ID, f"Timeout after {spec.timeout_sec}s", spec.task_id
            ) from exc
        except Exception as exc:
            raise RuntimeExecutionError(self.RUNTIME_ID, str(exc), spec.task_id) from exc

        elapsed_ms = (time.monotonic() - t0) * 1000
        stdout_text = stdout.decode(errors="replace").strip()
        stderr_text = stderr.decode(errors="replace").strip()
        if proc.returncode != 0:
            raise RuntimeExecutionError(
                self.RUNTIME_ID,
                stderr_text or stdout_text or f"exit {proc.returncode}",
                spec.task_id,
            )

        try:
            report = json.loads(stdout_text)
        except json.JSONDecodeError as exc:
            raise RuntimeExecutionError(
                self.RUNTIME_ID,
                f"Invalid JSON from task harness run --json: {stdout_text[:500]}",
                spec.task_id,
            ) from exc

        usage = report.get("usage") or {}
        total_tokens = None
        if isinstance(usage, dict):
            total_tokens = sum(
                value for value in (
                    usage.get("input_tokens"),
                    usage.get("output_tokens"),
                )
                if isinstance(value, int)
            ) or None

        return TaskResult(
            runtime_id=self.RUNTIME_ID,
            task_id=spec.task_id,
            success=True,
            output=str(report.get("text") or ""),
            model_used=report.get("model") or spec.model_preference or self._model or None,
            provider_used=report.get("provider") or spec.provider_preference or self._provider or None,
            tokens_used=total_tokens,
            execution_time_ms=elapsed_ms,
            metadata={
                "session_id": report.get("session_id"),
                "usage": usage,
                "stderr": stderr_text[:1000],
            },
        )

    async def stream_execute(self, spec: TaskSpec) -> AsyncIterator[str]:
        bin_path = shutil.which(self._bin)
        if not bin_path:
            raise RuntimeUnavailableError(self.RUNTIME_ID, f"Binary '{self._bin}' not found")

        workspace = spec.workspace_path or self._workspace
        command = self._build_command(
            bin_path,
            workspace=workspace,
            model=spec.model_preference or self._model or None,
            provider=spec.provider_preference or self._provider or None,
            provider_profile=str(spec.context.get("provider_profile") or self._provider_profile or "") or None,
            ndjson=True,
            instruction=spec.instruction,
        )

        try:
            proc = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace,
            )
        except Exception as exc:
            raise RuntimeExecutionError(self.RUNTIME_ID, str(exc), spec.task_id) from exc

        collected_text = ""
        try:
            assert proc.stdout is not None
            while True:
                line = await asyncio.wait_for(proc.stdout.readline(), timeout=float(spec.timeout_sec))
                if not line:
                    break
                raw = line.decode(errors="replace").strip()
                if not raw:
                    continue
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                event_type = event.get("type")
                if event_type == "text_delta":
                    chunk = str(event.get("text") or "")
                    collected_text += chunk
                    if chunk:
                        yield chunk
                elif event_type == "text_replace":
                    text = str(event.get("text") or "")
                    if text and text != collected_text:
                        collected_text = text
                        yield text
                elif event_type == "done":
                    final_text = str(event.get("text") or "")
                    if final_text and final_text != collected_text:
                        yield final_text
                    break
                elif event_type == "error":
                    raise RuntimeExecutionError(
                        self.RUNTIME_ID,
                        str(event.get("message") or "task harness stream error"),
                        spec.task_id,
                    )
            stderr = await proc.stderr.read() if proc.stderr else b""
            await asyncio.wait_for(proc.wait(), timeout=5.0)
            if proc.returncode != 0:
                raise RuntimeExecutionError(
                    self.RUNTIME_ID,
                    stderr.decode(errors="replace").strip() or f"exit {proc.returncode}",
                    spec.task_id,
                )
        except asyncio.TimeoutError as exc:
            proc.kill()
            raise RuntimeExecutionError(
                self.RUNTIME_ID, f"Timeout after {spec.timeout_sec}s", spec.task_id
            ) from exc

    def _build_command(
        self,
        bin_path: str,
        *,
        workspace: str,
        model: str | None,
        provider: str | None,
        provider_profile: str | None,
        ndjson: bool,
        instruction: str,
    ) -> list[str]:
        command = [bin_path, "--quiet", "-C", workspace]
        if provider:
            command.extend(["--provider", provider])
        if provider_profile:
            command.extend(["--provider-profile", provider_profile])
        if model:
            command.extend(["--model", model])
        command.extend(["run", "--ndjson" if ndjson else "--json", instruction])
        return command

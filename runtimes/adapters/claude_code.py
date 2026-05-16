"""runtimes/adapters/claude_code.py — Claude Code CLI adapter (FIRST CLASS).

Claude Code (https://docs.anthropic.com/claude-code) is Anthropic's official
AI coding CLI.  It runs as a subprocess with `--print` for non-interactive
execution, making it suitable for autonomous agent tasks.

Integration mode: SUBPROCESS
Tier: FIRST CLASS

Key capabilities:
  - Deep repo understanding (multi-file, multi-turn context)
  - Complex refactoring and bug fixing
  - Security review and risky-module analysis
  - Autonomous coding with full shell/file access
  - Skills and hooks system for reproducible workflows

Configuration (env vars or constructor config dict):
  CLAUDE_CODE_BIN          — Path to claude binary (default: claude)
  CLAUDE_CODE_MODEL        — Model to use (default: claude-sonnet-4-6)
  CLAUDE_CODE_WORKSPACE    — Working directory (default: .)
  CLAUDE_CODE_TIMEOUT_SEC  — Task timeout seconds (default: 600)
  ANTHROPIC_API_KEY        — Required for Claude Code to call Anthropic API
"""
from __future__ import annotations

import asyncio
import logging
import os
import shutil
import time
from typing import Any

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

log = logging.getLogger("runtime.claude_code")


class ClaudeCodeAdapter(RuntimeAdapter):
    """Adapter for Claude Code CLI — FIRST CLASS autonomous coding runtime."""

    RUNTIME_ID       = "claude_code"
    DISPLAY_NAME     = "Claude Code"
    DESCRIPTION      = (
        "Anthropic Claude Code CLI — deep repo understanding, complex "
        "refactoring, security review, and multi-file autonomous coding."
    )
    TIER             = RuntimeTier.FIRST_CLASS
    INTEGRATION_MODE = IntegrationMode.EXTERNAL_PROCESS
    DOCS_URL         = "https://docs.anthropic.com/claude-code"
    CAPABILITIES     = frozenset({
        RuntimeCapability.CODE_GENERATION,
        RuntimeCapability.CODE_REVIEW,
        RuntimeCapability.REPO_EDITING,
        RuntimeCapability.GIT_OPERATIONS,
        RuntimeCapability.FILE_READ_WRITE,
        RuntimeCapability.TOOL_USE,
        RuntimeCapability.SHELL_EXEC,
        RuntimeCapability.MULTI_FILE_EDIT,
        RuntimeCapability.STREAM_OUTPUT,
        RuntimeCapability.AUTONOMOUS_LOOP,
        RuntimeCapability.WEB_BROWSE,
        RuntimeCapability.AGENT_DELEGATION,
    })

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        cfg = config or {}
        self._bin = cfg.get("bin") or os.environ.get("CLAUDE_CODE_BIN", "claude")
        self._model = cfg.get("model") or os.environ.get(
            "CLAUDE_CODE_MODEL", "claude-sonnet-4-6"
        )
        self._workspace = cfg.get("workspace") or os.environ.get("CLAUDE_CODE_WORKSPACE", ".")
        self._timeout = int(
            cfg.get("timeout_sec") or os.environ.get("CLAUDE_CODE_TIMEOUT_SEC", "600")
        )

    def required_dependencies(self) -> list[RuntimeDependency]:
        deps = [
            RuntimeDependency(
                name="claude",
                config_var="CLAUDE_CODE_BIN",
                install_hint=(
                    "Install Claude Code: `npm install -g @anthropic-ai/claude-code` "
                    "or download from https://docs.anthropic.com/claude-code"
                ),
            ),
        ]
        if not os.environ.get("ANTHROPIC_API_KEY"):
            deps.append(RuntimeDependency(
                name="ANTHROPIC_API_KEY",
                config_var="ANTHROPIC_API_KEY",
                install_hint="Set ANTHROPIC_API_KEY environment variable with your Anthropic API key.",
            ))
        return deps

    # ── Health ────────────────────────────────────────────────────────────────

    async def health_check(self) -> RuntimeHealth:
        bin_path = shutil.which(self._bin)
        if not bin_path:
            return RuntimeHealth(
                runtime_id=self.RUNTIME_ID,
                available=False,
                error=f"'{self._bin}' not found in PATH. Install: npm install -g @anthropic-ai/claude-code",
            )
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return RuntimeHealth(
                runtime_id=self.RUNTIME_ID,
                available=False,
                error="ANTHROPIC_API_KEY not set — Claude Code cannot authenticate",
            )
        t0 = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_exec(
                bin_path, "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10.0)
            latency_ms = (time.monotonic() - t0) * 1000
            version = stdout.decode(errors="replace").strip().split("\n")[0]
            return RuntimeHealth(
                runtime_id=self.RUNTIME_ID,
                available=True,
                version=version or "unknown",
                latency_ms=round(latency_ms, 1),
                details={"bin": bin_path, "model": self._model},
            )
        except asyncio.TimeoutError:
            return RuntimeHealth(runtime_id=self.RUNTIME_ID, available=False,
                                 error="--version timed out")
        except Exception as exc:
            return RuntimeHealth(runtime_id=self.RUNTIME_ID, available=False, error=str(exc))

    # ── Execution ─────────────────────────────────────────────────────────────

    async def execute(self, spec: TaskSpec) -> TaskResult:
        bin_path = shutil.which(self._bin)
        if not bin_path:
            raise RuntimeUnavailableError(
                self.RUNTIME_ID, f"'{self._bin}' not found in PATH"
            )
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeUnavailableError(
                self.RUNTIME_ID, "ANTHROPIC_API_KEY not set"
            )

        workspace = spec.workspace_path or self._workspace
        model = spec.model_preference or self._model

        cmd = [
            bin_path,
            "--print",                          # non-interactive output mode
            "--dangerously-skip-permissions",   # autonomous execution
            "--model", model,
            spec.instruction,
        ]

        env = {**os.environ}
        if spec.context:
            env["CLAUDE_CODE_TASK_CONTEXT"] = json_safe(spec.context)

        t0 = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace,
                env=env,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=float(spec.timeout_sec or self._timeout),
                )
            except asyncio.TimeoutError as exc:
                proc.kill()
                raise RuntimeExecutionError(
                    self.RUNTIME_ID,
                    f"Claude Code task timed out after {spec.timeout_sec}s",
                    spec.task_id,
                ) from exc
        except RuntimeExecutionError:
            raise
        except Exception as exc:
            raise RuntimeExecutionError(
                self.RUNTIME_ID, f"Subprocess error: {exc}", spec.task_id
            ) from exc

        elapsed_ms = (time.monotonic() - t0) * 1000
        rc = proc.returncode
        out = stdout.decode(errors="replace").strip()
        err = stderr.decode(errors="replace").strip()

        success = rc == 0
        output = out or err

        if not success:
            log.warning(
                "ClaudeCode task %s exited %d: %s",
                spec.task_id, rc, err[:200],
            )

        return TaskResult(
            runtime_id=self.RUNTIME_ID,
            task_id=spec.task_id,
            success=success,
            output=output,
            model_used=model,
            provider_used="anthropic",
            execution_time_ms=elapsed_ms,
            metadata={"exit_code": rc, "stderr": err[:500] if err else ""},
        )


def json_safe(obj: Any) -> str:
    import json
    try:
        return json.dumps(obj)
    except Exception:
        return str(obj)

"""runtimes/adapters/jcode.py — jcode adapter (TIER 2).

jcode (https://github.com/1jehuang/jcode) is a high-performance Rust-based
AI coding agent.  It connects to any OpenAI-compatible endpoint, making it a
natural client for this proxy.

Integration modes:
  - CLI (default): spawn `jcode` with --provider-url pointing at the proxy
  - HTTP API: connect to an already-running jcode server via JCODE_BASE_URL

Tier: TIER_2 (high-performance local coding client; first-class integration
comes when the jcode HTTP server API stabilises)

Key capabilities over other adapters:
  - Sub-15 ms boot time, ~28 MB RAM footprint
  - Semantic vector memory (cosine-similarity recall across turns)
  - Multi-agent swarm coordination
  - Built-in browser automation (Firefox Agent Bridge)
  - MCP connectivity via .jcode/mcp.json

Configuration (env vars or constructor config dict):
  JCODE_BIN          — Path to jcode binary (default: jcode)
  JCODE_BASE_URL     — HTTP API URL if running jcode in server mode (optional)
  JCODE_PROVIDER_URL — OpenAI-compatible base URL passed to jcode CLI
                       (default: http://localhost:8000/v1)
  JCODE_MODEL        — Default model (default: env AGENT_EXECUTOR_MODEL)
  JCODE_API_KEY      — API key passed to jcode CLI (default: env PROXY_API_KEY)
  JCODE_WORKSPACE    — Default workspace root (default: .)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import time
from pathlib import Path
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

log = logging.getLogger("runtime.jcode")


class JCodeAdapter(RuntimeAdapter):
    """Adapter for jcode — TIER 2 high-performance Rust coding agent."""

    RUNTIME_ID      = "jcode"
    DISPLAY_NAME    = "jcode"
    DESCRIPTION     = (
        "1jehuang/jcode — high-performance Rust-based AI coding agent with "
        "semantic vector memory, multi-agent swarm, browser automation, and "
        "MCP connectivity. Connects to the local proxy as its OpenAI provider."
    )
    TIER            = RuntimeTier.TIER_2
    INTEGRATION_MODE = IntegrationMode.EXTERNAL_PROCESS
    DOCS_URL        = "https://github.com/1jehuang/jcode"
    CAPABILITIES    = frozenset({
        RuntimeCapability.CODE_GENERATION,
        RuntimeCapability.CODE_REVIEW,
        RuntimeCapability.REPO_EDITING,
        RuntimeCapability.FILE_READ_WRITE,
        RuntimeCapability.TOOL_USE,
        RuntimeCapability.MCP_CONNECTIVITY,
        RuntimeCapability.MEMORY_SESSIONS,
        RuntimeCapability.STREAM_OUTPUT,
        RuntimeCapability.MULTI_FILE_EDIT,
        RuntimeCapability.SHELL_EXEC,
        RuntimeCapability.WEB_BROWSE,
        RuntimeCapability.AUTONOMOUS_LOOP,
    })

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        cfg = config or {}
        self._bin = cfg.get("bin") or os.environ.get("JCODE_BIN", "jcode")
        self._base_url = cfg.get("base_url") or os.environ.get("JCODE_BASE_URL", "")
        self._provider_url = cfg.get("provider_url") or os.environ.get(
            "JCODE_PROVIDER_URL",
            os.environ.get("PROXY_BASE_URL", "http://localhost:8000") + "/v1",
        )
        self._model = cfg.get("model") or os.environ.get(
            "JCODE_MODEL", os.environ.get("AGENT_EXECUTOR_MODEL", "qwen3-coder:30b")
        )
        self._api_key = cfg.get("api_key") or os.environ.get(
            "JCODE_API_KEY", os.environ.get("PROXY_API_KEY", "")
        )
        self._workspace = cfg.get("workspace") or os.environ.get("JCODE_WORKSPACE", ".")

    def required_dependencies(self) -> list[RuntimeDependency]:
        if self._base_url:
            return []
        return [
            RuntimeDependency(
                name="jcode",
                config_var="JCODE_BIN",
                install_hint=(
                    "Install jcode from https://github.com/1jehuang/jcode "
                    "and ensure the binary is on PATH, or set JCODE_BIN."
                ),
            )
        ]

    # ── Health ────────────────────────────────────────────────────────────────

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
                error=(
                    f"Binary '{self._bin}' not found in PATH. "
                    "Install from https://github.com/1jehuang/jcode or set JCODE_BIN."
                ),
            )
        try:
            proc = await asyncio.create_subprocess_exec(
                bin_path, "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5.0)
            latency_ms = (time.monotonic() - t0) * 1000
            version_output = stdout.decode(errors="replace").strip() or stderr.decode(errors="replace").strip()
            return RuntimeHealth(
                runtime_id=self.RUNTIME_ID,
                available=True,
                version=version_output.split("\n")[0] or "unknown",
                latency_ms=round(latency_ms, 1),
                details={
                    "bin_path": bin_path,
                    "provider_url": self._provider_url,
                    "model": self._model,
                },
            )
        except Exception as exc:
            return RuntimeHealth(runtime_id=self.RUNTIME_ID, available=False, error=str(exc))

    # ── Execution ─────────────────────────────────────────────────────────────

    async def execute(self, spec: TaskSpec) -> TaskResult:
        if self._base_url:
            return await self._execute_via_http(spec)
        return await self._execute_via_cli(spec)

    async def _execute_via_cli(self, spec: TaskSpec) -> TaskResult:
        bin_path = shutil.which(self._bin)
        if not bin_path:
            raise RuntimeUnavailableError(
                self.RUNTIME_ID,
                f"Binary '{self._bin}' not found. Install jcode or set JCODE_BIN.",
            )

        workspace = spec.workspace_path or self._workspace
        model = spec.model_preference or self._model
        provider_url = self._provider_url

        cmd = [bin_path, "run", "--no-interactive", "--json"]
        if provider_url:
            cmd.extend(["--provider-url", provider_url])
        if self._api_key:
            cmd.extend(["--api-key", self._api_key])
        if model:
            cmd.extend(["--model", model])
        cmd.extend(["--workspace", workspace])
        cmd.append("--")
        cmd.append(spec.instruction)

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
        stdout_text = stdout.decode(errors="replace").strip()
        stderr_text = stderr.decode(errors="replace").strip()

        output = stdout_text or stderr_text
        tokens_used: int | None = None

        if stdout_text:
            try:
                data = json.loads(stdout_text)
                output = str(data.get("output") or data.get("text") or stdout_text)
                usage = data.get("usage") or {}
                if isinstance(usage, dict):
                    tokens_used = (usage.get("total_tokens") or
                                   (usage.get("input_tokens", 0) + usage.get("output_tokens", 0))
                                   ) or None
            except (json.JSONDecodeError, TypeError):
                output = stdout_text

        return TaskResult(
            runtime_id=self.RUNTIME_ID,
            task_id=spec.task_id,
            success=success,
            output=output,
            model_used=model,
            provider_used="local-proxy",
            tokens_used=tokens_used,
            execution_time_ms=elapsed_ms,
            metadata={
                "returncode": proc.returncode,
                "stderr": stderr_text[:500],
                "provider_url": provider_url,
            },
        )

    async def _execute_via_http(self, spec: TaskSpec) -> TaskResult:
        payload: dict[str, Any] = {
            "instruction": spec.instruction,
            "model": spec.model_preference or self._model,
            "workspace": spec.workspace_path or self._workspace,
            "task_id": spec.task_id,
        }
        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=float(spec.timeout_sec + 10)) as client:
                resp = await client.post(
                    f"{self._base_url}/run",
                    json=payload,
                    headers={"Authorization": f"Bearer {self._api_key}"} if self._api_key else {},
                )
        except httpx.ConnectError as exc:
            raise RuntimeUnavailableError(self.RUNTIME_ID, str(exc)) from exc
        except httpx.TimeoutException as exc:
            raise RuntimeExecutionError(
                self.RUNTIME_ID, f"Timeout after {spec.timeout_sec}s", spec.task_id
            ) from exc

        elapsed_ms = (time.monotonic() - t0) * 1000
        if resp.status_code not in (200, 201):
            raise RuntimeExecutionError(
                self.RUNTIME_ID, f"HTTP {resp.status_code}", spec.task_id
            )
        data = resp.json()
        usage = data.get("usage") or {}
        tokens_used = (
            usage.get("total_tokens") or
            (usage.get("input_tokens", 0) + usage.get("output_tokens", 0))
        ) or None
        return TaskResult(
            runtime_id=self.RUNTIME_ID,
            task_id=spec.task_id,
            success=data.get("success", True),
            output=str(data.get("output") or data.get("text") or ""),
            artifacts=data.get("artifacts", []),
            model_used=data.get("model_used", spec.model_preference or self._model),
            provider_used="local-proxy",
            tokens_used=tokens_used,
            execution_time_ms=elapsed_ms,
        )

    # ── MCP config helper ─────────────────────────────────────────────────────

    def write_mcp_config(self, workspace_path: str | None = None, proxy_url: str | None = None) -> Path:
        """Write .jcode/mcp.json in the workspace, pointing at our proxy's MCP endpoint.

        jcode reads .jcode/mcp.json for project-local MCP server configuration.
        This makes the local proxy's skills/tools available to jcode automatically.
        """
        root = Path(workspace_path or self._workspace).expanduser().resolve()
        config_dir = root / ".jcode"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "mcp.json"

        base = (proxy_url or self._provider_url or "http://localhost:8000/v1").rstrip("/v1").rstrip("/")
        mcp_config = {
            "mcpServers": {
                "local-llm-proxy": {
                    "type": "sse",
                    "url": f"{base}/mcp",
                    "headers": {
                        "Authorization": f"Bearer {self._api_key}"
                    } if self._api_key else {},
                }
            }
        }
        config_path.write_text(json.dumps(mcp_config, indent=2), encoding="utf-8")
        log.info("Wrote jcode MCP config to %s", config_path)
        return config_path

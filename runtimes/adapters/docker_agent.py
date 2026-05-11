"""runtimes/adapters/docker_agent.py — Docker-based agent runtime adapter.

Spawns a fresh Docker container for each task execution to provide
strong isolation, similar to the E2B setup in CompanyHelm.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import secrets
import time
from pathlib import Path
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

log = logging.getLogger("runtime.docker_agent")

class DockerAgentAdapter(RuntimeAdapter):
    """Adapter that runs agent tasks inside isolated Docker containers."""

    RUNTIME_ID = "docker_agent"
    DISPLAY_NAME = "Docker Agent (Isolated)"
    DESCRIPTION = "Runs agent tasks in fresh, isolated Docker containers."
    TIER = RuntimeTier.FIRST_CLASS
    INTEGRATION_MODE = IntegrationMode.EXTERNAL_PROCESS
    DOCS_URL = ""
    CAPABILITIES = frozenset({
        RuntimeCapability.CODE_GENERATION,
        RuntimeCapability.CODE_REVIEW,
        RuntimeCapability.REPO_EDITING,
        RuntimeCapability.FILE_READ_WRITE,
        RuntimeCapability.TOOL_USE,
        RuntimeCapability.SHELL_EXEC,
        RuntimeCapability.AUTONOMOUS_LOOP,
    })

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._image = (config or {}).get("image") or os.environ.get("AGENT_DOCKER_IMAGE", "local-llm-server-runtime:latest")
        self._network = (config or {}).get("network") or os.environ.get("AGENT_DOCKER_NETWORK", "host")

    async def health_check(self) -> RuntimeHealth:
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            available = proc.returncode == 0
            return RuntimeHealth(runtime_id=self.RUNTIME_ID, available=available, details={"image": self._image})
        except Exception as e:
            return RuntimeHealth(runtime_id=self.RUNTIME_ID, available=False, error=str(e))

    async def execute(self, spec: TaskSpec) -> TaskResult:
        container_name = f"agent-task-{spec.task_id}-{secrets.token_hex(4)}"
        workspace_path = Path(spec.workspace_path).resolve()
        log.info(f"Starting Docker container {container_name} for task {spec.task_id}")
        try:
            run_cmd = ["docker", "run", "-d", "--name", container_name, "--network", self._network, "-v", f"{workspace_path}:/app/workspace", "-e", f"OLLAMA_BASE={os.environ.get('OLLAMA_BASE', 'http://localhost:11434')}", "-e", f"GITHUB_TOKEN={spec.context.get('github_token', '')}", self._image]
            proc = await asyncio.create_subprocess_exec(*run_cmd)
            await proc.wait()
            if proc.returncode != 0: raise RuntimeExecutionError(self.RUNTIME_ID, "Failed to start Docker container", spec.task_id)
            container_url = "http://localhost:8080"
            async with httpx.AsyncClient(timeout=30.0) as client:
                for _ in range(15):
                    try:
                        resp = await client.get(f"{container_url}/health")
                        if resp.status_code == 200: break
                    except: pass
                    await asyncio.sleep(1.0)
                else: raise RuntimeExecutionError(self.RUNTIME_ID, "Container timed out starting", spec.task_id)
                payload = {"task_id": spec.task_id, "instruction": spec.instruction, "workspace_path": "/app/workspace", "model": spec.model_preference, "context": spec.context}
                resp = await client.post(f"{container_url}/tasks", json=payload)
                resp.raise_for_status()
                result_data = resp.json()
                if result_data.get("status") in ("queued", "running"):
                    while True:
                        await asyncio.sleep(2.0)
                        resp = await client.get(f"{container_url}/tasks/{spec.task_id}")
                        result_data = resp.json()
                        if result_data.get("status") not in ("queued", "running"): break
            return TaskResult(runtime_id=self.RUNTIME_ID, task_id=spec.task_id, success=result_data.get("success", False), output=result_data.get("output", ""), artifacts=result_data.get("artifacts", []), model_used=result_data.get("model_used"), provider_used=result_data.get("provider_used"), metadata=result_data.get("metadata", {}))
        finally:
            stop_proc = await asyncio.create_subprocess_exec("docker", "rm", "-f", container_name)
            await stop_proc.wait()

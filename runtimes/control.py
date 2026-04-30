"""runtimes/control.py — Runtime lifecycle management (start/stop/restart).

Provides endpoints to start, stop, and restart individual runtime containers.
When Docker is not available, falls back to spawning local subprocess wrappers.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from runtimes.manager import get_runtime_manager

log = logging.getLogger("qwen-proxy")

RUNTIME_CONTAINERS = {
    "hermes": "hermes",
    "opencode": "opencode",
    "goose": "goose",
    "aider": "aider",
}

# Local subprocess fallback ports (when Docker is unavailable)
RUNTIME_LOCAL_PORTS = {
    "hermes": 8100,
    "opencode": 8101,
    "goose": 8102,
    "aider": 8103,
}

# Keep track of locally-spawned runtime processes
_local_runtime_processes: dict[str, subprocess.Popen] = {}


def _get_ollama_base() -> str:
    """Return the Ollama base URL from environment or default."""
    return (
        os.environ.get("OLLAMA_BASE")
        or os.environ.get("OLLAMA_BASE_URL")
        or "http://localhost:11434"
    )


def _find_agent_runtime_script() -> Path | None:
    """Find the docker/agent_runtime.py script relative to this file."""
    candidate = Path(__file__).resolve().parent.parent / "docker" / "agent_runtime.py"
    if candidate.is_file():
        return candidate
    # Fallback: search in cwd
    candidate = Path.cwd() / "docker" / "agent_runtime.py"
    if candidate.is_file():
        return candidate
    return None


def _update_adapter_base_url(runtime_id: str, base_url: str) -> None:
    """Update the adapter's configured base URL so health checks hit the local process."""
    try:
        manager = get_runtime_manager()
        adapter = manager._registry.get(runtime_id)
        if adapter is None:
            return
        # Update the adapter's internal base URL if it has one
        if hasattr(adapter, "_base_url"):
            adapter._base_url = base_url
            log.info("Updated %s adapter base_url to %s", runtime_id, base_url)
    except Exception as exc:
        log.debug("Could not update adapter base_url for %s: %s", runtime_id, exc)


async def _start_local_runtime(runtime_id: str) -> dict[str, Any]:
    """Start a runtime as a local subprocess wrapper."""
    port = RUNTIME_LOCAL_PORTS.get(runtime_id)
    if port is None:
        return {
            "runtime_id": runtime_id,
            "action": "start",
            "status": "error",
            "error": f"No local port configured for runtime: {runtime_id}",
        }

    # Check if already running
    existing = _local_runtime_processes.get(runtime_id)
    if existing is not None and existing.poll() is None:
        base_url = f"http://localhost:{port}"
        _update_adapter_base_url(runtime_id, base_url)
        return {
            "runtime_id": runtime_id,
            "action": "start",
            "status": "already_running",
            "mode": "local_subprocess",
            "base_url": base_url,
        }

    script = _find_agent_runtime_script()
    if script is None:
        return {
            "runtime_id": runtime_id,
            "action": "start",
            "status": "error",
            "error": "agent_runtime.py wrapper script not found",
        }

    python_exe = sys.executable
    env = os.environ.copy()
    env["RUNTIME_NAME"] = runtime_id
    env["OLLAMA_BASE"] = _get_ollama_base()
    env["DEFAULT_MODEL"] = os.environ.get("DEFAULT_MODEL", "qwen3-coder:30b")
    env["PORT"] = str(port)

    try:
        proc = subprocess.Popen(
            [python_exe, str(script)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        _local_runtime_processes[runtime_id] = proc
        log.info("Started local runtime %s on port %d (pid=%d)", runtime_id, port, proc.pid)

        # Wait briefly for startup
        await asyncio.sleep(2.0)

        base_url = f"http://localhost:{port}"
        _update_adapter_base_url(runtime_id, base_url)

        # Trigger an immediate health check so the UI updates quickly
        try:
            manager = get_runtime_manager()
            asyncio.get_event_loop().create_task(
                manager.refresh_runtime_health(runtime_id)
            )
        except Exception as exc:
            log.debug("Could not trigger health refresh: %s", exc)

        return {
            "runtime_id": runtime_id,
            "action": "start",
            "status": "started",
            "mode": "local_subprocess",
            "base_url": base_url,
            "pid": proc.pid,
        }
    except Exception as exc:
        log.error("Failed to start local runtime %s: %s", runtime_id, exc)
        return {
            "runtime_id": runtime_id,
            "action": "start",
            "status": "error",
            "error": str(exc),
        }


async def _stop_local_runtime(runtime_id: str) -> dict[str, Any]:
    """Stop a locally-spawned runtime subprocess."""
    proc = _local_runtime_processes.pop(runtime_id, None)
    if proc is None:
        return {
            "runtime_id": runtime_id,
            "action": "stop",
            "status": "not_running",
            "mode": "local_subprocess",
        }

    try:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        log.info("Stopped local runtime %s (pid was %d)", runtime_id, proc.pid)
        return {
            "runtime_id": runtime_id,
            "action": "stop",
            "status": "stopped",
            "mode": "local_subprocess",
        }
    except Exception as exc:
        log.error("Error stopping local runtime %s: %s", runtime_id, exc)
        return {
            "runtime_id": runtime_id,
            "action": "stop",
            "status": "error",
            "error": str(exc),
        }


async def _runtime_health(runtime_id: str) -> dict[str, Any]:
    manager = get_runtime_manager()
    runtime = manager.get_runtime(runtime_id)
    if runtime is None:
        return {"available": False, "error": f"Unknown runtime: {runtime_id}"}
    health = runtime.get("health") or {}
    return health if isinstance(health, dict) else {"available": False}


def _is_docker_unavailable(error_lower: str) -> bool:
    """Return True when the error string indicates Docker is not reachable."""
    patterns = (
        "only available when running locally",
        "docker daemon",
        "cannot connect",
        "docker.sock",
        "daemon is running",
        "failed to connect to the docker",
    )
    return any(p in error_lower for p in patterns)


async def _remote_runtime_response(runtime_id: str, action: str) -> dict[str, Any]:
    health = await _runtime_health(runtime_id)
    available = health.get("available") is True
    if available:
        return {
            "runtime_id": runtime_id,
            "action": action,
            "status": "remote_managed",
            "remote_managed": True,
            "message": (
                "This runtime is reachable through its configured endpoint. "
                "No local Docker action is needed in this environment."
            ),
            "health": health,
        }

    return {
        "runtime_id": runtime_id,
        "action": action,
        "status": "docker_unavailable",
        "docker_unavailable": True,
        "remote_managed": False,
        "message": (
            "Local Docker lifecycle control is unavailable here. "
            "If this runtime is hosted remotely, manage it on that host and use Refresh Health to verify connectivity."
        ),
        "health": health,
    }


async def start_runtime(runtime_id: str) -> dict[str, Any]:
    """Start a runtime container."""
    if runtime_id not in RUNTIME_CONTAINERS:
        return {"error": f"Unknown runtime: {runtime_id}"}

    container_name = RUNTIME_CONTAINERS[runtime_id]
    try:
        subprocess.run(
            ["docker", "compose", "up", "-d", "--no-deps", "--no-recreate", container_name],
            check=True,
            capture_output=True,
            timeout=120,
        )
        log.info("Started runtime: %s", runtime_id)
        return {
            "runtime_id": runtime_id,
            "action": "start",
            "status": "started",
        }
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        if _is_docker_unavailable(error_msg.lower()):
            remote_resp = await _remote_runtime_response(runtime_id, "start")
            if remote_resp.get("remote_managed"):
                return remote_resp
            return await _start_local_runtime(runtime_id)
        log.error("Failed to start %s: %s", runtime_id, error_msg)
        return {
            "runtime_id": runtime_id,
            "action": "start",
            "status": "error",
            "error": error_msg,
        }
    except FileNotFoundError:
        # Docker not in PATH — check if already reachable, else try local subprocess fallback
        remote_resp = await _remote_runtime_response(runtime_id, "start")
        if remote_resp.get("remote_managed"):
            return remote_resp
        return await _start_local_runtime(runtime_id)
    except Exception as e:
        log.error("Error starting %s: %s", runtime_id, e)
        return {
            "runtime_id": runtime_id,
            "action": "start",
            "status": "error",
            "error": str(e),
        }


async def stop_runtime(runtime_id: str) -> dict[str, Any]:
    """Stop a runtime container."""
    if runtime_id not in RUNTIME_CONTAINERS:
        return {"error": f"Unknown runtime: {runtime_id}"}

    container_name = RUNTIME_CONTAINERS[runtime_id]
    try:
        subprocess.run(
            ["docker", "compose", "stop", container_name],
            check=True,
            capture_output=True,
            timeout=60,
        )
        log.info("Stopped runtime: %s", runtime_id)
        return {
            "runtime_id": runtime_id,
            "action": "stop",
            "status": "stopped",
        }
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        if _is_docker_unavailable(error_msg.lower()):
            remote_resp = await _remote_runtime_response(runtime_id, "stop")
            if remote_resp.get("remote_managed"):
                return remote_resp
            return await _stop_local_runtime(runtime_id)
        log.error("Failed to stop %s: %s", runtime_id, error_msg)
        return {
            "runtime_id": runtime_id,
            "action": "stop",
            "status": "error",
            "error": error_msg,
        }
    except FileNotFoundError:
        # Docker not in PATH — check if already reachable, else try local subprocess fallback
        remote_resp = await _remote_runtime_response(runtime_id, "stop")
        if remote_resp.get("remote_managed"):
            return remote_resp
        return await _stop_local_runtime(runtime_id)
    except Exception as e:
        log.error("Error stopping %s: %s", runtime_id, e)
        return {
            "runtime_id": runtime_id,
            "action": "stop",
            "status": "error",
            "error": str(e),
        }


async def start_all_runtimes() -> dict[str, Any]:
    """Start all runtime containers."""
    results = {}
    for runtime_id in RUNTIME_CONTAINERS.keys():
        results[runtime_id] = await start_runtime(runtime_id)
    log.info("Started all runtimes")
    return {"runtimes": results}


async def stop_all_runtimes() -> dict[str, Any]:
    """Stop all runtime containers."""
    results = {}
    for runtime_id in RUNTIME_CONTAINERS.keys():
        results[runtime_id] = await stop_runtime(runtime_id)
    log.info("Stopped all runtimes")
    return {"runtimes": results}

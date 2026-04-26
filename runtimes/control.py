"""runtimes/control.py — Runtime lifecycle management (start/stop/restart).

Provides endpoints to start, stop, and restart individual runtime containers.
"""

from __future__ import annotations

import logging
import subprocess
from typing import Any

from runtimes.manager import get_runtime_manager

log = logging.getLogger("qwen-proxy")

RUNTIME_CONTAINERS = {
    "hermes": "hermes",
    "opencode": "opencode",
    "goose": "goose",
    "aider": "aider",
}


async def _runtime_health(runtime_id: str) -> dict[str, Any]:
    manager = get_runtime_manager()
    runtime = manager.get_runtime(runtime_id)
    if runtime is None:
        return {"available": False, "error": f"Unknown runtime: {runtime_id}"}
    health = runtime.get("health") or {}
    return health if isinstance(health, dict) else {"available": False}


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
        log.info(f"Started runtime: {runtime_id}")
        return {
            "runtime_id": runtime_id,
            "action": "start",
            "status": "started",
        }
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        if "only available when running locally" in error_msg.lower():
            return await _remote_runtime_response(runtime_id, "start")
        log.error(f"Failed to start {runtime_id}: {error_msg}")
        return {
            "runtime_id": runtime_id,
            "action": "start",
            "status": "error",
            "error": error_msg,
        }
    except FileNotFoundError:
        return await _remote_runtime_response(runtime_id, "start")
    except Exception as e:
        log.error(f"Error starting {runtime_id}: {e}")
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
        log.info(f"Stopped runtime: {runtime_id}")
        return {
            "runtime_id": runtime_id,
            "action": "stop",
            "status": "stopped",
        }
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        if "only available when running locally" in error_msg.lower():
            return await _remote_runtime_response(runtime_id, "stop")
        log.error(f"Failed to stop {runtime_id}: {error_msg}")
        return {
            "runtime_id": runtime_id,
            "action": "stop",
            "status": "error",
            "error": error_msg,
        }
    except FileNotFoundError:
        return await _remote_runtime_response(runtime_id, "stop")
    except Exception as e:
        log.error(f"Error stopping {runtime_id}: {e}")
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

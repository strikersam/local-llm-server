"""runtimes — Pluggable agent runtime abstraction layer.

This package provides a clean interface for integrating multiple AI agent
runtimes (Hermes, OpenCode, Goose, OpenHands, Aider) under a unified API
with local-first routing, circuit-breaker health checks, and a policy engine.

Quick start::

    from runtimes.manager import get_runtime_manager
    from runtimes.base import TaskSpec
    import secrets

    mgr = get_runtime_manager()
    await mgr.start()

    spec = TaskSpec(
        task_id=secrets.token_hex(8),
        instruction="Implement a binary search function in Python",
        task_type="code_generation",
    )
    result, decision = await mgr.execute(spec)
    print(result.output)
"""

from runtimes.base import (
    RuntimeAdapter,
    RuntimeCapability,
    RuntimeTier,
    IntegrationMode,
    RuntimeHealth,
    RuntimeDependency,
    RuntimeValidationIssue,
    RuntimeReadinessReport,
    TaskResult,
    TaskSpec,
    RuntimeUnavailableError,
    RuntimeExecutionError,
    RuntimePreflightError,
)
from runtimes.manager import RuntimeManager, get_runtime_manager
from runtimes.api import runtime_router

__all__ = [
    "RuntimeAdapter",
    "RuntimeCapability",
    "RuntimeTier",
    "IntegrationMode",
    "RuntimeHealth",
    "RuntimeDependency",
    "RuntimeValidationIssue",
    "RuntimeReadinessReport",
    "TaskResult",
    "TaskSpec",
    "RuntimeUnavailableError",
    "RuntimeExecutionError",
    "RuntimePreflightError",
    "RuntimeManager",
    "get_runtime_manager",
    "runtime_router",
]

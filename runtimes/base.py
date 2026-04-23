"""runtimes/base.py — RuntimeAdapter abstract base class.

Every agent runtime (Hermes, OpenCode, Goose, OpenHands, Aider) must
implement this interface.  The control plane talks exclusively through
this contract; it never imports runtime-specific code directly.

Design principles:
  - Async-first: all I/O methods are async.
  - Typed: all methods carry full type annotations.
  - Graceful degradation: unavailable runtimes raise RuntimeUnavailableError
    instead of propagating opaque errors up the stack.
  - Capability-aware: each adapter declares what it can do via CAPABILITIES.
  - Health-aware: adapters expose an async health_check() so the health
    service can poll without guessing.
"""

from __future__ import annotations

import abc
import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator

log = logging.getLogger("qwen-proxy")


# ── Capability flags ──────────────────────────────────────────────────────────

class RuntimeCapability(str, Enum):
    """Discrete capabilities a runtime may or may not support."""
    CODE_GENERATION   = "code_generation"
    CODE_REVIEW       = "code_review"
    REPO_EDITING      = "repo_editing"
    GIT_OPERATIONS    = "git_operations"
    FILE_READ_WRITE   = "file_read_write"
    TOOL_USE          = "tool_use"
    WEB_BROWSE        = "web_browse"
    SHELL_EXEC        = "shell_exec"
    AGENT_DELEGATION  = "agent_delegation"
    SCHEDULED_TASKS   = "scheduled_tasks"
    MEMORY_SESSIONS   = "memory_sessions"
    MCP_CONNECTIVITY  = "mcp_connectivity"
    STREAM_OUTPUT     = "stream_output"
    MULTI_FILE_EDIT   = "multi_file_edit"
    AUTONOMOUS_LOOP   = "autonomous_loop"


# ── Tier classification ────────────────────────────────────────────────────────

class RuntimeTier(str, Enum):
    FIRST_CLASS  = "first_class"   # Fully integrated, production-ready
    TIER_2       = "tier_2"        # Supported, may have some limitations
    TIER_3       = "tier_3"        # Specialized, narrow use-case
    EXPERIMENTAL = "experimental"  # Supported but marked unstable


# ── Integration mode ──────────────────────────────────────────────────────────

class IntegrationMode(str, Enum):
    NATIVE          = "native"          # Direct library/API integration
    SIDECAR         = "sidecar"         # External process managed as sidecar
    EXTERNAL_PROCESS = "external_process"  # Spawned on demand, not managed
    PARTIAL         = "partial"         # Some features via API, some missing
    EXPERIMENTAL    = "experimental"    # Proof-of-concept level


# ── Result / error types ──────────────────────────────────────────────────────

class RuntimeUnavailableError(Exception):
    """Raised when a runtime is offline or not installed."""

    def __init__(self, runtime_id: str, reason: str = "") -> None:
        self.runtime_id = runtime_id
        self.reason = reason
        super().__init__(f"Runtime '{runtime_id}' unavailable: {reason}")


class RuntimeExecutionError(Exception):
    """Raised when a runtime fails during task execution."""

    def __init__(self, runtime_id: str, message: str, task_id: str = "") -> None:
        self.runtime_id = runtime_id
        self.task_id = task_id
        super().__init__(f"Runtime '{runtime_id}' execution error: {message}")


@dataclass
class RuntimeHealth:
    """Health status snapshot for a runtime."""
    runtime_id: str
    available: bool
    version: str | None = None
    latency_ms: float | None = None
    error: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "available": self.available,
            "version": self.version,
            "latency_ms": self.latency_ms,
            "error": self.error,
            "details": self.details,
        }


@dataclass
class TaskResult:
    """Result returned by a runtime after executing a task."""
    runtime_id: str
    task_id: str
    success: bool
    output: str
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    model_used: str | None = None
    provider_used: str | None = None
    tokens_used: int | None = None
    cost_usd: float | None = None
    execution_time_ms: float | None = None
    escalation_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "task_id": self.task_id,
            "success": self.success,
            "output": self.output,
            "artifacts": self.artifacts,
            "tool_calls": self.tool_calls,
            "model_used": self.model_used,
            "provider_used": self.provider_used,
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
            "execution_time_ms": self.execution_time_ms,
            "escalation_reason": self.escalation_reason,
            "metadata": self.metadata,
        }


@dataclass
class TaskSpec:
    """Specification for a task to be executed by a runtime."""
    task_id: str
    instruction: str
    task_type: str = "general"          # e.g. code_generation, code_review, reasoning
    workspace_path: str | None = None
    repo_url: str | None = None
    model_preference: str | None = None
    provider_preference: str | None = None
    allow_paid_escalation: bool = False
    max_tokens: int | None = None
    timeout_sec: int = 300
    context: dict[str, Any] = field(default_factory=dict)
    tool_allowlist: list[str] | None = None  # None = all tools allowed


# ── Abstract base ─────────────────────────────────────────────────────────────

class RuntimeAdapter(abc.ABC):
    """Abstract base class every runtime adapter must implement.

    Subclasses must set the class-level metadata attributes and implement
    all abstract methods.  See individual adapters for examples.
    """

    # ── Class-level metadata (override in subclass) ───────────────────────────
    RUNTIME_ID: str = ""
    DISPLAY_NAME: str = ""
    DESCRIPTION: str = ""
    TIER: RuntimeTier = RuntimeTier.TIER_2
    INTEGRATION_MODE: IntegrationMode = IntegrationMode.EXTERNAL_PROCESS
    CAPABILITIES: frozenset[RuntimeCapability] = frozenset()
    DOCS_URL: str = ""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config: dict[str, Any] = config or {}
        self._log = logging.getLogger(f"runtime.{self.RUNTIME_ID}")

    # ── Required methods ──────────────────────────────────────────────────────

    @abc.abstractmethod
    async def health_check(self) -> RuntimeHealth:
        """Return a health snapshot.  Must not raise; return available=False instead."""
        ...

    @abc.abstractmethod
    async def execute(self, spec: TaskSpec) -> TaskResult:
        """Execute a task and return the result.

        Must handle its own timeout (spec.timeout_sec).
        May raise RuntimeUnavailableError or RuntimeExecutionError.
        """
        ...

    # ── Optional streaming ────────────────────────────────────────────────────

    async def stream_execute(
        self, spec: TaskSpec
    ) -> AsyncIterator[str]:
        """Stream output tokens/lines.  Default implementation runs execute()
        and yields the full output as a single chunk."""
        result = await self.execute(spec)
        yield result.output

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Called once when the runtime is registered.  Override to start
        a subprocess, initialise a connection pool, etc."""

    async def stop(self) -> None:
        """Called when the runtime is being unregistered or the server
        is shutting down.  Override to terminate subprocesses."""

    # ── Introspection ─────────────────────────────────────────────────────────

    def supports(self, capability: RuntimeCapability) -> bool:
        """Return True if this runtime supports the given capability."""
        return capability in self.CAPABILITIES

    def as_dict(self) -> dict[str, Any]:
        """Serialise adapter metadata (no secrets)."""
        return {
            "runtime_id": self.RUNTIME_ID,
            "display_name": self.DISPLAY_NAME,
            "description": self.DESCRIPTION,
            "tier": self.TIER.value,
            "integration_mode": self.INTEGRATION_MODE.value,
            "capabilities": sorted(c.value for c in self.CAPABILITIES),
            "docs_url": self.DOCS_URL,
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.RUNTIME_ID!r} tier={self.TIER.value}>"

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
import os
import shutil
from dataclasses import dataclass, field as dataclass_field
from enum import Enum
from pathlib import Path
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


class RuntimePreflightError(Exception):
    """Raised when a runtime fails readiness validation before execution starts."""

    def __init__(self, runtime_id: str, report: "RuntimeReadinessReport") -> None:
        self.runtime_id = runtime_id
        self.report = report
        super().__init__(
            f"Runtime '{runtime_id}' failed preflight: {report.summary or 'runtime is not ready'}"
        )


@dataclass
class RuntimeDependency:
    """One runtime dependency that can be validated during preflight."""

    name: str
    kind: str = "binary"
    config_var: str | None = None
    install_hint: str | None = None
    required: bool = True


@dataclass
class RuntimeValidationIssue:
    """Structured, actionable preflight validation issue."""

    code: str
    message: str
    field: str | None = None
    fix_hint: str | None = None
    details: dict[str, Any] = dataclass_field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "field": self.field,
            "fix_hint": self.fix_hint,
            "details": self.details,
        }


@dataclass
class RuntimeReadinessReport:
    """Preflight result returned before a runtime task starts."""

    runtime_id: str
    ready: bool
    health: RuntimeHealth | None = None
    selected_runtime: str | None = None
    workspace_path: str | None = None
    dependencies: list[RuntimeDependency] = dataclass_field(default_factory=list)
    tools: dict[str, Any] = dataclass_field(default_factory=dict)
    issues: list[RuntimeValidationIssue] = dataclass_field(default_factory=list)
    summary: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "selected_runtime": self.selected_runtime or self.runtime_id,
            "ready": self.ready,
            "summary": self.summary,
            "workspace_path": self.workspace_path,
            "health": self.health.as_dict() if self.health else None,
            "dependencies": [
                {
                    "name": dep.name,
                    "kind": dep.kind,
                    "config_var": dep.config_var,
                    "install_hint": dep.install_hint,
                    "required": dep.required,
                }
                for dep in self.dependencies
            ],
            "tools": self.tools,
            "issues": [issue.as_dict() for issue in self.issues],
        }


@dataclass
class RuntimeHealth:
    """Health status snapshot for a runtime."""
    runtime_id: str
    available: bool
    version: str | None = None
    latency_ms: float | None = None
    error: str | None = None
    details: dict[str, Any] = dataclass_field(default_factory=dict)

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
    artifacts: list[dict[str, Any]] = dataclass_field(default_factory=list)
    tool_calls: list[dict[str, Any]] = dataclass_field(default_factory=list)
    model_used: str | None = None
    provider_used: str | None = None
    tokens_used: int | None = None
    cost_usd: float | None = None
    execution_time_ms: float | None = None
    escalation_reason: str | None = None
    metadata: dict[str, Any] = dataclass_field(default_factory=dict)

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
    context: dict[str, Any] = dataclass_field(default_factory=dict)
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

    async def cleanup_workspace(self, workspace_path: str | None) -> None:
        """Clean up any runtime-owned workspace resources after execution."""

    def required_dependencies(self) -> list[RuntimeDependency]:
        """Return runtime-specific dependency declarations for preflight."""
        return []

    def tool_availability_report(self) -> dict[str, Any]:
        """Return a best-effort tool availability report for diagnostics."""
        tools: dict[str, Any] = {}
        for dependency in self.required_dependencies():
            if dependency.kind == "binary":
                configured_name = (
                    os.environ.get(dependency.config_var, dependency.name)
                    if dependency.config_var
                    else dependency.name
                )
                tools[dependency.name] = {
                    "kind": dependency.kind,
                    "configured": configured_name,
                    "resolved_path": shutil.which(configured_name),
                    "config_var": dependency.config_var,
                }
        return tools

    async def provision_workspace(self, workspace_path: str | None) -> tuple[str | None, list[RuntimeValidationIssue]]:
        """Ensure the requested workspace exists and is writable."""
        if not workspace_path:
            return None, []

        issues: list[RuntimeValidationIssue] = []
        path = Path(workspace_path).expanduser()
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            issues.append(
                RuntimeValidationIssue(
                    code="workspace_create_failed",
                    field="workspace_path",
                    message=f"Workspace '{path}' could not be created.",
                    fix_hint="Choose a writable workspace path or create it before retrying.",
                    details={"workspace_path": str(path), "error": str(exc)},
                )
            )
            return str(path), issues

        if not path.is_dir():
            issues.append(
                RuntimeValidationIssue(
                    code="workspace_not_directory",
                    field="workspace_path",
                    message=f"Workspace '{path}' is not a directory.",
                    fix_hint="Point the runtime at a directory path.",
                    details={"workspace_path": str(path)},
                )
            )
            return str(path), issues

        if not os.access(path, os.W_OK):
            issues.append(
                RuntimeValidationIssue(
                    code="workspace_not_writable",
                    field="workspace_path",
                    message=f"Workspace '{path}' is not writable.",
                    fix_hint="Grant write permissions or select a different workspace path.",
                    details={"workspace_path": str(path)},
                )
            )
        return str(path), issues

    async def validate_task_spec(self, spec: TaskSpec) -> list[RuntimeValidationIssue]:
        """Validate task-specific prerequisites beyond runtime dependencies."""
        issues: list[RuntimeValidationIssue] = []
        if (spec.task_type in {"repo_editing", "git_operations"}) or bool(spec.context.get("requires_git")):
            git_path = shutil.which("git")
            if not git_path:
                issues.append(
                    RuntimeValidationIssue(
                        code="missing_git",
                        field="task_type",
                        message="This task requires git, but the 'git' binary is not available.",
                        fix_hint="Install git or run the task on a runtime with git available.",
                        details={"selected_runtime": self.RUNTIME_ID},
                    )
                )

        if spec.timeout_sec < 10:
            issues.append(
                RuntimeValidationIssue(
                    code="timeout_too_small",
                    field="timeout_sec",
                    message="Timeout budget is too small for agent execution.",
                    fix_hint="Increase timeout_sec to at least 10 seconds.",
                    details={"timeout_sec": spec.timeout_sec},
                )
            )
        return issues

    async def readiness_check(self, spec: TaskSpec) -> RuntimeReadinessReport:
        """Run runtime preflight validation before execution starts."""
        health = await self.health_check()
        issues: list[RuntimeValidationIssue] = []
        dependencies = self.required_dependencies()

        workspace_path, workspace_issues = await self.provision_workspace(spec.workspace_path)
        issues.extend(workspace_issues)

        for dependency in dependencies:
            if dependency.kind == "binary":
                configured_name = (
                    os.environ.get(dependency.config_var, dependency.name)
                    if dependency.config_var
                    else dependency.name
                )
                resolved_path = shutil.which(configured_name)
                if dependency.required and not resolved_path:
                    fix_hint = dependency.install_hint or f"Install '{configured_name}' and ensure it is on PATH."
                    if dependency.config_var:
                        fix_hint += f" You can also point {dependency.config_var} at the binary."
                    issues.append(
                        RuntimeValidationIssue(
                            code="missing_binary",
                            field=dependency.config_var or dependency.name,
                            message=f"Required binary '{configured_name}' is not available for runtime '{self.RUNTIME_ID}'.",
                            fix_hint=fix_hint,
                            details={
                                "binary": configured_name,
                                "dependency_name": dependency.name,
                                "config_var": dependency.config_var,
                                "selected_runtime": self.RUNTIME_ID,
                                "fallback_runtime_available": False,
                            },
                        )
                    )
            elif dependency.kind == "env":
                value = os.environ.get(dependency.name)
                if dependency.required and not value:
                    issues.append(
                        RuntimeValidationIssue(
                            code="missing_env_var",
                            field=dependency.name,
                            message=f"Required environment variable '{dependency.name}' is missing.",
                            fix_hint=dependency.install_hint or f"Set {dependency.name} before starting this runtime.",
                            details={"selected_runtime": self.RUNTIME_ID},
                        )
                    )

        issues.extend(await self.validate_task_spec(spec))

        if not health.available:
            issues.append(
                RuntimeValidationIssue(
                    code="runtime_unhealthy",
                    message=f"Runtime '{self.RUNTIME_ID}' is not ready.",
                    fix_hint="Inspect the runtime health error and fix the runtime before retrying.",
                    details={"health_error": health.error, "selected_runtime": self.RUNTIME_ID},
                )
            )

        summary = issues[0].message if issues else f"Runtime '{self.RUNTIME_ID}' is ready."
        return RuntimeReadinessReport(
            runtime_id=self.RUNTIME_ID,
            selected_runtime=self.RUNTIME_ID,
            ready=not issues,
            health=health,
            workspace_path=workspace_path,
            dependencies=dependencies,
            tools=self.tool_availability_report(),
            issues=issues,
            summary=summary,
        )

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

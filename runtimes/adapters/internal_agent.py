"""Internal runtime adapter that executes tasks via the built-in AgentRunner."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from agent.loop import AgentRunner
from runtimes.base import (
    IntegrationMode,
    RuntimeAdapter,
    RuntimeCapability,
    RuntimeExecutionError,
    RuntimeHealth,
    RuntimeTier,
    TaskResult,
    TaskSpec,
)


class InternalAgentAdapter(RuntimeAdapter):
    """Use the existing in-process agent loop as a runtime-managed fallback."""

    RUNTIME_ID = "internal_agent"
    DISPLAY_NAME = "Internal Agent"
    DESCRIPTION = "Built-in local agent loop routed through the runtime manager."
    TIER = RuntimeTier.TIER_2
    INTEGRATION_MODE = IntegrationMode.NATIVE
    DOCS_URL = ""
    CAPABILITIES = frozenset(
        {
            RuntimeCapability.CODE_GENERATION,
            RuntimeCapability.CODE_REVIEW,
            RuntimeCapability.REPO_EDITING,
            RuntimeCapability.FILE_READ_WRITE,
            RuntimeCapability.TOOL_USE,
            RuntimeCapability.SHELL_EXEC,
            RuntimeCapability.AUTONOMOUS_LOOP,
        }
    )

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        # Fallback order: config -> OLLAMA_BASE -> OLLAMA_BASE_URL -> default localhost
        self._ollama_base = (
            (config or {}).get("ollama_base") 
            or os.environ.get("OLLAMA_BASE") 
            or os.environ.get("OLLAMA_BASE_URL") 
            or "http://localhost:11434"
        )
        self._workspace_root = (config or {}).get("workspace_root") or str(Path(__file__).resolve().parents[2])

    async def health_check(self) -> RuntimeHealth:
        return RuntimeHealth(runtime_id=self.RUNTIME_ID, available=True, details={"workspace_root": self._workspace_root})

    async def execute(self, spec: TaskSpec) -> TaskResult:
        runner = AgentRunner(
            ollama_base=self._ollama_base,
            workspace_root=spec.workspace_path or self._workspace_root,
        )
        started = time.perf_counter()
        try:
            result = await runner.run(
                instruction=spec.instruction,
                history=list(spec.context.get("conversation", [])),
                requested_model=spec.model_preference,
                auto_commit=False,
                max_steps=int(spec.context.get("max_steps", 8)),
                user_id=str(spec.context.get("owner_id") or ""),
            )
        except Exception as exc:  # pragma: no cover - exercised by runtime tests with fakes
            raise RuntimeExecutionError(self.RUNTIME_ID, str(exc), spec.task_id) from exc

        metadata = dict(spec.context)
        metadata["raw_result"] = result
        if spec.context.get("task", {}).get("requires_approval"):
            metadata["task_status"] = "in_review"
            metadata["review_reason"] = "Awaiting human approval"
        if result.get("summary"):
            metadata["agent_comment"] = result["summary"]

        return TaskResult(
            runtime_id=self.RUNTIME_ID,
            task_id=spec.task_id,
            success=True,
            output=result.get("summary", ""),
            artifacts=[],
            tool_calls=[],
            model_used=spec.model_preference,
            provider_used="local",
            execution_time_ms=(time.perf_counter() - started) * 1000,
            metadata=metadata,
        )

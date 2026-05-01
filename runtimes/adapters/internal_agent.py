"""Internal runtime adapter that executes tasks via the built-in AgentRunner.

Routes through Nvidia NIM free models by default (no local infra needed).
Falls back to Ollama when NVIDIA_API_KEY is not set.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from agent.loop import AgentRunner
from provider_router import ProviderConfig
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

# Nvidia NIM endpoint — OpenAI-compatible, free tier
_NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
_NVIDIA_DEFAULT_MODEL = "meta/llama-3.3-70b-instruct"


def _nvidia_provider_chain() -> list[ProviderConfig]:
    """Build Nvidia NIM provider config from env.  Empty list when key is absent."""
    key = (
        os.environ.get("NVIDIA_API_KEY")
        or os.environ.get("NVidiaApiKey")
        or ""
    ).strip()
    if not key:
        return []
    base = (os.environ.get("NVIDIA_BASE_URL") or _NVIDIA_BASE_URL).rstrip("/")
    return [
        ProviderConfig(
            provider_id="nvidia-nim",
            type="openai-compatible",
            base_url=base,
            api_key=key,
            default_model=os.environ.get("NVIDIA_DEFAULT_MODEL") or _NVIDIA_DEFAULT_MODEL,
            priority=0,
        )
    ]


class InternalAgentAdapter(RuntimeAdapter):
    """Built-in agent loop — Nvidia NIM primary, Ollama fallback."""

    RUNTIME_ID = "internal_agent"
    DISPLAY_NAME = "Internal Agent (Nvidia NIM)"
    DESCRIPTION = "Built-in agent loop — routes through Nvidia NIM free models with Ollama as fallback."
    TIER = RuntimeTier.FIRST_CLASS
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
        self._ollama_base = (
            (config or {}).get("ollama_base")
            or os.environ.get("OLLAMA_BASE")
            or os.environ.get("OLLAMA_BASE_URL")
            or "http://localhost:11434"
        )
        self._workspace_root = (
            (config or {}).get("workspace_root")
            or str(Path(__file__).resolve().parents[2])
        )

    async def health_check(self) -> RuntimeHealth:
        nvidia_key = (
            os.environ.get("NVIDIA_API_KEY")
            or os.environ.get("NVidiaApiKey")
            or ""
        ).strip()
        return RuntimeHealth(
            runtime_id=self.RUNTIME_ID,
            available=True,
            details={
                "workspace_root": self._workspace_root,
                "provider": "nvidia-nim" if nvidia_key else "ollama",
            },
        )

    async def execute(self, spec: TaskSpec) -> TaskResult:
        nvidia_chain = _nvidia_provider_chain()

        # When Nvidia NIM is configured use its base URL as the primary endpoint
        # so AgentRunner builds the right ProviderConfig internally.
        if nvidia_chain:
            primary_base = nvidia_chain[0].base_url
            # Pass remaining chain entries (if any) as extra providers
            extra_chain = nvidia_chain[1:]
        else:
            primary_base = self._ollama_base
            extra_chain = []

        runner = AgentRunner(
            ollama_base=primary_base,
            workspace_root=spec.workspace_path or self._workspace_root,
            provider_chain=extra_chain,
        )

        started = time.perf_counter()
        try:
            # Resolve model: prefer spec → Nvidia default → leave None (auto)
            model = spec.model_preference
            if not model and nvidia_chain:
                model = nvidia_chain[0].default_model

            # auto_commit can be requested via task context; defaults off so the
            # agent writes files but lets the user review before committing.
            auto_commit = bool(spec.context.get("auto_commit", False))

            result = await runner.run(
                instruction=spec.instruction,
                history=list(spec.context.get("conversation", [])),
                requested_model=model,
                auto_commit=auto_commit,
                max_steps=int(spec.context.get("max_steps", 8)),
                user_id=str(spec.context.get("owner_id") or ""),
            )
        except Exception as exc:
            raise RuntimeExecutionError(self.RUNTIME_ID, str(exc), spec.task_id) from exc

        # Collect every file that was actually written to disk across all steps.
        changed_files: list[str] = []
        for step in result.get("steps", []):
            changed_files.extend(step.get("changed_files", []))
        unique_files = sorted(set(changed_files))

        metadata = dict(spec.context)
        metadata["raw_result"] = result
        metadata["changed_files"] = unique_files
        if spec.context.get("task", {}).get("requires_approval"):
            metadata["task_status"] = "in_review"
            metadata["review_reason"] = "Awaiting human approval"

        # Prefer the rich markdown report for the task discussion comment.
        # Falls back to the one-liner summary when report is unavailable.
        agent_comment = result.get("report") or result.get("summary") or ""
        if agent_comment:
            metadata["agent_comment"] = agent_comment

        # Determine actual success: the agent must have either changed files or
        # produced a non-empty text output.  An empty plan (0 steps executed) or
        # all-failed steps with no output is treated as a failure so the task is
        # not silently moved to DONE without any real work.
        steps = result.get("steps") or []
        applied_steps = [s for s in steps if s.get("status") == "applied"]
        output_text = result.get("report") or result.get("summary") or ""
        judge_verdict = str((result.get("judge") or {}).get("verdict") or "").upper()
        # A bare summary/report without file edits is not meaningful work; require
        # actual applied steps or changed files to consider the run a success.
        did_work = bool(unique_files or applied_steps) and judge_verdict != "BLOCKED"

        provider_label = "nvidia-nim" if nvidia_chain else "ollama"
        return TaskResult(
            runtime_id=self.RUNTIME_ID,
            task_id=spec.task_id,
            success=did_work,
            output=output_text,
            artifacts=unique_files,
            tool_calls=[],
            model_used=model or _NVIDIA_DEFAULT_MODEL,
            provider_used=provider_label,
            execution_time_ms=(time.perf_counter() - started) * 1000,
            metadata=metadata,
        )

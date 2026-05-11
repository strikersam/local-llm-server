"""Internal runtime adapter that executes tasks via the built-in AgentRunner.

Routes through Nvidia NIM free models by default (no local infra needed).
Falls back to Ollama when NVIDIA_API_KEY is not set.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

from agent.loop import AgentRunner
from provider_router import ProviderConfig
from runtimes.base import (
    IntegrationMode,
    RuntimeAdapter,
    RuntimeCapability,
    RuntimeDependency,
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
        """
        Initialize the adapter and configure the Ollama base URL, workspace root, and task-harness requirement.
        
        Parameters:
            config (dict[str, Any] | None): Optional overrides for adapter configuration. Recognized keys:
                - "ollama_base": Base URL for the local Ollama endpoint; falls back to the OLLAMA_BASE / OLLAMA_BASE_URL environment variables or "http://localhost:11434".
                - "workspace_root": Filesystem path for the workspace; falls back to the repository root derived from the package location.
                - "task_harness_required": If the value (string) equals "true" case-insensitively, the adapter will require an external task harness; if omitted the TASK_HARNESS_REQUIRED environment variable is consulted.
        """
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
        self._task_harness_required = str(
            (config or {}).get("task_harness_required", os.environ.get("TASK_HARNESS_REQUIRED", "false"))
        ).lower() == "true"

    def required_dependencies(self) -> list[RuntimeDependency]:
        """
        Determine required runtime dependencies for this adapter.
        
        When the adapter is configured to require a task harness, returns a single
        RuntimeDependency describing the harness (name "task-harness", config_var
        "TASK_HARNESS_BIN", and an install hint). Otherwise returns an empty list.
        
        Returns:
            list[RuntimeDependency]: Required runtime dependencies, or an empty list if none.
        """
        if not self._task_harness_required:
            return []
        return [
            RuntimeDependency(
                name="task-harness",
                config_var="TASK_HARNESS_BIN",
                install_hint="Install a compatible harness and point TASK_HARNESS_BIN at it.",
            )
        ]

    async def health_check(self) -> RuntimeHealth:
        """
        Determine availability of the internal agent runtime and which provider will be used.
        
        If an NVIDIA API key is configured the runtime is reported available and the provider is `"nvidia-nim"` with `details` containing `workspace_root` and `provider`. If no NVIDIA key is present the adapter performs a short HTTP probe of the local Ollama base URL; on success `available` is `True` and `details` includes `workspace_root`, `provider` (`"ollama"`), and `probe_url`. On probe failure `available` is `False` and `error` is set to `"Local Ollama not reachable"`.
        
        Returns:
            RuntimeHealth: Health result describing availability, `details`, and `error` when unavailable.
        """
        nvidia_key = (
            os.environ.get("NVIDIA_API_KEY")
            or os.environ.get("NVidiaApiKey")
            or ""
        ).strip()
        provider_label = "nvidia-nim" if nvidia_key else "ollama"
        # If Nvidia key present, assume external provider is reachable (best-effort)
        if nvidia_key:
            return RuntimeHealth(
                runtime_id=self.RUNTIME_ID,
                available=True,
                details={"workspace_root": self._workspace_root, "provider": provider_label},
            )

        # Probe local Ollama endpoint conservatively
        import httpx
        try:
            base = (os.environ.get("OLLAMA_BASE") or os.environ.get("OLLAMA_BASE_URL") or self._ollama_base).rstrip("/")
            # Prefer a lightweight endpoint; many Ollama installs respond on root
            probe_url = f"{base}/v1/health" if base.endswith(":11434") else base
            async with httpx.AsyncClient() as client:
                resp = await client.get(probe_url, timeout=1.0)
            if resp.status_code >= 200 and resp.status_code < 400:
                return RuntimeHealth(
                    runtime_id=self.RUNTIME_ID,
                    available=True,
                    details={"workspace_root": self._workspace_root, "provider": provider_label, "probe_url": probe_url},
                )
        except httpx.HTTPError as e:
            # fall through to unavailable
            log.debug("Ollama probe failed at %s: %s", probe_url if 'probe_url' in locals() else 'unknown', e)
        return RuntimeHealth(
            runtime_id=self.RUNTIME_ID,
            available=False,
            error="Local Ollama not reachable",
            details={"workspace_root": self._workspace_root, "provider": provider_label},
        )

    async def execute(self, spec: TaskSpec) -> TaskResult:
        """
        Execute a TaskSpec using an AgentRunner and return a TaskResult summarizing the run.
        
        Parameters:
            spec (TaskSpec): Specification for the task including instruction, context, optional model_preference, optional workspace_path, and task_id.
        
        Returns:
            TaskResult: Summary of execution containing runtime_id, task_id, success flag, output text, artifacts (changed files), model_used, provider_used, execution_time_ms, and metadata. Metadata includes the raw runner result under `raw_result`, the deduplicated `changed_files`, and `agent_comment` when available.
        
        Raises:
            RuntimeExecutionError: If the underlying AgentRunner raises an exception during execution.
        """
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
            github_token=spec.context.get("github_token"),
            email=spec.context.get("user_email"),
            department=spec.context.get("department"),
            key_id=spec.context.get("key_id"),
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
                max_steps=int(spec.context.get("max_steps", 30)),
                user_id=str(spec.context.get("owner_id") or ""),
                department=spec.context.get("department"),
                key_id=spec.context.get("key_id"),
                session_id=spec.context.get("session_id"),
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
        # Actual work is considered done if files were modified, steps were applied,
        # or if the agent produced a meaningful informational report/answer.
        did_work = (bool(unique_files or applied_steps) or len(output_text.strip()) > 20) and judge_verdict != "BLOCKED"

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

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
    RuntimeDependency,
    RuntimeExecutionError,
    RuntimeHealth,
    RuntimeTier,
    TaskResult,
    TaskSpec,
)

# Nvidia NIM endpoint — OpenAI-compatible, free tier
_NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
_NVIDIA_DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b"


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
        self._task_harness_required = str(
            (config or {}).get("task_harness_required", os.environ.get("TASK_HARNESS_REQUIRED", "false"))
        ).lower() == "true"

    def required_dependencies(self) -> list[RuntimeDependency]:
        """
        Return runtime dependencies required by this adapter.
        
        Returns:
            list[RuntimeDependency]: An empty list when a task harness is not required; otherwise a list containing a single `RuntimeDependency` for the `task-harness` with `config_var="TASK_HARNESS_BIN"` and an install hint.
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
        Determine availability of the internal agent runtime by preferring an NVIDIA NIM configuration and falling back to a conservative local Ollama probe.
        
        If an `NVIDIA_API_KEY` (or `NVidiaApiKey`) is present the runtime is reported available and labeled as the `nvidia-nim` provider. If no NVIDIA key is present the function attempts a short HTTP probe against the configured Ollama base (from `OLLAMA_BASE`, `OLLAMA_BASE_URL`, or the adapter's configured base). When probing the default local Ollama port (`:11434`) the `/v1/health` path is used; the probe uses a small timeout and must return a 2xx/3xx status to be considered healthy.
        
        Returns:
            RuntimeHealth: Availability status and details. `available=True` when an NVIDIA key exists or the Ollama probe succeeds; otherwise `available=False` with `error="Local Ollama not reachable"`. The returned `details` include `workspace_root` and `provider`, and when a successful probe occurs also include the `probe_url`.
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
            resp = httpx.get(probe_url, timeout=1.0)
            if resp.status_code >= 200 and resp.status_code < 400:
                return RuntimeHealth(
                    runtime_id=self.RUNTIME_ID,
                    available=True,
                    details={"workspace_root": self._workspace_root, "provider": provider_label, "probe_url": probe_url},
                )
        except Exception:
            # fall through to unavailable
            pass
        return RuntimeHealth(
            runtime_id=self.RUNTIME_ID,
            available=False,
            error="Local Ollama not reachable",
            details={"workspace_root": self._workspace_root, "provider": provider_label},
        )

    async def execute(self, spec: TaskSpec) -> TaskResult:
        """
        Execute a TaskSpec using the internal AgentRunner and convert the agent's outcome into a TaskResult.
        
        Parameters:
            spec (TaskSpec): Specification of the task to run, including instruction, model preference, workspace path, and contextual keys used to configure the runner (e.g., conversation, auto_commit, max_steps, owner_id, department, key_id, session_id).
        
        Returns:
            TaskResult: Aggregated result of the execution containing:
                - success: true when files were modified or applied steps exist, or when the agent produced a substantive textual report/summary (more than ~20 characters), unless the judge verdict is "BLOCKED".
                - output: the agent's report or summary.
                - artifacts: sorted list of unique file paths the agent changed.
                - model_used: model requested or chosen (falls back to a default).
                - provider_used: "nvidia-nim" when an NVIDIA provider chain was active, otherwise "ollama".
                - execution_time_ms and metadata (includes the raw agent result, changed_files, agent_comment, and task status/review info when applicable).
        
        Raises:
            RuntimeExecutionError: If the AgentRunner fails during execution.
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

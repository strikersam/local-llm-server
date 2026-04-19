"""workflow/phases.py — PhaseRunner: executes a single CRISPY phase.

Each phase type maps to a specific agent role.  The PhaseRunner:
  1. Selects the appropriate model via ModelRouter.
  2. Builds a role-specific system prompt + user message.
  3. Calls the Ollama-compatible chat endpoint.
  4. Persists the response as a durable artifact.
  5. Returns the artifact name so WorkflowEngine can record it.

Phase → Role → Artifact mapping
--------------------------------
context       Scout      context.md
research      Scout      research.md
investigate   Scout      investigation.md
structure     Architect  structure.md
plan          Architect  plan.md
execute       Coder      slice-{N:02d}.md       (per slice)
review        Reviewer   review-slice-{N:02d}.md
verify        Verifier   verify-slice-{N:02d}.json
report        Architect  final-report.md

Verifier is execution-only (runs pytest, ruff, etc.) — it never calls
an LLM for a verdict.  The LLM call in the Verifier phase is ONLY used
to parse the verification commands from the plan artifact; execution
itself uses agent/terminal.py.
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import httpx

from workflow.artifact_store import ArtifactStore
from workflow.models import (
    AgentRole,
    Artifact,
    CheckRun,
    ModelRoutingConfig,
    PhaseType,
    Slice,
    _now,
)

log = logging.getLogger("crispy-phase-runner")

# ── Default per-role model env vars ──────────────────────────────────────────

_ROLE_MODEL_ENV: dict[AgentRole, str] = {
    "architect": "CRISPY_ARCHITECT_MODEL",
    "scout": "CRISPY_SCOUT_MODEL",
    "coder": "CRISPY_CODER_MODEL",
    "reviewer": "CRISPY_REVIEWER_MODEL",
    "verifier": "CRISPY_VERIFIER_MODEL",
}

_ROLE_MODEL_DEFAULTS: dict[AgentRole, str] = {
    "architect": "qwen3-coder:30b",
    "scout": "deepseek-r1:32b",
    "coder": "qwen3-coder:30b",
    "reviewer": "deepseek-r1:32b",
    "verifier": "qwen3-coder:7b",
}

_PHASE_ROLE: dict[PhaseType, AgentRole] = {
    "context": "scout",
    "research": "scout",
    "investigate": "scout",
    "structure": "architect",
    "plan": "architect",
    "execute": "coder",
    "review": "reviewer",
    "verify": "verifier",
    "report": "architect",
}


def _resolve_model(role: AgentRole, routing: ModelRoutingConfig) -> str:
    """Return the model to use for *role*, respecting per-run routing config."""
    # 1. Per-run explicit override
    configured: str | None = getattr(routing, role, None)
    if configured:
        return configured
    # 2. Env var
    env_name = _ROLE_MODEL_ENV.get(role, "")
    from_env = os.environ.get(env_name, "").strip() if env_name else ""
    if from_env:
        return from_env
    # 3. Hard-coded default
    return _ROLE_MODEL_DEFAULTS.get(role, "qwen3-coder:30b")


# ── System prompts per role ───────────────────────────────────────────────────

_SCOUT_SYSTEM = """\
You are a SCOUT agent.  You are READ-ONLY.  You MUST NOT suggest code changes.
Your only job is to gather and report context faithfully.
Output must be a well-structured markdown document."""

_ARCHITECT_SYSTEM = """\
You are an ARCHITECT agent.  You are READ-ONLY.  You MUST NOT write code.
You analyse structures and produce plans.
Output a clear, markdown-formatted document."""

_CODER_SYSTEM = """\
You are a CODER agent.  You implement exactly one vertical slice.
You MUST include tests alongside every code change.
You MUST use the exact file paths specified in the slice specification.
Output a markdown document: ## What changed, ## Why, ## Files modified."""

_REVIEWER_SYSTEM = """\
You are a REVIEWER agent.  You are READ-ONLY with patch-suggestion rights.
You MUST NOT apply changes directly.  You review Coder output and report:
  - Blocking issues (must fix before verify)
  - Non-blocking suggestions
Output a markdown document with clear BLOCKING / NON-BLOCKING sections."""

_VERIFIER_SYSTEM = """\
You are a VERIFIER agent.  You output ONLY a JSON list of shell commands
to verify the slice.  Example: ["pytest -x", "ruff check ."]
No prose.  No markdown.  Only a valid JSON array of strings."""

_ROLE_SYSTEM: dict[AgentRole, str] = {
    "scout": _SCOUT_SYSTEM,
    "architect": _ARCHITECT_SYSTEM,
    "coder": _CODER_SYSTEM,
    "reviewer": _REVIEWER_SYSTEM,
    "verifier": _VERIFIER_SYSTEM,
}


# ── PhaseRunner ───────────────────────────────────────────────────────────────


class PhaseRunner:
    """Execute a single CRISPY phase and produce its artifact.

    The runner is intentionally stateless — state lives in :class:`ArtifactStore`
    and the caller (:class:`WorkflowEngine`).  This makes it easy to test
    individual phases in isolation.
    """

    def __init__(
        self,
        *,
        ollama_base: str,
        artifact_store: ArtifactStore,
        workspace_root: str | Path | None = None,
        timeout: float = 300.0,
    ) -> None:
        self._base = ollama_base.rstrip("/")
        self._store = artifact_store
        self._workspace = Path(workspace_root) if workspace_root else Path.cwd()
        self._timeout = timeout

    # ── Public ───────────────────────────────────────────────────────────────

    async def run_phase(
        self,
        *,
        run_id: str,
        phase: PhaseType,
        request: str,
        routing: ModelRoutingConfig,
        prior_artifacts: list[Artifact],
    ) -> Artifact:
        """Run *phase* for *run_id* and return the persisted artifact."""
        role = _PHASE_ROLE[phase]
        model = _resolve_model(role, routing)
        artifact_name = self._artifact_name(phase)
        context_block = self._build_context(prior_artifacts)
        user_message = self._build_user_message(phase, request, context_block)
        log.info(
            "PhaseRunner: run=%s phase=%s role=%s model=%s",
            run_id, phase, role, model,
        )
        content = await self._call_model(model, role, user_message)
        art = self._store.persist(
            run_id=run_id,
            phase=phase,
            name=artifact_name,
            content=content,
        )
        log.info(
            "PhaseRunner: artifact persisted run=%s name=%s size=%d",
            run_id, artifact_name, art.size_bytes,
        )
        return art

    async def run_slice_execute(
        self,
        *,
        run_id: str,
        sl: Slice,
        routing: ModelRoutingConfig,
        prior_artifacts: list[Artifact],
    ) -> Artifact:
        """Execute a single slice (coder phase) and return the artifact."""
        role: AgentRole = "coder"
        model = _resolve_model(role, routing)
        plan_content = self._store.content_by_name(run_id, "plan.md") or ""
        context_block = self._build_context(prior_artifacts)
        user_message = (
            f"## Active Slice\n\n"
            f"**Slice {sl.index:02d}**: {sl.title}\n\n"
            f"{sl.description}\n\n"
            f"**Target files**: {', '.join(sl.files) if sl.files else '(determine from description)'}\n\n"
            f"## Plan Reference\n\n{plan_content[:4000]}\n\n"
            f"## Prior Context\n\n{context_block}"
        )
        content = await self._call_model(model, role, user_message)
        artifact_name = f"slice-{sl.index:02d}.md"
        art = self._store.persist(
            run_id=run_id,
            phase="execute",
            name=artifact_name,
            content=content,
        )
        return art

    async def run_slice_review(
        self,
        *,
        run_id: str,
        sl: Slice,
        routing: ModelRoutingConfig,
        slice_artifact: Artifact,
    ) -> Artifact:
        """Review a single slice and return the review artifact."""
        role: AgentRole = "reviewer"
        model = _resolve_model(role, routing)
        slice_content = self._store.get_content(slice_artifact.artifact_id) or ""
        user_message = (
            f"## Slice to Review\n\n"
            f"**Slice {sl.index:02d}**: {sl.title}\n\n"
            f"{sl.description}\n\n"
            f"## Slice Output\n\n{slice_content}"
        )
        content = await self._call_model(model, role, user_message)
        artifact_name = f"review-slice-{sl.index:02d}.md"
        art = self._store.persist(
            run_id=run_id,
            phase="review",
            name=artifact_name,
            content=content,
        )
        return art

    async def run_slice_verify(
        self,
        *,
        run_id: str,
        sl: Slice,
        routing: ModelRoutingConfig,
        workspace_root: str | Path,
    ) -> CheckRun:
        """Verify a slice by executing commands. Returns a structured CheckRun.

        The Verifier LLM produces only a JSON list of commands to run.
        Actual execution happens via subprocess — no subjective LLM verdict.
        """
        import asyncio
        import hashlib
        import secrets
        import subprocess

        role: AgentRole = "verifier"
        model = _resolve_model(role, routing)
        ws = Path(workspace_root)

        # Ask LLM for the list of verification commands (JSON array only)
        user_message = (
            f"Slice {sl.index:02d}: {sl.title}\n"
            f"Files: {', '.join(sl.files)}\n\n"
            "Output ONLY a JSON array of shell commands to verify this slice.\n"
            "Include at minimum: pytest -x\n"
            "Do not include commands that modify the filesystem.\n"
            'Example: ["pytest -x", "ruff check ."]'
        )
        commands_raw = await self._call_model(model, role, user_message)

        # Parse the commands list from the LLM response
        commands: list[str] = ["pytest -x"]  # safe default
        try:
            import re
            m = re.search(r"\[.*\]", commands_raw, re.S)
            if m:
                parsed = json.loads(m.group(0))
                if isinstance(parsed, list) and all(isinstance(c, str) for c in parsed):
                    commands = parsed
        except Exception as exc:
            log.warning("Verifier command parse failed (%s), using default", exc)

        # Execute all commands — this is the ONLY source of truth
        combined_stdout: list[str] = []
        combined_stderr: list[str] = []
        final_exit_code = 0
        start_ms = int(time.perf_counter() * 1000)

        for cmd in commands:
            try:
                proc = subprocess.run(
                    cmd,
                    shell=True,
                    cwd=str(ws),
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                combined_stdout.append(f"$ {cmd}\n{proc.stdout}")
                combined_stderr.append(f"$ {cmd}\n{proc.stderr}")
                if proc.returncode != 0:
                    final_exit_code = proc.returncode
                    log.warning(
                        "Verify cmd failed: run=%s slice=%s cmd=%r exit=%d",
                        run_id, sl.slice_id, cmd, proc.returncode,
                    )
            except subprocess.TimeoutExpired:
                combined_stderr.append(f"$ {cmd}\n[TIMEOUT after 120s]")
                final_exit_code = 1
            except Exception as exc:
                combined_stderr.append(f"$ {cmd}\n[ERROR: {exc}]")
                final_exit_code = 1

        duration_ms = int(time.perf_counter() * 1000) - start_ms

        check_run = CheckRun(
            check_id="chk_" + secrets.token_hex(6),
            slice_id=sl.slice_id,
            run_id=run_id,
            commands=commands,
            exit_code=final_exit_code,
            stdout="\n".join(combined_stdout),
            stderr="\n".join(combined_stderr),
            passed=(final_exit_code == 0),
            duration_ms=duration_ms,
            ran_at=_now(),
        )

        # Persist the structured JSON result as an artifact
        check_content = json.dumps(check_run.model_dump(), indent=2)
        self._store.persist(
            run_id=run_id,
            phase="verify",
            name=f"verify-slice-{sl.index:02d}.json",
            content=check_content,
        )

        log.info(
            "Verifier: run=%s slice=%s exit_code=%d passed=%s",
            run_id, sl.slice_id, final_exit_code, check_run.passed,
        )
        return check_run

    # ── Internal ─────────────────────────────────────────────────────────────

    def _artifact_name(self, phase: PhaseType) -> str:
        mapping: dict[str, str] = {
            "context": "context.md",
            "research": "research.md",
            "investigate": "investigation.md",
            "structure": "structure.md",
            "plan": "plan.md",
            "report": "final-report.md",
        }
        return mapping.get(phase, f"{phase}.md")

    def _build_context(self, prior_artifacts: list[Artifact]) -> str:
        """Build a condensed context block from prior phase artifacts."""
        if not prior_artifacts:
            return "(no prior artifacts)"
        parts: list[str] = []
        for art in prior_artifacts[-4:]:  # last 4 to keep context lean
            try:
                content = Path(art.path).read_text(encoding="utf-8")
                # Cap each artifact to 2000 chars to avoid context explosion
                if len(content) > 2000:
                    content = content[:2000] + "\n...[truncated]"
                parts.append(f"### {art.name}\n\n{content}")
            except Exception:
                parts.append(f"### {art.name}\n\n[content unavailable]")
        return "\n\n---\n\n".join(parts)

    def _build_user_message(
        self, phase: PhaseType, request: str, context_block: str
    ) -> str:
        return (
            f"## Original Request\n\n{request}\n\n"
            f"## Prior Phase Artifacts\n\n{context_block}\n\n"
            f"## Your Task\n\nYou are running the **{phase.upper()}** phase. "
            f"Produce the required artifact now."
        )

    async def _call_model(
        self,
        model: str,
        role: AgentRole,
        user_message: str,
    ) -> str:
        """Call the Ollama-compatible endpoint and return raw text."""
        system = _ROLE_SYSTEM.get(role, "You are a helpful assistant.")
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_message},
            ],
            "stream": False,
        }
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(self._timeout, connect=10.0)
        ) as client:
            resp = await client.post(
                f"{self._base}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
        resp.raise_for_status()
        data = resp.json()
        return str(data["choices"][0]["message"]["content"])

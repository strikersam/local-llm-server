"""agents/swarm.py — AgentSwarm: routes workflow phases to the correct agent.

The AgentSwarm is the bridge between the WorkflowEngine (which manages
state and sequencing) and the individual agents (which know their role,
model, and system prompt).

Key value-adds over raw PhaseRunner
-------------------------------------
1.  Permission enforcement per role (write check, execute check).
2.  Handoff context — each agent receives a structured handoff that
    carries not only the raw artifacts but also the prior agent's verdict
    so the next agent knows exactly what to build on.
3.  Profile registry — the Swarm resolves which AgentProfile drives each
    phase; callers never hard-code model names.
4.  Coder ≠ Reviewer is architecturally enforced here: ``get_profile``
    returns different AgentProfile instances with different models.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from agents.profiles import AgentProfile, load_all_profiles
from workflow.artifact_store import ArtifactStore
from workflow.models import (
    AgentRole,
    Artifact,
    CheckRun,
    ModelRoutingConfig,
    PhaseType,
    Slice,
)
from workflow.phases import PhaseRunner

log = logging.getLogger("crispy-swarm")

# Phase → role mapping (mirrors phases.py but lives here as the authoritative copy)
PHASE_ROLE: dict[str, str] = {
    "context":     "scout",
    "research":    "scout",
    "investigate": "scout",
    "structure":   "architect",
    "plan":        "architect",
    "execute":     "coder",
    "review":      "reviewer",
    "verify":      "verifier",
    "report":      "architect",
}


class AgentSwarm:
    """Coordinates a team of specialised agents for a WorkflowRun.

    Parameters
    ----------
    ollama_base:
        Base URL of the Ollama / OpenAI-compat endpoint.
    artifact_store:
        Shared artifact store (same instance used by WorkflowEngine).
    workspace_root:
        Root of the project being built. Used by Verifier for subprocess cwd.
    profiles:
        Optional dict of role → AgentProfile. Defaults to ``load_all_profiles()``.
        Override in tests or to swap coder/reviewer models at runtime.
    timeout:
        Per-LLM-call timeout in seconds.
    """

    def __init__(
        self,
        *,
        ollama_base: str,
        artifact_store: ArtifactStore,
        workspace_root: str | Path | None = None,
        profiles: dict[str, AgentProfile] | None = None,
        timeout: float = 300.0,
    ) -> None:
        self._profiles = profiles or load_all_profiles()
        self._runner = PhaseRunner(
            ollama_base=ollama_base,
            artifact_store=artifact_store,
            workspace_root=workspace_root,
            timeout=timeout,
        )
        self._workspace = Path(workspace_root) if workspace_root else Path.cwd()
        log.info(
            "AgentSwarm ready | coder=%s | reviewer=%s",
            self._profiles["coder"].model,
            self._profiles["reviewer"].model,
        )

    # ── Public: profile access ────────────────────────────────────────────────

    def get_profile(self, role: str) -> AgentProfile:
        """Return the AgentProfile for *role*, raising KeyError if unknown."""
        try:
            return self._profiles[role]
        except KeyError:
            raise KeyError(f"Unknown agent role: {role!r}. Valid: {list(self._profiles)}")

    def role_for_phase(self, phase: str) -> str:
        """Return the agent role responsible for *phase*."""
        return PHASE_ROLE.get(phase, "architect")

    def profile_for_phase(self, phase: str) -> AgentProfile:
        """Return the AgentProfile for the agent driving *phase*."""
        return self.get_profile(self.role_for_phase(phase))

    def team_summary(self) -> list[dict[str, Any]]:
        """Return a JSON-serialisable summary of all agent profiles."""
        return [
            {
                "role": p.role,
                "name": p.name,
                "model": p.model,
                "can_write": p.can_write,
                "can_execute": p.can_execute,
                "can_review": p.can_review,
            }
            for p in self._profiles.values()
        ]

    # ── Public: phase execution ───────────────────────────────────────────────

    async def run_phase(
        self,
        *,
        run_id: str,
        phase: str,
        request: str,
        routing: ModelRoutingConfig,
        prior_artifacts: list[Artifact],
    ) -> Artifact:
        """Run a pre-gate or report phase through the correct agent.

        Enforces permission checks before delegating to PhaseRunner.
        """
        profile = self.profile_for_phase(phase)
        self._check_permissions(profile, phase, write_op=False)
        log.info(
            "Swarm: run=%s phase=%s agent=%s model=%s",
            run_id, phase, profile.name, profile.model,
        )
        # Inject profile model into routing so PhaseRunner uses this profile's model
        routing_with_model = self._patch_routing(routing, profile)
        return await self._runner.run_phase(
            run_id=run_id,
            phase=phase,
            request=request,
            routing=routing_with_model,
            prior_artifacts=prior_artifacts,
        )

    async def run_slice_execute(
        self,
        *,
        run_id: str,
        sl: Slice,
        routing: ModelRoutingConfig,
        prior_artifacts: list[Artifact],
    ) -> Artifact:
        """Execute a slice via the Coder agent (write-permitted)."""
        profile = self.get_profile("coder")
        self._check_permissions(profile, "execute", write_op=True)
        log.info(
            "Swarm[Coder:%s]: run=%s slice=%s",
            profile.model, run_id, sl.slice_id,
        )
        routing_with_model = self._patch_routing(routing, profile)
        return await self._runner.run_slice_execute(
            run_id=run_id,
            sl=sl,
            routing=routing_with_model,
            prior_artifacts=prior_artifacts,
        )

    async def run_slice_review(
        self,
        *,
        run_id: str,
        sl: Slice,
        routing: ModelRoutingConfig,
        slice_artifact: Artifact,
    ) -> Artifact:
        """Review a slice via the Reviewer agent (different model from Coder).

        This is the dual-model safety net: the Reviewer uses a deliberatly
        DIFFERENT model to catch blind spots the Coder's model may have.
        """
        reviewer = self.get_profile("reviewer")
        coder = self.get_profile("coder")
        if reviewer.model == coder.model:
            log.warning(
                "REVIEWER and CODER are using the same model (%s). "
                "Set CRISPY_REVIEWER_MODEL to a different model for better coverage.",
                reviewer.model,
            )
        self._check_permissions(reviewer, "review", write_op=False)
        log.info(
            "Swarm[Reviewer:%s vs Coder:%s]: run=%s slice=%s",
            reviewer.model, coder.model, run_id, sl.slice_id,
        )
        routing_with_model = self._patch_routing(routing, reviewer)
        return await self._runner.run_slice_review(
            run_id=run_id,
            sl=sl,
            routing=routing_with_model,
            slice_artifact=slice_artifact,
        )

    async def run_slice_verify(
        self,
        *,
        run_id: str,
        sl: Slice,
        routing: ModelRoutingConfig,
    ) -> CheckRun:
        """Run verification commands via the Verifier agent.

        The Verifier is execution-only: it produces a JSON list of commands
        to run (via LLM), then runs them as subprocesses.  No LLM verdict.
        """
        profile = self.get_profile("verifier")
        self._check_permissions(profile, "verify", write_op=False, execute_op=True)
        log.info(
            "Swarm[Verifier:%s]: run=%s slice=%s",
            profile.model, run_id, sl.slice_id,
        )
        routing_with_model = self._patch_routing(routing, profile)
        return await self._runner.run_slice_verify(
            run_id=run_id,
            sl=sl,
            routing=routing_with_model,
            workspace_root=self._workspace,
        )

    # ── Internal ──────────────────────────────────────────────────────────────

    def _patch_routing(
        self, routing: ModelRoutingConfig, profile: AgentProfile
    ) -> ModelRoutingConfig:
        """Return a copy of *routing* with the profile's model injected for its role."""
        data = routing.model_dump()
        data[profile.role] = profile.model
        return ModelRoutingConfig(**data)

    @staticmethod
    def _check_permissions(
        profile: AgentProfile,
        phase: str,
        *,
        write_op: bool = False,
        execute_op: bool = False,
    ) -> None:
        """Raise PermissionError if the profile lacks required permissions."""
        if write_op and not profile.can_write:
            raise PermissionError(
                f"Agent {profile.name!r} (role={profile.role!r}) attempted a write "
                f"operation in phase {phase!r} but can_write=False. "
                f"This is a CRISPY permission violation."
            )
        if execute_op and not profile.can_execute:
            raise PermissionError(
                f"Agent {profile.name!r} (role={profile.role!r}) attempted an execute "
                f"operation in phase {phase!r} but can_execute=False."
            )

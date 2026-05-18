"""tests/test_agents.py — Unit tests for agents/ package.

Tests cover:
  - AgentProfile construction and env-var override
  - Permission enforcement (write_op, execute_op)
  - AgentSwarm role routing and profile resolution
  - Dual-model invariant detection (coder ≠ reviewer warning)
  - team_summary serialisation
  - PhaseRunner delegation (mocked LLM call)
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.profiles import (
    AgentProfile,
    load_all_profiles,
    make_coder_profile,
    make_reviewer_profile,
    make_scout_profile,
)
from agents.swarm import PHASE_ROLE, AgentSwarm


# ── AgentProfile ──────────────────────────────────────────────────────────────

class TestAgentProfile:
    def test_defaults(self):
        p = make_coder_profile()
        assert p.role == "coder"
        assert p.can_write is True
        assert p.can_execute is False
        assert p.can_review is False

    def test_reviewer_cannot_write(self):
        p = make_reviewer_profile()
        assert p.can_write is False
        assert p.can_review is True

    def test_scout_read_only(self):
        p = make_scout_profile()
        assert p.can_write is False
        assert p.can_execute is False
        assert p.can_review is False

    def test_env_var_model_override(self, monkeypatch):
        monkeypatch.setenv("CRISPY_CODER_MODEL", "llama4-maverick:17b")
        p = make_coder_profile()
        assert p.model == "llama4-maverick:17b"

    def test_label_property(self):
        p = make_coder_profile()
        assert "Coder" in p.label
        assert p.model in p.label

    def test_coder_not_reviewer_by_default(self):
        coder = make_coder_profile()
        reviewer = make_reviewer_profile()
        # Default models must differ — this is the core invariant
        assert coder.model != reviewer.model, (
            "Coder and Reviewer should use different models by default. "
            f"Both are {coder.model!r}."
        )

    def test_load_all_profiles_has_five_roles(self):
        profiles = load_all_profiles()
        assert set(profiles.keys()) == {"architect", "scout", "coder", "reviewer", "verifier"}


# ── AgentSwarm — role routing ─────────────────────────────────────────────────

class TestSwarmRoleRouting:
    @pytest.fixture
    def swarm(self, tmp_path) -> AgentSwarm:
        from workflow.artifact_store import ArtifactStore
        store = ArtifactStore(artifacts_root=tmp_path / "arts", db_path=tmp_path / "arts.db")
        return AgentSwarm(
            ollama_base="http://localhost:11434",
            artifact_store=store,
            workspace_root=tmp_path,
        )

    def test_scout_drives_context_phase(self, swarm):
        assert swarm.role_for_phase("context") == "scout"
        assert swarm.role_for_phase("research") == "scout"
        assert swarm.role_for_phase("investigate") == "scout"

    def test_architect_drives_plan_phase(self, swarm):
        assert swarm.role_for_phase("plan") == "architect"
        assert swarm.role_for_phase("structure") == "architect"
        assert swarm.role_for_phase("report") == "architect"

    def test_coder_drives_execute(self, swarm):
        assert swarm.role_for_phase("execute") == "coder"

    def test_reviewer_drives_review(self, swarm):
        assert swarm.role_for_phase("review") == "reviewer"

    def test_verifier_drives_verify(self, swarm):
        assert swarm.role_for_phase("verify") == "verifier"

    def test_profile_for_phase_returns_correct_profile(self, swarm):
        p = swarm.profile_for_phase("execute")
        assert p.role == "coder"
        assert p.can_write is True

    def test_unknown_role_raises(self, swarm):
        with pytest.raises(KeyError):
            swarm.get_profile("wizard")


# ── AgentSwarm — permission enforcement ──────────────────────────────────────

class TestSwarmPermissions:
    @pytest.fixture
    def swarm(self, tmp_path) -> AgentSwarm:
        from workflow.artifact_store import ArtifactStore
        store = ArtifactStore(artifacts_root=tmp_path / "arts", db_path=tmp_path / "arts.db")
        return AgentSwarm(
            ollama_base="http://localhost:11434",
            artifact_store=store,
            workspace_root=tmp_path,
        )

    def test_write_op_blocked_for_scout(self, swarm):
        scout = swarm.get_profile("scout")
        with pytest.raises(PermissionError, match="can_write"):
            AgentSwarm._check_permissions(scout, "execute", write_op=True)

    def test_write_op_allowed_for_coder(self, swarm):
        coder = swarm.get_profile("coder")
        # Should not raise
        AgentSwarm._check_permissions(coder, "execute", write_op=True)

    def test_execute_op_blocked_for_reviewer(self, swarm):
        reviewer = swarm.get_profile("reviewer")
        with pytest.raises(PermissionError, match="can_execute"):
            AgentSwarm._check_permissions(reviewer, "verify", execute_op=True)

    def test_execute_op_allowed_for_verifier(self, swarm):
        verifier = swarm.get_profile("verifier")
        AgentSwarm._check_permissions(verifier, "verify", execute_op=True)

    def test_write_blocked_for_reviewer(self, swarm):
        reviewer = swarm.get_profile("reviewer")
        with pytest.raises(PermissionError, match="can_write"):
            AgentSwarm._check_permissions(reviewer, "execute", write_op=True)


# ── AgentSwarm — dual-model invariant ────────────────────────────────────────

class TestDualModelInvariant:
    @pytest.fixture
    def swarm_same_model(self, tmp_path) -> AgentSwarm:
        from workflow.artifact_store import ArtifactStore
        from agents.profiles import AgentProfile
        # Deliberately set coder == reviewer to trigger the warning
        profiles = load_all_profiles()
        profiles["reviewer"] = AgentProfile(
            role="reviewer",
            name="Reviewer",
            model=profiles["coder"].model,  # same model — bad!
            system_prompt="...",
            can_read=True,
            can_review=True,
        )
        store = ArtifactStore(artifacts_root=tmp_path / "arts", db_path=tmp_path / "arts.db")
        return AgentSwarm(
            ollama_base="http://localhost:11434",
            artifact_store=store,
            workspace_root=tmp_path,
            profiles=profiles,
        )

    def test_same_model_triggers_warning(self, swarm_same_model, caplog):
        """When coder == reviewer model, swarm should log a warning."""
        import logging, asyncio
        from workflow.artifact_store import ArtifactStore
        from workflow.models import ModelRoutingConfig, Slice, Artifact
        import secrets
        sl = Slice(
            slice_id="sl_test", run_id="wf_test", index=1,
            title="Test slice", description="desc",
        )
        fake_art = Artifact(
            artifact_id="art_x", run_id="wf_test", phase="execute",
            name="slice-01.md", path="/tmp/slice-01.md", size_bytes=10,
        )
        with caplog.at_level(logging.WARNING, logger="crispy-swarm"):
            with patch.object(
                swarm_same_model._runner, "run_slice_review",
                new=AsyncMock(return_value=fake_art)
            ):
                asyncio.run(
                    swarm_same_model.run_slice_review(
                        run_id="wf_test",
                        sl=sl,
                        routing=ModelRoutingConfig(),
                        slice_artifact=fake_art,
                    )
                )
        assert any("same model" in r.message for r in caplog.records)


# ── AgentSwarm — team_summary ─────────────────────────────────────────────────

class TestTeamSummary:
    @pytest.fixture
    def swarm(self, tmp_path) -> AgentSwarm:
        from workflow.artifact_store import ArtifactStore
        store = ArtifactStore(artifacts_root=tmp_path / "arts", db_path=tmp_path / "arts.db")
        return AgentSwarm(
            ollama_base="http://localhost:11434",
            artifact_store=store,
            workspace_root=tmp_path,
        )

    def test_summary_has_five_entries(self, swarm):
        summary = swarm.team_summary()
        assert len(summary) == 5

    def test_summary_fields(self, swarm):
        summary = swarm.team_summary()
        for entry in summary:
            assert "role" in entry
            assert "name" in entry
            assert "model" in entry
            assert "can_write" in entry
            assert "can_execute" in entry
            assert "can_review" in entry

    def test_only_coder_can_write(self, swarm):
        summary = swarm.team_summary()
        writers = [e["role"] for e in summary if e["can_write"]]
        assert writers == ["coder"]

    def test_only_verifier_can_execute(self, swarm):
        summary = swarm.team_summary()
        executers = [e["role"] for e in summary if e["can_execute"]]
        assert executers == ["verifier"]

    def test_only_reviewer_can_review(self, swarm):
        summary = swarm.team_summary()
        reviewers = [e["role"] for e in summary if e["can_review"]]
        assert reviewers == ["reviewer"]

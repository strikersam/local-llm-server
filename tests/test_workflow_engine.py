"""tests/test_workflow_engine.py — Integration tests for WorkflowEngine.

Uses tmp_path for isolation.  LLM calls are stubbed so tests run without
a running Ollama instance.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from workflow.artifact_store import ArtifactStore
from workflow.engine import WorkflowEngine, _extract_slices_from_plan
from workflow.models import (
    WorkflowBuildRequest,
    WorkflowRun,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def store(tmp_path: Path) -> ArtifactStore:
    return ArtifactStore(
        artifacts_root=tmp_path / "artifacts",
        db_path=tmp_path / "workflow.db",
    )


@pytest.fixture()
def engine(tmp_path: Path) -> WorkflowEngine:
    return WorkflowEngine(
        ollama_base="http://localhost:11434",
        db_path=tmp_path / "workflow.db",
        artifacts_root=tmp_path / "artifacts",
        workspace_root=tmp_path,
    )


def _stub_phase_runner(engine: WorkflowEngine, content: str = "# stub artifact") -> None:
    """Patch PhaseRunner to return a stub artifact without LLM calls."""
    from workflow.artifact_store import ArtifactStore
    from workflow.models import Artifact, _now

    async def fake_run_phase(
        *,
        run_id: str,
        phase: str,
        request: str,
        routing: Any,
        prior_artifacts: Any,
    ) -> Artifact:
        return engine._artifact_store.persist(
            run_id=run_id,
            phase=phase,
            name=_artifact_name_for(phase),
            content=content,
        )

    engine._phase_runner.run_phase = fake_run_phase  # type: ignore[method-assign]


def _artifact_name_for(phase: str) -> str:
    mapping = {
        "context": "context.md",
        "research": "research.md",
        "investigate": "investigation.md",
        "structure": "structure.md",
        "plan": "plan.md",
        "report": "final-report.md",
    }
    return mapping.get(phase, f"{phase}.md")


# ── Tests: run creation ───────────────────────────────────────────────────────


class TestWorkflowEngineCreate:
    def test_create_run_persists_to_db(self, engine: WorkflowEngine):
        req = WorkflowBuildRequest(
            request="Add comprehensive unit tests to the router module"
        )

        async def run():
            _stub_phase_runner(engine)
            # Patch _run_pre_gate_phases to not actually run in background
            with patch.object(engine, "_run_pre_gate_phases", new=AsyncMock()):
                return await engine.create_run(req)

        result = asyncio.run(run())
        assert result.run_id.startswith("wf_")
        assert result.status == "pending"
        assert result.title.startswith("Add comprehensive")
        # Verify it's persisted
        retrieved = engine.get(result.run_id)
        assert retrieved is not None
        assert retrieved.run_id == result.run_id

    def test_create_run_builds_phases(self, engine: WorkflowEngine):
        req = WorkflowBuildRequest(
            request="Implement the CRISPY workflow engine phase system"
        )

        async def run():
            with patch.object(engine, "_run_pre_gate_phases", new=AsyncMock()):
                return await engine.create_run(req)

        result = asyncio.run(run())
        phase_names = [p.name for p in result.phases]
        assert "context" in phase_names
        assert "research" in phase_names
        assert "plan" in phase_names
        assert "report" in phase_names

    def test_list_returns_created_run(self, engine: WorkflowEngine):
        req = WorkflowBuildRequest(
            request="Build something very important for the project"
        )

        async def run():
            with patch.object(engine, "_run_pre_gate_phases", new=AsyncMock()):
                return await engine.create_run(req)

        asyncio.run(run())
        listed = engine.list_runs()
        assert len(listed) == 1


# ── Tests: approval gate ──────────────────────────────────────────────────────


class TestApprovalGate:
    def _create_run_at_gate(self, engine: WorkflowEngine, req_text: str) -> WorkflowRun:
        """Create a run and manually put it in awaiting_approval state."""
        from workflow.models import ApprovalGate

        req = WorkflowBuildRequest(request=req_text)

        async def run():
            with patch.object(engine, "_run_pre_gate_phases", new=AsyncMock()):
                return await engine.create_run(req)

        result = asyncio.run(run())
        # Manually set awaiting_approval state (simulating pre-gate complete)
        with engine._lock:
            r = engine._runs[result.run_id]
            r.status = "awaiting_approval"
            r.approval_gate = ApprovalGate(
                gate_id="gate_test",
                run_id=result.run_id,
                status="pending",
            )
            engine._save(r)
        return engine.get(result.run_id)  # type: ignore[return-value]

    def test_approve_changes_status_to_executing(self, engine: WorkflowEngine):
        run = self._create_run_at_gate(
            engine, "Add authentication to the admin panel module"
        )

        async def do_approve():
            with patch.object(engine, "_run_post_gate", new=AsyncMock()):
                return engine.approve(run.run_id, approved_by="alice")

        updated = asyncio.run(do_approve())
        assert updated.status == "executing"
        assert updated.approval_gate.status == "approved"  # type: ignore[union-attr]
        assert updated.approval_gate.approved_by == "alice"  # type: ignore[union-attr]


    def test_reject_changes_status_to_failed(self, engine: WorkflowEngine):
        run = self._create_run_at_gate(
            engine, "Refactor the routing system across all modules"
        )
        updated = engine.reject(
            run.run_id, reason="Plan is incomplete", rejected_by="bob"
        )
        assert updated.status == "failed"
        assert updated.approval_gate.status == "rejected"  # type: ignore[union-attr]
        assert updated.approval_gate.rejection_reason == "Plan is incomplete"  # type: ignore[union-attr]

    def test_approve_wrong_status_raises_value_error(self, engine: WorkflowEngine):
        req = WorkflowBuildRequest(request="Build something critical for the system")

        async def run():
            with patch.object(engine, "_run_pre_gate_phases", new=AsyncMock()):
                return await engine.create_run(req)

        result = asyncio.run(run())
        # Status is "pending", not "awaiting_approval"
        with pytest.raises(ValueError, match="awaiting_approval"):
            engine.approve(result.run_id)

    def test_get_run_not_found_returns_none(self, engine: WorkflowEngine):
        assert engine.get("wf_nonexistent") is None


# ── Tests: cancel ─────────────────────────────────────────────────────────────


class TestCancel:
    def test_cancel_pending_run(self, engine: WorkflowEngine):
        req = WorkflowBuildRequest(request="Implement something that should be cancelled")

        async def run():
            with patch.object(engine, "_run_pre_gate_phases", new=AsyncMock()):
                return await engine.create_run(req)

        created = asyncio.run(run())
        updated = engine.cancel(created.run_id)
        assert updated.status == "cancelled"

    def test_cancel_done_run_raises(self, engine: WorkflowEngine):
        req = WorkflowBuildRequest(request="Something already complete and done now")

        async def run():
            with patch.object(engine, "_run_pre_gate_phases", new=AsyncMock()):
                return await engine.create_run(req)

        created = asyncio.run(run())
        with engine._lock:
            r = engine._runs[created.run_id]
            r.status = "done"
            engine._save(r)
        with pytest.raises(ValueError):
            engine.cancel(created.run_id)


# ── Tests: event log ──────────────────────────────────────────────────────────


class TestEventLog:
    def test_events_logged_on_create(self, engine: WorkflowEngine):
        req = WorkflowBuildRequest(request="Add comprehensive tests to the workflow module")

        async def run():
            with patch.object(engine, "_run_pre_gate_phases", new=AsyncMock()):
                return await engine.create_run(req)

        result = asyncio.run(run())
        events = engine.get_events(result.run_id)
        assert len(events) >= 1
        assert events[0]["event_type"] == "workflow_created"

    def test_events_from_position(self, engine: WorkflowEngine):
        req = WorkflowBuildRequest(request="Build a multi-step feature with proper testing")

        async def run():
            with patch.object(engine, "_run_pre_gate_phases", new=AsyncMock()):
                return await engine.create_run(req)

        result = asyncio.run(run())
        engine._log_event(result.run_id, "custom_event", {"key": "value"})
        all_events = engine.get_events(result.run_id)
        # from_position=1 should skip the first event
        if len(all_events) > 1:
            partial = engine.get_events(result.run_id, from_position=1)
            assert len(partial) == len(all_events) - 1


# ── Tests: slice extraction ───────────────────────────────────────────────────


class TestSliceExtraction:
    def test_extract_slices_from_valid_plan(self):
        plan = """
# Implementation Plan

## Slice 1: Add workflow models
Add Pydantic models for WorkflowRun, Phase, Slice.
Files: workflow/models.py, tests/test_workflow_models.py

## Slice 2: Add artifact store
Implement filesystem + SQLite artifact persistence.
Files: workflow/artifact_store.py
"""
        slices = _extract_slices_from_plan("wf_001", plan)
        assert len(slices) == 2
        assert slices[0].index == 1
        assert slices[0].title == "Add workflow models"
        assert "workflow/models.py" in slices[0].files
        assert slices[1].index == 2
        assert slices[1].title == "Add artifact store"
        assert "workflow/artifact_store.py" in slices[1].files

    def test_extract_slices_empty_plan(self):
        slices = _extract_slices_from_plan("wf_002", "# No slices here")
        assert slices == []

    def test_extract_slices_no_files_line(self):
        plan = "## Slice 1: Update the readme\nJust update the README with new docs.\n"
        slices = _extract_slices_from_plan("wf_003", plan)
        assert len(slices) == 1
        assert slices[0].files == []

    def test_slices_sorted_by_index(self):
        plan = """
## Slice 3: Third slice here
Some description here.

## Slice 1: First slice here
Some description here.

## Slice 2: Second slice here
Some description here.
"""
        slices = _extract_slices_from_plan("wf_004", plan)
        assert [s.index for s in slices] == [1, 2, 3]


# ── Tests: persistence across restart ────────────────────────────────────────


class TestPersistenceAcrossRestart:
    def test_runs_survive_engine_restart(self, tmp_path: Path):
        db_path = tmp_path / "workflow.db"
        arts_path = tmp_path / "artifacts"

        engine1 = WorkflowEngine(
            ollama_base="http://localhost:11434",
            db_path=db_path,
            artifacts_root=arts_path,
            workspace_root=tmp_path,
        )
        req = WorkflowBuildRequest(request="A task that must survive a server restart")

        async def run():
            with patch.object(engine1, "_run_pre_gate_phases", new=AsyncMock()):
                return await engine1.create_run(req)

        created = asyncio.run(run())
        run_id = created.run_id

        # Simulate engine restart with same DB
        engine2 = WorkflowEngine(
            ollama_base="http://localhost:11434",
            db_path=db_path,
            artifacts_root=arts_path,
            workspace_root=tmp_path,
        )
        retrieved = engine2.get(run_id)
        assert retrieved is not None
        assert retrieved.run_id == run_id
        assert retrieved.title == created.title

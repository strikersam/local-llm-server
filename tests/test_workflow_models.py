"""tests/test_workflow_models.py — Unit tests for workflow/models.py."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from workflow.models import (
    ApprovalGate,
    Artifact,
    CheckRun,
    ModelRoutingConfig,
    Phase,
    Slice,
    WorkflowBuildRequest,
    WorkflowRun,
)


class TestWorkflowBuildRequest:
    def test_valid_request(self):
        req = WorkflowBuildRequest(request="Add unit tests to the router module")
        assert req.request.startswith("Add")
        assert req.title is None
        assert req.model_routing.architect is None

    def test_request_too_short_is_rejected(self):
        with pytest.raises(ValidationError):
            WorkflowBuildRequest(request="short")

    def test_custom_title(self):
        req = WorkflowBuildRequest(request="Implement the CRISPY workflow engine", title="CRISPY")
        assert req.title == "CRISPY"

    def test_model_routing_override(self):
        req = WorkflowBuildRequest(
            request="Implement the CRISPY workflow engine",
            model_routing=ModelRoutingConfig(coder="devstral:latest"),
        )
        assert req.model_routing.coder == "devstral:latest"
        assert req.model_routing.architect is None


class TestWorkflowRun:
    def _make_run(self) -> WorkflowRun:
        return WorkflowRun(
            run_id="wf_test123",
            title="Test run",
            request="Build something important for the system",
            phases=[
                Phase(
                    phase_id="ph_1",
                    run_id="wf_test123",
                    name="context",
                    agent_role="scout",
                ),
                Phase(
                    phase_id="ph_2",
                    run_id="wf_test123",
                    name="plan",
                    agent_role="architect",
                ),
            ],
        )

    def test_run_creation(self):
        run = self._make_run()
        assert run.run_id == "wf_test123"
        assert run.status == "pending"
        assert len(run.phases) == 2
        assert len(run.slices) == 0
        assert len(run.artifacts) == 0

    def test_artifact_by_name_found(self):
        run = self._make_run()
        art = Artifact(
            artifact_id="art_001",
            run_id="wf_test123",
            phase="context",
            name="context.md",
            path="/tmp/context.md",
        )
        run.artifacts.append(art)
        found = run.artifact_by_name("context.md")
        assert found is not None
        assert found.artifact_id == "art_001"

    def test_artifact_by_name_not_found(self):
        run = self._make_run()
        assert run.artifact_by_name("missing.md") is None

    def test_phase_by_type_found(self):
        run = self._make_run()
        phase = run.phase_by_type("context")
        assert phase is not None
        assert phase.agent_role == "scout"

    def test_phase_by_type_not_found(self):
        run = self._make_run()
        assert run.phase_by_type("report") is None

    def test_slice_by_id(self):
        run = self._make_run()
        sl = Slice(
            slice_id="sl_abc",
            run_id="wf_test123",
            index=1,
            title="Slice 1",
            description="Implement something important here",
        )
        run.slices.append(sl)
        assert run.slice_by_id("sl_abc") is not None
        assert run.slice_by_id("sl_missing") is None

    def test_round_trip_serialisation(self):
        run = self._make_run()
        data = run.model_dump_json()
        restored = WorkflowRun.model_validate_json(data)
        assert restored.run_id == run.run_id
        assert len(restored.phases) == 2


class TestApprovalGate:
    def test_default_state(self):
        gate = ApprovalGate(gate_id="gate_001", run_id="wf_001")
        assert gate.status == "pending"
        assert gate.approved_by is None
        assert "structure.md" in gate.requires_review_of
        assert "plan.md" in gate.requires_review_of

    def test_approved(self):
        gate = ApprovalGate(gate_id="gate_001", run_id="wf_001")
        gate.status = "approved"
        gate.approved_by = "alice"
        assert gate.status == "approved"

    def test_rejected(self):
        gate = ApprovalGate(gate_id="gate_001", run_id="wf_001")
        gate.status = "rejected"
        gate.rejection_reason = "Plan is incomplete"
        assert gate.rejection_reason == "Plan is incomplete"


class TestCheckRun:
    def test_passed_when_exit_code_zero(self):
        cr = CheckRun(
            check_id="chk_001",
            slice_id="sl_001",
            run_id="wf_001",
            commands=["pytest -x"],
            exit_code=0,
            passed=True,
        )
        assert cr.passed is True

    def test_failed_when_exit_code_nonzero(self):
        cr = CheckRun(
            check_id="chk_002",
            slice_id="sl_001",
            run_id="wf_001",
            commands=["pytest -x"],
            exit_code=1,
            stdout="FAILED test_foo.py",
            passed=False,
        )
        assert cr.passed is False
        assert "FAILED" in cr.stdout

    def test_as_dict_contains_all_fields(self):
        cr = CheckRun(
            check_id="chk_003",
            slice_id="sl_001",
            run_id="wf_001",
            commands=["pytest -x", "ruff check ."],
            exit_code=0,
            passed=True,
        )
        d = cr.as_dict()
        assert "check_id" in d
        assert "commands" in d
        assert d["commands"] == ["pytest -x", "ruff check ."]


class TestSlice:
    def test_default_status_is_pending(self):
        sl = Slice(
            slice_id="sl_001",
            run_id="wf_001",
            index=1,
            title="First slice",
            description="Implement something notable and specific here",
        )
        assert sl.status == "pending"
        assert sl.check_run is None
        assert sl.files == []

    def test_with_files(self):
        sl = Slice(
            slice_id="sl_001",
            run_id="wf_001",
            index=1,
            title="Slice with files",
            description="Implement a thing with specific file targets here",
            files=["agent/loop.py", "tests/test_agent_runner.py"],
        )
        assert len(sl.files) == 2

    def test_as_dict(self):
        sl = Slice(
            slice_id="sl_001",
            run_id="wf_001",
            index=1,
            title="Slice",
            description="A notable description of what this slice implements",
        )
        d = sl.as_dict()
        assert d["slice_id"] == "sl_001"
        assert d["status"] == "pending"

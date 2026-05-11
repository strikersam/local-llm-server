"""Tests for agent/schemas.py — Pydantic models added in this PR."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent.schemas import (
    AcceptedJob,
    AgentJobEnvelope,
    CompletedJob,
    FailedJob,
    RunningJob,
)


class TestAcceptedJob:
    def test_valid_construction(self):
        job = AcceptedJob(
            session_id="sess-1",
            job_id="aj_abc123",
            status="queued",
            phase="queued",
            message="Agent workflow queued.",
        )
        assert job.session_id == "sess-1"
        assert job.job_id == "aj_abc123"
        assert job.status == "queued"
        assert job.phase == "queued"
        assert job.message == "Agent workflow queued."

    def test_model_dump_has_all_fields(self):
        job = AcceptedJob(
            session_id="s", job_id="j", status="queued", phase="queued", message="m"
        )
        d = job.model_dump()
        assert set(d.keys()) == {"session_id", "job_id", "status", "phase", "message"}

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            AcceptedJob(session_id="s", job_id="j", status="queued", phase="queued")


class TestRunningJob:
    def test_valid_construction_without_workspace(self):
        job = RunningJob(
            job_id="j1",
            session_id="s1",
            status="running",
            phase="planning",
            progress_events=[{"phase": "starting", "message": "ok"}],
        )
        assert job.workspace_path is None
        assert len(job.progress_events) == 1

    def test_valid_construction_with_workspace(self):
        job = RunningJob(
            job_id="j1",
            session_id="s1",
            status="running",
            phase="planning",
            progress_events=[],
            workspace_path="/tmp/ws",
        )
        assert job.workspace_path == "/tmp/ws"

    def test_model_dump_contains_workspace_path_key(self):
        job = RunningJob(
            job_id="j1", session_id="s1", status="running", phase="p",
            progress_events=[],
        )
        d = job.model_dump()
        assert "workspace_path" in d
        assert d["workspace_path"] is None


class TestCompletedJob:
    def test_valid_with_final_message(self):
        job = CompletedJob(
            job_id="j2",
            session_id="s2",
            status="succeeded",
            phase="completed",
            final_message="Task done.",
            result={"response": "Task done.", "raw": {}},
        )
        assert job.final_message == "Task done."
        assert job.result is not None

    def test_optional_fields_default_to_none(self):
        job = CompletedJob(
            job_id="j2", session_id="s2", status="succeeded", phase="completed"
        )
        assert job.final_message is None
        assert job.result is None

    def test_model_dump_keys(self):
        job = CompletedJob(
            job_id="j2", session_id="s2", status="succeeded", phase="completed"
        )
        d = job.model_dump()
        assert "final_message" in d
        assert "result" in d


class TestFailedJob:
    def test_valid_with_error(self):
        job = FailedJob(
            job_id="j3",
            session_id="s3",
            status="failed",
            phase="failed",
            error={"code": "runtime_preflight", "message": "Docker missing"},
        )
        assert job.error["code"] == "runtime_preflight"

    def test_missing_error_field_raises(self):
        with pytest.raises(ValidationError):
            FailedJob(job_id="j3", session_id="s3", status="failed", phase="failed")

    def test_model_dump_has_error(self):
        job = FailedJob(
            job_id="j3", session_id="s3", status="failed", phase="failed",
            error={"type": "ValueError", "message": "oops"},
        )
        d = job.model_dump()
        assert d["error"]["type"] == "ValueError"


class TestAgentJobEnvelope:
    def test_envelope_with_only_accepted(self):
        accepted = AcceptedJob(
            session_id="s", job_id="j", status="queued", phase="queued",
            message="queued",
        )
        envelope = AgentJobEnvelope(accepted=accepted)
        assert envelope.accepted.job_id == "j"
        assert envelope.running is None
        assert envelope.completed is None
        assert envelope.failed is None

    def test_envelope_with_completed(self):
        accepted = AcceptedJob(
            session_id="s", job_id="j", status="queued", phase="queued", message="m"
        )
        completed = CompletedJob(
            job_id="j", session_id="s", status="succeeded", phase="completed",
            final_message="done",
        )
        envelope = AgentJobEnvelope(accepted=accepted, completed=completed)
        assert envelope.completed.final_message == "done"

    def test_envelope_model_dump(self):
        accepted = AcceptedJob(
            session_id="s", job_id="j", status="queued", phase="queued", message="m"
        )
        envelope = AgentJobEnvelope(accepted=accepted)
        d = envelope.model_dump()
        assert "accepted" in d
        assert d["running"] is None
        assert d["failed"] is None
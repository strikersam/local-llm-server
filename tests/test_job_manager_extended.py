"""Extended tests for agent/job_manager.py covering normalization edge cases and
structured error codes introduced in this PR."""
from __future__ import annotations

import asyncio
import pytest

from agent.job_manager import AgentJob, AgentJobManager


# ── AgentJob.as_dict() final_message logic ────────────────────────────────────

class TestAgentJobAsDictFinalMessage:
    def _make_job(self, **kwargs) -> AgentJob:
        job = AgentJob(
            job_id="aj_test01",
            session_id="sess-test",
            instruction="do something",
        )
        for k, v in kwargs.items():
            setattr(job, k, v)
        return job

    def test_final_message_from_result_response(self):
        job = self._make_job(result={"response": "Hello from agent", "raw": {}})
        d = job.as_dict()
        assert d["final_message"] == "Hello from agent"

    def test_final_message_from_error_message(self):
        """When result has no response key, final_message falls back to error.message."""
        job = self._make_job(
            result={"raw": {}},
            error={"code": "runtime_unavailable", "message": "Docker not found"},
        )
        d = job.as_dict()
        assert d["final_message"] == "Docker not found"

    def test_final_message_none_when_no_keys(self):
        """Neither result.response nor error.message present → final_message is None."""
        job = self._make_job(result=None, error=None)
        d = job.as_dict()
        assert d["final_message"] is None

    def test_final_message_none_result_not_dict(self):
        """Non-dict result with no error → final_message is None."""
        job = self._make_job(result=None, error=None)
        d = job.as_dict()
        assert d["final_message"] is None

    def test_final_message_prefers_result_over_error(self):
        """result.response takes priority over error.message."""
        job = self._make_job(
            result={"response": "Success text"},
            error={"message": "Should not appear"},
        )
        d = job.as_dict()
        assert d["final_message"] == "Success text"

    def test_as_dict_includes_all_expected_keys(self):
        job = self._make_job()
        d = job.as_dict()
        expected_keys = {
            "job_id", "session_id", "instruction", "owner_id",
            "status", "phase", "created_at", "updated_at", "heartbeat_at",
            "runtime_id", "workspace_path", "requested_model", "provider_id",
            "progress_events", "result", "error", "final_message",
        }
        assert expected_keys.issubset(set(d.keys()))


# ── _run_job result normalization ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_job_normalizes_response_key():
    """When runner returns dict with 'response' key, it is used directly."""
    mgr = AgentJobManager()
    job = mgr.create_job(session_id="s-resp", instruction="respond")

    async def runner(heartbeat):
        return {"response": "Direct response text", "other": "ignored"}

    mgr.start_job(job.job_id, runner)
    for _ in range(200):
        if job.status in ("succeeded", "failed"):
            break
        await asyncio.sleep(0.01)

    assert job.status == "succeeded"
    assert job.result["response"] == "Direct response text"
    assert job.result["raw"]["response"] == "Direct response text"
    assert job.as_dict()["final_message"] == "Direct response text"


@pytest.mark.asyncio
async def test_run_job_normalizes_output_key():
    """When runner returns dict with 'output' key (no response/summary), it is used."""
    mgr = AgentJobManager()
    job = mgr.create_job(session_id="s-out", instruction="output test")

    async def runner(heartbeat):
        return {"output": "Output text from runner"}

    mgr.start_job(job.job_id, runner)
    for _ in range(200):
        if job.status in ("succeeded", "failed"):
            break
        await asyncio.sleep(0.01)

    assert job.status == "succeeded"
    assert job.result["response"] == "Output text from runner"


@pytest.mark.asyncio
async def test_run_job_normalizes_string_report_key():
    """When runner returns dict with string 'report' key, it is used as response."""
    mgr = AgentJobManager()
    job = mgr.create_job(session_id="s-rep", instruction="report test")

    async def runner(heartbeat):
        return {"report": "String report content"}

    mgr.start_job(job.job_id, runner)
    for _ in range(200):
        if job.status in ("succeeded", "failed"):
            break
        await asyncio.sleep(0.01)

    assert job.status == "succeeded"
    assert job.result["response"] == "String report content"


@pytest.mark.asyncio
async def test_run_job_handles_non_dict_string_result():
    """Non-dict runner return (plain string) gets wrapped into {response, raw}."""
    mgr = AgentJobManager()
    job = mgr.create_job(session_id="s-str", instruction="plain string")

    async def runner(heartbeat):
        return "plain string result"

    mgr.start_job(job.job_id, runner)
    for _ in range(200):
        if job.status in ("succeeded", "failed"):
            break
        await asyncio.sleep(0.01)

    assert job.status == "succeeded"
    assert isinstance(job.result, dict)
    assert job.result["response"] == "plain string result"
    assert job.result["raw"] == "plain string result"


# ── _run_job structured error codes ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_job_runtime_unavailable_error_structured():
    """RuntimeUnavailableError yields code='runtime_unavailable' in job.error."""
    from runtimes.base import RuntimeUnavailableError
    mgr = AgentJobManager()
    job = mgr.create_job(session_id="s-unav", instruction="unavailable test")

    async def runner(heartbeat):
        raise RuntimeUnavailableError("docker_agent", "Docker daemon not running")

    mgr.start_job(job.job_id, runner)
    for _ in range(200):
        if job.status in ("succeeded", "failed"):
            break
        await asyncio.sleep(0.01)

    assert job.status == "failed"
    assert isinstance(job.error, dict)
    assert job.error.get("code") == "runtime_unavailable"
    assert "Docker daemon not running" in job.error.get("message", "")


@pytest.mark.asyncio
async def test_run_job_runtime_execution_error_structured():
    """RuntimeExecutionError yields code='runtime_execution_error' in job.error."""
    from runtimes.base import RuntimeExecutionError
    mgr = AgentJobManager()
    job = mgr.create_job(session_id="s-exec", instruction="execution error test")

    async def runner(heartbeat):
        raise RuntimeExecutionError("internal_agent", "Subprocess failed", "task-123")

    mgr.start_job(job.job_id, runner)
    for _ in range(200):
        if job.status in ("succeeded", "failed"):
            break
        await asyncio.sleep(0.01)

    assert job.status == "failed"
    assert job.error.get("code") == "runtime_execution_error"
    assert "Subprocess failed" in job.error.get("message", "")


@pytest.mark.asyncio
async def test_run_job_generic_exception_has_no_structured_code():
    """A generic Exception yields error with type+message but no 'code' key."""
    mgr = AgentJobManager()
    job = mgr.create_job(session_id="s-gen", instruction="generic error test")

    async def runner(heartbeat):
        raise ValueError("Something unexpected")

    mgr.start_job(job.job_id, runner)
    for _ in range(200):
        if job.status in ("succeeded", "failed"):
            break
        await asyncio.sleep(0.01)

    assert job.status == "failed"
    assert job.error.get("type") == "ValueError"
    assert "Something unexpected" in job.error.get("message", "")
    # Generic exceptions do not carry 'code'
    assert "code" not in job.error


@pytest.mark.asyncio
async def test_run_job_appends_progress_events():
    """Heartbeat calls are recorded as progress_events in order."""
    mgr = AgentJobManager()
    job = mgr.create_job(session_id="s-ev", instruction="events test")

    async def runner(heartbeat):
        heartbeat("planning", "Starting planning phase")
        heartbeat("executing", "Executing step 1")
        return {"response": "done"}

    mgr.start_job(job.job_id, runner)
    for _ in range(200):
        if job.status in ("succeeded", "failed"):
            break
        await asyncio.sleep(0.01)

    assert job.status == "succeeded"
    phases = [e["phase"] for e in job.progress_events]
    # Should contain starting (from _run_job), planning, executing, completed
    assert "planning" in phases
    assert "executing" in phases
    assert "completed" in phases


@pytest.mark.asyncio
async def test_run_job_sets_status_transitions():
    """Job starts as queued → running → succeeded."""
    mgr = AgentJobManager()
    job = mgr.create_job(session_id="s-tr", instruction="transitions")
    assert job.status == "queued"

    async def runner(heartbeat):
        return {"response": "ok"}

    mgr.start_job(job.job_id, runner)
    for _ in range(200):
        if job.status in ("succeeded", "failed"):
            break
        await asyncio.sleep(0.01)

    assert job.status == "succeeded"
    assert job.phase == "completed"


# ── AgentJobManager list/get operations ──────────────────────────────────────

def test_list_jobs_filtered_by_session():
    mgr = AgentJobManager()
    j1 = mgr.create_job(session_id="sess-A", instruction="a1")
    j2 = mgr.create_job(session_id="sess-A", instruction="a2")
    j3 = mgr.create_job(session_id="sess-B", instruction="b1")

    all_jobs = mgr.list_jobs()
    assert len(all_jobs) == 3

    sess_a_jobs = mgr.list_jobs(session_id="sess-A")
    assert len(sess_a_jobs) == 2
    assert all(j.session_id == "sess-A" for j in sess_a_jobs)

    sess_b_jobs = mgr.list_jobs(session_id="sess-B")
    assert len(sess_b_jobs) == 1


def test_get_job_returns_none_for_unknown_id():
    mgr = AgentJobManager()
    assert mgr.get_job("nonexistent-job-id") is None


def test_create_job_stores_metadata():
    mgr = AgentJobManager()
    job = mgr.create_job(
        session_id="sess-meta",
        instruction="meta test",
        owner_id="user@example.com",
        runtime_id="docker_agent",
        requested_model="gpt-4",
        provider_id="openai",
    )
    assert job.owner_id == "user@example.com"
    assert job.runtime_id == "docker_agent"
    assert job.requested_model == "gpt-4"
    assert job.provider_id == "openai"
    assert job.status == "queued"
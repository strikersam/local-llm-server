"""Tests for agent/agency.py"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def setup_database_moks(monkeypatch):  # noqa: PT004
    pass


from agent.agency import (
    Agency,
    AgentDirective,
    AgentRole,
    get_agency,
    set_agency,
)


@pytest.fixture
def agency() -> Agency:
    return Agency(tick_minutes=60)


def test_agency_initial_status(agency: Agency):
    status = agency.get_status()
    assert status["running"] is False
    assert status["cycle_count"] == 0
    assert status["pending_directives"] == 0
    assert AgentRole.CEO.value in status["roles"]
    assert AgentRole.DEV.value in status["roles"]


@pytest.mark.asyncio
async def test_run_cycle_no_issues(tmp_path: Path, agency: Agency):
    """With no improvement loop available, CEO returns a 'not available' assessment."""
    # _ceo_assess imports get_improvement_loop from agent.improvement_loop at call time.
    # We patch at the source module level so the lazy import inside the method gets None.
    with patch("agent.improvement_loop.get_improvement_loop", return_value=None), \
         patch.object(agency, "_dispatch_directive"):
        result = await agency.run_cycle()

    assert result.cycle_id.startswith("cycle_")
    assert "ImprovementLoop not available" in result.ceo_assessment
    assert result.directives_issued == 0


@pytest.mark.asyncio
async def test_run_cycle_with_failing_tests(tmp_path: Path, agency: Agency):
    """Failing tests should trigger a Dev agent directive."""
    from agent.improvement_loop import ImprovementLoop, set_improvement_loop

    loop = ImprovementLoop(repo_root=tmp_path, scan_interval_hours=99)
    loop._state.failing_tests = ["tests/test_router.py::test_x"]
    loop._state.last_test_result = "fail"
    set_improvement_loop(loop)

    with patch.object(agency, "_dispatch_directive"):
        result = await agency.run_cycle()

    assert result.directives_issued >= 1
    assert any(d["role"] == AgentRole.DEV.value for d in result.directives)
    set_improvement_loop(None)


@pytest.mark.asyncio
async def test_run_cycle_with_security_issues(tmp_path: Path, agency: Agency):
    """Security issues should trigger a Security agent directive."""
    from agent.improvement_loop import (
        DetectedIssue,
        ImprovementLoop,
        IssueCategory,
        IssueSeverity,
        set_improvement_loop,
    )

    loop = ImprovementLoop(repo_root=tmp_path, scan_interval_hours=99)
    issue = DetectedIssue(
        issue_id="sec_test",
        category=IssueCategory.SECURITY,
        severity=IssueSeverity.HIGH,
        title="B101: hardcoded password",
        description="Found hardcoded password in auth.py:42",
    )
    loop._state.active_issues = [issue.as_dict()]
    set_improvement_loop(loop)

    with patch.object(agency, "_dispatch_directive"):
        result = await agency.run_cycle()

    assert any(d["role"] == AgentRole.SECURITY.value for d in result.directives)
    set_improvement_loop(None)


@pytest.mark.asyncio
async def test_ceo_assessment_nominal(tmp_path: Path, agency: Agency):
    """With no issues, CEO should report nominal."""
    from agent.improvement_loop import ImprovementLoop, set_improvement_loop

    loop = ImprovementLoop(repo_root=tmp_path, scan_interval_hours=99)
    set_improvement_loop(loop)

    with patch.object(agency, "_dispatch_directive"):
        result = await agency.run_cycle()

    assert "nominal" in result.ceo_assessment.lower() or result.directives_issued == 0
    set_improvement_loop(None)


def test_history_is_capped(agency: Agency):
    """Agency should cap history to 50 entries."""
    import asyncio

    async def _fill():
        for _ in range(55):
            with patch("agent.improvement_loop.get_improvement_loop", return_value=None), \
                 patch.object(agency, "_dispatch_directive"):
                await agency.run_cycle()

    asyncio.run(_fill())
    assert len(agency._history) <= 50


def test_singleton():
    orig = get_agency()
    a = Agency(tick_minutes=60)
    set_agency(a)
    assert get_agency() is a
    set_agency(orig)


def test_directive_as_dict():
    d = AgentDirective(
        directive_id="dir_abc",
        role=AgentRole.DEV,
        title="Fix tests",
        instruction="Run pytest and fix failures",
        priority=1,
    )
    dd = d.as_dict()
    assert dd["directive_id"] == "dir_abc"
    assert dd["role"] == "dev"
    assert dd["priority"] == 1
    assert dd["status"] == "pending"

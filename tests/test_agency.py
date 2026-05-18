"""Tests for agent/agency.py"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def setup_database_moks(monkeypatch):  # noqa: PT004
    pass


from agent.agency import (
    Agency,
    AgentDirective,
    AgentRole,
    _parse_ceo_directives,
    _build_ceo_prompt,
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
    assert AgentRole.SCOUT.value in status["roles"]
    assert AgentRole.OPTIMIZER.value in status["roles"]
    assert "runtime_routing" in status
    assert "ceo_model" in status


@pytest.mark.asyncio
async def test_run_cycle_no_issues(tmp_path: Path, agency: Agency) -> None:
    """With no improvement loop available, falls back to rule-based, nominal."""
    with patch("agent.improvement_loop.get_improvement_loop", return_value=None), \
         patch.object(agency, "_dispatch_directive"), \
         patch.object(agency, "_ceo_assess_llm", new_callable=AsyncMock,
                      side_effect=lambda state: agency._ceo_assess_rules(state)):
        result = await agency.run_cycle()

    assert result.cycle_id.startswith("cycle_")
    assert result.directives_issued == 0


@pytest.mark.asyncio
async def test_run_cycle_with_failing_tests(tmp_path: Path, agency: Agency) -> None:
    """Failing tests should trigger a Dev agent directive."""
    from agent.improvement_loop import ImprovementLoop, set_improvement_loop

    loop = ImprovementLoop(repo_root=tmp_path, scan_interval_hours=99)
    loop._state.failing_tests = ["tests/test_router.py::test_x"]
    loop._state.last_test_result = "fail"
    set_improvement_loop(loop)

    with patch.object(agency, "_dispatch_directive"), \
         patch.object(agency, "_ceo_assess_llm", new_callable=AsyncMock,
                      side_effect=lambda state: agency._ceo_assess_rules(state)):
        result = await agency.run_cycle()

    assert result.directives_issued >= 1
    assert any(d["role"] == AgentRole.DEV.value for d in result.directives)
    set_improvement_loop(None)


@pytest.mark.asyncio
async def test_run_cycle_with_security_issues(tmp_path: Path, agency: Agency) -> None:
    """Security issues should trigger a Security agent directive."""
    from agent.improvement_loop import (
        DetectedIssue, ImprovementLoop, IssueCategory, IssueSeverity, set_improvement_loop,
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

    with patch.object(agency, "_dispatch_directive"), \
         patch.object(agency, "_ceo_assess_llm", new_callable=AsyncMock,
                      side_effect=lambda state: agency._ceo_assess_rules(state)):
        result = await agency.run_cycle()

    assert any(d["role"] == AgentRole.SECURITY.value for d in result.directives)
    set_improvement_loop(None)


@pytest.mark.asyncio
async def test_ceo_assessment_nominal(tmp_path: Path, agency: Agency) -> None:
    """With no issues, CEO should report nominal."""
    from agent.improvement_loop import ImprovementLoop, set_improvement_loop

    loop = ImprovementLoop(repo_root=tmp_path, scan_interval_hours=99)
    set_improvement_loop(loop)

    with patch.object(agency, "_dispatch_directive"), \
         patch.object(agency, "_ceo_assess_llm", new_callable=AsyncMock,
                      side_effect=lambda state: agency._ceo_assess_rules(state)):
        result = await agency.run_cycle()

    assert "nominal" in result.ceo_assessment.lower() or result.directives_issued == 0
    set_improvement_loop(None)


@pytest.mark.asyncio
async def test_ceo_llm_parses_valid_json(agency: Agency) -> None:
    """CEO should parse valid JSON directive list from LLM response."""
    valid_json = """Here are my directives:
[
  {"role": "dev", "priority": 1, "title": "Fix failing tests", "instruction": "Run pytest and fix failures."},
  {"role": "security", "priority": 2, "title": "Remediate CVE", "instruction": "Update requests library."}
]
"""
    directives = _parse_ceo_directives(valid_json, cycle=1)
    assert len(directives) == 2
    assert directives[0].role == AgentRole.DEV
    assert directives[1].role == AgentRole.SECURITY
    assert directives[0].priority == 1
    assert "preferred_runtime" in directives[0].as_dict()


@pytest.mark.asyncio
async def test_ceo_llm_handles_empty_json(agency: Agency) -> None:
    """CEO should return empty list on '[]' or no-work response."""
    directives = _parse_ceo_directives("[]", cycle=1)
    assert directives == []


@pytest.mark.asyncio
async def test_ceo_llm_handles_invalid_json(agency: Agency) -> None:
    """CEO should gracefully handle non-JSON LLM response."""
    directives = _parse_ceo_directives("All systems look good, no action needed.", cycle=1)
    assert directives == []


@pytest.mark.asyncio
async def test_ceo_llm_unknown_role_defaults_to_dev(agency: Agency) -> None:
    json_text = '[{"role": "unknown_role", "priority": 3, "title": "T", "instruction": "I"}]'
    directives = _parse_ceo_directives(json_text, cycle=1)
    assert len(directives) == 1
    assert directives[0].role == AgentRole.DEV


def test_build_ceo_prompt_includes_context():
    state = {
        "improvement_loop": {
            "failing_tests": ["test_x", "test_y"],
            "active_issues": [{"category": "security", "title": "CVE in requests"}],
            "issues_detected": 5,
            "issues_resolved": 3,
            "scan_count": 10,
        },
        "log_monitor": {"tasks_created": 2},
        "top_trends": [
            {"source": "ollama", "title": "Ollama v1.0", "relevance_score": 0.9},
        ],
    }
    prompt = _build_ceo_prompt(state, cycle=5)
    assert "test_x" in prompt
    assert "CVE in requests" in prompt
    assert "Ollama v1.0" in prompt
    assert "cycle 5" in prompt


@pytest.mark.asyncio
async def test_run_cycle_with_trend_issues(tmp_path: Path, agency: Agency) -> None:
    """Trend issues should trigger a Scout directive on eligible cycles."""
    from agent.improvement_loop import (
        DetectedIssue, ImprovementLoop, IssueCategory, IssueSeverity, set_improvement_loop,
    )

    loop = ImprovementLoop(repo_root=tmp_path, scan_interval_hours=99)
    issue = DetectedIssue(
        issue_id="trend_abc",
        category=IssueCategory.TREND,
        severity=IssueSeverity.LOW,
        title="[Trend] Ollama v9.0 released",
        description="Source: ollama\nURL: https://example.com\n\nNew models supported.",
    )
    loop._state.active_issues = [issue.as_dict()]
    set_improvement_loop(loop)

    # Force cycle_count so that cycle % 3 == 0 (Scout condition)
    agency._cycle_count = 2  # will be incremented to 3 in run_cycle

    with patch.object(agency, "_dispatch_directive"), \
         patch.object(agency, "_ceo_assess_llm", new_callable=AsyncMock,
                      side_effect=lambda state: agency._ceo_assess_rules(state)):
        result = await agency.run_cycle()

    scout_directives = [d for d in result.directives if d["role"] == AgentRole.SCOUT.value]
    assert len(scout_directives) >= 1
    set_improvement_loop(None)


@pytest.mark.asyncio
async def test_directive_has_preferred_runtime(tmp_path: Path, agency: Agency) -> None:
    """Dev directives should prefer claude_code runtime."""
    from agent.improvement_loop import ImprovementLoop, set_improvement_loop

    loop = ImprovementLoop(repo_root=tmp_path, scan_interval_hours=99)
    loop._state.failing_tests = ["test_foo"]
    loop._state.last_test_result = "fail"
    set_improvement_loop(loop)

    dispatched = []
    with patch.object(agency, "_dispatch_directive", side_effect=dispatched.append), \
         patch.object(agency, "_ceo_assess_llm", new_callable=AsyncMock,
                      side_effect=lambda state: agency._ceo_assess_rules(state)):
        result = await agency.run_cycle()

    assert any(d["preferred_runtime"] == "claude_code" for d in result.directives)
    set_improvement_loop(None)


def test_history_is_capped(agency: Agency):
    """Agency should cap history to 50 entries."""
    import asyncio

    async def _fill():
        for _ in range(55):
            with patch("agent.improvement_loop.get_improvement_loop", return_value=None), \
                 patch.object(agency, "_dispatch_directive"), \
                 patch.object(agency, "_ceo_assess_llm", new_callable=AsyncMock,
                              side_effect=lambda state: agency._ceo_assess_rules(state)):
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
        preferred_runtime="claude_code",
    )
    dd = d.as_dict()
    assert dd["directive_id"] == "dir_abc"
    assert dd["role"] == "dev"
    assert dd["priority"] == 1
    assert dd["status"] == "pending"
    assert dd["preferred_runtime"] == "claude_code"


def test_all_roles_in_enum():
    roles = {r.value for r in AgentRole}
    assert "ceo" in roles
    assert "dev" in roles
    assert "security" in roles
    assert "reviewer" in roles
    assert "release" in roles
    assert "scout" in roles
    assert "optimizer" in roles

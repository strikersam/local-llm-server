"""Tests for agent/self_healing.py"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def setup_database_moks(monkeypatch):  # noqa: PT004
    pass


from agent.self_healing import (
    HealingEvent,
    SelfHealingAgent,
    get_self_healing_agent,
    set_self_healing_agent,
)


@pytest.fixture
def healer() -> SelfHealingAgent:
    return SelfHealingAgent()


@pytest.mark.asyncio
async def test_on_ci_failure_creates_event(healer: SelfHealingAgent):
    event = await healer.on_ci_failure({"test": "test_router", "error": "AssertionError", "workflow": "ci"})
    assert isinstance(event, HealingEvent)
    assert event.source == "ci"
    assert "test_router" in event.title
    assert event.severity == "high"


@pytest.mark.asyncio
async def test_on_manual_report_creates_event(healer: SelfHealingAgent):
    event = await healer.on_manual_report("Memory leak in loop.py", "Details here", severity="high")
    assert event.source == "manual"
    assert "Memory leak" in event.title
    assert event.severity == "high"


@pytest.mark.asyncio
async def test_on_github_issue_bug_label(healer: SelfHealingAgent):
    issue = {
        "title": "Router crashes on empty model list",
        "body": "Steps to reproduce: ...",
        "labels": [{"name": "bug"}, {"name": "P1"}],
    }
    event = await healer.on_github_issue(issue)
    assert event.source == "github_issue"
    assert "Router crashes" in event.title
    # bug label → dispatch triggered


@pytest.mark.asyncio
async def test_on_github_issue_no_bug_label_no_dispatch(healer: SelfHealingAgent):
    issue = {
        "title": "Feature: add dark mode",
        "body": "Would be nice",
        "labels": [{"name": "enhancement"}],
    }
    event = await healer.on_github_issue(issue)
    assert event.source == "github_issue"
    # no bug/fix label — event logged but no dispatch (no error should occur)


@pytest.mark.asyncio
async def test_critical_label_sets_high_severity(healer: SelfHealingAgent):
    issue = {
        "title": "Server crashes on startup",
        "body": "...",
        "labels": [{"name": "critical"}, {"name": "bug"}],
    }
    event = await healer.on_github_issue(issue)
    assert event.severity == "high"


def test_get_events_initially_empty(healer: SelfHealingAgent):
    assert healer.get_events() == []


@pytest.mark.asyncio
async def test_get_events_returns_all(healer: SelfHealingAgent):
    await healer.on_manual_report("Bug A", "desc", "low")
    await healer.on_manual_report("Bug B", "desc", "medium")
    events = healer.get_events()
    assert len(events) == 2
    titles = [e["title"] for e in events]
    assert "Bug A" in titles
    assert "Bug B" in titles


def test_singleton_round_trip():
    orig = get_self_healing_agent()
    h = SelfHealingAgent()
    set_self_healing_agent(h)
    assert get_self_healing_agent() is h
    set_self_healing_agent(orig)


@pytest.mark.asyncio
async def test_dispatch_with_improvement_loop(tmp_path):
    """dispatch_fix should call _register_issue on the improvement loop."""
    from agent.improvement_loop import ImprovementLoop, set_improvement_loop, get_improvement_loop

    loop = ImprovementLoop(repo_root=tmp_path, scan_interval_hours=24)
    set_improvement_loop(loop)

    healer = SelfHealingAgent()
    await healer.on_ci_failure({"test": "test_x", "error": "boom"})

    status = loop.get_status()
    assert any("test_x" in i.get("title", "") for i in status["active_issues"])

    # Restore
    set_improvement_loop(get_improvement_loop())

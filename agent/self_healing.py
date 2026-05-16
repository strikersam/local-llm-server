"""agent/self_healing.py — Self-Healing Agent

Translates external failure signals (CI webhooks, GitHub issue events, manual
dashboard reports) into improvement tasks dispatched through ImprovementLoop.

Flow:
    CI failure webhook   → on_ci_failure()   → _dispatch_fix()
    GitHub bug issue     → on_github_issue()  → _dispatch_fix()
    Dashboard bug report → on_manual_report() → _dispatch_fix()
"""
from __future__ import annotations

import logging
import secrets
import time
from dataclasses import dataclass
from typing import Any

log = logging.getLogger("qwen-proxy")


@dataclass
class HealingEvent:
    event_id: str
    source: str       # "ci" | "github_issue" | "manual"
    title: str
    description: str
    severity: str     # "critical" | "high" | "medium" | "low"
    created_at: str
    task_id: str | None = None
    resolved: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "source": self.source,
            "title": self.title,
            "severity": self.severity,
            "created_at": self.created_at,
            "resolved": self.resolved,
            "task_id": self.task_id,
        }


class SelfHealingAgent:
    """Translate external failure signals into improvement tasks.

    Usage::

        healer = SelfHealingAgent()
        await healer.on_ci_failure({"test": "test_router", "error": "..."})
        await healer.on_manual_report("Memory leak", "...")
    """

    def __init__(self) -> None:
        self._events: list[HealingEvent] = []

    # ── Public API ────────────────────────────────────────────────────────────

    async def on_ci_failure(self, failure_info: dict[str, Any]) -> HealingEvent:
        """Called when a CI workflow fails."""
        test_name = failure_info.get("test", "unknown-test")
        error = failure_info.get("error", "")
        workflow = failure_info.get("workflow", "ci")
        event = self._make_event(
            source="ci",
            title=f"CI failure: {test_name} in {workflow}",
            description=(
                f"Test `{test_name}` failed in workflow `{workflow}`.\n\n"
                f"Error:\n```\n{error[:2000]}\n```"
            ),
            severity="high",
        )
        log.info("SelfHealingAgent: CI failure — %s", event.title)
        await self._dispatch_fix(event)
        return event

    async def on_github_issue(self, issue: dict[str, Any]) -> HealingEvent:
        """Called when a GitHub issue with a bug label is opened."""
        title = issue.get("title", "Unknown issue")
        body = issue.get("body", "")
        labels = [la.get("name", "") for la in issue.get("labels", [])]
        severity = "high" if any(l in labels for l in ("critical", "P0")) else "medium"
        event = self._make_event(
            source="github_issue",
            title=f"Bug: {title}",
            description=f"GitHub issue: {title}\n\n{body[:2000]}",
            severity=severity,
        )
        log.info("SelfHealingAgent: GitHub issue — %s", title)
        if any(l in labels for l in ("bug", "fix")):
            await self._dispatch_fix(event)
        return event

    async def on_manual_report(
        self, title: str, description: str, severity: str = "medium"
    ) -> HealingEvent:
        """Called from the v4 dashboard 'Report Bug' form."""
        event = self._make_event(
            source="manual", title=title, description=description, severity=severity
        )
        log.info("SelfHealingAgent: manual report — %s", title)
        await self._dispatch_fix(event)
        return event

    def get_events(self) -> list[dict[str, Any]]:
        return [e.as_dict() for e in self._events]

    # ── Internal ──────────────────────────────────────────────────────────────

    def _make_event(
        self, *, source: str, title: str, description: str, severity: str
    ) -> HealingEvent:
        event = HealingEvent(
            event_id="he_" + secrets.token_hex(6),
            source=source,
            title=title,
            description=description,
            severity=severity,
            created_at=_now(),
        )
        self._events.append(event)
        return event

    async def _dispatch_fix(self, event: HealingEvent) -> None:
        from agent.improvement_loop import (
            DetectedIssue,
            IssueCategory,
            IssueSeverity,
            get_improvement_loop,
        )

        loop = get_improvement_loop()
        if not loop:
            log.warning("SelfHealingAgent: ImprovementLoop not available — fix not dispatched")
            return

        sev = IssueSeverity.HIGH if event.severity in ("critical", "high") else IssueSeverity.MEDIUM
        cat = IssueCategory.TEST_FAILURE if event.source == "ci" else IssueCategory.TODO_FIXME
        issue = DetectedIssue(
            issue_id=event.event_id,
            category=cat,
            severity=sev,
            title=event.title,
            description=event.description,
        )
        loop._register_issue(issue)
        loop._schedule_fix(issue)
        log.info("SelfHealingAgent: fix dispatched for %s", event.event_id)


# ── Singleton ─────────────────────────────────────────────────────────────────

_healer_instance: SelfHealingAgent | None = None


def set_self_healing_agent(instance: SelfHealingAgent) -> None:
    global _healer_instance
    _healer_instance = instance


def get_self_healing_agent() -> SelfHealingAgent | None:
    return _healer_instance


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

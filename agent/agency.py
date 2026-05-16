"""agent/agency.py — Autonomous Agent Agency

Runs the repo as a self-managing agency where a CEO agent coordinates a
swarm of specialist agents.  Each agent has a defined role and toolset;
the CEO issues directives based on the improvement loop state.

Agency roles:
  CEO        — reads the improvement loop state, decides what needs doing,
                issues directives to the other agents and tracks completion.
  Dev        — implements code fixes (test failures, TODO markers, tech debt).
  Security   — remediates security findings from the scanner.
  Reviewer   — runs council-review skill on recent changes.
  Release    — checks release readiness and updates changelog/version.

The agency runs on a configurable tick interval (default 15 minutes).
Each tick the CEO evaluates the issue backlog and dispatches one task per
available agent role.

Usage (called from proxy.py once at startup)::

    agency = Agency()
    agency.start()

    # Or trigger a single cycle immediately (e.g. from the v4 dashboard):
    result = await agency.run_cycle()
"""
from __future__ import annotations

import asyncio
import logging
import secrets
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

log = logging.getLogger("qwen-proxy")

_REPO_ROOT = Path(__file__).parent.parent

TICK_INTERVAL_MINUTES = int(__import__("os").environ.get("AGENCY_TICK_MINUTES", "15"))


def _now_str() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class AgentRole(str, Enum):
    CEO = "ceo"
    DEV = "dev"
    SECURITY = "security"
    REVIEWER = "reviewer"
    RELEASE = "release"


@dataclass
class AgentDirective:
    directive_id: str
    role: AgentRole
    title: str
    instruction: str
    priority: int = 5          # 1=highest, 10=lowest
    issued_at: str = field(default_factory=_now_str)
    status: str = "pending"   # pending | running | done | failed
    result: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "directive_id": self.directive_id,
            "role": self.role.value,
            "title": self.title,
            "priority": self.priority,
            "issued_at": self.issued_at,
            "status": self.status,
            "result": self.result,
        }


@dataclass
class AgencyCycleResult:
    cycle_id: str
    started_at: str
    directives_issued: int
    directives: list[dict]
    improvement_issues_seen: int
    ceo_assessment: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "started_at": self.started_at,
            "directives_issued": self.directives_issued,
            "directives": self.directives,
            "improvement_issues_seen": self.improvement_issues_seen,
            "ceo_assessment": self.ceo_assessment,
        }


class Agency:
    """Autonomous multi-agent agency for continuous codebase management.

    The CEO role is implemented locally (reads state, issues directives).
    Worker roles (Dev, Security, Reviewer, Release) are dispatched as
    scheduled jobs through AgentScheduler so they run via the existing
    TaskDispatcher → AgentRunner pipeline.

    Usage::

        agency = Agency()
        agency.start()               # background tick every TICK_INTERVAL_MINUTES
        result = await agency.run_cycle()   # immediate cycle
    """

    def __init__(self, tick_minutes: int = TICK_INTERVAL_MINUTES) -> None:
        self._tick = tick_minutes * 60
        self._running = False
        self._thread: threading.Thread | None = None
        self._history: list[AgencyCycleResult] = []
        self._directives: list[AgentDirective] = []
        self._cycle_count = 0

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="agency-tick", daemon=True)
        self._thread.start()
        log.info("Agency started (tick=%dm, roles=%s)", self._tick // 60,
                 [r.value for r in AgentRole])

    def stop(self) -> None:
        self._running = False

    def get_status(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "tick_minutes": self._tick // 60,
            "cycle_count": self._cycle_count,
            "pending_directives": sum(1 for d in self._directives if d.status == "pending"),
            "recent_cycles": [c.as_dict() for c in self._history[-3:]],
            "roles": [r.value for r in AgentRole],
        }

    async def run_cycle(self) -> AgencyCycleResult:
        """Run one full agency cycle (CEO assessment → directives → dispatch)."""
        cycle_id = "cycle_" + secrets.token_hex(4)
        started_at = _now_str()
        self._cycle_count += 1
        log.info("Agency cycle %s starting", cycle_id)

        # 1. CEO: assess the current state
        assessment, directives = self._ceo_assess()

        # 2. Dispatch directives to worker agents via scheduler
        for directive in directives:
            self._directives.append(directive)
            self._dispatch_directive(directive)

        result = AgencyCycleResult(
            cycle_id=cycle_id,
            started_at=started_at,
            directives_issued=len(directives),
            directives=[d.as_dict() for d in directives],
            improvement_issues_seen=self._issue_count(),
            ceo_assessment=assessment,
        )
        self._history.append(result)
        if len(self._history) > 50:
            self._history = self._history[-50:]

        log.info(
            "Agency cycle %s complete — %d directive(s) issued",
            cycle_id, len(directives),
        )
        return result

    # ── CEO Logic ─────────────────────────────────────────────────────────────

    def _ceo_assess(self) -> tuple[str, list[AgentDirective]]:
        """CEO reads the improvement state and issues directives."""
        from agent.improvement_loop import get_improvement_loop
        from agent.log_monitor import get_log_monitor

        loop = get_improvement_loop()
        directives: list[AgentDirective] = []
        summary_parts: list[str] = []

        if not loop:
            return "ImprovementLoop not available — no directives issued.", directives

        state = loop.get_status()
        active_issues = state.get("active_issues", [])
        failing_tests = state.get("failing_tests", [])
        last_test_result = state.get("last_test_result")
        monitor = get_log_monitor()
        monitor_stats = monitor.get_stats() if monitor else {}

        # ── Priority 1: Fix failing tests ────────────────────────────────────
        if failing_tests:
            directives.append(self._make_directive(
                role=AgentRole.DEV,
                title=f"Fix {len(failing_tests)} failing test(s)",
                instruction=(
                    f"The following tests are currently failing:\n"
                    + "\n".join(f"- `{t}`" for t in failing_tests[:10])
                    + "\n\nRun `pytest -x` to see the failures. Fix each one with the minimum "
                    "correct change. Update docs/changelog.md under `### Fixed`. "
                    "Do NOT skip or mock tests to make them pass — fix the actual code."
                ),
                priority=1,
            ))
            summary_parts.append(f"{len(failing_tests)} failing test(s) → Dev agent dispatched")

        # ── Priority 2: Security findings ────────────────────────────────────
        security_issues = [i for i in active_issues if i.get("category") == "security"]
        if security_issues:
            top = security_issues[0]
            directives.append(self._make_directive(
                role=AgentRole.SECURITY,
                title=f"Remediate security finding: {top.get('title', '')[:60]}",
                instruction=top.get("description", "Fix the security finding."),
                priority=2,
            ))
            summary_parts.append(f"{len(security_issues)} security finding(s) → Security agent dispatched")

        # ── Priority 3: Backend error burst ──────────────────────────────────
        tasks_from_logs = monitor_stats.get("tasks_created", 0)
        if tasks_from_logs > 0 and last_test_result != "fail":
            todo_issues = [i for i in active_issues if i.get("category") == "todo_fixme"]
            if todo_issues:
                top_todo = todo_issues[0]
                directives.append(self._make_directive(
                    role=AgentRole.DEV,
                    title=f"Resolve code marker: {top_todo.get('title', '')[:60]}",
                    instruction=top_todo.get("description", "Resolve the code marker."),
                    priority=4,
                ))
                summary_parts.append("Code marker → Dev agent dispatched")

        # ── Priority 4: Periodic review ───────────────────────────────────────
        if self._cycle_count % 4 == 0:
            directives.append(self._make_directive(
                role=AgentRole.REVIEWER,
                title="Council review of recent changes",
                instruction=(
                    "Run the council-review skill on all changes since the last tag:\n"
                    "  `git log $(git describe --tags --abbrev=0)..HEAD --oneline`\n"
                    "Review the diff for correctness, security, and maintainability. "
                    "Open a GitHub issue for each significant finding. "
                    "Update docs/changelog.md if needed."
                ),
                priority=6,
            ))
            summary_parts.append("Periodic review → Reviewer agent dispatched")

        # ── Priority 5: Release readiness (weekly) ────────────────────────────
        if self._cycle_count % 48 == 0:  # ~every 12h at 15m tick
            directives.append(self._make_directive(
                role=AgentRole.RELEASE,
                title="Release readiness check",
                instruction=(
                    "Run the release-readiness skill. If all checks pass:\n"
                    "1. Bump the version in docs/changelog.md (move [Unreleased] to a dated version).\n"
                    "2. Run `pytest` — must be green.\n"
                    "3. Commit with message `release: vX.Y.Z`.\n"
                    "If checks fail, create a GitHub issue listing what needs fixing."
                ),
                priority=8,
            ))
            summary_parts.append("Release readiness check → Release agent dispatched")

        if not summary_parts:
            summary_parts.append("All systems nominal — no critical issues detected")

        return " | ".join(summary_parts), directives

    # ── Dispatch ──────────────────────────────────────────────────────────────

    def _dispatch_directive(self, directive: AgentDirective) -> None:
        """Send a directive to the scheduler as an immediately-firing job."""
        from agent.scheduler import get_scheduler

        try:
            scheduler = get_scheduler()
            job = scheduler.create(
                name=f"agency:{directive.directive_id}",
                cron="* * * * *",  # fires on next minute boundary
                instruction=directive.instruction,
                tags=["agency", directive.role.value, f"priority-{directive.priority}"],
            )
            directive.status = "running"
            log.info(
                "Agency dispatched directive %s to role=%s via job %s",
                directive.directive_id, directive.role.value, job.job_id,
            )
        except Exception as exc:
            directive.status = "failed"
            directive.result = str(exc)
            log.warning("Agency: failed to dispatch directive %s: %s", directive.directive_id, exc)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _make_directive(
        self, *, role: AgentRole, title: str, instruction: str, priority: int
    ) -> AgentDirective:
        return AgentDirective(
            directive_id="dir_" + secrets.token_hex(4),
            role=role,
            title=title,
            instruction=instruction,
            priority=priority,
        )

    def _issue_count(self) -> int:
        from agent.improvement_loop import get_improvement_loop
        loop = get_improvement_loop()
        if not loop:
            return 0
        return len(loop.get_status().get("active_issues", []))

    def _loop(self) -> None:
        while self._running:
            try:
                asyncio.run(self.run_cycle())
            except Exception as exc:
                log.error("Agency tick error: %s", exc)
            time.sleep(self._tick)


# ── Singleton ─────────────────────────────────────────────────────────────────

_agency_instance: Agency | None = None


def set_agency(instance: Agency) -> None:
    global _agency_instance
    _agency_instance = instance


def get_agency() -> Agency | None:
    return _agency_instance

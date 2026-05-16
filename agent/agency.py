"""agent/agency.py — Autonomous Agent Agency (CEO-driven, LLM-powered)

Runs the repo as a self-managing agency where a CEO agent — backed by the
local LLM proxy itself — coordinates a swarm of specialist runtimes.

Agency architecture:
  CEO (LLM-powered) — calls the proxy's /v1/chat/completions with full state
                       context; issues structured directives to worker runtimes.
  Dev        → ClaudeCode / InternalAgent — code fixes, new features, tests
  Security   → ClaudeCode / InternalAgent — CVE remediation, secret cleanup
  Reviewer   → InternalAgent — council-review skill on recent commits
  Release    → InternalAgent — release-readiness, changelog, version bump
  Scout      → InternalAgent — trend evaluation, doc sync, repowise analysis
  Optimizer  → Goose / Aider — performance profiling, refactoring

Runtime routing:
  • ClaudeCode  → complex multi-file coding, security-sensitive, long tasks
  • Hermes      → autonomous long-running research / refactoring loops
  • Goose       → CLI automation, shell-heavy tasks
  • Aider       → focused file-level edits with context
  • OpenCode    → repo-aware editing, git operations
  • InternalAgent → quick analysis, simple fixes, fallback
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import secrets
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import httpx

log = logging.getLogger("qwen-proxy")

_REPO_ROOT = Path(__file__).parent.parent
TICK_INTERVAL_MINUTES = int(os.environ.get("AGENCY_TICK_MINUTES", "15"))
PROXY_BASE_URL = os.environ.get("AGENCY_PROXY_URL", "http://localhost:8000")
CEO_MODEL = os.environ.get("AGENCY_CEO_MODEL", "qwen3-coder:14b")


def _now_str() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ── Role / Runtime mapping ─────────────────────────────────────────────────────

class AgentRole(str, Enum):
    CEO       = "ceo"
    DEV       = "dev"
    SECURITY  = "security"
    REVIEWER  = "reviewer"
    RELEASE   = "release"
    SCOUT     = "scout"
    OPTIMIZER = "optimizer"


# Preferred runtime per role (ordered: first available wins)
_ROLE_RUNTIME_PREFERENCE: dict[AgentRole, list[str]] = {
    AgentRole.DEV:       ["claude_code", "internal_agent"],
    AgentRole.SECURITY:  ["claude_code", "internal_agent"],
    AgentRole.REVIEWER:  ["internal_agent", "claude_code"],
    AgentRole.RELEASE:   ["internal_agent", "claude_code"],
    AgentRole.SCOUT:     ["internal_agent"],
    AgentRole.OPTIMIZER: ["goose", "aider", "internal_agent"],
}


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class AgentDirective:
    directive_id: str
    role: AgentRole
    title: str
    instruction: str
    priority: int = 5
    preferred_runtime: str = "internal_agent"
    issued_at: str = field(default_factory=_now_str)
    status: str = "pending"
    result: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "directive_id": self.directive_id,
            "role": self.role.value,
            "title": self.title,
            "priority": self.priority,
            "preferred_runtime": self.preferred_runtime,
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


# ── Agency ────────────────────────────────────────────────────────────────────

class Agency:
    """CEO-coordinated multi-agent agency for continuous codebase management.

    The CEO calls the local proxy LLM for strategic assessment.
    Worker agents are dispatched via AgentScheduler → runtime routing.
    """

    def __init__(self, tick_minutes: int = TICK_INTERVAL_MINUTES) -> None:
        self._tick = tick_minutes * 60
        self._running = False
        self._thread: threading.Thread | None = None
        self._history: list[AgencyCycleResult] = []
        self._directives: list[AgentDirective] = []
        self._cycle_count = 0

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="agency-tick", daemon=True)
        self._thread.start()
        log.info(
            "Agency started (tick=%dm, CEO model=%s, roles=%s)",
            self._tick // 60, CEO_MODEL, [r.value for r in AgentRole],
        )

    def stop(self) -> None:
        self._running = False

    def get_status(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "tick_minutes": self._tick // 60,
            "cycle_count": self._cycle_count,
            "ceo_model": CEO_MODEL,
            "pending_directives": sum(1 for d in self._directives if d.status == "pending"),
            "recent_cycles": [c.as_dict() for c in self._history[-5:]],
            "roles": [r.value for r in AgentRole],
            "runtime_routing": {k.value: v for k, v in _ROLE_RUNTIME_PREFERENCE.items()},
        }

    # ── Main cycle ────────────────────────────────────────────────────────────

    async def run_cycle(self) -> AgencyCycleResult:
        cycle_id = "cycle_" + secrets.token_hex(4)
        started_at = _now_str()
        self._cycle_count += 1
        log.info("Agency cycle %s starting (count=%d)", cycle_id, self._cycle_count)

        state_context = self._build_state_context()

        # CEO assessment — try LLM first, fall back to rule-based
        assessment, directives = await self._ceo_assess_llm(state_context)

        for directive in directives:
            self._directives.append(directive)
            self._dispatch_directive(directive)

        if len(self._directives) > 200:
            self._directives = self._directives[-200:]

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

        log.info("Agency cycle %s done — %d directive(s)", cycle_id, len(directives))
        return result

    # ── State snapshot ────────────────────────────────────────────────────────

    def _build_state_context(self) -> dict[str, Any]:
        ctx: dict[str, Any] = {
            "cycle_count": self._cycle_count,
            "timestamp": _now_str(),
        }
        try:
            from agent.improvement_loop import get_improvement_loop
            loop = get_improvement_loop()
            if loop:
                status = loop.get_status()
                ctx["improvement_loop"] = {
                    "active_issues": status.get("active_issues", [])[:10],
                    "failing_tests": status.get("failing_tests", [])[:10],
                    "scan_count": status.get("scan_count", 0),
                    "issues_detected": status.get("issues_detected", 0),
                    "issues_resolved": status.get("issues_resolved", 0),
                }
        except Exception:
            pass
        try:
            from agent.log_monitor import get_log_monitor
            monitor = get_log_monitor()
            if monitor:
                ctx["log_monitor"] = monitor.get_stats()
        except Exception:
            pass
        try:
            from agent.trend_watcher import get_trend_watcher
            watcher = get_trend_watcher()
            if watcher:
                ctx["trends"] = watcher.get_stats()
                ctx["top_trends"] = watcher.get_alerts(limit=3)
        except Exception:
            pass
        try:
            from agent.self_healing import get_self_healing_agent
            healer = get_self_healing_agent()
            if healer:
                ctx["self_healing"] = {"recent_events": healer.get_events()[-5:]}
        except Exception:
            pass
        return ctx

    # ── CEO: LLM-powered assessment ───────────────────────────────────────────

    async def _ceo_assess_llm(
        self, state: dict[str, Any]
    ) -> tuple[str, list[AgentDirective]]:
        """Call the local proxy LLM to perform CEO strategic assessment."""
        try:
            prompt = _build_ceo_prompt(state, self._cycle_count)
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{PROXY_BASE_URL}/v1/chat/completions",
                    json={
                        "model": CEO_MODEL,
                        "messages": [
                            {"role": "system", "content": _CEO_SYSTEM_PROMPT},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.3,
                        "max_tokens": 1024,
                    },
                    headers={"Authorization": f"Bearer {_get_api_key()}"},
                )
            if resp.status_code == 200:
                text = resp.json()["choices"][0]["message"]["content"]
                directives = _parse_ceo_directives(text, self._cycle_count)
                return text[:500], directives
        except Exception as exc:
            log.debug("Agency CEO LLM call failed, using rule-based: %s", exc)
        return self._ceo_assess_rules(state)

    # ── CEO: Rule-based fallback ──────────────────────────────────────────────

    def _ceo_assess_rules(
        self, state: dict[str, Any]
    ) -> tuple[str, list[AgentDirective]]:
        directives: list[AgentDirective] = []
        parts: list[str] = []
        loop_state = state.get("improvement_loop", {})
        failing = loop_state.get("failing_tests", [])
        active  = loop_state.get("active_issues", [])

        if failing:
            directives.append(self._make_directive(
                role=AgentRole.DEV, priority=1,
                title=f"Fix {len(failing)} failing test(s)",
                instruction=(
                    f"Tests failing:\n" + "\n".join(f"- `{t}`" for t in failing[:10])
                    + "\n\nRun `pytest -x`, fix each failure with minimum correct change. "
                    "Update docs/changelog.md under `### Fixed`. Never mock to hide failures."
                ),
            ))
            parts.append(f"{len(failing)} failing test(s) → Dev dispatched")

        security_issues = [i for i in active if i.get("category") == "security"]
        if security_issues:
            top = security_issues[0]
            directives.append(self._make_directive(
                role=AgentRole.SECURITY, priority=2,
                title=f"Security: {top.get('title', '')[:60]}",
                instruction=top.get("description", "Remediate the security finding."),
            ))
            parts.append(f"{len(security_issues)} security issue(s) → Security dispatched")

        trend_issues = [i for i in active if "[Trend]" in i.get("title", "")]
        if trend_issues and self._cycle_count % 3 == 0:
            top = trend_issues[0]
            directives.append(self._make_directive(
                role=AgentRole.SCOUT, priority=5,
                title=f"Evaluate trend: {top.get('title', '')[:60]}",
                instruction=(
                    top.get("description", "Evaluate if this AI trend is applicable.") +
                    "\n\nIf actionable (e.g. new Ollama model), update router/registry.py "
                    "and docs/changelog.md. Otherwise create a GitHub issue for tracking."
                ),
            ))
            parts.append("Trend evaluation → Scout dispatched")

        if self._cycle_count % 4 == 0:
            directives.append(self._make_directive(
                role=AgentRole.REVIEWER, priority=6,
                title="Periodic council review",
                instruction=(
                    "Run the council-review skill on changes since the last git tag. "
                    "Flag correctness, security, or maintainability issues. "
                    "Create GitHub issues for significant findings."
                ),
            ))
            parts.append("Council review → Reviewer dispatched")

        if self._cycle_count % 8 == 0:
            directives.append(self._make_directive(
                role=AgentRole.OPTIMIZER, priority=7,
                title="Performance & code quality pass",
                instruction=(
                    "Profile the proxy for hot paths (model routing, chat streaming). "
                    "Identify any O(n²) loops, unnecessary DB queries, or blocking I/O. "
                    "Apply targeted optimizations. Update changelog under `### Changed`."
                ),
            ))
            parts.append("Performance pass → Optimizer dispatched")

        if self._cycle_count % 48 == 0:
            directives.append(self._make_directive(
                role=AgentRole.RELEASE, priority=8,
                title="Release readiness check",
                instruction=(
                    "Run the release-readiness skill. If checks pass: bump version in "
                    "docs/changelog.md (move [Unreleased] to a dated version), run pytest, "
                    "commit `release: vX.Y.Z`. If checks fail, create a GitHub issue."
                ),
            ))
            parts.append("Release check → Release dispatched")

        if not parts:
            parts.append("All systems nominal")

        return " | ".join(parts), directives

    # ── Dispatch ──────────────────────────────────────────────────────────────

    def _dispatch_directive(self, directive: AgentDirective) -> None:
        from agent.scheduler import get_scheduler
        try:
            scheduler = get_scheduler()
            job = scheduler.create(
                name=f"agency:{directive.directive_id}",
                cron="* * * * *",
                instruction=directive.instruction,
                tags=["agency", directive.role.value,
                      f"priority-{directive.priority}",
                      f"runtime-{directive.preferred_runtime}"],
            )
            directive.status = "running"
            log.info(
                "Agency dispatched %s → role=%s runtime=%s job=%s",
                directive.directive_id, directive.role.value,
                directive.preferred_runtime, job.job_id,
            )
        except Exception as exc:
            directive.status = "failed"
            directive.result = str(exc)
            log.warning("Agency: dispatch failed for %s: %s", directive.directive_id, exc)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _make_directive(
        self, *, role: AgentRole, title: str, instruction: str, priority: int,
    ) -> AgentDirective:
        prefs = _ROLE_RUNTIME_PREFERENCE.get(role, ["internal_agent"])
        return AgentDirective(
            directive_id="dir_" + secrets.token_hex(4),
            role=role,
            title=title,
            instruction=instruction,
            priority=priority,
            preferred_runtime=prefs[0],
        )

    def _issue_count(self) -> int:
        try:
            from agent.improvement_loop import get_improvement_loop
            loop = get_improvement_loop()
            return len(loop.get_status().get("active_issues", [])) if loop else 0
        except Exception:
            return 0

    def _loop(self) -> None:
        while self._running:
            try:
                asyncio.run(self.run_cycle())
            except Exception as exc:
                log.error("Agency tick error: %s", exc)
            time.sleep(self._tick)


# ── CEO LLM prompt helpers ─────────────────────────────────────────────────────

_CEO_SYSTEM_PROMPT = """You are the CEO agent of an autonomous AI engineering agency.
Your repo is a self-hosted OpenAI-compatible LLM proxy (local-llm-server).

Your job: review the current system state and issue up to 3 prioritized directives.

Respond ONLY with valid JSON array of directives. Each directive:
{
  "role": "dev|security|reviewer|release|scout|optimizer",
  "priority": 1-10,
  "title": "short title under 60 chars",
  "instruction": "detailed instruction for the agent (multi-line ok)"
}

Priority guide: 1=critical test failures, 2=security CVEs, 3=backend errors,
4=code quality, 5=trend evaluation, 6=review, 7=optimization, 8=release check.

Only issue directives where there is real work to do. If all nominal, return [].
"""


def _build_ceo_prompt(state: dict[str, Any], cycle: int) -> str:
    lines = [f"# Agency state — cycle {cycle} at {_now_str()}\n"]
    loop = state.get("improvement_loop", {})
    if loop.get("failing_tests"):
        lines.append(f"**FAILING TESTS ({len(loop['failing_tests'])}):**")
        for t in loop["failing_tests"][:5]:
            lines.append(f"  - {t}")
    if loop.get("active_issues"):
        lines.append(f"\n**ACTIVE ISSUES ({len(loop['active_issues'])}):**")
        for i in loop["active_issues"][:5]:
            lines.append(f"  [{i.get('category')}] {i.get('title')}")
    monitor = state.get("log_monitor", {})
    if monitor.get("tasks_created", 0) > 0:
        lines.append(f"\n**LOG ERRORS captured:** {monitor['tasks_created']} tasks created")
    trends = state.get("top_trends", [])
    if trends:
        lines.append(f"\n**LATEST TRENDS:**")
        for t in trends:
            lines.append(f"  [{t['source']}] {t['title']} (relevance={t['relevance_score']:.2f})")
    lines.append(f"\nIssue totals — detected: {loop.get('issues_detected',0)}, "
                 f"resolved: {loop.get('issues_resolved',0)}, "
                 f"scans: {loop.get('scan_count',0)}")
    return "\n".join(lines)


def _parse_ceo_directives(
    text: str, cycle: int
) -> list[AgentDirective]:
    directives: list[AgentDirective] = []
    try:
        start = text.find("[")
        end   = text.rfind("]") + 1
        if start < 0 or end <= start:
            return directives
        items = json.loads(text[start:end])
        for item in items[:4]:
            role_str = item.get("role", "dev")
            try:
                role = AgentRole(role_str)
            except ValueError:
                role = AgentRole.DEV
            prefs = _ROLE_RUNTIME_PREFERENCE.get(role, ["internal_agent"])
            directives.append(AgentDirective(
                directive_id="dir_" + secrets.token_hex(4),
                role=role,
                title=str(item.get("title", "CEO directive"))[:80],
                instruction=str(item.get("instruction", "")),
                priority=int(item.get("priority", 5)),
                preferred_runtime=prefs[0],
            ))
    except Exception as exc:
        log.debug("Agency: failed to parse CEO JSON response: %s", exc)
    return directives


def _get_api_key() -> str:
    return (
        os.environ.get("PROXY_API_KEY")
        or os.environ.get("ADMIN_TOKEN")
        or "agency-internal"
    )


# ── Singleton ──────────────────────────────────────────────────────────────────

_agency_instance: Agency | None = None


def set_agency(instance: Agency) -> None:
    global _agency_instance
    _agency_instance = instance


def get_agency() -> Agency | None:
    return _agency_instance

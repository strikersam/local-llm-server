"""agent/improvement_loop.py — Continuous Improvement Engine

Background scanner that detects issues (failing tests, FIXME markers, missing
coverage) and dispatches repair tasks via the AgentScheduler.

Flow:
    ImprovementLoop.start()
      → _scan_cycle() every SCAN_INTERVAL_HOURS
        → scan_for_issues()      — detect problems
        → _register_issue()      — persist to state file
        → _on_task(...)          — create a scheduled fix job
"""
from __future__ import annotations

import json
import logging
import os
import secrets
import subprocess
import threading
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

log = logging.getLogger("qwen-proxy")

_REPO_ROOT = Path(__file__).parent.parent
_STATE_FILE = _REPO_ROOT / ".claude" / "state" / "improvement-state.json"

SCAN_INTERVAL_HOURS = int(os.environ.get("IMPROVEMENT_SCAN_INTERVAL_HOURS", "6"))
_CRITICAL_CRON = "* * * * *"    # fires within 60 s — for test failures
_LOW_CRON = "0 9 * * *"         # daily at 9 am — for low-priority issues


class IssueSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IssueCategory(str, Enum):
    TEST_FAILURE = "test_failure"
    TODO_FIXME = "todo_fixme"
    MISSING_TEST = "missing_test"
    SECURITY = "security"
    PERFORMANCE = "performance"
    DOCUMENTATION = "documentation"


@dataclass
class DetectedIssue:
    issue_id: str
    category: IssueCategory
    severity: IssueSeverity
    title: str
    description: str
    file_path: str | None = None
    line_number: int | None = None
    detected_at: str = field(default_factory=lambda: _now())
    task_id: str | None = None
    resolved: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_instruction(self) -> str:
        parts = [
            f"Fix the following {self.category.value} issue in the local-llm-server codebase.",
            f"\n**Issue:** {self.title}",
            f"**Severity:** {self.severity.value}",
            f"**Description:** {self.description}",
        ]
        if self.file_path:
            parts.append(f"**File:** {self.file_path}")
        if self.line_number:
            parts.append(f"**Line:** {self.line_number}")
        parts += [
            "\nPlease:",
            "1. Investigate the issue thoroughly.",
            "2. Make the minimum necessary code changes to fix it.",
            "3. Add a regression test when applicable.",
            "4. Update docs/changelog.md under [Unreleased].",
        ]
        return "\n".join(parts)


@dataclass
class ImprovementLoopState:
    last_scan: str | None = None
    scan_count: int = 0
    issues_detected: int = 0
    issues_resolved: int = 0
    active_issues: list[dict] = field(default_factory=list)
    resolved_issues: list[dict] = field(default_factory=list)
    last_test_run: str | None = None
    last_test_result: str | None = None  # "pass" | "fail" | "error"
    failing_tests: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class ImprovementLoop:
    """Background scanner and task dispatcher for continuous codebase improvement.

    Usage::

        loop = ImprovementLoop(on_task=scheduler.create)
        loop.start()
        status = loop.get_status()
    """

    def __init__(
        self,
        *,
        repo_root: Path = _REPO_ROOT,
        on_task: Callable[..., Any] | None = None,
        scan_interval_hours: int = SCAN_INTERVAL_HOURS,
    ) -> None:
        self._repo_root = repo_root
        self._on_task = on_task
        self._interval = scan_interval_hours * 3600
        self._state = self._load_state()
        self._lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, name="improvement-loop", daemon=True
        )
        self._thread.start()
        log.info("ImprovementLoop started (interval=%dh)", self._interval // 3600)

    def stop(self) -> None:
        self._running = False
        log.info("ImprovementLoop stopping")

    def trigger_scan(self) -> list[DetectedIssue]:
        """Run a scan immediately (blocking). Returns newly detected issues."""
        return self._scan_cycle()

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            return self._state.as_dict()

    def set_on_task(self, callback: Callable[..., Any] | None) -> None:
        self._on_task = callback

    def mark_resolved(self, issue_id: str) -> bool:
        with self._lock:
            for issue in self._state.active_issues:
                if issue.get("issue_id") == issue_id:
                    issue["resolved"] = True
                    self._state.resolved_issues.append(issue)
                    self._state.active_issues = [
                        i for i in self._state.active_issues
                        if i.get("issue_id") != issue_id
                    ]
                    self._state.issues_resolved += 1
                    self._save_state()
                    return True
        return False

    # ── Internal ──────────────────────────────────────────────────────────────

    def _loop(self) -> None:
        while self._running:
            try:
                self._scan_cycle()
            except Exception as exc:
                log.error("ImprovementLoop scan error: %s", exc)
            time.sleep(self._interval)

    def _scan_cycle(self) -> list[DetectedIssue]:
        log.info("ImprovementLoop: starting scan cycle")
        issues: list[DetectedIssue] = []
        issues.extend(self._scan_test_failures())
        issues.extend(self._scan_todo_fixme())
        issues.extend(self._scan_missing_tests())
        issues.extend(self._scan_security())

        new_issues = self._filter_new_issues(issues)
        for issue in new_issues:
            self._register_issue(issue)
            self._schedule_fix(issue)

        with self._lock:
            self._state.last_scan = _now()
            self._state.scan_count += 1
            self._state.issues_detected += len(new_issues)
            self._save_state()

        log.info("ImprovementLoop: scan complete — %d new issues", len(new_issues))
        return new_issues

    def _scan_test_failures(self) -> list[DetectedIssue]:
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "--tb=no", "-q", "--no-header"],
                capture_output=True,
                text=True,
                cwd=str(self._repo_root),
                timeout=120,
            )
            output = result.stdout + result.stderr
            with self._lock:
                self._state.last_test_run = _now()
                self._state.last_test_result = "pass" if result.returncode == 0 else "fail"

            if result.returncode == 0:
                with self._lock:
                    self._state.failing_tests = []
                return []

            failing = [
                line[7:].split(" - ")[0].strip()
                for line in output.splitlines()
                if line.startswith("FAILED ")
            ]
            with self._lock:
                self._state.failing_tests = failing[:20]

            return [
                DetectedIssue(
                    issue_id="tf_" + secrets.token_hex(4),
                    category=IssueCategory.TEST_FAILURE,
                    severity=IssueSeverity.HIGH,
                    title=f"Failing test: {test}",
                    description=(
                        f"The test `{test}` is currently failing.\n"
                        f"Output:\n```\n{output[:1000]}\n```"
                    ),
                    file_path=test.split("::")[0] if "::" in test else None,
                )
                for test in failing[:5]
            ]
        except subprocess.TimeoutExpired:
            log.warning("ImprovementLoop: pytest timed out")
        except Exception as exc:
            log.warning("ImprovementLoop: test scan error: %s", exc)
        return []

    def _scan_todo_fixme(self) -> list[DetectedIssue]:
        try:
            result = subprocess.run(
                ["grep", "-rn", "--include=*.py", "-E", r"FIXME|TODO.?FIX|HACK.?URGENT", "."],
                capture_output=True,
                text=True,
                cwd=str(self._repo_root),
                timeout=30,
            )
            issues = []
            for line in result.stdout.splitlines()[:10]:
                parts = line.split(":", 2)
                if len(parts) < 3:
                    continue
                file_path, line_num, content = parts[0], parts[1], parts[2].strip()
                issues.append(DetectedIssue(
                    issue_id="td_" + secrets.token_hex(4),
                    category=IssueCategory.TODO_FIXME,
                    severity=IssueSeverity.MEDIUM,
                    title=f"Code marker in {file_path}:{line_num}",
                    description=f"Unresolved marker: `{content[:200]}`",
                    file_path=file_path,
                    line_number=int(line_num) if line_num.isdigit() else None,
                ))
            return issues
        except Exception as exc:
            log.warning("ImprovementLoop: todo scan error: %s", exc)
        return []

    def _scan_missing_tests(self) -> list[DetectedIssue]:
        try:
            test_dir = self._repo_root / "tests"
            existing = {f.stem.replace("test_", "") for f in test_dir.glob("test_*.py")}
            issues = []
            for py_file in self._repo_root.glob("*.py"):
                if py_file.stem.startswith("_") or py_file.stem in ("proxy", "conftest"):
                    continue
                if py_file.stem not in existing:
                    issues.append(DetectedIssue(
                        issue_id="mt_" + secrets.token_hex(4),
                        category=IssueCategory.MISSING_TEST,
                        severity=IssueSeverity.LOW,
                        title=f"No test coverage: {py_file.name}",
                        description=f"`{py_file.name}` has no test file in `tests/`.",
                        file_path=str(py_file.relative_to(self._repo_root)),
                    ))
            return issues[:5]
        except Exception as exc:
            log.warning("ImprovementLoop: missing-test scan error: %s", exc)
        return []

    def _scan_security(self) -> list[DetectedIssue]:
        try:
            from agent.security_scanner import SecurityScanner
            scanner = SecurityScanner(repo_root=self._repo_root)
            findings = scanner.run_all()
            issues = []
            for f in findings:
                sev = IssueSeverity.HIGH if f.severity == "high" else IssueSeverity.MEDIUM
                issues.append(DetectedIssue(
                    issue_id=f.finding_id,
                    category=IssueCategory.SECURITY,
                    severity=sev,
                    title=f.title,
                    description=f.description,
                    file_path=f.file_path,
                    line_number=f.line_number,
                ))
            return issues
        except Exception as exc:
            log.warning("ImprovementLoop: security scan error: %s", exc)
        return []

    def _filter_new_issues(self, issues: list[DetectedIssue]) -> list[DetectedIssue]:
        with self._lock:
            known = {i.get("title") for i in self._state.active_issues}
        return [i for i in issues if i.title not in known]

    def _register_issue(self, issue: DetectedIssue) -> None:
        with self._lock:
            self._state.active_issues.append(issue.as_dict())
            self._save_state()

    def _schedule_fix(self, issue: DetectedIssue) -> None:
        if not self._on_task:
            return
        cron = _CRITICAL_CRON if issue.severity in (IssueSeverity.CRITICAL, IssueSeverity.HIGH) else _LOW_CRON
        try:
            self._on_task(
                name=f"fix:{issue.issue_id}",
                cron=cron,
                instruction=issue.to_instruction(),
                tags=["auto-improvement", issue.category.value],
            )
            log.info("ImprovementLoop: scheduled fix for %s (%s)", issue.issue_id, issue.title)
        except Exception as exc:
            log.warning("ImprovementLoop: could not schedule fix for %s: %s", issue.issue_id, exc)

    def _state_file(self) -> Path:
        return self._repo_root / ".claude" / "state" / "improvement-state.json"

    def _load_state(self) -> ImprovementLoopState:
        try:
            data = json.loads(self._state_file().read_text())
            valid = {k for k in ImprovementLoopState.__dataclass_fields__}
            return ImprovementLoopState(**{k: v for k, v in data.items() if k in valid})
        except Exception:
            return ImprovementLoopState()

    def _save_state(self) -> None:
        sf = self._state_file()
        sf.parent.mkdir(parents=True, exist_ok=True)
        sf.write_text(json.dumps(self._state.as_dict(), indent=2))


# ── Singleton ─────────────────────────────────────────────────────────────────

_loop_instance: ImprovementLoop | None = None


def set_improvement_loop(instance: ImprovementLoop) -> None:
    global _loop_instance
    _loop_instance = instance


def get_improvement_loop() -> ImprovementLoop | None:
    return _loop_instance


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

"""
Claude Code setup auditor.

Inspired by the practice of using Claude Code to self-configure and validate
its own development environment. Checks that key Claude Code integrations are
in place: CLAUDE.md coverage, hooks, skills, and state files.

Usage:
  python scripts/claude_setup_audit.py [--json]

Exit codes:
  0 — all checks pass (score 100 %)
  1 — one or more checks failed
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


@dataclass
class CheckResult:
    name: str
    passed: bool
    message: str
    weight: int = 1


@dataclass
class AuditReport:
    results: list[CheckResult] = field(default_factory=list)

    @property
    def score(self) -> int:
        total = sum(r.weight for r in self.results)
        passed = sum(r.weight for r in self.results if r.passed)
        return int(passed / total * 100) if total else 0

    @property
    def ok(self) -> bool:
        return all(r.passed for r in self.results)


def _check_claude_md_sections(path: Path) -> list[CheckResult]:
    results = []
    required = [
        ("What This Repo Does", "purpose section"),
        ("Codebase Map", "file map"),
        ("Key Commands", "commands cheatsheet"),
        ("Coding Rules", "coding rules"),
        ("Testing Expectations", "test expectations"),
        ("Changelog Rule", "changelog enforcement"),
    ]
    if not path.exists():
        return [CheckResult("CLAUDE.md exists", False, f"{path} not found", weight=5)]

    text = path.read_text()
    results.append(CheckResult("CLAUDE.md exists", True, str(path)))
    for heading, label in required:
        present = heading in text
        results.append(CheckResult(
            f"CLAUDE.md: {label}",
            present,
            f"Section '{heading}' {'found' if present else 'missing'}",
        ))
    return results


def _check_hooks() -> list[CheckResult]:
    hooks_dir = REPO_ROOT / ".claude" / "hooks"
    results = []
    if not hooks_dir.is_dir():
        return [CheckResult("hooks directory", False, f"{hooks_dir} not found")]

    results.append(CheckResult("hooks directory", True, str(hooks_dir)))
    hook_files = list(hooks_dir.glob("*"))
    results.append(CheckResult(
        "hooks populated",
        len(hook_files) > 0,
        f"{len(hook_files)} hook file(s) found",
    ))

    git_config = REPO_ROOT / ".git" / "config"
    hooks_activated = False
    if git_config.exists():
        content = git_config.read_text()
        hooks_activated = ".claude/hooks" in content
    results.append(CheckResult(
        "hooks activated (git config)",
        hooks_activated,
        "hooksPath = .claude/hooks" + ("" if hooks_activated else " — run: git config core.hooksPath .claude/hooks"),
    ))
    return results


def _check_skills() -> list[CheckResult]:
    skills_dir = REPO_ROOT / ".claude" / "skills"
    results = []
    if not skills_dir.is_dir():
        return [CheckResult("skills directory", False, f"{skills_dir} not found")]

    skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir()]
    results.append(CheckResult("skills directory", True, str(skills_dir)))
    results.append(CheckResult(
        "skills populated",
        len(skill_dirs) >= 5,
        f"{len(skill_dirs)} skill(s) installed (recommended ≥ 5)",
    ))

    key_skills = ["council-review", "implementation-planner", "test-first-executor", "changelog-enforcer"]
    for skill in key_skills:
        present = (skills_dir / skill).is_dir()
        results.append(CheckResult(f"skill: {skill}", present, f"{'found' if present else 'missing'}"))
    return results


def _check_state() -> list[CheckResult]:
    state_dir = REPO_ROOT / ".claude" / "state"
    results = []
    if not state_dir.is_dir():
        return [CheckResult("state directory", False, f"{state_dir} not found")]

    results.append(CheckResult("state directory", True, str(state_dir)))
    agent_state = state_dir / "agent-state.json"
    results.append(CheckResult(
        "agent-state.json",
        agent_state.exists(),
        "session state file " + ("found" if agent_state.exists() else "missing — run ai_runner.py start"),
    ))
    return results


def _check_agents_config() -> list[CheckResult]:
    agents_dir = REPO_ROOT / ".claude" / "agents"
    if not agents_dir.is_dir():
        return [CheckResult("agents config", False, f"{agents_dir} not found")]
    agent_files = list(agents_dir.glob("*.md")) + list(agents_dir.glob("*.json"))
    return [
        CheckResult("agents config directory", True, str(agents_dir)),
        CheckResult(
            "agent definitions",
            len(agent_files) > 0,
            f"{len(agent_files)} agent definition(s) found",
        ),
    ]


def run_audit(repo_root: Path = REPO_ROOT) -> AuditReport:
    report = AuditReport()
    report.results += _check_claude_md_sections(repo_root / "CLAUDE.md")
    report.results += _check_hooks()
    report.results += _check_skills()
    report.results += _check_state()
    report.results += _check_agents_config()
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit Claude Code setup completeness")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    report = run_audit()

    if args.json:
        print(json.dumps({
            "score": report.score,
            "ok": report.ok,
            "checks": [
                {"name": r.name, "passed": r.passed, "message": r.message}
                for r in report.results
            ],
        }, indent=2))
    else:
        print(f"\nClaude Code Setup Audit — {REPO_ROOT.name}")
        print("=" * 50)
        for r in report.results:
            icon = "✓" if r.passed else "✗"
            print(f"  {icon} {r.name}: {r.message}")
        print()
        print(f"Score: {report.score}%  {'✓ All checks pass' if report.ok else '✗ Some checks failed'}")

    sys.exit(0 if report.ok else 1)


if __name__ == "__main__":
    main()

"""Tests for scripts/claude_setup_audit.py"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.claude_setup_audit import (
    AuditReport,
    CheckResult,
    run_audit,
    _check_claude_md_sections,
    _check_hooks,
    _check_skills,
    _check_state,
)


def test_run_audit_returns_report():
    report = run_audit(REPO_ROOT)
    assert isinstance(report, AuditReport)
    assert len(report.results) > 0
    assert 0 <= report.score <= 100


def test_check_claude_md_exists():
    results = _check_claude_md_sections(REPO_ROOT / "CLAUDE.md")
    exists_check = next(r for r in results if r.name == "CLAUDE.md exists")
    assert exists_check.passed, "CLAUDE.md must exist at repo root"


def test_check_claude_md_key_sections():
    results = _check_claude_md_sections(REPO_ROOT / "CLAUDE.md")
    section_checks = [r for r in results if "CLAUDE.md:" in r.name]
    assert len(section_checks) >= 5
    failed = [r for r in section_checks if not r.passed]
    assert not failed, f"Missing CLAUDE.md sections: {[r.name for r in failed]}"


def test_check_claude_md_missing_file(tmp_path):
    results = _check_claude_md_sections(tmp_path / "CLAUDE.md")
    assert len(results) == 1
    assert not results[0].passed
    assert "not found" in results[0].message


def test_hooks_directory_exists():
    results = _check_hooks()
    dir_check = next(r for r in results if r.name == "hooks directory")
    assert dir_check.passed, ".claude/hooks directory must exist"


def test_skills_directory_populated():
    results = _check_skills()
    pop_check = next(r for r in results if r.name == "skills populated")
    assert pop_check.passed, "At least 5 skills must be installed"


def test_key_skills_present():
    results = _check_skills()
    for skill in ["council-review", "implementation-planner", "test-first-executor", "changelog-enforcer"]:
        check = next((r for r in results if r.name == f"skill: {skill}"), None)
        assert check is not None
        assert check.passed, f"Key skill '{skill}' must be installed"


def test_state_directory_exists():
    results = _check_state()
    dir_check = next(r for r in results if r.name == "state directory")
    assert dir_check.passed, ".claude/state directory must exist"


def test_audit_report_score():
    report = AuditReport(results=[
        CheckResult("a", True, "ok", weight=2),
        CheckResult("b", False, "fail", weight=2),
    ])
    assert report.score == 50
    assert not report.ok


def test_audit_report_all_pass():
    report = AuditReport(results=[
        CheckResult("a", True, "ok"),
        CheckResult("b", True, "ok"),
    ])
    assert report.score == 100
    assert report.ok


def test_cli_json_output():
    result = subprocess.run(
        [sys.executable, "scripts/claude_setup_audit.py", "--json"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    data = json.loads(result.stdout)
    assert "score" in data
    assert "ok" in data
    assert "checks" in data
    assert isinstance(data["checks"], list)


def test_cli_text_output():
    result = subprocess.run(
        [sys.executable, "scripts/claude_setup_audit.py"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert "Score:" in result.stdout
    assert "Claude Code Setup Audit" in result.stdout

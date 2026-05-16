"""Tests for agent/security_scanner.py"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def setup_database_moks(monkeypatch):  # noqa: PT004
    pass


from agent.security_scanner import SecurityFinding, SecurityScanner, _tool_available


def test_security_finding_as_dict():
    f = SecurityFinding(
        scanner="bandit",
        severity="high",
        title="B106: hardcoded password",
        description="A hardcoded password was found",
        file_path="auth.py",
        line_number=42,
    )
    d = f.as_dict()
    assert d["scanner"] == "bandit"
    assert d["severity"] == "high"
    assert d["file_path"] == "auth.py"
    assert d["line_number"] == 42


def test_security_finding_to_issue_instruction():
    f = SecurityFinding(
        scanner="safety",
        severity="high",
        title="CVE in requests",
        description="SSRF vulnerability",
        cve="CVE-2023-1234",
    )
    inst = f.to_issue_instruction()
    assert "safety" in inst
    assert "CVE-2023-1234" in inst
    assert "docs/changelog.md" in inst
    assert "### Security" in inst


def test_secret_grep_finds_pattern(tmp_path: Path):
    (tmp_path / "config.py").write_text(
        'API_KEY = "sk-abcdefghijklmnopqrstuvwxyz1234"\n'
    )
    scanner = SecurityScanner(repo_root=tmp_path)
    findings = scanner._run_secret_grep()
    assert any("sk-" in f.title or "sk-" in f.description for f in findings)


def test_secret_grep_skips_comments(tmp_path: Path):
    (tmp_path / "config.py").write_text(
        '# API_KEY = "sk-abcdefghijklmnopqrstuvwxyz1234"\n'
    )
    scanner = SecurityScanner(repo_root=tmp_path)
    findings = scanner._run_secret_grep()
    assert findings == []


def test_secret_grep_empty_dir(tmp_path: Path):
    scanner = SecurityScanner(repo_root=tmp_path)
    findings = scanner._run_secret_grep()
    assert findings == []


def test_run_bandit_skipped_when_not_available(tmp_path: Path):
    scanner = SecurityScanner(repo_root=tmp_path)
    with patch("agent.security_scanner._tool_available", return_value=False):
        findings = scanner._run_bandit()
    assert findings == []


def test_run_safety_skipped_when_not_available(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text("requests==2.28.0\n")
    scanner = SecurityScanner(repo_root=tmp_path)
    with patch("agent.security_scanner._tool_available", return_value=False):
        findings = scanner._run_safety()
    assert findings == []


def test_run_safety_skipped_when_no_requirements(tmp_path: Path):
    scanner = SecurityScanner(repo_root=tmp_path)
    with patch("agent.security_scanner._tool_available", return_value=True):
        findings = scanner._run_safety()
    assert findings == []


def test_run_all_aggregates(tmp_path: Path):
    scanner = SecurityScanner(repo_root=tmp_path)
    with patch.object(scanner, "_run_bandit", return_value=[]):

        with patch.object(scanner, "_run_safety", return_value=[]):
            with patch.object(scanner, "_run_secret_grep", return_value=[
                SecurityFinding(scanner="secrets", severity="high",
                                title="Test secret", description="desc")
            ]):
                findings = scanner.run_all()

    assert len(findings) == 1
    assert findings[0].scanner == "secrets"


def test_tool_available_missing():
    assert _tool_available("definitely_not_a_real_tool_xyz") is False

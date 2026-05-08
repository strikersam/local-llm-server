"""Tests for scripts/fabric_cli.py and the fabric-patterns pattern engine."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
PATTERNS_DIR = REPO_ROOT / ".claude" / "skills" / "fabric-patterns" / "patterns"
CLI = [sys.executable, str(REPO_ROOT / "scripts" / "fabric_cli.py")]


def test_list_returns_installed_patterns() -> None:
    result = subprocess.run(CLI + ["list"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "summarize" in result.stdout
    assert "extract_wisdom" in result.stdout


def test_list_includes_new_patterns() -> None:
    result = subprocess.run(CLI + ["list"], capture_output=True, text=True)
    assert "code_review" in result.stdout
    assert "improve_prompt" in result.stdout
    assert "explain_code" in result.stdout


def test_show_returns_pattern_content() -> None:
    result = subprocess.run(CLI + ["show", "summarize"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "summary" in result.stdout.lower()


def test_show_missing_pattern_exits_nonzero() -> None:
    result = subprocess.run(CLI + ["show", "nonexistent_pattern_xyz"], capture_output=True, text=True)
    assert result.returncode != 0


def test_apply_substitutes_content_variable() -> None:
    result = subprocess.run(
        CLI + ["apply", "summarize", "--input", "The quick brown fox jumps."],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "The quick brown fox jumps." in result.stdout


def test_apply_custom_variable() -> None:
    result = subprocess.run(
        CLI + ["apply", "summarize", "--input", "Hello world", "--var", "extra=ignored"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0


def test_apply_missing_pattern_exits_nonzero() -> None:
    result = subprocess.run(
        CLI + ["apply", "no_such_pattern", "--input", "text"],
        capture_output=True, text=True,
    )
    assert result.returncode != 0


def test_stitch_chains_two_patterns() -> None:
    result = subprocess.run(
        CLI + ["stitch", "summarize", "extract_wisdom", "--input", "AI is transforming software development."],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert len(result.stdout.strip()) > 0


def test_stitch_missing_pattern_exits_nonzero() -> None:
    result = subprocess.run(
        CLI + ["stitch", "summarize", "no_such_pattern", "--input", "text"],
        capture_output=True, text=True,
    )
    assert result.returncode != 0


def test_save_and_show_roundtrip(tmp_path: Path) -> None:
    source = tmp_path / "my_pattern.md"
    source.write_text("---\nname: tmp_test\ndescription: temp\nversion: \"1.0.0\"\n---\n{{content}} processed.\n")
    result = subprocess.run(CLI + ["save", "tmp_test_pattern", str(source)], capture_output=True, text=True)
    assert result.returncode == 0

    show = subprocess.run(CLI + ["show", "tmp_test_pattern"], capture_output=True, text=True)
    assert show.returncode == 0
    assert "processed" in show.stdout

    # Cleanup
    (PATTERNS_DIR / "tmp_test_pattern.md").unlink(missing_ok=True)


def test_new_scaffolds_pattern(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    name = "scaffold_test_xyz"
    dest = PATTERNS_DIR / f"{name}.md"
    dest.unlink(missing_ok=True)

    result = subprocess.run(
        CLI + ["new", name, "--description", "Test scaffold"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert dest.exists()
    content = dest.read_text()
    assert "Test scaffold" in content
    assert "{{content}}" in content

    dest.unlink(missing_ok=True)


def test_path_traversal_rejected_in_show() -> None:
    for bad in ["../escape", "../../etc/passwd", "foo/bar", "FOO", ".hidden"]:
        result = subprocess.run(CLI + ["show", bad], capture_output=True, text=True)
        assert result.returncode != 0, f"Expected non-zero for name '{bad}'"


def test_path_traversal_rejected_in_apply() -> None:
    result = subprocess.run(
        CLI + ["apply", "../escape", "--input", "x"],
        capture_output=True, text=True,
    )
    assert result.returncode != 0


def test_path_traversal_rejected_in_stitch() -> None:
    result = subprocess.run(
        CLI + ["stitch", "summarize", "../../hook", "--input", "x"],
        capture_output=True, text=True,
    )
    assert result.returncode != 0


def test_all_bundled_patterns_have_valid_frontmatter() -> None:
    for p in PATTERNS_DIR.glob("*.md"):
        content = p.read_text()
        assert content.startswith("---"), f"{p.name} missing frontmatter"
        parts = content.split("---", 2)
        assert len(parts) >= 3, f"{p.name} has malformed frontmatter"
        assert "name:" in parts[1], f"{p.name} frontmatter missing name field"
        assert "description:" in parts[1], f"{p.name} frontmatter missing description field"

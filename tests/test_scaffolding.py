"""Tests for agent/scaffolding.py — Project Scaffolding."""
from pathlib import Path

import pytest

from agent.scaffolding import ProjectScaffolder


def test_list_builtin_templates():
    s = ProjectScaffolder()
    templates = s.list()
    names = [t.name for t in templates]
    assert "python-library" in names
    assert "fastapi-service" in names
    assert "cli-tool" in names


def test_get_template():
    s = ProjectScaffolder()
    t = s.get("python-library")
    assert t is not None
    assert "src/__init__.py" in t.files


def test_get_nonexistent_returns_none():
    s = ProjectScaffolder()
    assert s.get("no-such-template") is None


def test_apply_python_library(tmp_path: Path):
    s = ProjectScaffolder()
    result = s.apply("python-library", tmp_path / "my-lib")
    assert result.success is True
    assert len(result.files_created) > 0
    assert (tmp_path / "my-lib" / "src" / "__init__.py").exists()


def test_apply_fastapi_service(tmp_path: Path):
    s = ProjectScaffolder()
    result = s.apply("fastapi-service", tmp_path / "my-svc")
    assert result.success is True
    assert (tmp_path / "my-svc" / "main.py").exists()


def test_apply_cli_tool(tmp_path: Path):
    s = ProjectScaffolder()
    result = s.apply("cli-tool", tmp_path / "my-cli")
    assert result.success is True
    assert (tmp_path / "my-cli" / "cli.py").exists()


def test_apply_unknown_template(tmp_path: Path):
    s = ProjectScaffolder()
    result = s.apply("nope", tmp_path / "x")
    assert result.success is False
    assert result.error is not None


def test_apply_skips_existing_without_overwrite(tmp_path: Path):
    s = ProjectScaffolder()
    target = tmp_path / "lib"
    s.apply("python-library", target)
    # Modify a file
    init = target / "src" / "__init__.py"
    init.write_text("MODIFIED", encoding="utf-8")
    # Apply again without overwrite
    s.apply("python-library", target, overwrite=False)
    assert init.read_text(encoding="utf-8") == "MODIFIED"


def test_apply_overwrites_when_flag_set(tmp_path: Path):
    s = ProjectScaffolder()
    target = tmp_path / "lib2"
    s.apply("python-library", target)
    init = target / "src" / "__init__.py"
    init.write_text("MODIFIED", encoding="utf-8")
    s.apply("python-library", target, overwrite=True)
    # Content should be reset to template default
    assert "MODIFIED" not in init.read_text(encoding="utf-8")


def test_as_dict():
    s = ProjectScaffolder()
    d = s.get("cli-tool").as_dict()
    assert "name" in d
    assert "description" in d
    assert "file_count" in d

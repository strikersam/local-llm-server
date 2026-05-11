import pytest
from pathlib import Path
from agent.repowise import RepowiseIntelligence

@pytest.fixture
def repowise(tmp_path):
    # Create a structure with FastAPI-like keywords
    """
    Create a temporary repository structure with example FastAPI and React files and return a RepowiseIntelligence instance pointed at it.

    Parameters:
        tmp_path (pathlib.Path): Temporary directory provided by pytest; used as the root for the generated repository tree. The fixture creates `api/` (server.py, router.py, models.py) and `web/` (App.js, utils.js, hooks.js).

    Returns:
        RepowiseIntelligence: An instance initialized to analyze the generated temporary repository.
    """
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "server.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n@app.get('/')\ndef read_root(): return {'Hello': 'World'}")
    (tmp_path / "api" / "router.py").write_text("def route(): pass")
    (tmp_path / "api" / "models.py").write_text("class User: pass")

    # Create a structure with React-like keywords
    (tmp_path / "web").mkdir()
    (tmp_path / "web" / "App.js").write_text("import React, { useState } from 'react';\nfunction App() { return <div></div>; }")
    (tmp_path / "web" / "utils.js").write_text("def util(): pass")
    (tmp_path / "web" / "hooks.js").write_text("def hook(): pass")

    return RepowiseIntelligence(tmp_path)

@pytest.mark.asyncio
async def test_get_architecture_summary(repowise):
    summary = await repowise.get_architecture_summary()
    assert "key_modules" in summary
    assert "patterns" in summary

    module_names = [m["name"] for m in summary["key_modules"]]
    assert "api" in module_names
    assert "web" in module_names

    assert "FastAPI/REST" in summary["patterns"]
    assert "React/Frontend" in summary["patterns"]

def test_get_context_token_estimation(repowise):
    """
    Verify that get_context returns a context containing a token estimation line for the provided file selector.

    Asserts that calling repowise.get_context(["api/server.py"]) includes the substring "Estimated total tokens:" in the returned context.
    """
    context = repowise.get_context(["api/server.py"])
    assert "Estimated total tokens:" in context

def test_extract_symbol_v2(repowise):
    # Test class extraction
    context = repowise.get_context(["User:api/models.py"])
    assert "class User: pass" in context

    # Test function extraction
    context = repowise.get_context(["read_root:api/server.py"])
    assert "def read_root():" in context


# ---------------------------------------------------------------------------
# Additional tests for new functionality in this PR
# ---------------------------------------------------------------------------

class TestRepowiseInitAcceptsString:
    """__init__ should convert str paths to Path objects."""

    def test_init_with_string_path(self, tmp_path):
        ri = RepowiseIntelligence(str(tmp_path))
        assert ri.root == tmp_path
        assert isinstance(ri.root, Path)

    def test_init_with_path_object(self, tmp_path):
        ri = RepowiseIntelligence(tmp_path)
        assert ri.root == tmp_path
        assert isinstance(ri.root, Path)


class TestGetOverviewIsAsync:
    """get_overview must be awaitable and return all five keys."""

    @pytest.mark.asyncio
    async def test_get_overview_returns_all_keys(self, repowise):
        overview = await repowise.get_overview()
        for key in ("repository_map", "hotspots", "entry_points", "git_health", "architecture"):
            assert key in overview, f"Key {key!r} missing from overview"

    @pytest.mark.asyncio
    async def test_get_overview_architecture_is_dict(self, repowise):
        overview = await repowise.get_overview()
        assert isinstance(overview["architecture"], dict)
        assert "key_modules" in overview["architecture"]
        assert "patterns" in overview["architecture"]


class TestGetArchitectureSummaryEdgeCases:
    """Edge-case behaviour of get_architecture_summary."""

    @pytest.mark.asyncio
    async def test_empty_directory_has_no_key_modules(self, tmp_path):
        ri = RepowiseIntelligence(tmp_path)
        summary = await ri.get_architecture_summary()
        assert summary["key_modules"] == []

    @pytest.mark.asyncio
    async def test_dir_with_two_or_fewer_files_excluded(self, tmp_path):
        # Only 2 Python files — threshold is > 2, so this dir should NOT appear
        (tmp_path / "small").mkdir()
        (tmp_path / "small" / "a.py").write_text("pass")
        (tmp_path / "small" / "b.py").write_text("pass")
        ri = RepowiseIntelligence(tmp_path)
        summary = await ri.get_architecture_summary()
        module_names = [m["name"] for m in summary["key_modules"]]
        assert "small" not in module_names

    @pytest.mark.asyncio
    async def test_dir_with_three_files_included(self, tmp_path):
        (tmp_path / "large").mkdir()
        for name in ("a.py", "b.py", "c.py"):
            (tmp_path / "large" / name).write_text("pass")
        ri = RepowiseIntelligence(tmp_path)
        summary = await ri.get_architecture_summary()
        module_names = [m["name"] for m in summary["key_modules"]]
        assert "large" in module_names

    @pytest.mark.asyncio
    async def test_docker_pattern_detected(self, tmp_path):
        (tmp_path / "Dockerfile").write_text("FROM python:3.11\n")
        ri = RepowiseIntelligence(tmp_path)
        summary = await ri.get_architecture_summary()
        assert "Docker" in summary["patterns"]

    @pytest.mark.asyncio
    async def test_agentic_pattern_detected(self, tmp_path):
        (tmp_path / "main.py").write_text("# agent loop tool prompt\n")
        ri = RepowiseIntelligence(tmp_path)
        summary = await ri.get_architecture_summary()
        assert "Agentic" in summary["patterns"]

    @pytest.mark.asyncio
    async def test_no_patterns_when_no_keywords(self, tmp_path):
        (tmp_path / "hello.py").write_text("print('hello')\n")
        ri = RepowiseIntelligence(tmp_path)
        summary = await ri.get_architecture_summary()
        # No known-pattern keywords present
        for pattern in ("FastAPI/REST", "React/Frontend", "Docker"):
            assert pattern not in summary["patterns"]

    @pytest.mark.asyncio
    async def test_hidden_dirs_excluded_from_key_modules(self, tmp_path):
        # Directories starting with "." should be excluded
        (tmp_path / ".hidden").mkdir()
        for i in range(5):
            (tmp_path / ".hidden" / f"f{i}.py").write_text("pass")
        ri = RepowiseIntelligence(tmp_path)
        summary = await ri.get_architecture_summary()
        module_names = [m["name"] for m in summary["key_modules"]]
        assert ".hidden" not in module_names


class TestGetContextTokenEstimation:
    """Token estimation prefix should be present and reflect content size."""

    def test_token_estimate_is_non_negative_integer(self, repowise):
        context = repowise.get_context(["api/server.py"])
        # Extract the number from the comment
        import re
        match = re.search(r"Estimated total tokens: (\d+)", context)
        assert match, "Token count not found in output"
        assert int(match.group(1)) >= 0

    def test_token_estimate_increases_with_more_files(self, repowise):
        import re
        single = repowise.get_context(["api/server.py"])
        multi = repowise.get_context(["api/server.py", "api/router.py"])
        single_tokens = int(re.search(r"Estimated total tokens: (\d+)", single).group(1))
        multi_tokens = int(re.search(r"Estimated total tokens: (\d+)", multi).group(1))
        assert multi_tokens > single_tokens

    def test_token_prefix_comes_before_file_content(self, repowise):
        context = repowise.get_context(["api/server.py"])
        prefix_idx = context.index("<!-- Estimated total tokens:")
        file_idx = context.index("<file path=")
        assert prefix_idx < file_idx

    def test_empty_targets_returns_only_prefix(self, repowise):
        context = repowise.get_context([])
        assert "<!-- Estimated total tokens: 0 -->" in context


class TestExtractSymbolImprovements:
    """Tests for improved _extract_symbol patterns (anchored + async def)."""

    def test_async_def_symbol_extracted(self, tmp_path):
        src = tmp_path / "async_mod.py"
        src.write_text("async def fetch_data():\n    return []\n")
        ri = RepowiseIntelligence(tmp_path)
        result = ri._extract_symbol(src, "fetch_data", ["source"])
        assert "async def fetch_data():" in result
        assert 'name="fetch_data"' in result

    def test_class_not_confused_with_substring(self, tmp_path):
        # "UserProfile" should NOT be found when looking for "User"
        src = tmp_path / "models.py"
        src.write_text("class UserProfile: pass\n")
        ri = RepowiseIntelligence(tmp_path)
        result = ri._extract_symbol(src, "User", ["source"])
        assert 'status="not_found"' in result

    def test_symbol_not_found_returns_not_found_element(self, tmp_path):
        src = tmp_path / "empty.py"
        src.write_text("x = 1\n")
        ri = RepowiseIntelligence(tmp_path)
        result = ri._extract_symbol(src, "missing_fn", ["source"])
        assert 'status="not_found"' in result

    def test_trailing_blank_lines_trimmed(self, tmp_path):
        src = tmp_path / "functions.py"
        src.write_text(
            "def greet():\n"
            "    return 'hello'\n"
            "\n"
            "\n"
        )
        ri = RepowiseIntelligence(tmp_path)
        result = ri._extract_symbol(src, "greet", ["source"])
        # The closing tag should immediately follow the last non-empty line
        assert result.endswith("</symbol>")
        # No trailing blank lines inside symbol tags
        inner = result.split("<symbol")[1].split(">", 1)[1].rsplit("</symbol>", 1)[0]
        assert not inner.endswith("\n\n")

    def test_blank_lines_inside_function_preserved(self, tmp_path):
        src = tmp_path / "funcs.py"
        src.write_text(
            "def compute():\n"
            "    x = 1\n"
            "\n"
            "    return x\n"
        )
        ri = RepowiseIntelligence(tmp_path)
        result = ri._extract_symbol(src, "compute", ["source"])
        # The blank line in the middle should still be present
        assert "x = 1" in result
        assert "return x" in result

    def test_javascript_function_extracted(self, tmp_path):
        src = tmp_path / "utils.js"
        src.write_text("function add(a, b) {\n  return a + b;\n}\n")
        ri = RepowiseIntelligence(tmp_path)
        result = ri._extract_symbol(src, "add", ["source"])
        assert "function add" in result

    def test_const_arrow_function_extracted(self, tmp_path):
        src = tmp_path / "utils.js"
        src.write_text("const multiply = (a, b) => a * b;\n")
        ri = RepowiseIntelligence(tmp_path)
        result = ri._extract_symbol(src, "multiply", ["source"])
        assert "const multiply" in result

    def test_error_on_unreadable_file(self, tmp_path):
        src = tmp_path / "mod.py"
        src.write_text("def foo(): pass\n")
        ri = RepowiseIntelligence(tmp_path)
        # Simulate read failure
        from unittest.mock import patch
        with patch("pathlib.Path.read_text", side_effect=PermissionError("denied")):
            result = ri._extract_symbol(src, "foo", ["source"])
        assert 'error="' in result

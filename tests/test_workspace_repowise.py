import os
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from agent.tools import WorkspaceTools

@pytest.fixture
def tools(tmp_path):
    """
    Provide a WorkspaceTools instance rooted at a temporary pytest workspace and create a minimal app.py file inside it.

    Creates a file named `app.py` containing `def main(): pass` in the provided `tmp_path` and returns a WorkspaceTools object initialized with that path.

    Returns:
        WorkspaceTools: A WorkspaceTools instance pointing to the temporary workspace containing the created `app.py`.
    """
    (tmp_path / "app.py").write_text("def main(): pass")
    return WorkspaceTools(tmp_path)

@pytest.mark.asyncio
async def test_get_overview_integration(tools):
    overview = await tools.get_overview()
    assert "repository_map" in overview
    assert "hotspots" in overview

def test_get_context_integration(tools):
    context = tools.get_context(["app.py"])
    assert "<file path=\"app.py\">" in context

def test_get_risk_integration(tools):
    risk = tools.get_risk()
    assert "overall_hotspots" in risk

def test_get_why_integration(tools, tmp_path):
    # Just check it returns a string without crashing
    import subprocess
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    why = tools.get_why("app.py")
    assert isinstance(why, str)


# ---------------------------------------------------------------------------
# Additional tests for changes in this PR
# ---------------------------------------------------------------------------

class TestGetOverviewIsAsync:
    """WorkspaceTools.get_overview must be async and delegate to repowise."""

    @pytest.mark.asyncio
    async def test_get_overview_is_awaitable(self, tools):
        import inspect
        assert inspect.iscoroutinefunction(tools.get_overview)

    @pytest.mark.asyncio
    async def test_get_overview_returns_architecture_key(self, tools):
        overview = await tools.get_overview()
        assert "architecture" in overview

    @pytest.mark.asyncio
    async def test_get_overview_delegates_to_repowise(self, tools):
        """get_overview should await repowise.get_overview."""
        expected = {
            "repository_map": "map",
            "hotspots": [],
            "entry_points": [],
            "git_health": {"total_commits": 0, "total_authors": 0},
            "architecture": {"key_modules": [], "patterns": []},
        }
        tools.repowise.get_overview = AsyncMock(return_value=expected)
        result = await tools.get_overview()
        tools.repowise.get_overview.assert_awaited_once()
        assert result == expected

    @pytest.mark.asyncio
    async def test_get_overview_all_keys_present(self, tools):
        overview = await tools.get_overview()
        for key in ("repository_map", "hotspots", "entry_points", "git_health", "architecture"):
            assert key in overview


class TestGetContextDelegates:
    """WorkspaceTools.get_context should delegate faithfully to repowise."""

    def test_get_context_returns_token_estimate(self, tools):
        context = tools.get_context(["app.py"])
        assert "Estimated total tokens:" in context

    def test_get_context_source_include(self, tools):
        context = tools.get_context(["app.py"], include=["source"])
        assert "def main(): pass" in context

    def test_get_context_metrics_include(self, tools):
        context = tools.get_context(["app.py"], include=["metrics"])
        assert "<metrics" in context

    def test_get_context_with_glob(self, tools, tmp_path):
        (tmp_path / "utils.py").write_text("def helper(): return 42\n")
        context = tools.get_context(["*.py"])
        # Both files should appear
        assert "app.py" in context

    def test_get_context_nonexistent_file_graceful(self, tools):
        # No exception; empty content for missing file
        context = tools.get_context(["nonexistent_file_xyz.py"])
        assert isinstance(context, str)

    def test_get_context_symbol_extraction(self, tools, tmp_path):
        (tmp_path / "helpers.py").write_text(
            "def compute(x):\n    return x * 2\n"
        )
        context = tools.get_context(["compute:helpers.py"])
        assert "def compute" in context


class TestGetOverviewMultipleDirectories:
    """Integration test: overview reflects actual directory structure."""

    @pytest.mark.asyncio
    async def test_overview_with_subdir(self, tmp_path):
        (tmp_path / "app.py").write_text("def main(): pass")
        (tmp_path / "lib").mkdir()
        for i in range(4):
            (tmp_path / "lib" / f"mod{i}.py").write_text("pass")
        t = WorkspaceTools(tmp_path)
        overview = await t.get_overview()
        # lib has 4 files (> 2), should appear as a key module
        module_names = [m["name"] for m in overview["architecture"]["key_modules"]]
        assert "lib" in module_names

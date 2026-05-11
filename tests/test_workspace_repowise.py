import os
import pytest
from pathlib import Path
from agent.tools import WorkspaceTools

@pytest.fixture
def tools(tmp_path):
    (tmp_path / "app.py").write_text("def main(): pass")
    return WorkspaceTools(tmp_path)

def test_get_overview_integration(tools):
    overview = tools.get_overview()
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

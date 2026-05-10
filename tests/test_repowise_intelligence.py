import os
import pytest
import subprocess
from pathlib import Path
from agent.repowise import RepowiseIntelligence

@pytest.fixture
def repo_path(tmp_path):
    # Initialize git repo
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "you@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Your Name"], cwd=tmp_path, check=True)

    # app.py (committed)
    f = tmp_path / "app.py"
    f.write_text("import os\ndef main(): pass")
    subprocess.run(["git", "add", "app.py"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit. WHY: Bootstrap the app."], cwd=tmp_path, check=True)

    # utils.py (uncommitted)
    (tmp_path / "utils.py").write_text("def helper(): pass")

    # docs/README.md (uncommitted)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "README.md").write_text("# Docs")

    return tmp_path

@pytest.fixture
def repowise(repo_path):
    return RepowiseIntelligence(repo_path)

def test_get_repository_map(repowise):
    # git ls-files only sees app.py, but fallback/fallback should see others
    repo_map = repowise.get_repository_map()
    assert "- app.py" in repo_map
    # Since it's a git repo but utils.py is untracked, it won't show up in git ls-files
    # But if we were NOT in a git repo, it would.
    # Let's commit everything to be sure.

def test_get_repository_map_all_committed(repo_path):
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", "Add everything"], cwd=repo_path, check=True)
    repowise = RepowiseIntelligence(repo_path)
    repo_map = repowise.get_repository_map()
    assert "- app.py" in repo_map
    assert "- utils.py" in repo_map
    assert "- docs" in repo_map
    assert "  - README.md" in repo_map

def test_find_entry_points(repowise):
    entry_points = repowise.find_entry_points()
    assert "app.py" in entry_points

def test_get_context_file(repowise):
    context = repowise.get_context(["app.py"])
    assert "<file path=\"app.py\">" in context
    assert "import os" in context

def test_get_context_symbol(repowise):
    context = repowise.get_context(["main:app.py"])
    assert "<symbol name=\"main\" path=\"app.py\">" in context
    assert "def main(): pass" in context

def test_get_context_dependencies(repowise):
    context = repowise.get_context(["app.py"], include=["source", "callees"])
    assert "<dependencies>" in context
    assert "- callee: os" in context

def test_get_hotspots(repowise):
    hotspots = repowise.get_hotspots()
    assert len(hotspots) > 0
    assert hotspots[0]["path"] == "app.py"

def test_get_why(repowise):
    why = repowise.get_why("app.py")
    assert "Bootstrap the app" in why

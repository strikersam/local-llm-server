import json
import os
import tempfile
from pathlib import Path
from agent.repowise import RepowiseIntelligence


def test_repowise_intelligence_initialization(tmp_path):
    """Test that the RepowiseIntelligence class initializes correctly."""
    intelligence = RepowiseIntelligence(tmp_path)
    assert intelligence.root == tmp_path
    assert intelligence.intelligence_dir == tmp_path / ".Codex" / "skills" / "repowise-intelligence" / "intelligence"
    assert intelligence.intelligence_dir.exists()


def test_update_intelligence_creates_files(tmp_path):
    """Test that update_intelligence creates the expected intelligence files."""
    intelligence = RepowiseIntelligence(tmp_path)
    # Create a dummy Python file to have something to analyze
    dummy_file = tmp_path / "dummy.py"
    dummy_file.write_text("""
def hello():
    \"\"\"This is a dummy function.\"\"\"
    print("Hello, world!")

class DummyClass:
    pass
""")
    # Run update_intelligence
    intelligence.update_intelligence()
    # Check that the expected files were created
    assert intelligence.dependency_graph_file.exists()
    assert intelligence.symbol_graph_file.exists()
    assert intelligence.git_history_file.exists()
    assert intelligence.decisions_file.exists()
    assert intelligence.documentation_dir.exists()
    # Check that the last commit file was created
    assert intelligence.last_commit_file.exists()


def test_get_overview_returns_dict(tmp_path):
    """Test that get_overview returns a dictionary."""
    intelligence = RepowiseIntelligence(tmp_path)
    # Create a dummy file
    dummy_file = tmp_path / "dummy.py"
    dummy_file.write_text("print('hello')")
    overview = intelligence.get_overview()
    assert isinstance(overview, dict)
    # Check for expected keys
    assert "repository_map" in overview
    assert "hotspots" in overview
    assert "entry_points" in overview
    assert "git_health" in overview


def test_get_context_returns_string(tmp_path):
    """Test that get_context returns a string."""
    intelligence = RepowiseIntelligence(tmp_path)
    # Create a dummy file
    dummy_file = tmp_path / "dummy.py"
    dummy_file.write_text("print('hello')")
    context = intelligence.get_context(["dummy.py"], include=["source"])
    assert isinstance(context, str)
    assert "dummy.py" in context
    assert "print('hello')" in context


def test_get_risk_returns_dict(tmp_path):
    """Test that get_risk returns a dictionary."""
    intelligence = RepowiseIntelligence(tmp_path)
    # Create a dummy file
    dummy_file = tmp_path / "dummy.py"
    dummy_file.write_text("print('hello')")
    risk = intelligence.get_risk(changed_files=["dummy.py"])
    assert isinstance(risk, dict)
    assert "overall_hotspots" in risk
    assert "impact_analysis" in risk


def test_get_why_returns_string(tmp_path):
    """Test that get_why returns a string."""
    intelligence = RepowiseIntelligence(tmp_path)
    # Create a dummy file with a decision comment
    dummy_file = tmp_path / "dummy.py"
    dummy_file.write_text("# WHY: This is a decision\nprint('hello')")
    intelligence.update_intelligence()
    why = intelligence.get_why("dummy.py")
    assert isinstance(why, str)
    # It should find the inline decision
    assert "WHY:" in why or "No documented decisions" in why


def test_get_answer_returns_string(tmp_path):
    """Test that get_answer returns a string."""
    intelligence = RepowiseIntelligence(tmp_path)
    # Create a dummy file with a docstring
    dummy_file = tmp_path / "dummy.py"
    dummy_file.write_text("\"\"\"This is a dummy module.\"\"\"\nprint('hello')")
    intelligence.update_intelligence()
    answer = intelligence.get_answer("dummy module")
    assert isinstance(answer, str)
    # It should find something in the documentation
    assert len(answer) > 0
    assert "Confidence:" in answer


def test_search_codebase_returns_string(tmp_path):
    """Test that search_codebase returns a string."""
    intelligence = RepowiseIntelligence(tmp_path)
    # Create a dummy file
    dummy_file = tmp_path / "dummy.py"
    dummy_file.write_text("print('hello world')")
    intelligence.update_intelligence()
    result = intelligence.search_codebase("hello")
    assert isinstance(result, str)
    # It should find something
    assert len(result) > 0
    assert "dummy.py" in result or "No documentation found" in result


def test_get_decision_flownodes_returns_string(tmp_path):
    """Test that get_decision_flownodes returns a string."""
    intelligence = RepowiseIntelligence(tmp_path)
    # Create a dummy file with a decision comment
    dummy_file = tmp_path / "dummy.py"
    dummy_file.write_text("# WHY: This is a decision\nprint('hello')")
    intelligence.update_intelligence()
    result = intelligence.get_decision_flownodes()
    assert isinstance(result, str)
    # It should find something or return a message saying none found
    assert len(result) > 0
    assert "No decision-linked flow nodes" in result or "File:" in result


if __name__ == "__main__":
    # For manual testing
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
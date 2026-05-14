import os
from pathlib import Path
from agent.tools import WorkspaceTools
from agent.repowise import RepowiseIntelligence


def test_workspace_tools_initialization(tmp_path, monkeypatch):
    """Test that WorkspaceTools initializes correctly."""
    # Set the environment variable for the root
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(tmp_path))
    tools = WorkspaceTools()
    assert tools.root == tmp_path.resolve()
    assert isinstance(tools.repowise, RepowiseIntelligence)


def test_tools_expose_new_methods(tmp_path, monkeypatch):
    """Test that the new tools are exposed and return strings."""
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(tmp_path))
    tools = WorkspaceTools(tmp_path)
    # Create a dummy file to have something to analyze
    dummy_file = tmp_path / "dummy.py"
    dummy_file.write_text("\"\"\"This is a dummy module.\"\"\"\nprint('hello')")
    # We need to update the intelligence first
    tools.repowise.update_intelligence()
    # Test get_answer
    answer = tools.get_answer("dummy module")
    assert isinstance(answer, str)
    assert len(answer) > 0
    # Test search_codebase
    search_result = tools.search_codebase("hello")
    assert isinstance(search_result, str)
    assert len(search_result) > 0
    # Test get_decision_flownodes
    # Add a decision comment to the dummy file
    dummy_file.write_text("# WHY: This is a decision\nprint('hello')")
    tools.repowise.update_intelligence()
    decision_result = tools.get_decision_flownodes()
    assert isinstance(decision_result, str)
    assert len(decision_result) > 0


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
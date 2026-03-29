from pathlib import Path

from agent_tools import WorkspaceTools


def test_workspace_tools_list_read_search_and_apply_diff(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    sample = root / "app.py"
    sample.write_text("print('hello')\n", encoding="utf-8")

    tools = WorkspaceTools(root)

    listed = tools.list_files(limit=10)
    assert "app.py" in listed

    content = tools.read_file("app.py")
    assert "hello" in content

    hits = tools.search_code("hello", limit=5)
    assert hits
    assert hits[0]["path"] == "app.py"

    diff_result = tools.apply_diff("app.py", "print('updated')\n")
    assert "updated" in tools.read_file("app.py")
    assert "app.py" in diff_result["path"]

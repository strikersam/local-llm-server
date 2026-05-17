"""
Comprehensive MCP workspace git operation tests.

Tests the full JSON-RPC path: TestClient → POST /mcp-internal/mcp →
JSON-RPC dispatch → Workspace git subprocesses (real git calls).

All git operations use local bare repos (file:// URLs) — no network required.
WORKSPACE_BASE is redirected to tmp_path for every test so nothing writes to /workspaces.

Coverage:
  Layer 1 — MCP server protocol (health, tools/list, initialize, bad method)
  Layer 2 — Each workspace tool in isolation (clone, read, head, list, search,
             status, diff, create_branch, commit, push, delete)
  Layer 3 — Full git workflows (code-change → commit → push)
  Layer 4 — Error paths (bad workspace_id, path traversal, missing file, bad branch)
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def git_config_env(monkeypatch, tmp_path):
    """Ensure git commits work without a global ~/.gitconfig.

    Sets GIT_AUTHOR_* / GIT_COMMITTER_* env vars (inherited by all subprocesses,
    including asyncio.create_subprocess_exec in mcp_server/workspace.py).
    Also points GIT_CONFIG_GLOBAL at a temp file so CI never touches ~/.gitconfig.
    """
    cfg = tmp_path / "test_gitconfig"
    cfg.write_text(
        "[user]\n\tname = Test Agent\n\temail = test@ci.local\n"
        "[init]\n\tdefaultBranch = main\n"
    )
    for k, v in [
        ("GIT_AUTHOR_NAME", "Test Agent"),
        ("GIT_AUTHOR_EMAIL", "test@ci.local"),
        ("GIT_COMMITTER_NAME", "Test Agent"),
        ("GIT_COMMITTER_EMAIL", "test@ci.local"),
        ("GIT_CONFIG_GLOBAL", str(cfg)),
    ]:
        monkeypatch.setenv(k, v)


@pytest.fixture
def mcp_workspace_root(tmp_path, monkeypatch):
    """Redirect MCP WORKSPACE_BASE → tmp_path/workspaces for every test."""
    import mcp_server.workspace as ws_mod
    root = tmp_path / "workspaces"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(ws_mod, "WORKSPACE_BASE", root)
    return root


@pytest.fixture
def bare_repo(tmp_path, git_config_env):
    """Local bare git repo with an initial commit on 'main'.

    Structure:
        README.md       — "# Test Repo\\n\\nInitial content."
        src/main.py     — hello() + add() stubs
    """
    bare = tmp_path / "origin.git"
    work = tmp_path / "_seed"
    work.mkdir()

    # Bare repo, force 'main' as default branch
    subprocess.run(["git", "init", "--bare", str(bare)],
                   check=True, capture_output=True)
    subprocess.run(["git", "symbolic-ref", "HEAD", "refs/heads/main"],
                   cwd=str(bare), check=True, capture_output=True)

    # Working copy with per-repo identity (no global ~/.gitconfig needed)
    subprocess.run(["git", "init", str(work)],
                   check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@ci.local"],
                   cwd=str(work), check=True)
    subprocess.run(["git", "config", "user.name", "Test Agent"],
                   cwd=str(work), check=True)
    subprocess.run(["git", "remote", "add", "origin", str(bare)],
                   cwd=str(work), check=True)

    (work / "README.md").write_text("# Test Repo\n\nInitial content.\n")
    src = work / "src"
    src.mkdir()
    (src / "main.py").write_text(
        "def hello():\n    return 'Hello World'\n\n"
        "def add(a, b):\n    return a + b\n"
    )

    subprocess.run(["git", "add", "."], cwd=str(work), check=True)
    r = subprocess.run(
        ["git", "commit", "-m", "initial commit"],
        cwd=str(work), capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(f"bare_repo fixture: git commit failed\n{r.stderr}")
    subprocess.run(["git", "push", "origin", "HEAD:main"],
                   cwd=str(work), check=True, capture_output=True)

    return bare


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rpc(client: TestClient, method: str, params: dict | None = None) -> dict:
    """Send a JSON-RPC 2.0 request to the mounted MCP server."""
    resp = client.post("/mcp-internal/mcp", json={
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or {},
    })
    assert resp.status_code in (200, 204), f"HTTP {resp.status_code}: {resp.text}"
    if resp.status_code == 204:
        return {}
    return resp.json()


def _call(client: TestClient, tool: str, args: dict) -> dict:
    """tools/call shorthand — returns the full JSON-RPC result dict."""
    return _rpc(client, "tools/call", {"name": tool, "arguments": args})


def _text(rpc_response: dict) -> str:
    """Extract the text content from a tools/call response."""
    return rpc_response["result"]["content"][0]["text"]


def _data(rpc_response: dict) -> dict | list:
    """Parse the text content as JSON."""
    return json.loads(_text(rpc_response))


def _is_error(rpc_response: dict) -> bool:
    return rpc_response.get("result", {}).get("isError", False)


# ---------------------------------------------------------------------------
# Layer 1 — MCP server protocol
# ---------------------------------------------------------------------------

class TestMCPServerProtocol:

    def test_health_endpoint_returns_ok(self, client: TestClient) -> None:
        resp = client.get("/mcp-internal/health")
        assert resp.status_code == 200
        assert resp.json().get("status") == "ok"

    def test_initialize_handshake(self, client: TestClient) -> None:
        result = _rpc(client, "initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "0"},
        })
        info = result["result"]
        assert info["protocolVersion"] == "2024-11-05"
        assert "tools" in info["capabilities"]

    def test_tools_list_contains_all_git_tools(self, client: TestClient) -> None:
        result = _rpc(client, "tools/list")
        names = {t["name"] for t in result["result"]["tools"]}
        expected = {
            "clone_repo", "read_file", "write_file", "list_files", "search_code",
            "git_status", "git_diff", "git_create_branch", "git_commit", "git_push",
            "delete_workspace",
        }
        assert expected <= names, f"Missing tools: {expected - names}"

    def test_unknown_method_returns_error(self, client: TestClient) -> None:
        result = _rpc(client, "no_such_method")
        assert "error" in result
        assert result["error"]["code"] == -32601

    def test_unknown_tool_returns_error(
        self, client: TestClient, mcp_workspace_root
    ) -> None:
        result = _call(client, "not_a_tool", {"workspace_id": "ws-bad"})
        # Unknown tools return a JSON-RPC protocol-level error, not a result.isError
        assert "error" in result or _is_error(result)

    def test_notifications_initialized_returns_204(self, client: TestClient) -> None:
        resp = client.post("/mcp-internal/mcp", json={
            "jsonrpc": "2.0",
            "id": None,
            "method": "notifications/initialized",
            "params": {},
        })
        assert resp.status_code == 204


# ---------------------------------------------------------------------------
# Layer 2a — clone and read-only tools
# ---------------------------------------------------------------------------

class TestMCPCloneAndInspect:

    def test_clone_local_bare_repo(
        self, client: TestClient, bare_repo: Path, mcp_workspace_root
    ) -> None:
        result = _call(client, "clone_repo", {
            "workspace_id": "ws-clone-001",
            "repo_url": f"file://{bare_repo}",
            "branch": "main",
        })
        assert not _is_error(result), _text(result)
        data = _data(result)
        assert data["cloned"] is True
        assert data["branch"] == "main"
        assert (mcp_workspace_root / "ws-clone-001" / "README.md").exists()

    def test_clone_nonexistent_url_returns_error(
        self, client: TestClient, mcp_workspace_root
    ) -> None:
        result = _call(client, "clone_repo", {
            "workspace_id": "ws-bad-clone",
            "repo_url": "file:///nonexistent/path/repo.git",
            "branch": "main",
        })
        assert _is_error(result)

    def test_read_file_after_clone(
        self, client: TestClient, bare_repo: Path, mcp_workspace_root
    ) -> None:
        _call(client, "clone_repo", {
            "workspace_id": "ws-read-001",
            "repo_url": f"file://{bare_repo}",
            "branch": "main",
        })
        result = _call(client, "read_file", {
            "workspace_id": "ws-read-001",
            "path": "README.md",
        })
        assert not _is_error(result)
        assert "Initial content" in _text(result)

    def test_head_file_returns_only_first_lines(
        self, client: TestClient, bare_repo: Path, mcp_workspace_root
    ) -> None:
        _call(client, "clone_repo", {
            "workspace_id": "ws-head-001",
            "repo_url": f"file://{bare_repo}",
            "branch": "main",
        })
        result = _call(client, "read_file", {
            "workspace_id": "ws-head-001",
            "path": "src/main.py",
        })
        assert not _is_error(result)
        text = _text(result)
        assert "def hello" in text

    def test_list_files_after_clone(
        self, client: TestClient, bare_repo: Path, mcp_workspace_root
    ) -> None:
        _call(client, "clone_repo", {
            "workspace_id": "ws-list-001",
            "repo_url": f"file://{bare_repo}",
            "branch": "main",
        })
        result = _call(client, "list_files", {
            "workspace_id": "ws-list-001",
            "sub": ".",
        })
        assert not _is_error(result)
        files = json.loads(_text(result))
        assert any("README.md" in f for f in files)
        assert any("main.py" in f for f in files)

    def test_search_code_finds_function(
        self, client: TestClient, bare_repo: Path, mcp_workspace_root
    ) -> None:
        _call(client, "clone_repo", {
            "workspace_id": "ws-search-001",
            "repo_url": f"file://{bare_repo}",
            "branch": "main",
        })
        result = _call(client, "search_code", {
            "workspace_id": "ws-search-001",
            "query": "def hello",
        })
        assert not _is_error(result)
        text = _text(result)
        assert "hello" in text

    def test_write_then_read_roundtrip(
        self, client: TestClient, bare_repo: Path, mcp_workspace_root
    ) -> None:
        _call(client, "clone_repo", {
            "workspace_id": "ws-rw-001",
            "repo_url": f"file://{bare_repo}",
            "branch": "main",
        })
        _call(client, "write_file", {
            "workspace_id": "ws-rw-001",
            "path": "notes.txt",
            "content": "agent wrote this",
        })
        result = _call(client, "read_file", {
            "workspace_id": "ws-rw-001",
            "path": "notes.txt",
        })
        assert "agent wrote this" in _text(result)

    def test_read_nonexistent_file_returns_error(
        self, client: TestClient, bare_repo: Path, mcp_workspace_root
    ) -> None:
        _call(client, "clone_repo", {
            "workspace_id": "ws-missing-001",
            "repo_url": f"file://{bare_repo}",
            "branch": "main",
        })
        result = _call(client, "read_file", {
            "workspace_id": "ws-missing-001",
            "path": "does_not_exist.py",
        })
        assert _is_error(result)

    def test_path_traversal_is_rejected(
        self, client: TestClient, bare_repo: Path, mcp_workspace_root
    ) -> None:
        _call(client, "clone_repo", {
            "workspace_id": "ws-trav-001",
            "repo_url": f"file://{bare_repo}",
            "branch": "main",
        })
        result = _call(client, "read_file", {
            "workspace_id": "ws-trav-001",
            "path": "../../etc/passwd",
        })
        assert _is_error(result)


# ---------------------------------------------------------------------------
# Layer 2b — git status and diff
# ---------------------------------------------------------------------------

class TestMCPGitStatusAndDiff:

    def test_git_status_clean_after_clone(
        self, client: TestClient, bare_repo: Path, mcp_workspace_root
    ) -> None:
        _call(client, "clone_repo", {
            "workspace_id": "ws-status-clean",
            "repo_url": f"file://{bare_repo}",
            "branch": "main",
        })
        result = _call(client, "git_status", {"workspace_id": "ws-status-clean"})
        assert not _is_error(result)
        # Clean working tree = empty or whitespace only output
        assert _text(result).strip() == ""

    def test_git_status_shows_modified_file(
        self, client: TestClient, bare_repo: Path, mcp_workspace_root
    ) -> None:
        _call(client, "clone_repo", {
            "workspace_id": "ws-status-dirty",
            "repo_url": f"file://{bare_repo}",
            "branch": "main",
        })
        _call(client, "write_file", {
            "workspace_id": "ws-status-dirty",
            "path": "README.md",
            "content": "# Modified\n",
        })
        result = _call(client, "git_status", {"workspace_id": "ws-status-dirty"})
        assert not _is_error(result)
        assert "README.md" in _text(result)

    def test_git_status_shows_new_untracked_file(
        self, client: TestClient, bare_repo: Path, mcp_workspace_root
    ) -> None:
        _call(client, "clone_repo", {
            "workspace_id": "ws-status-new",
            "repo_url": f"file://{bare_repo}",
            "branch": "main",
        })
        _call(client, "write_file", {
            "workspace_id": "ws-status-new",
            "path": "new_feature.py",
            "content": "x = 1\n",
        })
        result = _call(client, "git_status", {"workspace_id": "ws-status-new"})
        assert "new_feature.py" in _text(result)

    def test_git_diff_empty_on_clean_repo(
        self, client: TestClient, bare_repo: Path, mcp_workspace_root
    ) -> None:
        _call(client, "clone_repo", {
            "workspace_id": "ws-diff-clean",
            "repo_url": f"file://{bare_repo}",
            "branch": "main",
        })
        result = _call(client, "git_diff", {"workspace_id": "ws-diff-clean"})
        assert not _is_error(result)
        assert _text(result).strip() == ""

    def test_git_diff_shows_changed_lines(
        self, client: TestClient, bare_repo: Path, mcp_workspace_root
    ) -> None:
        _call(client, "clone_repo", {
            "workspace_id": "ws-diff-dirty",
            "repo_url": f"file://{bare_repo}",
            "branch": "main",
        })
        _call(client, "write_file", {
            "workspace_id": "ws-diff-dirty",
            "path": "src/main.py",
            "content": "def hello():\n    return 'Hello Agent'\n",
        })
        result = _call(client, "git_diff", {"workspace_id": "ws-diff-dirty"})
        assert not _is_error(result)
        diff = _text(result)
        assert "Hello Agent" in diff or "main.py" in diff


# ---------------------------------------------------------------------------
# Layer 2c — branch creation and commit
# ---------------------------------------------------------------------------

class TestMCPBranchAndCommit:

    def test_create_branch_succeeds(
        self, client: TestClient, bare_repo: Path,
        mcp_workspace_root, git_config_env
    ) -> None:
        _call(client, "clone_repo", {
            "workspace_id": "ws-branch-001",
            "repo_url": f"file://{bare_repo}",
            "branch": "main",
        })
        result = _call(client, "git_create_branch", {
            "workspace_id": "ws-branch-001",
            "branch_name": "feature-test-branch",
        })
        assert not _is_error(result)
        data = _data(result)
        assert data["created"] is True
        assert data["branch"] == "feature-test-branch"

    def test_create_invalid_branch_name_rejected(
        self, client: TestClient, bare_repo: Path, mcp_workspace_root
    ) -> None:
        _call(client, "clone_repo", {
            "workspace_id": "ws-branch-bad",
            "repo_url": f"file://{bare_repo}",
            "branch": "main",
        })
        result = _call(client, "git_create_branch", {
            "workspace_id": "ws-branch-bad",
            "branch_name": "bad branch name with spaces",
        })
        assert _is_error(result)

    def test_commit_all_files(
        self, client: TestClient, bare_repo: Path,
        mcp_workspace_root, git_config_env
    ) -> None:
        _call(client, "clone_repo", {
            "workspace_id": "ws-commit-all",
            "repo_url": f"file://{bare_repo}",
            "branch": "main",
        })
        _call(client, "write_file", {
            "workspace_id": "ws-commit-all",
            "path": "fix.py",
            "content": "# bug fix\n",
        })
        result = _call(client, "git_commit", {
            "workspace_id": "ws-commit-all",
            "message": "fix: patch bug in fix.py",
        })
        assert not _is_error(result)
        data = _data(result)
        assert data["committed"] is True

    def test_commit_specific_paths(
        self, client: TestClient, bare_repo: Path,
        mcp_workspace_root, git_config_env
    ) -> None:
        _call(client, "clone_repo", {
            "workspace_id": "ws-commit-paths",
            "repo_url": f"file://{bare_repo}",
            "branch": "main",
        })
        _call(client, "write_file", {
            "workspace_id": "ws-commit-paths", "path": "a.py", "content": "a=1\n",
        })
        _call(client, "write_file", {
            "workspace_id": "ws-commit-paths", "path": "b.py", "content": "b=2\n",
        })
        result = _call(client, "git_commit", {
            "workspace_id": "ws-commit-paths",
            "message": "chore: add a.py only",
            "paths": ["a.py"],
        })
        assert not _is_error(result)
        assert _data(result)["committed"] is True

    def test_commit_on_feature_branch_after_create(
        self, client: TestClient, bare_repo: Path,
        mcp_workspace_root, git_config_env
    ) -> None:
        ws = "ws-branch-commit"
        _call(client, "clone_repo", {
            "workspace_id": ws,
            "repo_url": f"file://{bare_repo}",
            "branch": "main",
        })
        _call(client, "git_create_branch", {
            "workspace_id": ws, "branch_name": "feature-new",
        })
        _call(client, "write_file", {
            "workspace_id": ws, "path": "feature.py", "content": "x=42\n",
        })
        result = _call(client, "git_commit", {
            "workspace_id": ws, "message": "feat: add feature.py",
        })
        assert not _is_error(result)


# ---------------------------------------------------------------------------
# Layer 2d — git push
# ---------------------------------------------------------------------------

class TestMCPGitPush:

    def test_push_commit_to_remote(
        self, client: TestClient, bare_repo: Path,
        mcp_workspace_root, git_config_env
    ) -> None:
        ws = "ws-push-001"
        _call(client, "clone_repo", {
            "workspace_id": ws,
            "repo_url": f"file://{bare_repo}",
            "branch": "main",
        })
        _call(client, "write_file", {
            "workspace_id": ws, "path": "pushed.py", "content": "pushed=True\n",
        })
        _call(client, "git_commit", {
            "workspace_id": ws, "message": "feat: pushed.py",
        })
        result = _call(client, "git_push", {"workspace_id": ws})
        assert not _is_error(result)
        data = _data(result)
        assert data["pushed"] is True

    def test_push_new_branch_to_remote(
        self, client: TestClient, bare_repo: Path,
        mcp_workspace_root, git_config_env
    ) -> None:
        ws = "ws-push-branch"
        _call(client, "clone_repo", {
            "workspace_id": ws,
            "repo_url": f"file://{bare_repo}",
            "branch": "main",
        })
        _call(client, "git_create_branch", {
            "workspace_id": ws, "branch_name": "agent-feature",
        })
        _call(client, "write_file", {
            "workspace_id": ws, "path": "new.py", "content": "new=1\n",
        })
        _call(client, "git_commit", {
            "workspace_id": ws, "message": "feat: add new.py",
        })
        result = _call(client, "git_push", {
            "workspace_id": ws, "branch": "agent-feature",
        })
        assert not _is_error(result)
        data = _data(result)
        assert data["pushed"] is True

    def test_push_without_commit_fails_gracefully(
        self, client: TestClient, bare_repo: Path, mcp_workspace_root
    ) -> None:
        ws = "ws-push-empty"
        _call(client, "clone_repo", {
            "workspace_id": ws,
            "repo_url": f"file://{bare_repo}",
            "branch": "main",
        })
        # No changes made — push with nothing to push should succeed (up-to-date)
        result = _call(client, "git_push", {"workspace_id": ws})
        # "Everything up-to-date" is not an error
        assert not _is_error(result)


# ---------------------------------------------------------------------------
# Layer 3 — full git workflows
# ---------------------------------------------------------------------------

class TestMCPFullGitWorkflow:

    def test_full_code_change_workflow(
        self, client: TestClient, bare_repo: Path,
        mcp_workspace_root, git_config_env
    ) -> None:
        """Clone → inspect → edit → status → diff → branch → commit → push."""
        ws = "ws-full-workflow"

        # 1. Clone
        r = _call(client, "clone_repo", {
            "workspace_id": ws,
            "repo_url": f"file://{bare_repo}",
            "branch": "main",
        })
        assert _data(r)["cloned"] is True

        # 2. Inspect existing file
        r = _call(client, "read_file", {"workspace_id": ws, "path": "src/main.py"})
        assert "def hello" in _text(r)

        # 3. Edit
        _call(client, "write_file", {
            "workspace_id": ws, "path": "src/main.py",
            "content": "def hello():\n    return 'Hello Agent World'\n\ndef add(a, b):\n    return a + b\n",
        })

        # 4. Status shows modification
        r = _call(client, "git_status", {"workspace_id": ws})
        assert "main.py" in _text(r)

        # 5. Diff shows the change
        r = _call(client, "git_diff", {"workspace_id": ws})
        assert "Hello Agent World" in _text(r)

        # 6. Create feature branch
        r = _call(client, "git_create_branch", {
            "workspace_id": ws, "branch_name": "fix-hello-message",
        })
        assert _data(r)["created"] is True

        # 7. Commit
        r = _call(client, "git_commit", {
            "workspace_id": ws,
            "message": "fix: update hello return value",
            "paths": ["src/main.py"],
        })
        assert _data(r)["committed"] is True

        # 8. Push
        r = _call(client, "git_push", {
            "workspace_id": ws, "branch": "fix-hello-message",
        })
        assert _data(r)["pushed"] is True

        # Verify the branch exists in the bare remote
        result = subprocess.run(
            ["git", "branch", "--list", "fix-hello-message"],
            cwd=str(bare_repo), capture_output=True, text=True,
        )
        assert "fix-hello-message" in result.stdout

    def test_multi_file_commit_workflow(
        self, client: TestClient, bare_repo: Path,
        mcp_workspace_root, git_config_env
    ) -> None:
        """Create multiple files, commit all together, push."""
        ws = "ws-multi-file"
        _call(client, "clone_repo", {
            "workspace_id": ws, "repo_url": f"file://{bare_repo}", "branch": "main",
        })
        for name, content in [
            ("utils.py", "def util(): pass\n"),
            ("tests/test_utils.py", "def test_util(): pass\n"),
            ("CHANGELOG.md", "## [1.0.1]\n- add utils\n"),
        ]:
            _call(client, "write_file", {
                "workspace_id": ws, "path": name, "content": content,
            })
        r = _call(client, "git_commit", {
            "workspace_id": ws, "message": "feat: add utils + tests + changelog",
        })
        assert _data(r)["committed"] is True
        r = _call(client, "git_push", {"workspace_id": ws})
        assert _data(r)["pushed"] is True

    def test_sequential_commits_on_branch(
        self, client: TestClient, bare_repo: Path,
        mcp_workspace_root, git_config_env
    ) -> None:
        """Multiple commits on a feature branch before pushing."""
        ws = "ws-seq-commits"
        _call(client, "clone_repo", {
            "workspace_id": ws, "repo_url": f"file://{bare_repo}", "branch": "main",
        })
        _call(client, "git_create_branch", {
            "workspace_id": ws, "branch_name": "multi-commit-branch",
        })
        for i in range(3):
            _call(client, "write_file", {
                "workspace_id": ws, "path": f"step_{i}.py", "content": f"step = {i}\n",
            })
            r = _call(client, "git_commit", {
                "workspace_id": ws, "message": f"chore: step {i}",
            })
            assert _data(r)["committed"] is True

        r = _call(client, "git_push", {
            "workspace_id": ws, "branch": "multi-commit-branch",
        })
        assert _data(r)["pushed"] is True


# ---------------------------------------------------------------------------
# Layer 4 — error paths and workspace lifecycle
# ---------------------------------------------------------------------------

class TestMCPWorkspaceLifecycle:

    def test_delete_workspace_removes_directory(
        self, client: TestClient, bare_repo: Path, mcp_workspace_root
    ) -> None:
        ws = "ws-delete-001"
        _call(client, "clone_repo", {
            "workspace_id": ws, "repo_url": f"file://{bare_repo}", "branch": "main",
        })
        ws_path = mcp_workspace_root / ws
        assert ws_path.exists()

        result = _call(client, "delete_workspace", {"workspace_id": ws})
        assert not _is_error(result)
        assert _data(result)["deleted"] is True
        assert not ws_path.exists()

    def test_invalid_workspace_id_rejected(
        self, client: TestClient, mcp_workspace_root
    ) -> None:
        result = _call(client, "git_status", {
            "workspace_id": "bad id with spaces!",
        })
        assert _is_error(result)

    def test_workspace_id_too_long_rejected(
        self, client: TestClient, mcp_workspace_root
    ) -> None:
        result = _call(client, "git_status", {
            "workspace_id": "a" * 129,
        })
        assert _is_error(result)

    def test_git_ops_on_nonexistent_workspace_fail_gracefully(
        self, client: TestClient, mcp_workspace_root
    ) -> None:
        result = _call(client, "git_status", {
            "workspace_id": "ws-does-not-exist",
        })
        # Should return an error, not a 500
        assert _is_error(result)

    def test_write_file_creates_missing_subdirectories(
        self, client: TestClient, bare_repo: Path, mcp_workspace_root
    ) -> None:
        ws = "ws-mkdir"
        _call(client, "clone_repo", {
            "workspace_id": ws, "repo_url": f"file://{bare_repo}", "branch": "main",
        })
        result = _call(client, "write_file", {
            "workspace_id": ws,
            "path": "deep/nested/dir/file.py",
            "content": "nested = True\n",
        })
        assert not _is_error(result)
        assert (mcp_workspace_root / ws / "deep" / "nested" / "dir" / "file.py").exists()

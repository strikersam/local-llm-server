"""tests/test_mcp_server.py — Unit tests for the MCP server and client.

Tests:
  - MCP server: initialize, tools/list, tools/call dispatch
  - Workspace: read/write file, list files, search code, path traversal rejection
  - MCP client: circuit breaker, unavailable fallback
  - Agent loop: MCP tools surfaced, local fallback when MCP is None
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Make sure repo root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ── Workspace tests ───────────────────────────────────────────────────────────

class TestWorkspace:
    def setup_method(self):
        self._tmp = tempfile.mkdtemp()
        # Patch workspace base so we don't write to /workspaces
        import mcp_server.workspace as ws_mod
        ws_mod.WORKSPACE_BASE = Path(self._tmp)

    def teardown_method(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _ws(self, ws_id: str = "test-ws"):
        from mcp_server.workspace import Workspace
        return Workspace(ws_id)

    def test_read_write_file(self):
        ws = self._ws()
        ws.ensure()
        ws.write_file("hello.txt", "hello world")
        assert ws.read_file("hello.txt") == "hello world"

    def test_read_missing_file_raises(self):
        ws = self._ws()
        ws.ensure()
        with pytest.raises(FileNotFoundError):
            ws.read_file("nonexistent.txt")

    def test_write_creates_parent_dirs(self):
        ws = self._ws()
        ws.ensure()
        ws.write_file("sub/dir/file.py", "x = 1")
        assert (ws.root / "sub" / "dir" / "file.py").read_text() == "x = 1"

    def test_list_files(self):
        ws = self._ws()
        ws.ensure()
        ws.write_file("a.py", "a")
        ws.write_file("sub/b.py", "b")
        files = ws.list_files()
        assert "a.py" in files
        assert "sub/b.py" in files

    def test_search_code(self):
        ws = self._ws()
        ws.ensure()
        ws.write_file("main.py", "def hello():\n    return 42\n")
        results = ws.search_code("hello")
        assert any(r["file"] == "main.py" for r in results)
        assert any("hello" in r["text"] for r in results)

    def test_search_code_no_results(self):
        ws = self._ws()
        ws.ensure()
        ws.write_file("main.py", "x = 1\n")
        results = ws.search_code("zzznomatch")
        assert results == []

    def test_path_traversal_rejected(self):
        from mcp_server.workspace import Workspace
        ws = Workspace("safe-ws")
        ws.ensure()
        with pytest.raises(ValueError, match="[Pp]ath traversal"):
            ws.read_file("../../etc/passwd")

    def test_path_traversal_symlink_rejected(self):
        ws = self._ws()
        ws.ensure()
        link = ws.root / "evil_link"
        link.symlink_to("/etc")
        with pytest.raises(ValueError, match="[Pp]ath traversal"):
            ws.read_file("evil_link/passwd")

    def test_invalid_workspace_id_rejected(self):
        from mcp_server.workspace import Workspace
        with pytest.raises(ValueError):
            Workspace("../../evil")

    def test_delete(self):
        ws = self._ws()
        ws.ensure()
        ws.write_file("f.txt", "data")
        assert ws.root.exists()
        ws.delete()
        assert not ws.root.exists()

    def test_run_command(self):
        ws = self._ws()
        ws.ensure()
        result = asyncio.run(ws.run_command("echo hello"))
        assert result["exit_code"] == 0
        assert "hello" in result["stdout"]

    def test_run_command_timeout(self):
        ws = self._ws()
        ws.ensure()
        result = asyncio.run(ws.run_command("sleep 10", timeout=1))
        assert result["exit_code"] == -1
        assert "Timed out" in result["stderr"]


# ── MCP server endpoint tests ─────────────────────────────────────────────────

@pytest.fixture()
def mcp_client(tmp_path):
    """TestClient for the MCP FastAPI app with workspace base patched to tmp_path."""
    import mcp_server.workspace as ws_mod
    original = ws_mod.WORKSPACE_BASE
    ws_mod.WORKSPACE_BASE = tmp_path
    from mcp_server.server import app
    with TestClient(app) as client:
        yield client
    ws_mod.WORKSPACE_BASE = original


class TestMCPServer:
    def test_health(self, mcp_client):
        resp = mcp_client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def _rpc(self, client, method: str, params: dict | None = None, req_id: int = 1) -> Any:
        payload = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params or {}}
        resp = client.post("/mcp", json=payload)
        assert resp.status_code == 200
        return resp.json()

    def test_initialize(self, mcp_client):
        resp = self._rpc(mcp_client, "initialize")
        assert "result" in resp
        assert resp["result"]["protocolVersion"] == "2024-11-05"
        assert "tools" in resp["result"]["capabilities"]

    def test_tools_list(self, mcp_client):
        resp = self._rpc(mcp_client, "tools/list")
        tools = resp["result"]["tools"]
        names = {t["name"] for t in tools}
        assert "clone_repo" in names
        assert "read_file" in names
        assert "write_file" in names
        assert "run_command" in names
        assert "git_commit" in names
        assert "git_push" in names
        assert "delete_workspace" in names

    def test_tools_list_all_have_input_schema(self, mcp_client):
        resp = self._rpc(mcp_client, "tools/list")
        for tool in resp["result"]["tools"]:
            assert "inputSchema" in tool, f"Tool {tool['name']} missing inputSchema"

    def test_write_then_read_file(self, mcp_client):
        ws_id = "srv-test-write"
        # write
        resp = self._rpc(mcp_client, "tools/call", {
            "name": "write_file",
            "arguments": {"workspace_id": ws_id, "path": "hello.txt", "content": "world"},
        })
        assert resp["result"]["isError"] is False
        # read
        resp = self._rpc(mcp_client, "tools/call", {
            "name": "read_file",
            "arguments": {"workspace_id": ws_id, "path": "hello.txt"},
        })
        assert resp["result"]["isError"] is False
        assert "world" in resp["result"]["content"][0]["text"]

    def test_list_files(self, mcp_client):
        ws_id = "srv-test-list"
        self._rpc(mcp_client, "tools/call", {
            "name": "write_file",
            "arguments": {"workspace_id": ws_id, "path": "a.py", "content": "x"},
        })
        resp = self._rpc(mcp_client, "tools/call", {
            "name": "list_files",
            "arguments": {"workspace_id": ws_id},
        })
        assert resp["result"]["isError"] is False
        assert "a.py" in resp["result"]["content"][0]["text"]

    def test_search_code(self, mcp_client):
        ws_id = "srv-test-search"
        self._rpc(mcp_client, "tools/call", {
            "name": "write_file",
            "arguments": {"workspace_id": ws_id, "path": "f.py", "content": "def magic(): pass"},
        })
        resp = self._rpc(mcp_client, "tools/call", {
            "name": "search_code",
            "arguments": {"workspace_id": ws_id, "query": "magic"},
        })
        assert resp["result"]["isError"] is False
        assert "magic" in resp["result"]["content"][0]["text"]

    def test_run_command(self, mcp_client):
        ws_id = "srv-test-cmd"
        self._rpc(mcp_client, "tools/call", {
            "name": "write_file",
            "arguments": {"workspace_id": ws_id, "path": "f.txt", "content": "x"},
        })
        resp = self._rpc(mcp_client, "tools/call", {
            "name": "run_command",
            "arguments": {"workspace_id": ws_id, "cmd": "echo hi"},
        })
        assert resp["result"]["isError"] is False
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content["exit_code"] == 0
        assert "hi" in content["stdout"]

    def test_delete_workspace(self, mcp_client, tmp_path):
        ws_id = "srv-test-del"
        self._rpc(mcp_client, "tools/call", {
            "name": "write_file",
            "arguments": {"workspace_id": ws_id, "path": "x.txt", "content": "x"},
        })
        resp = self._rpc(mcp_client, "tools/call", {
            "name": "delete_workspace",
            "arguments": {"workspace_id": ws_id},
        })
        assert resp["result"]["isError"] is False
        assert not (tmp_path / ws_id).exists()

    def test_unknown_tool_returns_error(self, mcp_client):
        resp = self._rpc(mcp_client, "tools/call", {
            "name": "no_such_tool",
            "arguments": {},
        })
        assert "error" in resp

    def test_unknown_method_returns_error(self, mcp_client):
        resp = self._rpc(mcp_client, "no/such/method")
        assert "error" in resp

    def test_read_missing_file_is_tool_error(self, mcp_client):
        resp = self._rpc(mcp_client, "tools/call", {
            "name": "read_file",
            "arguments": {"workspace_id": "noexist", "path": "ghost.txt"},
        })
        assert resp["result"]["isError"] is True
        assert "[tool error:" in resp["result"]["content"][0]["text"]

    def test_path_traversal_is_tool_error(self, mcp_client):
        resp = self._rpc(mcp_client, "tools/call", {
            "name": "read_file",
            "arguments": {"workspace_id": "safe-ws", "path": "../../etc/passwd"},
        })
        assert resp["result"]["isError"] is True


# ── MCPClient tests ───────────────────────────────────────────────────────────

class TestMCPClient:
    def test_returns_none_when_no_url(self):
        from agent.mcp_client import get_mcp_client
        client = get_mcp_client("")
        assert client is None

    def test_circuit_breaker_opens_after_failures(self):
        from agent.mcp_client import MCPClient, _CB_FAILURE_THRESHOLD
        client = MCPClient("http://localhost:19999")
        for _ in range(_CB_FAILURE_THRESHOLD):
            client._on_failure()
        assert client._is_open()

    def test_circuit_breaker_closed_initially(self):
        from agent.mcp_client import MCPClient
        client = MCPClient("http://localhost:19999")
        assert not client._is_open()

    def test_circuit_breaker_resets_on_success(self):
        from agent.mcp_client import MCPClient, _CB_FAILURE_THRESHOLD
        client = MCPClient("http://localhost:19999")
        for _ in range(_CB_FAILURE_THRESHOLD):
            client._on_failure()
        assert client._is_open()
        client._on_success()
        assert not client._is_open()
        assert client._failures == 0

    def test_rpc_raises_unavailable_when_circuit_open(self):
        from agent.mcp_client import MCPClient, MCPUnavailableError, _CB_FAILURE_THRESHOLD
        client = MCPClient("http://localhost:19999")
        for _ in range(_CB_FAILURE_THRESHOLD):
            client._on_failure()
        with pytest.raises(MCPUnavailableError, match="circuit breaker"):
            asyncio.run(client._rpc("tools/list"))

    def test_rpc_raises_unavailable_when_server_down(self):
        from agent.mcp_client import MCPClient, MCPUnavailableError
        client = MCPClient("http://localhost:19999")
        with pytest.raises(MCPUnavailableError):
            asyncio.run(client._rpc("tools/list"))

    def test_call_tool_parses_text_content(self):
        from agent.mcp_client import MCPClient
        client = MCPClient("http://localhost:19999")
        mock_result = {
            "content": [{"type": "text", "text": '{"done": true}'}],
            "isError": False,
        }
        with patch.object(client, "_rpc", AsyncMock(return_value=mock_result)):
            result = asyncio.run(client.call_tool("write_file", {}))
        assert '{"done": true}' == result

    def test_call_tool_raises_on_is_error(self):
        from agent.mcp_client import MCPClient
        client = MCPClient("http://localhost:19999")
        mock_result = {
            "content": [{"type": "text", "text": "[tool error: file not found]"}],
            "isError": True,
        }
        with patch.object(client, "_rpc", AsyncMock(return_value=mock_result)):
            with pytest.raises(RuntimeError, match="tool error"):
                asyncio.run(client.call_tool("read_file", {}))

    def test_health_returns_false_when_down(self):
        from agent.mcp_client import MCPClient
        client = MCPClient("http://localhost:19999")
        result = asyncio.run(client.health())
        assert result is False


# ── Agent loop MCP integration ────────────────────────────────────────────────

class TestAgentLoopMCPIntegration:
    """Ensure _dispatch_tool routes MCP-only tools correctly."""

    def _make_runner(self, mcp_client=None):
        from agent.loop import AgentRunner
        runner = AgentRunner.__new__(AgentRunner)
        runner._mcp = mcp_client
        from agent.tools import WorkspaceTools
        runner.tools = MagicMock(spec=WorkspaceTools)
        runner.tools.root = Path("fake-workspace")
        return runner

    def test_mcp_only_tool_returns_unavailable_when_no_client(self):
        runner = self._make_runner(mcp_client=None)
        result = asyncio.run(
            runner._dispatch_tool("clone_repo", {"workspace_id": "x", "repo_url": "https://github.com/a/b"})
        )
        assert result.startswith("[tool error:") and "not set" in result

    def test_mcp_only_tool_delegates_when_client_present(self):
        from agent.mcp_client import MCPClient
        mock_mcp = MagicMock(spec=MCPClient)
        mock_mcp.call_tool = AsyncMock(return_value='{"cloned": true}')
        runner = self._make_runner(mcp_client=mock_mcp)
        result = asyncio.run(
            runner._dispatch_tool("clone_repo", {
                "workspace_id": "x",
                "repo_url": "https://github.com/a/b",
                "branch": "main",
            })
        )
        mock_mcp.call_tool.assert_called_once_with("clone_repo", {
            "workspace_id": "x",
            "repo_url": "https://github.com/a/b",
            "branch": "main",
        })
        assert result == '{"cloned": true}'

    def test_run_command_falls_back_to_local_when_mcp_unavailable(self):
        from agent.mcp_client import MCPClient, MCPUnavailableError
        mock_mcp = MagicMock(spec=MCPClient)
        mock_mcp.call_tool = AsyncMock(side_effect=MCPUnavailableError("down"))
        runner = self._make_runner(mcp_client=mock_mcp)

        async def fake_run_command(cmd, timeout=120):
            return f"ran: {cmd}"

        runner._run_command = fake_run_command
        result = asyncio.run(
            runner._dispatch_tool("run_command", {"cmd": "echo hi"})
        )
        assert "ran: echo hi" in result

    def test_write_file_falls_back_to_local_when_mcp_unavailable(self):
        from agent.mcp_client import MCPClient, MCPUnavailableError
        mock_mcp = MagicMock(spec=MCPClient)
        mock_mcp.call_tool = AsyncMock(side_effect=MCPUnavailableError("down"))
        runner = self._make_runner(mcp_client=mock_mcp)
        runner.tools.write_file = MagicMock(return_value={"written": True})
        asyncio.run(
            runner._dispatch_tool("write_file", {"path": "f.py", "content": "x"})
        )
        runner.tools.write_file.assert_called_once_with("f.py", "x")

    def test_git_commit_delegates_to_mcp(self):
        from agent.mcp_client import MCPClient
        mock_mcp = MagicMock(spec=MCPClient)
        mock_mcp.call_tool = AsyncMock(return_value='{"committed": true}')
        runner = self._make_runner(mcp_client=mock_mcp)
        result = asyncio.run(
            runner._dispatch_tool("git_commit", {"workspace_id": "x", "message": "test"})
        )
        mock_mcp.call_tool.assert_called_once_with("git_commit", {
            "workspace_id": "x", "message": "test"
        })
        assert '{"committed": true}' == result

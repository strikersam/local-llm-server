"""agent/mcp_client.py — Async MCP client for the mcp-server Docker container.

Talks to the MCP server at MCP_SERVER_BASE_URL via JSON-RPC 2.0 over HTTP.
Implements a simple open/close circuit breaker so a crashed or missing
MCP server never stalls the agent loop — callers get a clear "unavailable"
error and can fall back to local tools.

Usage::

    client = MCPClient("http://mcp-server:8008")
    await client.initialize()          # optional warm-up / handshake
    tools = await client.list_tools()
    result = await client.call_tool("clone_repo", {
        "workspace_id": "sess-abc123",
        "repo_url": "https://github.com/owner/repo",
        "branch": "main",
    })
"""
from __future__ import annotations

import itertools
import json
import logging
import os
import time
from typing import Any

import httpx

log = logging.getLogger("qwen-proxy")

_DEFAULT_BASE_URL = os.environ.get("MCP_SERVER_BASE_URL", "")

# Circuit breaker constants
_CB_FAILURE_THRESHOLD = 3    # consecutive failures before opening
_CB_RECOVERY_TIMEOUT = 30.0  # seconds before trying again (half-open)


class MCPUnavailableError(RuntimeError):
    """Raised when the MCP server is unreachable or the circuit is open."""


class MCPClient:
    """Thin async MCP client with open/close circuit breaker.

    Thread-safe only within a single asyncio event loop (no cross-loop sharing).
    """

    def __init__(self, base_url: str | None = None, timeout: float = 30.0) -> None:
        self.base_url = (base_url or _DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self._id_counter = itertools.count(1)
        # Circuit breaker state
        self._failures = 0
        self._opened_at: float | None = None

    # ── circuit breaker ──────────────────────────────────────────────────────

    def _is_open(self) -> bool:
        if self._opened_at is None:
            return False
        if time.monotonic() - self._opened_at >= _CB_RECOVERY_TIMEOUT:
            # Half-open: let one request through
            self._opened_at = None
            return False
        return True

    def _on_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def _on_failure(self) -> None:
        self._failures += 1
        if self._failures >= _CB_FAILURE_THRESHOLD:
            self._opened_at = time.monotonic()
            log.warning(
                "MCP circuit breaker OPEN after %d failures (recovery in %ds)",
                self._failures, int(_CB_RECOVERY_TIMEOUT),
            )

    # ── low-level RPC ────────────────────────────────────────────────────────

    async def _rpc(self, method: str, params: dict[str, Any] | None = None) -> Any:
        if not self.base_url:
            raise MCPUnavailableError("MCP_SERVER_BASE_URL not configured")
        if self._is_open():
            raise MCPUnavailableError("MCP server circuit breaker is open; using local tools")

        req_id = next(self._id_counter)
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {},
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.base_url}/mcp", json=payload)
                resp.raise_for_status()
            body = resp.json()
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as exc:
            self._on_failure()
            raise MCPUnavailableError(f"MCP server unreachable: {exc}") from exc
        except (ValueError, Exception) as exc:
            self._on_failure()
            raise MCPUnavailableError(f"MCP server returned invalid JSON: {exc}") from exc

        self._on_success()
        if "error" in body:
            err = body["error"]
            raise RuntimeError(f"MCP error {err.get('code')}: {err.get('message')}")
        return body.get("result")

    # ── public API ───────────────────────────────────────────────────────────

    async def initialize(self) -> dict[str, Any]:
        """Perform MCP handshake. Optional — tools/call works without it."""
        return await self._rpc("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "local-llm-server", "version": "1.0.0"},
        })

    async def list_tools(self) -> list[dict[str, Any]]:
        result = await self._rpc("tools/list")
        return result.get("tools", [])

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Call a tool and return the text content of the first content item."""
        result = await self._rpc("tools/call", {"name": name, "arguments": arguments})
        content = result.get("content", [])
        if content:
            text = content[0].get("text", "")
            is_error = result.get("isError", False)
            if is_error:
                raise RuntimeError(text)
            return text
        return json.dumps(result, default=str)

    async def health(self) -> bool:
        """Return True if the MCP server is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/health")
                return resp.status_code == 200
        except Exception:
            return False


# Module-level singleton — created lazily when MCP_SERVER_BASE_URL is set.
_client: MCPClient | None = None


def get_mcp_client(base_url: str | None = None) -> MCPClient | None:
    """Return the module-level MCPClient, or None if not configured."""
    global _client
    url = base_url or _DEFAULT_BASE_URL
    if not url:
        return None
    if _client is None or (base_url and _client.base_url != base_url.rstrip("/")):
        _client = MCPClient(url)
    return _client

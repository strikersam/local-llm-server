"""mcp_server/workspace.py — Isolated workspace manager for the MCP server.

Each workspace is a directory under WORKSPACE_BASE keyed by workspace_id.
Git operations, file reads/writes, and command execution are scoped to the workspace.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

log = logging.getLogger("mcp-server")

WORKSPACE_BASE = Path(os.environ.get("MCP_WORKSPACE_BASE", "/workspaces"))
_SAFE_ID = re.compile(r"^[a-zA-Z0-9_\-]{1,128}$")


def _validate_workspace_id(ws_id: str) -> None:
    if not _SAFE_ID.match(ws_id):
        raise ValueError(f"Invalid workspace_id: {ws_id!r}")


def workspace_path(ws_id: str) -> Path:
    _validate_workspace_id(ws_id)
    return WORKSPACE_BASE / ws_id


def _safe_path(root: Path, rel: str) -> Path:
    """Resolve rel against root, reject path traversal."""
    target = (root / rel).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError:
        raise ValueError(f"Path traversal rejected: {rel!r}")
    return target


async def _run(
    *args: str,
    cwd: Path,
    timeout: int = 120,
    env: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    """Run a subprocess. Never uses shell=True."""
    merged_env = {**os.environ, **(env or {})}
    proc = await asyncio.create_subprocess_exec(
        *args,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=merged_env,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        raise RuntimeError(f"Command timed out after {timeout}s: {args[0]}")
    return proc.returncode, stdout.decode(errors="replace"), stderr.decode(errors="replace")


class Workspace:
    """Manages a single isolated workspace directory."""

    def __init__(self, ws_id: str) -> None:
        _validate_workspace_id(ws_id)
        self.ws_id = ws_id
        self.root = workspace_path(ws_id)

    def exists(self) -> bool:
        return self.root.is_dir()

    def ensure(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    # ── git operations ──────────────────────────────────────────────────

    async def clone(self, repo_url: str, branch: str = "main") -> dict[str, Any]:
        """Clone repo_url into this workspace. Injects token from env if available."""
        self.ensure()
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        authed_url = repo_url
        if token and repo_url.startswith("https://github.com/"):
            authed_url = repo_url.replace(
                "https://github.com/", f"https://{token}@github.com/"
            )
        rc, out, err = await _run(
            "git", "clone", "--depth=20", "--branch", branch, authed_url, ".",
            cwd=self.root,
        )
        # Scrub token from any error messages before logging/returning
        err = err.replace(token or "", "***") if token else err
        if rc != 0:
            raise RuntimeError(f"git clone failed: {err.strip()}")
        return {"cloned": True, "branch": branch, "workspace_id": self.ws_id}

    async def status(self) -> str:
        rc, out, err = await _run("git", "status", "--short", cwd=self.root)
        if rc != 0:
            raise RuntimeError(f"git status failed: {err.strip()}")
        return out

    async def diff(self) -> str:
        rc, out, err = await _run("git", "diff", "HEAD", cwd=self.root)
        return out

    async def create_branch(self, branch_name: str) -> dict[str, Any]:
        if not re.match(r"^[a-zA-Z0-9/_\-\.]{1,100}$", branch_name):
            raise ValueError(f"Invalid branch name: {branch_name!r}")
        rc, out, err = await _run("git", "checkout", "-b", branch_name, cwd=self.root)
        if rc != 0:
            raise RuntimeError(f"git checkout -b failed: {err.strip()}")
        return {"branch": branch_name, "created": True}

    async def commit(self, message: str, paths: list[str] | None = None) -> dict[str, Any]:
        if paths:
            for p in paths:
                safe = _safe_path(self.root, p)
                await _run("git", "add", str(safe.relative_to(self.root)), cwd=self.root)
        else:
            await _run("git", "add", "-A", cwd=self.root)
        rc, out, err = await _run("git", "commit", "-m", message, cwd=self.root)
        if rc != 0:
            raise RuntimeError(f"git commit failed: {err.strip()}")
        return {"committed": True, "message": message}

    async def push(self, branch: str | None = None) -> dict[str, Any]:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        env: dict[str, str] = {}
        if token:
            # Pass token via GIT_ASKPASS so it never appears in process args
            env["GIT_ASKPASS"] = "echo"
            env["GIT_USERNAME"] = "x-token"
            env["GIT_PASSWORD"] = token
        if branch:
            rc, out, err = await _run(
                "git", "push", "--set-upstream", "origin", branch,
                cwd=self.root, env=env,
            )
        else:
            rc, out, err = await _run("git", "push", cwd=self.root, env=env)
        err_clean = err.replace(token or "", "***") if token else err
        if rc != 0:
            raise RuntimeError(f"git push failed: {err_clean.strip()}")
        return {"pushed": True}

    # ── file operations ─────────────────────────────────────────────────

    def read_file(self, path: str) -> str:
        if not path or not isinstance(path, str):
            raise ValueError("path must be a non-empty string")
        target = _safe_path(self.root, path)
        if not target.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return target.read_text(encoding="utf-8", errors="replace")

    def write_file(self, path: str, content: str) -> dict[str, Any]:
        if not path or not isinstance(path, str):
            raise ValueError("path must be a non-empty string")
        target = _safe_path(self.root, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {"written": True, "path": path}

    def list_files(self, sub: str = ".", limit: int = 200) -> list[str]:
        if not isinstance(sub, str):
            sub = "."
        base = _safe_path(self.root, sub)
        results = []
        for p in base.rglob("*"):
            if p.is_file() and ".git" not in p.parts:
                results.append(str(p.relative_to(self.root)))
            if len(results) >= limit:
                break
        return sorted(results)

    def search_code(self, query: str, limit: int = 30) -> list[dict[str, Any]]:
        results = []
        for path in self.root.rglob("*"):
            if not path.is_file() or ".git" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if query.lower() in line.lower():
                    results.append({
                        "file": str(path.relative_to(self.root)),
                        "line": i,
                        "text": line.rstrip(),
                    })
                    if len(results) >= limit:
                        return results
        return results

    # ── command execution ───────────────────────────────────────────────

    async def run_command(self, cmd: str, timeout: int = 60) -> dict[str, Any]:
        """Run a shell command inside the workspace via an explicit shell binary."""
        if not cmd or not isinstance(cmd, str):
            raise ValueError("cmd must be a non-empty string")
        # Pass cmd as a positional argument to /bin/sh -c so the shell string is
        # never interpolated by the Python subprocess layer (no shell=True).
        proc = await asyncio.create_subprocess_exec(
            "/bin/sh", "-c", cmd,
            cwd=str(self.root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return {"stdout": "", "stderr": f"Timed out after {timeout}s", "exit_code": -1}
        return {
            "stdout": stdout.decode(errors="replace"),
            "stderr": stderr.decode(errors="replace"),
            "exit_code": proc.returncode,
        }

    # ── lifecycle ────────────────────────────────────────────────────────

    def delete(self) -> None:
        if self.root.exists():
            shutil.rmtree(self.root, ignore_errors=True)

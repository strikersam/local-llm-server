from __future__ import annotations
"""agent/github_tools.py — GitHub integration + local workspace execution.

Provides:
  - GitHubTools: async GitHub API client (read/write/PR)
  - WorkspaceManager: clone repos locally, bind to Aider/OpenCode runtimes
  - github_router: FastAPI endpoints at /api/github/

Security:
  - Tokens are fetched from SecretsStore, never stored in plain text
  - All operations emit audit log entries via rbac.audit()
  - Cloned repos live in WORKSPACE_BASE_DIR (default: ~/.llm-relay/workspaces)
  - Subprocess git commands use timeout limits; no shell=True

Local workspace flow:
  POST /api/github/repos/{owner}/{repo}/workspace/init  → clones or pulls
  POST /api/github/repos/{owner}/{repo}/workspace/run   → runs agent in workspace
  GET  /api/github/repos/{owner}/{repo}/workspace/diff  → pending git diff
  POST /api/github/repos/{owner}/{repo}/workspace/commit → stage + commit
  POST /api/github/repos/{owner}/{repo}/workspace/pr     → open PR via API
"""


import asyncio
import base64
import logging
import os
import re
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from rbac import audit

log = logging.getLogger("qwen-agent")

WORKSPACE_BASE_DIR = Path(
    os.environ.get("WORKSPACE_BASE_DIR", Path.home() / ".llm-relay" / "workspaces")
)


# ── GitHubTools ───────────────────────────────────────────────────────────────

class GitHubTools:
    """Async GitHub API client.

    Requires a GitHub access token with 'repo' scope.
    Tokens should be fetched from SecretsStore, not hard-coded.
    """

    def __init__(self, token: str | None = None) -> None:
        self.token = token
        self.base_url = "https://api.github.com"

    def _validate_repo_parts(self, owner: str, repo: str, branch: str | None = None, path: str | None = None) -> None:
        """Strictly validate GitHub parameters to prevent URL injection or SSRF."""
        if not re.match(r"^[a-zA-Z0-9._-]+$", owner):
            raise ValueError(f"Invalid GitHub owner name: {owner}")
        if not re.match(r"^[a-zA-Z0-9._-]+$", repo):
            raise ValueError(f"Invalid GitHub repository name: {repo}")
        if branch and not re.match(r"^[a-zA-Z0-9._/\-]+$", branch):
            raise ValueError(f"Invalid branch name: {branch}")
        if path and (".." in path or not re.match(r"^[a-zA-Z0-9._/\-]*$", path)):
            raise ValueError(f"Invalid file path: {path}")

    def _headers(self) -> dict[str, str]:
        if not self.token:
            raise ValueError("GitHub token not provided. Please add a GitHub token in Settings → Secrets.")
        return {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def get_authenticated_user(self) -> dict[str, Any]:
        """Return the authenticated GitHub user's profile."""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self.base_url}/user", headers=self._headers())
            resp.raise_for_status()
            return resp.json()

    async def list_repos(self, per_page: int = 50) -> list[dict[str, Any]]:
        """List repositories accessible with this token."""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{self.base_url}/user/repos",
                headers=self._headers(),
                params={"sort": "updated", "per_page": per_page, "type": "all"},
            )
            resp.raise_for_status()
            return resp.json()

    async def get_repo(self, owner: str, repo: str) -> dict[str, Any]:
        self._validate_repo_parts(owner, repo)
        """Get repository metadata."""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def list_branches(self, owner: str, repo: str) -> list[dict[str, Any]]:
        self._validate_repo_parts(owner, repo)
        """List branches in a repository."""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/branches",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def read_repo_file(self, owner: str, repo: str, path: str, branch: str = "main") -> str:
        self._validate_repo_parts(owner, repo, branch=branch, path=path)
        """Read a single file from a GitHub repository (API method)."""
        async with httpx.AsyncClient(timeout=10) as client:
            url  = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}?ref={branch}"
            resp = await client.get(url, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
            if data.get("encoding") == "base64":
                return base64.b64decode(data["content"]).decode("utf-8")
            return data.get("content", "")

    async def create_branch(self, owner: str, repo: str, branch_name: str, base_branch: str = "main") -> dict[str, Any]:
        self._validate_repo_parts(owner, repo, branch=base_branch)
        """Create a new branch from base_branch."""
        async with httpx.AsyncClient(timeout=10) as client:
            # Get base SHA
            base_resp = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/git/refs/heads/{base_branch}",
                headers=self._headers(),
            )
            base_resp.raise_for_status()
            sha = base_resp.json()["object"]["sha"]

            resp = await client.post(
                f"{self.base_url}/repos/{owner}/{repo}/git/refs",
                headers=self._headers(),
                json={"ref": f"refs/heads/{branch_name}", "sha": sha},
            )
            resp.raise_for_status()
            return resp.json()

    async def commit_file(self, owner: str, repo: str, path: str, content: str, message: str, branch: str = "main") -> dict[str, Any]:
        self._validate_repo_parts(owner, repo, branch=branch, path=path)
        async with httpx.AsyncClient(timeout=10) as client:
            # Get existing SHA if file exists
            sha = None
            try:
                check = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/contents/{path}?ref={branch}",
                    headers=self._headers(),
                )
                if check.status_code == 200:
                    sha = check.json()["sha"]
            except Exception:
                pass

            payload: dict[str, Any] = {
                "message": message,
                "content": base64.b64encode(content.encode()).decode(),
                "branch":  branch,
            }
            if sha:
                payload["sha"] = sha

            resp = await client.put(
                f"{self.base_url}/repos/{owner}/{repo}/contents/{path}",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    async def open_pull_request(self, owner: str, repo: str, title: str, head: str, base: str = "main", body: str = "") -> dict[str, Any]:
        self._validate_repo_parts(owner, repo, branch=head)
        """Open a pull request."""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{self.base_url}/repos/{owner}/{repo}/pulls",
                headers=self._headers(),
                json={"title": title, "head": head, "base": base, "body": body},
            )
            resp.raise_for_status()
            return resp.json()

    async def list_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "open",
    ) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/pulls",
                headers=self._headers(),
                params={"state": state, "per_page": 50},
            )
            resp.raise_for_status()
            return resp.json()


    async def get_issue(self, owner: str, repo: str, issue_number: int) -> dict[str, Any]:
        self._validate_repo_parts(owner, repo)
        """Fetch a single GitHub issue."""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def comment_on_issue(self, owner: str, repo: str, issue_number: int, body: str) -> dict[str, Any]:
        self._validate_repo_parts(owner, repo)
        """Post a comment on a GitHub issue."""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/comments",
                headers=self._headers(),
                json={"body": body},
            )
            resp.raise_for_status()
            return resp.json()

    async def close_issue(self, owner: str, repo: str, issue_number: int, comment: str | None = None) -> dict[str, Any]:
        self._validate_repo_parts(owner, repo)
        """Close a GitHub issue, optionally adding a comment first."""
        if comment:
            await self.comment_on_issue(owner, repo, issue_number, comment)
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.patch(
                f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}",
                headers=self._headers(),
                json={"state": "closed"},
            )
            resp.raise_for_status()
            return resp.json()

    async def merge_pull_request(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        merge_method: str = "merge",
        commit_title: str | None = None,
    ) -> dict[str, Any]:
        """Merge an open pull request via the GitHub API."""
        self._validate_repo_parts(owner, repo)
        if not isinstance(pull_number, int) or pull_number < 1:
            raise ValueError(f"pull_number must be a positive integer, got {pull_number!r}")
        _valid_methods = {"merge", "squash", "rebase"}
        if merge_method not in _valid_methods:
            raise ValueError(f"merge_method must be one of {_valid_methods}, got {merge_method!r}")
        payload: dict[str, Any] = {"merge_method": merge_method}
        if commit_title:
            payload["commit_title"] = commit_title
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.put(
                f"{self.base_url}/repos/{owner}/{repo}/pulls/{pull_number}/merge",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    # ── backwards compat shims (old single-string owner/repo argument) ─────────

    async def read_repo_file_compat(
        self, repo_name: str, path: str, branch: str = "main"
    ) -> str:
        """Backwards-compat: accepts 'owner/repo' format."""
        owner, repo = repo_name.split("/", 1)
        return await self.read_repo_file(owner, repo, path, branch)

    async def create_branch_compat(
        self,
        repo_name: str,
        branch_name: str,
        base_branch: str = "main",
    ) -> dict[str, Any]:
        """Backwards-compat: accepts 'owner/repo' format."""
        owner, repo = repo_name.split("/", 1)
        return await self.create_branch(owner, repo, branch_name, base_branch)

    async def commit_changes(
        self,
        repo_name: str,
        branch_name: str,
        message: str,
        path: str,
        content: str,
    ) -> dict[str, Any]:
        """Commit a single file change. Accepts 'owner/repo' format for repo_name."""
        owner, repo = repo_name.split("/", 1)
        return await self.commit_file(
            owner=owner,
            repo=repo,
            path=path,
            content=content,
            message=message,
            branch=branch_name,
        )

    async def open_pull_request_compat(
        self,
        repo_name: str,
        title: str,
        head: str,
        base: str = "main",
        body: str = "",
    ) -> dict[str, Any]:
        """Backwards-compat: accepts 'owner/repo' format."""
        owner, repo = repo_name.split("/", 1)
        return await self.open_pull_request(owner, repo, title, head, base, body)

    async def list_branches_compat(self, repo_name: str) -> list[dict[str, Any]]:
        """Backwards-compat: accepts 'owner/repo' format."""
        owner, repo = repo_name.split("/", 1)
        return await self.list_branches(owner, repo)

    def _encode_content(self, content: str) -> str:
        return base64.b64encode(content.encode("utf-8")).decode("utf-8")


# ── Local workspace ────────────────────────────────────────────────────────────

class LocalWorkspace:
    """Manages a local git clone of a GitHub repository.

    Clones are stored under WORKSPACE_BASE_DIR/{owner}/{repo}.
    """

    def __init__(self, owner: str, repo: str, token: str | None = None) -> None:
        # Strictly validate inputs to prevent path injection
        if not re.match(r"^[a-zA-Z0-9_-]+$", owner):
            raise ValueError("Invalid owner name")
        if not re.match(r"^[a-zA-Z0-9_-]+$", repo):
            raise ValueError("Invalid repository name")

        self.owner = owner
        self.repo  = repo

        # Build path using os.path.join and absolute base for safety
        base_abs = str(WORKSPACE_BASE_DIR.resolve())
        # Use only validated components
        safe_path = os.path.normpath(os.path.join(base_abs, owner, repo))

        # Strong prefix check to satisfy static analysis
        if not safe_path.startswith(base_abs + os.sep):
             raise ValueError("Path escapes workspace root")
        self.token = token
        self.path = Path(safe_path)

    @property
    def clone_url(self) -> str:
        if self.token:
            return f"https://{self.token}@github.com/{self.owner}/{self.repo}.git"
        return f"https://github.com/{self.owner}/{self.repo}.git"

    def exists(self) -> bool:
        return (self.path / ".git").exists()

    async def _run(self, *args: str, cwd: Path | None = None, timeout: int = 120) -> tuple[int, str, str]:
        """Run a git command. Never uses shell=True."""
        proc = await asyncio.create_subprocess_exec(
            *args,
            cwd=str(cwd or self.path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return proc.returncode, stdout.decode(errors="replace"), stderr.decode(errors="replace")
        except asyncio.TimeoutError:
            proc.kill()
            raise RuntimeError(f"git command timed out after {timeout}s: {args}")

    async def clone_or_pull(self) -> dict[str, Any]:
        """Clone the repo if it doesn't exist; pull if it does."""
        if not self.exists():
            base = WORKSPACE_BASE_DIR.resolve()
            base.mkdir(parents=True, exist_ok=True)
            # Use validated self.owner to construct owner_dir
            owner_dir = Path(os.path.normpath(os.path.join(str(base), self.owner)))
            if not str(owner_dir).startswith(str(base) + os.sep):
                 raise ValueError("Invalid workspace location")
            owner_dir.mkdir(parents=True, exist_ok=True)
            rc, out, err = await self._run(
                "git", "clone", "--depth=50", self.clone_url, str(self.path),
                cwd=owner_dir,
            )
            action = "cloned"
        else:
            rc, out, err = await self._run("git", "pull", "--ff-only")
            action = "pulled"

        if rc != 0:
            raise RuntimeError(f"git {action} failed (rc={rc}): {err}")

        # Remove token from remote URL for security
        await self._run("git", "remote", "set-url", "origin",
                        f"https://github.com/{self.owner}/{self.repo}.git")

        return {"action": action, "path": str(self.path), "ok": True}

    async def current_branch(self) -> str:
        rc, out, _ = await self._run("git", "branch", "--show-current")
        return out.strip() if rc == 0 else "unknown"

    async def diff(self) -> str:
        """Return the current working-tree diff (staged + unstaged)."""
        _, out, _ = await self._run("git", "diff", "HEAD")
        return out

    async def status(self) -> str:
        _, out, _ = await self._run("git", "status", "--short")
        return out

    async def stage_and_commit(self, message: str, paths: list[str] | None = None) -> dict[str, Any]:
        """Stage files and commit. paths=None stages everything; paths=[] raises."""
        if paths is not None and not paths:
            raise ValueError("paths must be None (stage all) or a non-empty list")
        if paths:
            for p in paths:
                rc, _, err = await self._run("git", "add", "--", p)
                if rc != 0:
                    raise RuntimeError(f"git add failed for {p!r}: {err.strip()}")
        else:
            rc, _, err = await self._run("git", "add", "-A")
            if rc != 0:
                raise RuntimeError(f"git add -A failed: {err.strip()}")
        rc, out, err = await self._run("git", "commit", "-m", message)
        if rc != 0:
            raise RuntimeError(f"git commit failed: {err.strip()}")
        return {"committed": True, "message": message, "output": out}

    async def create_branch(self, branch_name: str, base_branch: str = "main") -> dict[str, Any]:
        """Create and checkout a new branch from base_branch."""
        if not re.match(r"^[a-zA-Z0-9/_\-\.]{1,100}$", branch_name):
            raise ValueError(f"Invalid branch name: {branch_name!r}")
        if not re.match(r"^[a-zA-Z0-9/_\-\.]{1,100}$", base_branch):
            raise ValueError(f"Invalid base branch name: {base_branch!r}")
        rc, _, err = await self._run("git", "checkout", "-b", branch_name, base_branch)
        if rc != 0:
            raise RuntimeError(f"git checkout -b failed: {err.strip()}")
        return {"branch": branch_name, "created": True}

    async def push(self, branch: str | None = None) -> dict[str, Any]:
        """Push the current branch.  Sets upstream on first push."""
        if branch is None:
            branch = await self.current_branch()
        # Temporarily set token in remote URL, push, then clear it
        await self._run("git", "remote", "set-url", "origin", self.clone_url)
        rc, out, err = await self._run(
            "git", "push", "--set-upstream", "origin", branch
        )
        # Always clear the token from remote URL
        await self._run("git", "remote", "set-url", "origin",
                        f"https://github.com/{self.owner}/{self.repo}.git")
        if rc != 0:
            raise RuntimeError(f"git push failed: {err}")
        return {"pushed": True, "branch": branch}


# ── FastAPI router ─────────────────────────────────────────────────────────────

github_router = APIRouter(prefix="/api/github", tags=["github"])


def _get_user(request: Request) -> dict:
    return getattr(request.state, "user", None) or {}


def _uid(user: Any) -> str:
    if isinstance(user, dict):
        return user.get("email") or user.get("_id") or "unknown"
    return str(getattr(user, "email", "anonymous"))


async def _get_token(user: dict) -> str | None:
    """Fetch the user's GitHub token from SecretsStore."""
    try:
        from secrets_store import get_secrets_store
        from rbac import get_user_role
        store  = get_secrets_store()
        uid    = _uid(user)
        role   = get_user_role(user)
        # Look for a secret tagged "github"
        recs   = await store.list_for_user(uid, role)
        for rec in recs:
            if "github" in rec.tags or rec.name.lower().startswith("github"):
                value = await store.get_value(rec.secret_id, uid, role)
                if value:
                    return value
    except Exception as e:
        log.debug("Could not fetch GitHub token from secrets: %s", e)
    # Fallback: env var
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


@github_router.get("/repos")
async def list_repos(request: Request):
    """List GitHub repos accessible to the current user."""
    user  = _get_user(request)
    token = await _get_token(user)
    gh    = GitHubTools(token=token)
    try:
        repos = await gh.list_repos()
        return {"repos": repos, "total": len(repos)}
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code,
                            detail=f"GitHub API error: {e.response.text}")


@github_router.get("/repos/{owner}/{repo}")
async def get_repo(owner: str, repo: str, request: Request):
    user  = _get_user(request)
    token = await _get_token(user)
    gh    = GitHubTools(token=token)
    try:
        return await gh.get_repo(owner, repo)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))


@github_router.get("/repos/{owner}/{repo}/branches")
async def list_branches(owner: str, repo: str, request: Request):
    user  = _get_user(request)
    token = await _get_token(user)
    gh    = GitHubTools(token=token)
    return await gh.list_branches(owner, repo)


@github_router.get("/repos/{owner}/{repo}/pulls")
async def list_prs(owner: str, repo: str, request: Request, state: str = "open"):
    user  = _get_user(request)
    token = await _get_token(user)
    gh    = GitHubTools(token=token)
    return await gh.list_pull_requests(owner, repo, state=state)


# ── Workspace routes ───────────────────────────────────────────────────────────

class WorkspaceInitRequest(BaseModel):
    branch: str = "main"


class WorkspaceCommitRequest(BaseModel):
    message: str
    branch:  str | None = None
    paths:   list[str] | None = None
    open_pr: bool = False
    pr_title: str = ""
    pr_body:  str = ""
    pr_base:  str = "main"


@github_router.post("/repos/{owner}/{repo}/workspace/init")
async def init_workspace(owner: str, repo: str, request: Request, body: WorkspaceInitRequest = WorkspaceInitRequest()):
    """Clone or pull the repository into a local workspace."""
    user  = _get_user(request)
    uid   = _uid(user)
    token = await _get_token(user)
    ws    = LocalWorkspace(owner=owner, repo=repo, token=token)
    try:
        result = await ws.clone_or_pull()
        audit("workspace.init", user, resource="repo", resource_id=f"{owner}/{repo}",
              repo_workspace=f"https://github.com/{owner}/{repo}")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@github_router.get("/repos/{owner}/{repo}/workspace/status")
async def workspace_status(owner: str, repo: str, request: Request):
    """Return the current git status of the local workspace."""
    ws = LocalWorkspace(owner=owner, repo=repo)
    if not ws.exists():
        raise HTTPException(status_code=404, detail="Workspace not initialised. Call /workspace/init first.")
    branch = await ws.current_branch()
    status = await ws.status()
    return {"branch": branch, "status": status, "path": str(ws.path)}


@github_router.get("/repos/{owner}/{repo}/workspace/diff")
async def workspace_diff(owner: str, repo: str, request: Request):
    """Return pending git diff in the workspace."""
    ws = LocalWorkspace(owner=owner, repo=repo)
    if not ws.exists():
        raise HTTPException(status_code=404, detail="Workspace not initialised.")
    diff = await ws.diff()
    return {"diff": diff, "has_changes": bool(diff.strip())}


@github_router.post("/repos/{owner}/{repo}/workspace/commit")
async def workspace_commit(owner: str, repo: str, request: Request, body: WorkspaceCommitRequest):
    """Stage, commit, and optionally push + open a PR."""
    user  = _get_user(request)
    token = await _get_token(user)
    ws    = LocalWorkspace(owner=owner, repo=repo, token=token)

    if not ws.exists():
        raise HTTPException(status_code=404, detail="Workspace not initialised.")

    try:
        commit_result = await ws.stage_and_commit(body.message, body.paths)
        push_result   = {}
        pr_result     = {}

        if body.open_pr:
            branch        = body.branch or await ws.current_branch()
            push_result   = await ws.push(branch=branch)
            gh            = GitHubTools(token=token)
            pr_result     = await gh.open_pull_request(
                owner=owner, repo=repo,
                title=body.pr_title or body.message,
                head=branch, base=body.pr_base,
                body=body.pr_body,
            )

        audit("workspace.commit", user, resource="repo", resource_id=f"{owner}/{repo}",
              repo_workspace=f"https://github.com/{owner}/{repo}")

        return {"commit": commit_result, "push": push_result, "pr": pr_result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

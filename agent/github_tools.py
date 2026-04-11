from __future__ import annotations

import httpx
import logging
from typing import Any

log = logging.getLogger("qwen-agent")

class GitHubTools:
    """Tools for interacting with GitHub repositories.
    
    Requires a GitHub access token with 'repo' scope.
    """

    def __init__(self, token: str | None = None) -> None:
        self.token = token
        self.base_url = "https://api.github.com"

    def _headers(self) -> dict[str, str]:
        if not self.token:
            raise ValueError("GitHub token not provided. Please grant repo access in Settings.")
        return {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

    async def read_repo_file(self, repo_name: str, path: str, branch: str = "main") -> str:
        """Read a file from a GitHub repository."""
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/repos/{repo_name}/contents/{path}?ref={branch}"
            resp = await client.get(url, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
            if data.get("encoding") == "base64":
                import base64
                return base64.b64decode(data["content"]).decode("utf-8")
            return data["content"]

    async def create_branch(self, repo_name: str, branch_name: str, base_branch: str = "main") -> dict[str, Any]:
        """Create a new branch in a GitHub repository."""
        async with httpx.AsyncClient() as client:
            # 1. Get base branch SHA
            base_url = f"{self.base_url}/repos/{repo_name}/git/refs/heads/{base_branch}"
            base_resp = await client.get(base_url, headers=self._headers())
            base_resp.raise_for_status()
            sha = base_resp.json()["object"]["sha"]

            # 2. Create new ref
            url = f"{self.base_url}/repos/{repo_name}/git/refs"
            resp = await client.post(
                url,
                headers=self._headers(),
                json={
                    "ref": f"refs/heads/{branch_name}",
                    "sha": sha
                }
            )
            resp.raise_for_status()
            return resp.json()

    async def commit_changes(self, repo_name: str, branch_name: str, message: str, path: str, content: str) -> dict[str, Any]:
        """Commit a single file change to a branch. (Simplified for individual file updates)"""
        async with httpx.AsyncClient() as client:
            # 1. Get file SHA if it exists
            url = f"{self.base_url}/repos/{repo_name}/contents/{path}?ref={branch_name}"
            sha = None
            try:
                resp = await client.get(url, headers=self._headers())
                if resp.status_code == 200:
                    sha = resp.json()["sha"]
            except Exception:
                pass

            # 2. Create/Update file
            payload = {
                "message": message,
                "content": self._encode_content(content),
                "branch": branch_name
            }
            if sha:
                payload["sha"] = sha
            
            put_url = f"{self.base_url}/repos/{repo_name}/contents/{path}"
            resp = await client.put(put_url, headers=self._headers(), json=payload)
            resp.raise_for_status()
            return resp.json()

    async def open_pull_request(self, repo_name: str, title: str, head: str, base: str = "main", body: str = "") -> dict[str, Any]:
        """Open a pull request on GitHub."""
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/repos/{repo_name}/pulls"
            resp = await client.post(
                url,
                headers=self._headers(),
                json={
                    "title": title,
                    "head": head,
                    "base": base,
                    "body": body
                }
            )
            resp.raise_for_status()
            return resp.json()

    async def list_repos(self) -> list[dict[str, Any]]:
        """List repositories the token has access to."""
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/user/repos"
            resp = await client.get(url, headers=self._headers(), params={"sort": "updated", "per_page": 50})
            resp.raise_for_status()
            return resp.json()

    async def list_branches(self, repo_name: str) -> list[dict[str, Any]]:
        """List branches in a repository."""
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/repos/{repo_name}/branches"
            resp = await client.get(url, headers=self._headers())
            resp.raise_for_status()
            return resp.json()

    def _encode_content(self, content: str) -> str:
        import base64
        return base64.b64encode(content.encode("utf-8")).decode("utf-8")

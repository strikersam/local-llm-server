"""agent/github_tools.py — GitHub integration.
"""

from __future__ import annotations

import base64
import logging
from typing import Any

import httpx
from fastapi import APIRouter

log = logging.getLogger("qwen-agent")
github_router = APIRouter(prefix="/api/github", tags=["github"])

@github_router.get("/status")
async def github_status():
    return {"status": "ok"}

class GitHubTools:
    def __init__(self, token: str | None = None) -> None:
        self.token = token
        self.base_url = "https://api.github.com"

    def _headers(self) -> dict[str, str]:
        if not self.token: raise ValueError("Token missing")
        return {"Authorization": f"token {self.token}", "Accept": "application/vnd.github.v3+json"}

    async def _request(self, method, endpoint, data=None, params=None):
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.request(method, f"{self.base_url}{endpoint}", headers=self._headers(), json=data, params=params)
            resp.raise_for_status()
            return resp.json()

    async def list_repos(self) -> list: return await self._request("GET", "/user/repos")
    async def read_repo_file(self, r, p, b="main") -> str:
        owner, repo = r.split("/", 1)
        data = await self._request("GET", f"/repos/{owner}/{repo}/contents/{p}", params={"ref": b})
        return base64.b64decode(data["content"]).decode("utf-8") if data.get("encoding") == "base64" else data.get("content", "")

    async def comment_on_issue(self, r, n, b):
        owner, repo = r.split("/", 1)
        return await self._request("POST", f"/repos/{owner}/{repo}/issues/{n}/comments", data={"body": b})

    async def close_issue(self, r, n, comment=None):
        owner, repo = r.split("/", 1)
        if comment: await self.comment_on_issue(r, n, comment)
        return await self._request("PATCH", f"/repos/{owner}/{repo}/issues/{n}", data={"state": "closed"})

    async def get_issue(self, r, n):
        owner, repo = r.split("/", 1)
        return await self._request("GET", f"/repos/{owner}/{repo}/issues/{n}")

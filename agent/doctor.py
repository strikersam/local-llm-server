from __future__ import annotations
import shutil
import httpx
import logging
import os
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

log = logging.getLogger("qwen-agent")

class PreflightIssue(BaseModel):
    code: str
    message: str
    fix_hint: str
    details: Optional[Dict[str, Any]] = None

class PreflightReport(BaseModel):
    ready: bool
    summary: str
    issues: List[PreflightIssue] = []

class DirectChatDoctor:
    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token

    async def check_all(self, repo_url: Optional[str] = None, repo_ref: Optional[str] = None) -> PreflightReport:
        issues = []

        # 1. Git Binary
        if not shutil.which("git"):
            issues.append(PreflightIssue(
                code="missing_git_binary",
                message="'git' binary not found on PATH.",
                fix_hint="Install git and ensure it is on PATH."
            ))

        # 2. GitHub Token
        if not self.github_token:
            issues.append(PreflightIssue(
                code="missing_github_token",
                message="No GitHub token available for this user.",
                fix_hint="Add a GitHub token in Settings or set GH_TOKEN/GITHUB_TOKEN."
            ))
        else:
            # 3. GitHub Token Validity
            try:
                headers = {
                    "Authorization": f"token {self.github_token}",
                    "Accept": "application/vnd.github+json",
                }
                async with httpx.AsyncClient() as client:
                    resp = await client.get("https://api.github.com/user", headers=headers, timeout=5.0)
                    if resp.status_code != 200:
                        issues.append(PreflightIssue(
                            code="invalid_github_token",
                            message="GitHub token rejected by GitHub API.",
                            fix_hint="Reconnect GitHub in Settings or set a valid token with repo scopes.",
                            details={"status_code": resp.status_code}
                        ))
                    else:
                        scopes = resp.headers.get("X-OAuth-Scopes", "").lower()
                        # Basic check: should have 'repo' for write ops
                        if "repo" not in scopes:
                             log.warning("GitHub token missing 'repo' scope")
            except Exception as e:
                issues.append(PreflightIssue(
                    code="github_api_unreachable",
                    message="Could not validate GitHub token due to network error.",
                    fix_hint="Ensure the server can reach api.github.com.",
                    details={"error": str(e)}
                ))

        if issues:
            return PreflightReport(
                ready=False,
                summary="Preflight checks failed",
                issues=issues
            )

        return PreflightReport(ready=True, summary="System healthy")

def translate_error_to_conversational(error_detail: Any) -> str:
    """Translate technical preflight issues into a conversational assistant reply."""
    if isinstance(error_detail, dict) and "issues" in error_detail:
        issues = error_detail["issues"]
        if not issues:
            return "I encountered an unexpected configuration issue. Please check the logs."

        # Humanize the first major issue
        first = issues[0]
        msg = first.get("message", "unknown error")
        hint = first.get("fix_hint", "")

        reply = f"I'm ready to help, but I noticed a configuration issue: {msg}"
        if hint:
            reply += f" {hint}"
        return reply

    return f"I encountered a technical problem: {str(error_detail)}"

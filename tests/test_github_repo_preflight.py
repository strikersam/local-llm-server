from __future__ import annotations
import subprocess
from pathlib import Path
from fastapi.testclient import TestClient
import pytest
import proxy
import direct_chat
from agent.state import AgentSessionStore
from agent.job_manager import AgentJobManager


def _fake_user():
    """
    Create a UserInfo representing a fixed test user for tests.
    
    Returns:
        direct_chat.UserInfo: A user with id "u1" and email "repo-tester@example.com".
    """
    return direct_chat.UserInfo(id="u1", email="repo-tester@example.com")


def test_repo_access_preflight_fails_when_git_ls_remote_fails(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(direct_chat, "_direct_chat_store", AgentSessionStore(db_path=str(tmp_path / "chat_repo.db")))
    monkeypatch.setattr(direct_chat, "_agent_jobs", AgentJobManager())
    proxy.app.dependency_overrides[direct_chat._get_current_user] = _fake_user

    # Ensure git binary appears present
    import shutil
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/git")

    # Return a token
    async def fake_get_token(email):
        """
        Provide a fake GitHub personal access token for the given email.
        
        Parameters:
            email (str): User email address; unused but kept to match the production signature.
        
        Returns:
            str: The placeholder token 'ghp_FAKE'.
        """
        return "ghp_FAKE"
    monkeypatch.setattr(direct_chat, "_get_github_token_for_user", fake_get_token)

    # Simulate git ls-remote failing by patching WorkspaceManager.repo_access_preflight
    from workspace.manager import WorkspaceManager
    async def fake_repo_access(self, repo_url, token=None, timeout=8):
        """
        Simulate a repository access preflight that always fails with an authentication error.
        
        Parameters:
            repo_url (str): Repository URL to check.
            token (str | None): Optional authentication token.
            timeout (int): Timeout in seconds for the preflight check.
        
        Returns:
            dict: Result with `ok` set to False and `error` set to "fatal: Authentication failed".
        """
        return {"ok": False, "error": "fatal: Authentication failed"}
    monkeypatch.setattr(WorkspaceManager, "repo_access_preflight", fake_repo_access)

    client = TestClient(proxy.app)
    payload = {"content": "Please clone this repo and create PR", "agent_mode": True, "metadata": {"repo_url": "https://github.com/example/notfound.git"}}
    resp = client.post("/api/chat/send", json=payload)
    assert resp.status_code == 412
    detail = resp.json().get("detail")
    assert detail and not detail.get("ready")
    codes = {i.get("code") for i in detail.get("issues", [])}
    assert "git_repo_access" in codes

    proxy.app.dependency_overrides.clear()

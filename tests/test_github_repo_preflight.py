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
    Create a fixed test UserInfo representing a fake user.
    
    Returns:
        direct_chat.UserInfo: A user object with id "u1" and email "repo-tester@example.com".
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
    monkeypatch.setattr(direct_chat, "_get_github_token_for_user", lambda email: "ghp_FAKE")

    # Simulate git ls-remote failing by patching subprocess.run
    def fake_run(cmd, stdout, stderr, env, timeout):
        """
        Simulate a failing subprocess.run invocation that mimics `git ls-remote` authentication failure.
        
        This function ignores its inputs and returns an object shaped like subprocess.CompletedProcess with:
        - returncode: 128
        - stderr: b"fatal: Authentication failed"
        - stdout: b""
        
        Returns:
            An object with `returncode`, `stderr`, and `stdout` attributes representing a git authentication failure.
        """
        class P: returncode=128; stderr=b"fatal: Authentication failed"; stdout=b""
        return P()
    monkeypatch.setattr("subprocess.run", fake_run)

    client = TestClient(proxy.app)
    payload = {"content": "Please clone this repo and create PR", "agent_mode": True, "metadata": {"repo_url": "https://github.com/example/notfound.git"}}
    resp = client.post("/api/chat/send", json=payload)
    assert resp.status_code == 412
    detail = resp.json().get("detail")
    assert detail and not detail.get("ready")
    codes = {i.get("code") for i in detail.get("issues", [])}
    assert "git_repo_access" in codes

    proxy.app.dependency_overrides.clear()

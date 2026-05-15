from __future__ import annotations
from pathlib import Path
from fastapi.testclient import TestClient
import proxy
import direct_chat
from agent.state import AgentSessionStore
from agent.job_manager import AgentJobManager


def _fake_user():
    """
    Create a fake authenticated user for tests.
    
    Returns:
        direct_chat.UserInfo: A UserInfo instance with id "u1" and email "refpath-tester@example.com".
    """
    return direct_chat.UserInfo(id="u1", email="refpath-tester@example.com")


def test_repo_ref_preflight_fails(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(direct_chat, "_direct_chat_store", AgentSessionStore(db_path=str(tmp_path / "chat_ref.db")))
    monkeypatch.setattr(direct_chat, "_agent_jobs", AgentJobManager())
    proxy.app.dependency_overrides[direct_chat._get_current_user] = _fake_user

    import shutil
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/git")
    monkeypatch.setattr(direct_chat, "_get_github_token_for_user", lambda email: "ghp_FAKE")

    # Patch WorkspaceManager.validate_repo_ref to simulate missing ref
    from workspace.manager import WorkspaceManager
    monkeypatch.setattr(WorkspaceManager, "validate_repo_ref", lambda self, repo, ref, token=None: {"ok": False, "error": "ref_not_found"})

    client = TestClient(proxy.app)
    payload = {"content": "Please implement the feature and open a pull request with the changes", "agent_mode": True, "metadata": {"repo_url": "https://github.com/example/repo.git", "repo_ref": "nonexistent-branch"}}
    resp = client.post("/api/chat/send", json=payload)
    assert resp.status_code == 412
    detail = resp.json().get("detail")
    assert detail and not detail.get("ready")
    codes = {i.get("code") for i in detail.get("issues", [])}
    assert "git_repo_ref" in codes

    proxy.app.dependency_overrides.clear()


def test_repo_path_preflight_fails(monkeypatch, tmp_path: Path):
    """
    Verifies the API returns a 412 preflight failure when repository path validation fails.
    
    Sets up a fake authenticated user and stubs workspace validation to simulate a missing/invalid repo path, posts an agent-mode chat request referencing that path, and asserts the response status is 412, the returned detail indicates the request is not ready, and the reported issues include the "git_repo_path" code.
    """
    monkeypatch.setattr(direct_chat, "_direct_chat_store", AgentSessionStore(db_path=str(tmp_path / "chat_path.db")))
    monkeypatch.setattr(direct_chat, "_agent_jobs", AgentJobManager())
    proxy.app.dependency_overrides[direct_chat._get_current_user] = _fake_user

    import shutil
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/git")
    monkeypatch.setattr(direct_chat, "_get_github_token_for_user", lambda email: "ghp_FAKE")

    from workspace.manager import WorkspaceManager
    monkeypatch.setattr(WorkspaceManager, "validate_repo_path", lambda self, repo, ref, path, token=None: {"ok": False, "error": "http_404"})

    client = TestClient(proxy.app)
    payload = {"content": "Please implement the feature and open a pull request with the changes", "agent_mode": True, "metadata": {"repo_url": "https://github.com/example/repo.git", "repo_ref": "main", "repo_path": "src/does/not/exist.py"}}
    resp = client.post("/api/chat/send", json=payload)
    assert resp.status_code == 412
    detail = resp.json().get("detail")
    assert detail and not detail.get("ready")
    codes = {i.get("code") for i in detail.get("issues", [])}
    assert "git_repo_path" in codes

    proxy.app.dependency_overrides.clear()

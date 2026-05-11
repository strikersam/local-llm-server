from __future__ import annotations
from pathlib import Path
from fastapi.testclient import TestClient
import proxy
import direct_chat
from agent.state import AgentSessionStore
from agent.job_manager import AgentJobManager


def _fake_user():
    """
    Provide a fixed test user for authentication overrides used in integration tests.
    
    Returns:
        direct_chat.UserInfo: A UserInfo with id "u1" and email "refpath-tester@example.com".
    """
    return direct_chat.UserInfo(id="u1", email="refpath-tester@example.com")


def test_repo_ref_preflight_fails(monkeypatch, tmp_path: Path):
    """
    Verifies that sending an agent-mode chat is rejected when the provided repository ref fails preflight validation.
    
    Patches dependencies to simulate an authenticated user, available git, and a GitHub token, and stubs WorkspaceManager.validate_repo_ref to return {"ok": False, "error": "ref_not_found"}. Sends POST /api/chat/send with metadata.repo_ref set to a nonexistent branch and asserts the response is HTTP 412, the returned detail indicates not ready, and the issues include the code "git_repo_ref".
    """
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
    payload = {"content": "Please open PR", "agent_mode": True, "metadata": {"repo_url": "https://github.com/example/repo.git", "repo_ref": "nonexistent-branch"}}
    resp = client.post("/api/chat/send", json=payload)
    assert resp.status_code == 412
    detail = resp.json().get("detail")
    assert detail and not detail.get("ready")
    codes = {i.get("code") for i in detail.get("issues", [])}
    assert "git_repo_ref" in codes

    proxy.app.dependency_overrides.clear()


def test_repo_path_preflight_fails(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(direct_chat, "_direct_chat_store", AgentSessionStore(db_path=str(tmp_path / "chat_path.db")))
    monkeypatch.setattr(direct_chat, "_agent_jobs", AgentJobManager())
    proxy.app.dependency_overrides[direct_chat._get_current_user] = _fake_user

    import shutil
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/git")
    monkeypatch.setattr(direct_chat, "_get_github_token_for_user", lambda email: "ghp_FAKE")

    from workspace.manager import WorkspaceManager
    monkeypatch.setattr(WorkspaceManager, "validate_repo_path", lambda self, repo, ref, path, token=None: {"ok": False, "error": "http_404"})

    client = TestClient(proxy.app)
    payload = {"content": "Please open PR", "agent_mode": True, "metadata": {"repo_url": "https://github.com/example/repo.git", "repo_ref": "main", "repo_path": "src/does/not/exist.py"}}
    resp = client.post("/api/chat/send", json=payload)
    assert resp.status_code == 412
    detail = resp.json().get("detail")
    assert detail and not detail.get("ready")
    codes = {i.get("code") for i in detail.get("issues", [])}
    assert "git_repo_path" in codes

    proxy.app.dependency_overrides.clear()

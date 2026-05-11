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
    Verify that an agent-mode chat request is rejected when repository ref preflight validation fails.
    
    Sends a POST to /api/chat/send with agent_mode enabled and a nonexistent repo ref, and asserts the response has HTTP 412, the returned `detail.ready` is falsy, and one of the reported issue `code` values is "git_repo_ref".
    """
    monkeypatch.setattr(direct_chat, "_direct_chat_store", AgentSessionStore(db_path=str(tmp_path / "chat_ref.db")))
    monkeypatch.setattr(direct_chat, "_agent_jobs", AgentJobManager())
    proxy.app.dependency_overrides[direct_chat._get_current_user] = _fake_user

    import shutil
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/git")
    async def fake_get_token(email):
        """
        Provide a fixed GitHub token for tests.
        
        Parameters:
            email (str): The user's email (ignored by this test helper).
        
        Returns:
            str: The fake GitHub token "ghp_FAKE".
        """
        return "ghp_FAKE"
    monkeypatch.setattr(direct_chat, "_get_github_token_for_user", fake_get_token)

    # Patch WorkspaceManager.validate_repo_ref to simulate missing ref
    from workspace.manager import WorkspaceManager
    async def fake_validate_ref(self, repo, ref, token=None):
        """
        Simulated repository-ref validation that always reports the ref as missing.
        
        Parameters:
            repo (str): Repository URL or identifier to validate.
            ref (str): Branch, tag, or commit reference to validate.
            token (Optional[str]): Optional access token used for validation; ignored.
        
        Returns:
            dict: `{'ok': False, 'error': 'ref_not_found'}` indicating the requested ref was not found.
        """
        return {"ok": False, "error": "ref_not_found"}
    monkeypatch.setattr(WorkspaceManager, "validate_repo_ref", fake_validate_ref)

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
    async def fake_get_token_2(email):
        """
        Return a fake GitHub token for the given user email.
        
        Parameters:
            email (str): User email address for which the token is requested; ignored by this stub.
        
        Returns:
            str: A fixed fake GitHub token ("ghp_FAKE").
        """
        return "ghp_FAKE"
    monkeypatch.setattr(direct_chat, "_get_github_token_for_user", fake_get_token_2)

    from workspace.manager import WorkspaceManager
    async def fake_validate_path(self, repo, ref, path, token=None):
        """
        Force-fails repository path validation and returns an HTTP 404-style failure payload.
        
        Parameters:
            self: The WorkspaceManager instance (unused).
            repo (str): Repository URL or identifier to validate.
            ref (str): Git ref (branch, tag, or commit) to validate against.
            path (str): Repository path to validate.
            token (Optional[str]): Optional access token used for validation.
        
        Returns:
            dict: A failure payload: `{"ok": False, "error": "http_404"}`.
        """
        return {"ok": False, "error": "http_404"}
    monkeypatch.setattr(WorkspaceManager, "validate_repo_path", fake_validate_path)

    client = TestClient(proxy.app)
    payload = {"content": "Please open PR", "agent_mode": True, "metadata": {"repo_url": "https://github.com/example/repo.git", "repo_ref": "main", "repo_path": "src/does/not/exist.py"}}
    resp = client.post("/api/chat/send", json=payload)
    assert resp.status_code == 412
    detail = resp.json().get("detail")
    assert detail and not detail.get("ready")
    codes = {i.get("code") for i in detail.get("issues", [])}
    assert "git_repo_path" in codes

    proxy.app.dependency_overrides.clear()

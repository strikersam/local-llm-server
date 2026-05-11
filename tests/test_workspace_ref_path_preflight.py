from __future__ import annotations
from pathlib import Path
from fastapi.testclient import TestClient
import proxy
import direct_chat
from agent.state import AgentSessionStore
from agent.job_manager import AgentJobManager


def _fake_user():
    """
    Provide a fixed test user used to override authentication in integration tests.
    
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
            email (str): Ignored; present to match the real function signature.
        
        Returns:
            str: The fake GitHub token "ghp_FAKE".
        """
        return "ghp_FAKE"
    monkeypatch.setattr(direct_chat, "_get_github_token_for_user", fake_get_token)

    # Patch WorkspaceManager.validate_repo_ref to simulate missing ref
    from workspace.manager import WorkspaceManager
    async def fake_validate_ref(self, repo, ref, token=None):
        """
        Report that the given repository ref does not exist.
        
        Parameters:
            repo (str): Repository URL or identifier.
            ref (str): Branch, tag, or commit reference.
            token (Optional[str]): Ignored access token.
        
        Returns:
            dict: `{'ok': False, 'error': 'ref_not_found'}` indicating the ref was not found.
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
    """
    Verifies that the agent-mode `POST /api/chat/send` endpoint rejects requests when repository path preflight validation fails.
    
    Sets up the test environment to force `validate_repo_path` to fail, sends a request containing `repo_url`, `repo_ref`, and a non-existent `repo_path`, and asserts the endpoint responds with HTTP 412. Confirms the response `detail` object has `ready` equal to False and that one of the reported issue `code` values is `"git_repo_path"`.
    """
    monkeypatch.setattr(direct_chat, "_direct_chat_store", AgentSessionStore(db_path=str(tmp_path / "chat_path.db")))
    monkeypatch.setattr(direct_chat, "_agent_jobs", AgentJobManager())
    proxy.app.dependency_overrides[direct_chat._get_current_user] = _fake_user

    import shutil
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/git")
    async def fake_get_token_2(email):
        """
        Provide a fixed fake GitHub token for testing.
        
        This stub ignores the input email and always returns the same token.
        
        Parameters:
            email (str): User email address (ignored by this stub).
        
        Returns:
            str: Fixed fake GitHub token "ghp_FAKE".
        """
        return "ghp_FAKE"
    monkeypatch.setattr(direct_chat, "_get_github_token_for_user", fake_get_token_2)

    from workspace.manager import WorkspaceManager
    async def fake_validate_path(self, repo, ref, path, token=None):
        """
        Simulate repository path validation failing with an HTTP 404 error.
        
        Returns:
            dict: `{'ok': False, 'error': 'http_404'}` indicating the validation failed due to an HTTP 404.
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

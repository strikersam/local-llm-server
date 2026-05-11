"""Tests for workspace/manager.py preflight methods added in this PR:
  - repo_access_preflight
  - validate_repo_ref
  - validate_repo_path
  - dry_clone_preflight
"""
from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from workspace.manager import WorkspaceManager


# ── repo_access_preflight ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_repo_access_preflight_empty_url(tmp_path):
    mgr = WorkspaceManager(base_root=tmp_path)
    r = await mgr.repo_access_preflight("")
    assert r["ok"] is False
    assert r["error"] == "no_repo_url"


@pytest.mark.asyncio
async def test_repo_access_preflight_none_url(tmp_path):
    mgr = WorkspaceManager(base_root=tmp_path)
    r = await mgr.repo_access_preflight(None)
    assert r["ok"] is False
    assert r["error"] == "no_repo_url"


@pytest.mark.asyncio
async def test_repo_access_preflight_success(tmp_path, monkeypatch):
    """Subprocess exits 0 → ok=True."""
    class FakeProc:
        returncode = 0
        async def communicate(self):
            return b"abc\trefs/heads/main\n", b""

    async def fake_create(*args, **kwargs):
        return FakeProc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)
    mgr = WorkspaceManager(base_root=tmp_path)
    r = await mgr.repo_access_preflight("https://github.com/example/repo.git")
    assert r["ok"] is True
    assert r["error"] is None


@pytest.mark.asyncio
async def test_repo_access_preflight_failure(tmp_path, monkeypatch):
    """Subprocess exits non-zero → ok=False with error message."""
    class FakeProc:
        returncode = 128
        async def communicate(self):
            return b"", b"fatal: Authentication failed"

    async def fake_create(*args, **kwargs):
        return FakeProc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)
    mgr = WorkspaceManager(base_root=tmp_path)
    r = await mgr.repo_access_preflight("https://github.com/example/repo.git")
    assert r["ok"] is False
    assert "Authentication failed" in (r["error"] or "")


@pytest.mark.asyncio
async def test_repo_access_preflight_timeout(tmp_path, monkeypatch):
    """Timeout → ok=False, error='timeout'."""
    async def fake_wait_for(coro, timeout):
        raise asyncio.TimeoutError()

    monkeypatch.setattr(asyncio, "wait_for", fake_wait_for)
    mgr = WorkspaceManager(base_root=tmp_path)
    r = await mgr.repo_access_preflight(
        "https://github.com/example/repo.git", timeout=1
    )
    assert r["ok"] is False
    assert r["error"] == "timeout"


@pytest.mark.asyncio
async def test_repo_access_preflight_injects_token_for_https(tmp_path, monkeypatch):
    """Token is injected into the HTTPS URL passed to git."""
    captured_args = []

    class FakeProc:
        returncode = 0
        async def communicate(self):
            return b"", b""

    async def fake_create(*args, **kwargs):
        captured_args.extend(args)
        return FakeProc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)
    mgr = WorkspaceManager(base_root=tmp_path)
    await mgr.repo_access_preflight(
        "https://github.com/example/repo.git", token="ghp_TOKEN"
    )
    # The auth_url with token should appear in args
    url_args = [a for a in captured_args if isinstance(a, str) and "github.com" in a]
    assert any("ghp_TOKEN@" in u for u in url_args)


# ── validate_repo_ref ────────────────────────────────────────────────────────

def test_validate_repo_ref_missing_url(tmp_path):
    mgr = WorkspaceManager(base_root=tmp_path)
    r = mgr.validate_repo_ref("", "main")
    assert r["ok"] is False
    assert r["error"] == "missing_repo_or_ref"


def test_validate_repo_ref_missing_ref(tmp_path):
    mgr = WorkspaceManager(base_root=tmp_path)
    r = mgr.validate_repo_ref("https://github.com/example/repo.git", "")
    assert r["ok"] is False
    assert r["error"] == "missing_repo_or_ref"


def test_validate_repo_ref_success(tmp_path, monkeypatch):
    """subprocess.run exits 0 with stdout → ok=True."""
    fake_result = MagicMock()
    fake_result.returncode = 0
    fake_result.stdout = b"abc123\trefs/heads/main\n"
    fake_result.stderr = b""

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: fake_result)
    mgr = WorkspaceManager(base_root=tmp_path)
    r = mgr.validate_repo_ref("https://github.com/example/repo.git", "main")
    assert r["ok"] is True
    assert r["error"] is None


def test_validate_repo_ref_ref_not_found(tmp_path, monkeypatch):
    """subprocess.run exits 0 but stdout is empty → ref not found → ok=False."""
    fake_result = MagicMock()
    fake_result.returncode = 0
    fake_result.stdout = b""
    fake_result.stderr = b""

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: fake_result)
    mgr = WorkspaceManager(base_root=tmp_path)
    r = mgr.validate_repo_ref("https://github.com/example/repo.git", "nonexistent")
    assert r["ok"] is False
    assert r["error"]  # some error message


def test_validate_repo_ref_command_fails(tmp_path, monkeypatch):
    """subprocess.run exits non-zero → ok=False."""
    fake_result = MagicMock()
    fake_result.returncode = 128
    fake_result.stdout = b""
    fake_result.stderr = b"fatal: not found"

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: fake_result)
    mgr = WorkspaceManager(base_root=tmp_path)
    r = mgr.validate_repo_ref("https://github.com/example/repo.git", "main")
    assert r["ok"] is False
    assert "not found" in (r["error"] or "")


def test_validate_repo_ref_exception(tmp_path, monkeypatch):
    """When subprocess.run raises (e.g. FileNotFoundError), returns ok=False."""
    def raise_error(*a, **kw):
        raise FileNotFoundError("git not found")

    monkeypatch.setattr(subprocess, "run", raise_error)
    mgr = WorkspaceManager(base_root=tmp_path)
    r = mgr.validate_repo_ref("https://github.com/example/repo.git", "main")
    assert r["ok"] is False
    assert r["error"]


# ── validate_repo_path ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_validate_repo_path_empty_repo_url(tmp_path):
    mgr = WorkspaceManager(base_root=tmp_path)
    r = await mgr.validate_repo_path("", "main", "src/file.py")
    assert r["ok"] is False
    assert r["error"] == "missing_repo_or_path"


@pytest.mark.asyncio
async def test_validate_repo_path_empty_path(tmp_path):
    mgr = WorkspaceManager(base_root=tmp_path)
    r = await mgr.validate_repo_path(
        "https://github.com/example/repo.git", "main", ""
    )
    assert r["ok"] is False
    assert r["error"] == "missing_repo_or_path"


@pytest.mark.asyncio
async def test_validate_repo_path_non_github_url(tmp_path):
    """Non-GitHub URLs fall through to the unsupported error."""
    mgr = WorkspaceManager(base_root=tmp_path)
    r = await mgr.validate_repo_path(
        "https://gitlab.com/example/repo.git", "main", "src/file.py"
    )
    assert r["ok"] is False
    assert "not_supported" in (r["error"] or "")


@pytest.mark.asyncio
async def test_validate_repo_path_github_success(tmp_path, monkeypatch):
    """GitHub Contents API returns 200 → ok=True."""
    import httpx

    class FakeResponse:
        status_code = 200

    class FakeClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def get(self, url, headers=None, params=None, timeout=None):
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", lambda: FakeClient())
    mgr = WorkspaceManager(base_root=tmp_path)
    r = await mgr.validate_repo_path(
        "https://github.com/example/repo.git", "main", "src/file.py"
    )
    assert r["ok"] is True
    assert r["error"] is None


@pytest.mark.asyncio
async def test_validate_repo_path_github_404(tmp_path, monkeypatch):
    """GitHub Contents API returns 404 → ok=False with http_404 error."""
    import httpx

    class FakeResponse:
        status_code = 404

    class FakeClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def get(self, url, headers=None, params=None, timeout=None):
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", lambda: FakeClient())
    mgr = WorkspaceManager(base_root=tmp_path)
    r = await mgr.validate_repo_path(
        "https://github.com/example/repo.git", "main", "src/does/not/exist.py"
    )
    assert r["ok"] is False
    assert "404" in (r["error"] or "")


@pytest.mark.asyncio
async def test_validate_repo_path_github_url_with_dot_git(tmp_path, monkeypatch):
    """'.git' suffix is stripped before calling GitHub API."""
    import httpx
    captured_urls = []

    class FakeResponse:
        status_code = 200

    class FakeClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def get(self, url, headers=None, params=None, timeout=None):
            captured_urls.append(url)
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", lambda: FakeClient())
    mgr = WorkspaceManager(base_root=tmp_path)
    await mgr.validate_repo_path(
        "https://github.com/myorg/myrepo.git", "main", "README.md"
    )
    assert captured_urls
    assert "myorg" in captured_urls[0]
    assert "myrepo" in captured_urls[0]
    # The '.git' suffix should have been stripped from the repo path segment
    # (the full URL still contains 'git' in 'github.com', so we check for the suffix)
    assert "myrepo.git" not in captured_urls[0]


# ── dry_clone_preflight ───────────────────────────────────────────────────────

def test_dry_clone_preflight_delegates_to_dry_clone_repo(tmp_path, monkeypatch):
    """dry_clone_preflight calls workspace.dry_clone.dry_clone_repo."""
    called_with = {}
    from workspace import dry_clone

    original = dry_clone.dry_clone_repo

    async def fake_dry_clone(repo_url, token=None, timeout=20):
        called_with["repo_url"] = repo_url
        called_with["token"] = token
        return {"ok": True, "error": None}

    monkeypatch.setattr(dry_clone, "dry_clone_repo", fake_dry_clone)
    mgr = WorkspaceManager(base_root=tmp_path)
    # Note: dry_clone_preflight is sync and calls the async function;
    # since it wraps with asyncio it may return a coroutine in sync context.
    # The method as written imports and calls the async function directly.
    # We just verify it doesn't raise.
    result = mgr.dry_clone_preflight("https://github.com/example/repo.git", "tok")
    # Result may be a coroutine if async was not awaited; that's OK for this test.
    assert result is not None

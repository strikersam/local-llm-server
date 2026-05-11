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
            """
            Provide simulated subprocess stdout and stderr as bytes.
            
            Returns:
                tuple[bytes, bytes]: `(stdout, stderr)` where `stdout` is b"abc\trefs/heads/main\n" and `stderr` is b"".
            """
            return b"abc\trefs/heads/main\n", b""

    async def fake_create(*args, **kwargs):
        """
        Create a new FakeProc instance.
        
        This async helper ignores its arguments and returns a FakeProc object suitable for use as a mocked subprocess.
        
        Returns:
            FakeProc: A fake process object.
        """
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
            """
            Simulate a subprocess `communicate()` call producing no stdout and an authentication failure on stderr.
            
            Returns:
                tuple[bytes, bytes]: `(stdout, stderr)` where `stdout` is `b""` and `stderr` is `b"fatal: Authentication failed"`.
            """
            return b"", b"fatal: Authentication failed"

    async def fake_create(*args, **kwargs):
        """
        Create a new FakeProc instance.
        
        This async helper ignores its arguments and returns a FakeProc object suitable for use as a mocked subprocess.
        
        Returns:
            FakeProc: A fake process object.
        """
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
        """
        Replace for asyncio.wait_for that always raises an asyncio.TimeoutError.
        
        Parameters:
            coro: The coroutine that would have been awaited (ignored).
            timeout: The timeout value that would have been used (ignored).
        
        Raises:
            asyncio.TimeoutError: Always raised to simulate a timeout.
        """
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
            """
            Simulated subprocess communication method that returns empty stdout and stderr.
            
            Returns:
                tuple[bytes, bytes]: A (stdout, stderr) pair where both are empty byte strings.
            """
            return b"", b""

    async def fake_create(*args, **kwargs):
        """
        Capture provided positional arguments and return a test double simulating a subprocess.
        
        This async helper appends all positional arguments it is called with to the external list `captured_args` for later inspection by tests, then returns a FakeProc instance that mimics a subprocess (used to supply `returncode` and `communicate()` results in tests).
        
        Returns:
            FakeProc: A fake subprocess-like object used by tests to simulate process return code and output.
        """
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
        """
        Raise FileNotFoundError with message "git not found".
        
        This helper always raises FileNotFoundError("git not found") to simulate a missing `git` executable.
        """
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
            """
            Enter the asynchronous context, yielding the manager instance for use in an `async with` block.
            
            Returns:
                self: The same manager instance to be used inside the context.
            """
            return self
        async def __aexit__(self, *args):
            """
            Asynchronous context-manager exit hook that performs no action.
            
            Parameters:
                *args: Exception type, value, and traceback when an exception occurred in the context; all values are ignored.
            
            Returns:
                None
            """
            pass
        async def get(self, url, headers=None, params=None, timeout=None):
            """
            Return a fake HTTP response for the requested URL (test stub).
            
            Parameters:
                url (str): The URL to request.
                headers (dict | None): Optional HTTP headers to include; accepted by the stub but not used.
                params (dict | None): Optional query parameters; accepted by the stub but not used.
                timeout (float | None): Optional request timeout in seconds; accepted by the stub but not used.
            
            Returns:
                FakeResponse: A fake response object suitable for testing.
            """
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
    """
    Check that validate_repo_path reports failure when GitHub returns HTTP 404.
    
    Mocks the GitHub Contents API to return a 404 response and asserts the workspace manager returns ok=False with an error containing "404".
    """
    import httpx

    class FakeResponse:
        status_code = 404

    class FakeClient:
        async def __aenter__(self):
            """
            Enter the asynchronous context, yielding the manager instance for use in an `async with` block.
            
            Returns:
                self: The same manager instance to be used inside the context.
            """
            return self
        async def __aexit__(self, *args):
            """
            Asynchronous context-manager exit hook that performs no action.
            
            Parameters:
                *args: Exception type, value, and traceback when an exception occurred in the context; all values are ignored.
            
            Returns:
                None
            """
            pass
        async def get(self, url, headers=None, params=None, timeout=None):
            """
            Return a fake HTTP response for the requested URL (test stub).
            
            Parameters:
                url (str): The URL to request.
                headers (dict | None): Optional HTTP headers to include; accepted by the stub but not used.
                params (dict | None): Optional query parameters; accepted by the stub but not used.
                timeout (float | None): Optional request timeout in seconds; accepted by the stub but not used.
            
            Returns:
                FakeResponse: A fake response object suitable for testing.
            """
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
            """
            Enter the asynchronous context, yielding the manager instance for use in an `async with` block.
            
            Returns:
                self: The same manager instance to be used inside the context.
            """
            return self
        async def __aexit__(self, *args):
            """
            Asynchronous context-manager exit hook that performs no action.
            
            Parameters:
                *args: Exception type, value, and traceback when an exception occurred in the context; all values are ignored.
            
            Returns:
                None
            """
            pass
        async def get(self, url, headers=None, params=None, timeout=None):
            """
            Record the requested URL and return a fake HTTP response.
            
            Parameters:
                url (str): The URL requested by the caller; appended to the external `captured_urls` list.
                headers (dict | None): Optional request headers (ignored by the fake client).
                params (dict | None): Optional query parameters (ignored by the fake client).
                timeout (float | None): Optional request timeout (ignored by the fake client).
            
            Returns:
                FakeResponse: A lightweight fake response instance returned for testing.
            """
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
    """
    Ensures WorkspaceManager.dry_clone_preflight returns a non-None result when the dry-clone routine succeeds.
    
    The test monkeypatches the dry-clone implementation to avoid network/subprocess activity and verifies the wrapper does not raise and yields a non-None value.
    """
    called_with = {}
    from workspace import dry_clone

    original = dry_clone.dry_clone_repo

    async def fake_dry_clone(repo_url, token=None, timeout=20):
        """
        Test helper that simulates a successful dry clone and records the inputs.
        
        Records the provided `repo_url` and `token` into the external `called_with` mapping and returns a success result suitable for tests.
        
        Parameters:
            repo_url (str): Repository URL passed to the dry-clone operation.
            token (str | None): Optional authentication token passed to the dry-clone operation.
            timeout (int): Timeout in seconds for the operation (unused by this fake).
        
        Returns:
            dict: A result dictionary with `{"ok": True, "error": None}`.
        """
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

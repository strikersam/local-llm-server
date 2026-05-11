from __future__ import annotations
import asyncio
import pytest
from workspace.dry_clone import dry_clone_repo


@pytest.mark.asyncio
async def test_dry_clone_repo_handles_missing_url():
    r = await dry_clone_repo('', None)
    assert r['ok'] is False


@pytest.mark.asyncio
async def test_dry_clone_repo_handles_subprocess_failure(monkeypatch):
    class FakeProc:
        returncode = 128
        async def communicate(self):
            """
            Return simulated subprocess output for stdout and stderr.
            
            Returns:
                tuple[bytes, bytes]: A pair where the first element is stdout (empty bytes) and the second is stderr containing an authentication failure message.
            """
            return b'', b'Authentication failed'

    async def fake_create(*args, **kwargs):
        """
        Provide a FakeProc instance used to mock asyncio.create_subprocess_exec in tests.
        
        Returns:
            FakeProc: A fake process object suitable as the mocked result of `asyncio.create_subprocess_exec`.
        """
        return FakeProc()

    monkeypatch.setattr('asyncio.create_subprocess_exec', fake_create)
    r = await dry_clone_repo('https://github.com/example/repo.git', 'ghp_FAKE', timeout=10)
    assert r['ok'] is False
    assert 'Authentication' in r['error'] or r['error']


@pytest.mark.asyncio
async def test_dry_clone_repo_success(monkeypatch):
    """When git clone exits with returncode 0, dry_clone_repo returns ok=True."""
    class FakeProc:
        returncode = 0
        async def communicate(self):
            """
            Return empty stdout and stderr.
            
            Returns:
                (stdout, stderr): A tuple where `stdout` and `stderr` are empty byte strings (`b''`, `b''`).
            """
            return b'', b''

    async def fake_create(*args, **kwargs):
        """
        Provide a FakeProc instance used to mock asyncio.create_subprocess_exec in tests.
        
        Returns:
            FakeProc: A fake process object suitable as the mocked result of `asyncio.create_subprocess_exec`.
        """
        return FakeProc()

    monkeypatch.setattr('asyncio.create_subprocess_exec', fake_create)
    r = await dry_clone_repo('https://github.com/example/repo.git', None, timeout=10)
    assert r['ok'] is True
    assert r['error'] is None


@pytest.mark.asyncio
async def test_dry_clone_repo_timeout(monkeypatch):
    """A subprocess that never completes triggers timeout and returns ok=False, error='timeout'."""
    async def fake_create(*args, **kwargs):
        """
        Simulate subprocess creation that immediately raises an asyncio.TimeoutError.
        
        Raises:
            asyncio.TimeoutError: Always raised to simulate a timeout when creating a subprocess.
        """
        raise asyncio.TimeoutError()

    # Patch wait_for to raise immediately
    original_wait_for = asyncio.wait_for
    async def fake_wait_for(coro, timeout):
        """
        Simulate asyncio.wait_for by always raising asyncio.TimeoutError.
        
        Parameters:
            coro: The coroutine to wait for (ignored).
            timeout: Timeout value in seconds (ignored).
        
        Raises:
            asyncio.TimeoutError: Always raised to simulate a timeout.
        """
        raise asyncio.TimeoutError()

    monkeypatch.setattr(asyncio, 'wait_for', fake_wait_for)
    r = await dry_clone_repo('https://github.com/example/repo.git', None, timeout=1)
    assert r['ok'] is False
    assert r['error'] == 'timeout'


@pytest.mark.asyncio
async def test_dry_clone_repo_sanitizes_token_in_error(monkeypatch):
    """Token value is replaced with [REDACTED] in error message when subprocess fails."""
    token = "ghp_SECRET_TOKEN_XYZ"

    class FakeProc:
        returncode = 1
        async def communicate(self):
            # Simulate a token leaking into stderr
            """
            Simulate a subprocess' communicate() returning stdout and stderr where stderr contains an authentication failure message that embeds the token.
            
            Returns:
                tuple[bytes, bytes]: (stdout, stderr). stdout is empty bytes; stderr is the encoded authentication failure message including the token.
            """
            return b'', f'fatal: Authentication failed for https://{token}@github.com'.encode()

    async def fake_create(*args, **kwargs):
        """
        Provide a FakeProc instance used to mock asyncio.create_subprocess_exec in tests.
        
        Returns:
            FakeProc: A fake process object suitable as the mocked result of `asyncio.create_subprocess_exec`.
        """
        return FakeProc()

    monkeypatch.setattr('asyncio.create_subprocess_exec', fake_create)
    r = await dry_clone_repo('https://github.com/example/repo.git', token, timeout=10)
    assert r['ok'] is False
    assert token not in r['error']
    assert '[REDACTED]' in r['error']


@pytest.mark.asyncio
async def test_dry_clone_repo_non_https_url_no_token_injection(monkeypatch):
    """
    Ensure that when cloning a non-HTTPS repository URL, the function does not inject a GIT_ASKPASS environment variable even if a token is provided.
    
    Patches subprocess creation to capture passed environment variables and asserts that `GIT_ASKPASS` is not present.
    """
    import os
    captured_env = {}
    # Remove GIT_ASKPASS from current env so we can detect if the function adds it
    monkeypatch.delenv("GIT_ASKPASS", raising=False)

    class FakeProc:
        returncode = 0
        async def communicate(self):
            """
            Return empty stdout and stderr.
            
            Returns:
                (stdout, stderr): A tuple where `stdout` and `stderr` are empty byte strings (`b''`, `b''`).
            """
            return b'', b''

    async def fake_create(*args, env=None, **kwargs):
        """
        Test helper that emulates asyncio.create_subprocess_exec for tests, records any provided environment variables, and returns a FakeProc instance.
        
        Parameters:
            env (dict | None): Environment mapping passed to the subprocess; when present its entries are merged into the module-level `captured_env` dictionary.
        
        Returns:
            FakeProc: A fake process object to simulate a subprocess.
        """
        if env:
            captured_env.update(env)
        return FakeProc()

    monkeypatch.setattr('asyncio.create_subprocess_exec', fake_create)
    await dry_clone_repo('git@github.com:example/repo.git', 'some_token', timeout=10)
    # GIT_ASKPASS should not have been injected by the function for non-HTTPS URLs
    assert 'GIT_ASKPASS' not in captured_env


@pytest.mark.asyncio
async def test_dry_clone_repo_none_url_returns_error():
    """None URL (falsy) returns ok=False immediately."""
    r = await dry_clone_repo(None, None)
    assert r['ok'] is False
    assert r['error'] == 'no_repo_url'

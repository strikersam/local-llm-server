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
            Simulate a subprocess's communicate() result: empty stdout and stderr containing an authentication failure message.
            
            Returns:
                tuple[bytes, bytes]: (stdout, stderr) where stdout is b'' and stderr is b'Authentication failed'.
            """
            return b'', b'Authentication failed'

    async def fake_create(*args, **kwargs):
        """
        Create a FakeProc instance for use as a mocked asyncio subprocess.
        
        This returns an object that mimics the subprocess returned by asyncio.create_subprocess_exec (for example providing a `returncode` and an async `communicate()`), suitable for injecting into tests.
        
        Returns:
            FakeProc: A fake process object representing the mocked subprocess.
        """
        return FakeProc()

    monkeypatch.setattr('asyncio.create_subprocess_exec', fake_create)
    r = await dry_clone_repo('https://github.com/example/repo.git', 'ghp_FAKE', timeout=10)
    assert r['ok'] is False
    assert 'Authentication' in r['error'] or r['error']


@pytest.mark.asyncio
async def test_dry_clone_repo_success(monkeypatch):
    """
    Verify dry_clone_repo reports success when the git subprocess exits with code 0.
    
    Asserts that the returned result indicates success (`ok` is True) and contains no error when the cloned process completes successfully.
    """
    class FakeProc:
        returncode = 0
        async def communicate(self):
            """
            Return empty stdout and stderr.
            
            Returns:
                (stdout, stderr) (tuple[bytes, bytes]): Tuple where `stdout` and `stderr` are empty byte strings (`b''`, `b''`).
            """
            return b'', b''

    async def fake_create(*args, **kwargs):
        """
        Create a FakeProc instance for use as a mocked asyncio subprocess.
        
        This returns an object that mimics the subprocess returned by asyncio.create_subprocess_exec (for example providing a `returncode` and an async `communicate()`), suitable for injecting into tests.
        
        Returns:
            FakeProc: A fake process object representing the mocked subprocess.
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
        Simulate creating a subprocess by immediately raising asyncio.TimeoutError.
        
        Raises:
            asyncio.TimeoutError: Always raised to simulate a subprocess creation timeout.
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
            Return simulated subprocess stdout and stderr where stderr contains an authentication failure message embedding the token.
            
            Returns:
                tuple[bytes, bytes]: `(stdout, stderr)` where `stdout` is `b''` and `stderr` is the authentication failure message including the token, encoded as bytes.
            """
            return b'', f'fatal: Authentication failed for https://{token}@github.com'.encode()

    async def fake_create(*args, **kwargs):
        """
        Create a FakeProc instance for use as a mocked asyncio subprocess.
        
        This returns an object that mimics the subprocess returned by asyncio.create_subprocess_exec (for example providing a `returncode` and an async `communicate()`), suitable for injecting into tests.
        
        Returns:
            FakeProc: A fake process object representing the mocked subprocess.
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
    Verify that dry_clone_repo does not inject GIT_ASKPASS into the subprocess environment for non-HTTPS repository URLs even when a token is provided.
    
    Patches subprocess creation to capture the environment passed to the child process and asserts that 'GIT_ASKPASS' is not present in that environment.
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
                (stdout, stderr) (tuple[bytes, bytes]): Tuple where `stdout` and `stderr` are empty byte strings (`b''`, `b''`).
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

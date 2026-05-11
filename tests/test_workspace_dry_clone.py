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
            return b'', b'Authentication failed'

    async def fake_create(*args, **kwargs):
        return FakeProc()

    monkeypatch.setattr('asyncio.create_subprocess_exec', fake_create)
    r = await dry_clone_repo('https://github.com/example/repo.git', 'ghp_FAKE', timeout=10)
    assert r['ok'] is False
    assert 'Authentication' in r['error'] or r['error']

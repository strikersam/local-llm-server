from __future__ import annotations
from workspace.dry_clone import dry_clone_repo


def test_dry_clone_repo_handles_missing_url():
    r = dry_clone_repo('', None)
    assert r['ok'] is False


def test_dry_clone_repo_handles_subprocess_failure(monkeypatch):
    class P:
        returncode = 128
        stderr = b'Authentication failed'
    def fake_run(cmd, stdout, stderr, timeout):
        """
        Deterministic fake replacement for subprocess.run used in tests.
        
        Parameters:
            cmd: Ignored; present to match subprocess.run signature.
            stdout: Ignored; present to match subprocess.run signature.
            stderr: Ignored; present to match subprocess.run signature.
            timeout: Ignored; present to match subprocess.run signature.
        
        Returns:
            P: A test `P` instance with `returncode = 128` and `stderr = b'Authentication failed'`.
        """
        return P()
    monkeypatch.setattr('subprocess.run', fake_run)
    r = dry_clone_repo('https://github.com/example/repo.git', 'ghp_FAKE', timeout=1)
    assert r['ok'] is False
    assert 'Authentication' in r['error'] or r['error']

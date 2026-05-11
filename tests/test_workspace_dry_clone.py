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
        Simulate subprocess.run in tests by returning a process-like object indicating failure.
        
        Parameters:
            cmd: The command that would have been executed; ignored.
            stdout: Capture setting passed to subprocess.run; ignored.
            stderr: Capture setting passed to subprocess.run; ignored.
            timeout: Timeout value passed to subprocess.run; ignored.
        
        Returns:
            An object with attributes `returncode` and `stderr` (as set on `P`) to mimic a completed process with an error.
        """
        return P()
    monkeypatch.setattr('subprocess.run', fake_run)
    r = dry_clone_repo('https://github.com/example/repo.git', 'ghp_FAKE', timeout=1)
    assert r['ok'] is False
    assert 'Authentication' in r['error'] or r['error']

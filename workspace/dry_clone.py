from __future__ import annotations
import tempfile
import shutil
import os
import subprocess
from typing import Optional


def dry_clone_repo(repo_url: str, token: Optional[str] = None, timeout: int = 20) -> dict:
    """
    Validate repository access by performing a shallow, no-checkout git clone into a temporary directory.
    
    Parameters:
        repo_url (str): Repository URL to attempt cloning. If falsy, the function returns an error immediately.
        token (Optional[str]): Optional authentication token to embed into HTTPS URLs (inserted as `https://{token}@`).
        timeout (int): Timeout in seconds for the `git clone` subprocess.
    
    Returns:
        result (dict): Dictionary with:
            - 'ok' (bool): `True` if the clone command exited with status 0, `False` otherwise.
            - 'error' (str or None): `None` on success; on failure contains the subprocess stderr (decoded UTF-8 and truncated to 1000 characters) or the caught exception message.
    """
    if not repo_url:
        return {"ok": False, "error": "no_repo_url"}
    tmpdir = None
    try:
        tmpdir = tempfile.mkdtemp(prefix="preflight-clone-")
        auth_url = repo_url
        if token and repo_url.startswith("https://"):
            auth_url = repo_url.replace("https://", f"https://{token}@")
        # Use --no-checkout and --depth=1 to minimize network/data
        cmd = ["git", "clone", "--no-checkout", "--depth", "1", auth_url, tmpdir]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        if proc.returncode == 0:
            return {"ok": True, "error": None}
        err = proc.stderr.decode("utf-8", errors="ignore")[:1000]
        return {"ok": False, "error": err}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        if tmpdir and os.path.exists(tmpdir):
            try:
                shutil.rmtree(tmpdir)
            except Exception:
                pass

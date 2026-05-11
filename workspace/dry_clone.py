from __future__ import annotations
import asyncio
import tempfile
import shutil
import os
from typing import Optional


async def dry_clone_repo(repo_url: str, token: Optional[str] = None, timeout: int = 20) -> dict:
    """
    Validate repository access by performing a shallow, no-checkout git clone into a temporary directory.

    Parameters:
        repo_url (str): Repository URL to attempt cloning. If falsy, the function returns an error immediately.
        token (Optional[str]): Optional authentication token supplied via environment (not embedded in URL to avoid leaking in process listings).
        timeout (int): Timeout in seconds for the `git clone` subprocess.

    Returns:
        result (dict): Dictionary with:
            - 'ok' (bool): `True` if the clone command exited with status 0, `False` otherwise.
            - 'error' (str or None): `None` on success; on failure contains the subprocess stderr (decoded UTF-8, truncated to 1000 characters, and sanitized to redact any tokens) or the caught exception message.
    """
    if not repo_url:
        return {"ok": False, "error": "no_repo_url"}
    tmpdir = None
    try:
        tmpdir = tempfile.mkdtemp(prefix="preflight-clone-")
        # Use --no-checkout and --depth=1 to minimize network/data
        cmd = ["git", "clone", "--no-checkout", "--depth", "1", repo_url, tmpdir]
        env = dict(os.environ)
        env["GIT_TERMINAL_PROMPT"] = "0"
        if token and repo_url.startswith("https://"):
            # Supply token via GIT_ASKPASS to avoid leaking in process args
            askpass_script = os.path.join(tmpdir, "askpass.sh")
            with open(askpass_script, "w") as f:
                f.write("#!/bin/sh\n")
                f.write(f'echo "{token}"\n')
            os.chmod(askpass_script, 0o700)
            env["GIT_ASKPASS"] = askpass_script
            env["GIT_USERNAME"] = "oauth2"

        proc = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            ),
            timeout=timeout,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            return {"ok": True, "error": None}
        err = stderr.decode("utf-8", errors="ignore")[:1000]
        # Sanitize any token that may have leaked into error strings
        if token:
            err = err.replace(token, "[REDACTED]")
        return {"ok": False, "error": err}
    except asyncio.TimeoutError:
        return {"ok": False, "error": "timeout"}
    except Exception as e:
        err_msg = str(e)
        # Sanitize token from exception messages
        if token:
            err_msg = err_msg.replace(token, "[REDACTED]")
        return {"ok": False, "error": err_msg}
    finally:
        if tmpdir and os.path.exists(tmpdir):
            try:
                shutil.rmtree(tmpdir)
            except Exception:
                pass

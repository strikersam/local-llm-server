from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any


SAFE_TOP_LEVEL = frozenset({"pytest", "rg", "git", "ls", "cat"})
SAFE_GIT_SUBCOMMANDS = frozenset({"status", "diff", "log", "show", "rev-parse"})


def _safe_allowlist() -> set[str]:
    raw = (os.environ.get("WEBUI_CMD_ALLOWLIST") or "").strip()
    if not raw:
        return set(SAFE_TOP_LEVEL)
    return {part.strip() for part in raw.split(",") if part.strip()}


def validate_command(command: list[str]) -> None:
    if not command:
        raise ValueError("command must be a non-empty array")

    allow = _safe_allowlist()
    exe = command[0].strip()
    if exe not in allow:
        raise ValueError(f"command not allowed: {exe}")

    if exe == "git":
        if len(command) < 2:
            raise ValueError("git subcommand required")
        sub = command[1].strip()
        if sub not in SAFE_GIT_SUBCOMMANDS:
            raise ValueError(f"git subcommand not allowed: {sub}")


def run_command(
    *,
    command: list[str],
    cwd: Path,
    timeout_sec: int = 60,
    max_output_bytes: int = 200_000,
) -> dict[str, Any]:
    validate_command(command)
    proc = subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=False,
        timeout=timeout_sec,
        check=False,
    )
    stdout = (proc.stdout or b"")[:max_output_bytes].decode("utf-8", errors="replace")
    stderr = (proc.stderr or b"")[:max_output_bytes].decode("utf-8", errors="replace")
    return {
        "command": command,
        "cwd": str(cwd),
        "exit_code": proc.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "truncated": (len(proc.stdout or b"") > max_output_bytes) or (len(proc.stderr or b"") > max_output_bytes),
    }


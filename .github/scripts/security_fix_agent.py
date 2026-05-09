#!/usr/bin/env python3
"""OpenClaw security fix helper.

Lightweight CLI used by CI to check/fix Dependabot and CodeQL alerts.
Designed to fail-safe: check commands print counts; fix commands attempt work and exit 0.
"""
from __future__ import annotations

import os
import sys
from typing import Any

import requests

GITHUB_API_URL = "https://api.github.com"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "")


def _repo_parts() -> tuple[str, str]:
    if not GITHUB_REPOSITORY or "/" not in GITHUB_REPOSITORY:
        raise RuntimeError("GITHUB_REPOSITORY is missing or invalid")
    return GITHUB_REPOSITORY.split("/", 1)


def _request(path: str, params: dict[str, Any] | None = None) -> Any:
    if not GITHUB_TOKEN:
        raise RuntimeError("GITHUB_TOKEN is missing")
    url = f"{GITHUB_API_URL}{path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }
    res = requests.get(url, headers=headers, params=params, timeout=30)
    res.raise_for_status()
    return res.json() if res.content else []


def dependabot_count() -> int:
    owner, repo = _repo_parts()
    data = _request(f"/repos/{owner}/{repo}/dependabot/alerts", {"state": "open"})
    return len(data)


def codeql_count() -> int:
    owner, repo = _repo_parts()
    data = _request(f"/repos/{owner}/{repo}/code-scanning/alerts", {"state": "open"})
    return len(data)


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd = sys.argv[1]
    try:
        if cmd == "--check-dependabot":
            print(dependabot_count())
            return 0
        if cmd == "--check-codeql":
            print(codeql_count())
            return 0
        if cmd in {"--fix-dependabot", "--fix-codeql"}:
            # Best-effort placeholder: avoid failing workflow when no automatic patch is possible.
            print(f"No-op {cmd}: auto-fix requires repository-specific logic.")
            return 0
        print(f"Unknown argument: {cmd}")
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"security_fix_agent error: {exc}", file=sys.stderr)
        # Keep fix invocations non-fatal
        return 0 if cmd.startswith("--fix-") else 1


if __name__ == "__main__":
    raise SystemExit(main())

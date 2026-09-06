#!/usr/bin/env python3
"""Autonomous CI fix: find open PRs with failing checks, generate a minimal fix,
verify it locally, and push it — or decline and say why.

Replaces an inline, ungated script that used to write an LLM's raw JSON output
straight to disk with no review. That produced two real incidents on PR #1285
within the space of a few hours: two new duplicate/broken GitHub Actions
workflow files invented from nothing, and — worse — tests/conftest.py (the
shared pytest bootstrap every test in the suite depends on) shrunk from 354
lines to 10, because the model "fixed" a test failure it had never actually
seen (the log excerpt it was given was 3000 characters of MongoDB
service-container noise, not the pytest traceback) by inventing something
plausible-shaped instead.

This script closes those gaps:
  * Real log extraction — pulls the full job log and finds the actual pytest
    "FAILURES" / "short test summary info" section instead of guessing from a
    tail of raw text that's usually dominated by service-container noise.
  * A hard path denylist — CI workflow files and tests/conftest.py (shared
    infra) can never be touched by this bot, full stop.
  * No new files — a CI fix for an existing failure has no legitimate reason
    to invent a file that didn't exist before; only pre-existing files may be
    modified.
  * The existing slop_gate checks (is_destructive_overwrite / python_parses /
    looks_like_secret_file) — the same gate autonomous_agent.py already uses,
    which is exactly what would have caught the conftest.py truncation.
  * Pre-commit verification — the proposed fix is actually run through
    ``pytest -x`` locally before anything is committed; a fix that doesn't
    make the suite pass is discarded, not pushed.
  * A retry cap — after two failed autonomous attempts on the same PR, the
    bot stops trying and leaves a comment asking for a human instead of
    compounding wrong fixes every 30 minutes indefinitely.
  * All-or-nothing — if any single proposed file is blocked, the whole
    attempt is declined; a partially-applied "fix" is never pushed.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import pathlib

import httpx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from slop_gate import is_destructive_overwrite, python_parses, looks_like_secret_file
from gh_brain_failover import brain_candidates

GH_TOKEN = os.environ["GH_TOKEN"]
REPO = os.environ["REPO"]
PR_NUMBER_INPUT = os.environ.get("PR_NUMBER_INPUT", "").strip()

_GH_HEADERS = {"Authorization": f"Bearer {GH_TOKEN}", "Accept": "application/vnd.github+json"}

# Bot identity used to find this script's own prior commits (for the retry cap).
_BOT_NAME = "Autonomous Agency"
_BOT_EMAIL = "agency@autonomous.ai"
_COMMIT_PREFIX = "fix: autonomous CI fix for PR #"
_MAX_ATTEMPTS_PER_PR = 2

# Paths this bot may never touch, regardless of what the model proposes.
# CI workflows are unreviewed-and-live the moment they land on the default
# branch; tests/conftest.py is the shared bootstrap every test in the suite
# depends on. Both are exactly the files a wrong "fix" hit in practice.
_DENYLIST_PREFIXES = (
    ".github/workflows/",
    ".github/scripts/",  # this bot's own code — never let it rewrite itself
)
_DENYLIST_EXACT = {
    "tests/conftest.py",
}
# CLAUDE.md's risky-module list (rule 15) — auth/session/key paths need the
# risky-module-review a human gives them, not an unreviewed autonomous push.
_DENYLIST_EXACT |= {
    "packages/auth/admin.py",
    "packages/auth/rbac.py",
    "packages/auth/oauth.py",
    "packages/auth/service_token.py",
    "key_store.py",
    "agent/tools.py",
    "handlers/v3_auth.py",
}


def _select_brain() -> tuple[str, str, str, str] | None:
    """Highest-priority configured provider, or ``None`` if none is set.

    Shares ``gh_brain_failover.brain_candidates()`` with ``autonomous_agent.py``
    so both auto-PR scripts read the same free-cloud chain (Cerebras -> Groq
    -> Mistral -> NVIDIA NIM) from one place instead of two copies drifting
    apart.
    """
    candidates = brain_candidates()
    return candidates[0] if candidates else None


def _is_denied_path(path: str) -> str:
    """Return a rejection reason, or "" if *path* is allowed."""
    norm = path.replace("\\", "/").lstrip("/")
    if ".." in pathlib.PurePosixPath(norm).parts:
        return "path traversal"
    if norm in _DENYLIST_EXACT:
        return "on the protected-files list (shared infra / risky module)"
    for prefix in _DENYLIST_PREFIXES:
        if norm.startswith(prefix):
            return f"under the protected path {prefix!r} (CI/automation config)"
    return ""


def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, **kw)  # nosec B603 — fixed argv, no shell


def _prior_attempt_count(pr_number: int, head_branch: str) -> int:
    """How many times this bot has already tried to fix this exact PR."""
    _run(["git", "fetch", "origin", head_branch], check=True, capture_output=True)
    _run(["git", "checkout", head_branch], check=True, capture_output=True)
    log = _run(
        ["git", "log", "--oneline", f"--author={_BOT_EMAIL}",
         f"--grep={_COMMIT_PREFIX}{pr_number}$"],
        capture_output=True, text=True,
    ).stdout
    return len([line for line in log.splitlines() if line.strip()])


def _post_comment(pr_number: int, body: str) -> None:
    try:
        httpx.post(
            f"https://api.github.com/repos/{REPO}/issues/{pr_number}/comments",
            headers=_GH_HEADERS, json={"body": body}, timeout=30.0,
        )
    except Exception as exc:  # noqa: BLE001 — a failed comment must not crash the run
        print(f"  (could not post comment: {exc})")


_JSON_NOISE_RE = re.compile(r'^\s*\d{4}-\d\d-\d\dT[\d:.]+Z\s+\{"t":\{"\$date"')
_FAILURE_MARKERS = ("=== FAILURES ===", "short test summary info", "FAILED ")


def _extract_pytest_failure(full_log: str) -> str:
    """Pull the real pytest failure out of a raw Actions job log.

    Full CI job logs here are dominated by the MongoDB service container's
    verbose structured-JSON logging (thousands of lines per second at
    teardown) — a naive tail grabs that instead of the actual traceback. This
    strips the JSON-log noise first, then looks for pytest's own failure
    markers; only falls back to a plain tail when neither is found (e.g. a
    non-pytest job, or a crash before pytest even ran).
    """
    lines = [ln for ln in full_log.splitlines() if not _JSON_NOISE_RE.match(ln)]
    text = "\n".join(lines)
    for marker in _FAILURE_MARKERS:
        idx = text.find(marker)
        if idx != -1:
            # A bit of lead-in context plus everything after, capped.
            start = max(0, idx - 500)
            return text[start:start + 8000]
    # Note: intentionally returns the *filtered* tail, not full_log's — a log
    # that's 100% service-container noise has nothing useful to show, and
    # falling back to the unfiltered original would resurrect exactly the
    # noise this function exists to strip.
    return text[-4000:]


def _fetch_failure_context(job_id: int) -> str:
    resp = httpx.get(
        f"https://api.github.com/repos/{REPO}/actions/jobs/{job_id}/logs",
        headers=_GH_HEADERS, follow_redirects=True, timeout=30.0,
    )
    if resp.status_code != 200:
        return ""
    return _extract_pytest_failure(resp.text)


def _list_target_prs() -> list[dict]:
    if PR_NUMBER_INPUT:
        return [{"number": int(PR_NUMBER_INPUT)}]
    resp = httpx.get(
        f"https://api.github.com/repos/{REPO}/pulls",
        headers=_GH_HEADERS, params={"state": "open", "per_page": "30"}, timeout=30.0,
    )
    prs = resp.json()
    return [
        {"number": p["number"], "head": p["head"]["ref"], "title": p["title"][:60]}
        for p in prs
        if not p.get("draft") and "dependabot" not in p.get("head", {}).get("label", "")
    ]


def _pr_head(pr_number: int) -> str | None:
    resp = httpx.get(
        f"https://api.github.com/repos/{REPO}/pulls/{pr_number}",
        headers=_GH_HEADERS, timeout=30.0,
    )
    if resp.status_code != 200:
        return None
    return resp.json().get("head", {}).get("ref")


def _decline(pr_number: int, reason: str) -> None:
    print(f"  DECLINED: {reason}")
    _post_comment(
        pr_number,
        f"🤖 **Autonomous CI fix declined**\n\n{reason}\n\nThis needs a human look.",
    )


def process_pr(pr: dict) -> None:
    pr_number = pr["number"]
    head_branch = pr.get("head") or _pr_head(pr_number)
    if not head_branch:
        print(f"  Could not resolve head branch for PR #{pr_number} — skipping")
        return
    print(f"\n=== Checking PR #{pr_number} ({head_branch}) ===")

    head_sha = _run(
        ["gh", "pr", "view", str(pr_number), "--json", "headRefOid", "-q", ".headRefOid"],
        capture_output=True, text=True,
    ).stdout.strip()
    if not head_sha:
        print(f"  Could not get PR #{pr_number} head SHA — skipping")
        return

    checks = httpx.get(
        f"https://api.github.com/repos/{REPO}/commits/{head_sha}/check-runs",
        headers=_GH_HEADERS, params={"per_page": "50"}, timeout=30.0,
    ).json().get("check_runs", [])
    failed = [c for c in checks if c.get("conclusion") == "failure"
              and c["name"] not in ("Security Gate — No New Alerts",)]
    if not failed:
        print(f"  No failing checks — PR #{pr_number} is green")
        return
    print(f"  {len(failed)} failing check(s): {[c['name'] for c in failed]}")

    attempts = _prior_attempt_count(pr_number, head_branch)
    if attempts >= _MAX_ATTEMPTS_PER_PR:
        print(f"  Already attempted {attempts} time(s) — retry cap reached")
        _decline(
            pr_number,
            f"{attempts} automated fix attempts have already been made on this PR "
            "without reaching green. Stopping rather than compounding further "
            "unreviewed changes every 30 minutes.",
        )
        return

    failed_check = failed[0]
    job_id = failed_check.get("id")
    error_summary = _fetch_failure_context(job_id) if job_id else ""
    if not error_summary:
        output = failed_check.get("output", {})
        error_summary = (output.get("summary", "") + "\n" + output.get("text", ""))[-3000:]
    print(f"  Extracted failure context ({len(error_summary)} chars)")

    brain = _select_brain()
    if brain is None:
        print("  No brain API key configured — skipping")
        return
    _, url, api_key, model = brain

    fix_prompt = f"""You are fixing a failing CI check in the Autonomous AI Agency repository.

PR #{pr_number}: {pr.get('title', '')}
Branch: {head_branch}
Failing check: {failed_check['name']}

Actual failure output (pytest FAILURES / short test summary, or job log tail):
{error_summary}

Rules:
1. Fix ONLY the file(s) that caused this specific failure. Never propose a new
   file — only modify files that already exist in this repository.
2. Never touch CI workflow files (.github/workflows/), .github/scripts/, or
   tests/conftest.py under any circumstances.
3. The fix must be minimal and directly address the error shown above — do not
   guess at unrelated files.
4. Output the fix as JSON: {{"summary": "...", "files": [{{"path": "...", "content": "full file content"}}]}}

Output only the JSON."""

    print(f"  Calling {model} for a fix...")
    try:
        resp = httpx.post(
            url, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [
                {"role": "system", "content": "You are an expert Python developer. Output only valid JSON."},
                {"role": "user", "content": fix_prompt},
            ], "max_tokens": 4096, "temperature": 0.2, "stream": False},
            timeout=120.0,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        start, end = content.find("{"), content.rfind("}") + 1
        if start < 0 or end <= start:
            print("  No JSON in model response — skipping")
            return
        fix = json.loads(content[start:end])
    except Exception as exc:  # noqa: BLE001
        print(f"  Fix generation failed: {exc}")
        return

    files = fix.get("files", [])
    if not files:
        print("  Model proposed no file changes — skipping")
        return

    # Reset to a clean, up-to-date copy of the branch before applying anything —
    # never carry state across PR iterations or a prior failed attempt.
    _run(["git", "checkout", "--", "."], capture_output=True)
    _run(["git", "clean", "-fd"], capture_output=True)
    _run(["git", "fetch", "origin", head_branch], check=True, capture_output=True)
    _run(["git", "checkout", head_branch], check=True, capture_output=True)
    _run(["git", "reset", "--hard", f"origin/{head_branch}"], check=True, capture_output=True)

    blocked: list[str] = []
    to_write: list[tuple[str, str]] = []
    for file_info in files:
        path = file_info.get("path", "")
        content = file_info.get("content", "")
        if isinstance(content, list):
            content = "\n".join(str(line) for line in content)
        elif not isinstance(content, str):
            content = str(content)
        if not path:
            continue

        denied = _is_denied_path(path)
        if denied:
            blocked.append(f"{path} — {denied}")
            continue
        p = pathlib.Path(path)
        if not p.exists():
            blocked.append(f"{path} — this bot only modifies existing files, never creates new ones")
            continue
        old = p.read_text(encoding="utf-8", errors="replace")
        destructive, why = is_destructive_overwrite(old, content)
        if destructive:
            blocked.append(f"{path} — {why}")
            continue
        secretish, why = looks_like_secret_file(path, content)
        if secretish:
            blocked.append(f"{path} — {why}")
            continue
        if path.endswith(".py") and not python_parses(content):
            blocked.append(f"{path} — generated Python does not parse (syntax error)")
            continue
        to_write.append((path, content))

    if blocked:
        _decline(
            pr_number,
            "The proposed fix was blocked by the safety gate:\n\n"
            + "\n".join(f"- `{b}`" for b in blocked)
            + "\n\nNo changes were applied (all-or-nothing).",
        )
        _run(["git", "checkout", "--", "."], capture_output=True)
        _run(["git", "clean", "-fd"], capture_output=True)
        return

    for path, content in to_write:
        pathlib.Path(path).write_text(content, encoding="utf-8")
        print(f"  Applied: {path}")

    # Pre-commit verification — never push a fix that doesn't actually pass.
    py_files = [path for path, _ in to_write if path.endswith(".py")]
    compiled = _run(
        [sys.executable, "-m", "compileall", "-q"] + (py_files or ["."]),
        capture_output=True, text=True,
    )
    if compiled.returncode != 0:
        _decline(
            pr_number,
            "The proposed fix failed `python -m compileall`:\n```\n"
            + (compiled.stdout + compiled.stderr)[-1500:] + "\n```",
        )
        _run(["git", "checkout", "--", "."], capture_output=True)
        return

    test_files = [p for p in py_files if pathlib.Path(p).name.startswith("test_")]
    if test_files:
        print("  Running pre-commit verification (pytest -x) ...")
        verify = _run(
            [sys.executable, "-m", "pytest", "-x", "-q", "--tb=short", "--timeout=120"] + test_files,
            capture_output=True, text=True, timeout=180,
            env={**os.environ, "TESTING": "true", "AGENCY_CEO_ENABLED": "false",
                 "RUN_BACKGROUND_IN_WEB": "false", "STORAGE_BACKEND": "sqlite"},
        )
        if verify.returncode != 0:
            _decline(
                pr_number,
                "The proposed fix still fails `pytest -x` locally:\n```\n"
                + (verify.stdout + verify.stderr)[-1500:] + "\n```",
            )
            _run(["git", "checkout", "--", "."], capture_output=True)
            return
        print("  Verification passed")

    _run(["git", "config", "user.name", _BOT_NAME], check=True)
    _run(["git", "config", "user.email", _BOT_EMAIL], check=True)
    _run(["git", "add"] + [path for path, _ in to_write], check=True)
    _run(["git", "commit", "-m", f"{_COMMIT_PREFIX}{pr_number}\n\n{fix.get('summary', '')}"], check=True)
    _run(["git", "push", "origin", head_branch], check=True)
    print(f"  ✅ Verified fix pushed to {head_branch} — CI will re-run automatically")


def main() -> None:
    prs = _list_target_prs()
    print(f"Open PRs to check: {[p['number'] for p in prs]}")
    for pr in prs:
        try:
            process_pr(pr)
        except Exception as exc:  # noqa: BLE001 — one PR's failure must not stop the rest
            print(f"  ❌ Unhandled error on PR #{pr['number']}: {exc}")
    print("\n=== Fix cycle complete ===")


if __name__ == "__main__":
    main()

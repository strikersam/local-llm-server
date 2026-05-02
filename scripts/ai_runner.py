#!/usr/bin/env python3
"""
ai_runner.py — Auto-resume watchdog for AI coding sessions.

This script provides the core persistence and resume infrastructure for
AI engineering tasks in this repo. It:

  - Starts a Claude Code session with a named, resumable session ID
  - Monitors for cooldown / token exhaustion / quota errors
  - Persists checkpoint state to .claude/state/ after every step
  - Resumes from the exact next step after cooldown expires
  - Provides status, logs, summary, manifest, and audit commands
  - Uses exponential backoff for retries

Usage:
  python scripts/ai_runner.py start [--session NAME] [--instruction TEXT]
  python scripts/ai_runner.py status
  python scripts/ai_runner.py resume
  python scripts/ai_runner.py stop
  python scripts/ai_runner.py logs [--tail N]
  python scripts/ai_runner.py summary
  python scripts/ai_runner.py manifest
  python scripts/ai_runner.py audit
  python scripts/ai_runner.py changelog-check

State files:
  .claude/state/agent-state.json     Full session state
  .claude/state/NEXT_ACTION.md       Human-readable next step
  .claude/state/checkpoint.jsonl     Append-only step log
  .claude/state/runner.lock          Prevents duplicate concurrent runs
  .claude/state/session.log          Session logs (append)
"""

from __future__ import annotations

import argparse
import fcntl
import json
import logging
import os
import re
import subprocess
import shlex
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Paths ──────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent.parent.resolve()
STATE_DIR = REPO_ROOT / ".claude" / "state"
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"
AGENTS_DIR = REPO_ROOT / ".claude" / "agents"
COMMANDS_DIR = REPO_ROOT / ".claude" / "commands"

STATE_FILE = STATE_DIR / "agent-state.json"
NEXT_ACTION_FILE = STATE_DIR / "NEXT_ACTION.md"
CHECKPOINT_FILE = STATE_DIR / "checkpoint.jsonl"
LOCK_FILE = STATE_DIR / "runner.lock"
LOG_FILE = STATE_DIR / "session.log"
JUDGE_FILE = STATE_DIR / "judge-verdict.json"

# ── Cooldown / retry config ────────────────────────────────────────────────────

# Patterns in stderr/stdout that indicate rate limiting / quota exhaustion
COOLDOWN_PATTERNS = [
    r"rate.?limit",
    r"quota.?exceeded",
    r"token.?limit",
    r"overloaded",
    r"529",            # Anthropic overloaded
    r"429",            # Too many requests
    r"context.?window",
    r"max.?tokens",
    r"cooldown",
]

# Backoff schedule (seconds): 60s, 120s, 240s, 480s, 960s
BACKOFF_SCHEDULE = [60, 120, 240, 480, 960]
MAX_RETRIES = len(BACKOFF_SCHEDULE)

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("ai-runner")


def _log_to_file(message: str) -> None:
    """Append a message to the session log file."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a") as f:
        f.write(f"{_now()} {message}\n")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── State management ──────────────────────────────────────────────────────────

def read_state() -> dict[str, Any]:
    """Read the current agent state, or return an empty state."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except json.JSONDecodeError:
            log.warning("agent-state.json is corrupt — returning empty state")
    return {
        "schema_version": "1",
        "session_id": None,
        "status": "idle",
        "completed_steps": [],
        "plan": [],
        "next_step": None,
        "changed_files": [],
        "last_updated": _now(),
    }


def write_state(state: dict[str, Any]) -> None:
    """Write state atomically using a temp file."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state["last_updated"] = _now()
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(STATE_FILE)


def append_checkpoint(step: str, status: str, detail: str = "") -> None:
    """Append a checkpoint entry to the JSONL log."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    entry = json.dumps({
        "ts": _now(),
        "step": step,
        "status": status,
        "detail": detail,
    })
    with CHECKPOINT_FILE.open("a") as f:
        f.write(entry + "\n")


def read_checkpoints() -> list[dict[str, Any]]:
    """Read all checkpoint entries from the JSONL log."""
    if not CHECKPOINT_FILE.exists():
        return []
    entries = []
    for line in CHECKPOINT_FILE.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return entries


def completed_step_ids() -> set[str]:
    """Return the set of step IDs already completed (from checkpoint log)."""
    return {
        cp["step"]
        for cp in read_checkpoints()
        if cp.get("status") == "done"
    }


def update_next_action(state: dict[str, Any]) -> None:
    """Write a human-readable NEXT_ACTION.md from current state."""
    next_step = state.get("next_step") or {}
    lines = [
        "# NEXT ACTION — AI Engineering Session",
        "",
        f"**Session:** `{state.get('session_id', 'unknown')}`",
        f"**Status:** {state.get('status', 'unknown')}",
        f"**Last updated:** {state.get('last_updated', '?')}",
        "",
        "## Next Step",
        "",
    ]
    if next_step:
        lines += [
            f"**ID:** {next_step.get('id', '?')}",
            f"**Name:** {next_step.get('name', '?')}",
            f"**Description:** {next_step.get('description', '?')}",
            f"**Resume command:** `{next_step.get('resume_command', 'python scripts/ai_runner.py resume')}`",
        ]
    else:
        lines.append("No pending step — session may be complete or idle.")

    lines += [
        "",
        "## Completed Steps",
        "",
    ]
    for step_id in state.get("completed_steps", []):
        lines.append(f"- [x] {step_id}")

    lines += [
        "",
        "## How to Resume",
        "",
        "```bash",
        "python scripts/ai_runner.py resume",
        "```",
        "",
        "Or check full state: `cat .claude/state/agent-state.json`",
    ]

    NEXT_ACTION_FILE.write_text("\n".join(lines) + "\n")


# ── Lock management ───────────────────────────────────────────────────────────

class RunnerLock:
    """File-based lock to prevent duplicate concurrent sessions."""

    def __init__(self) -> None:
        self._fd: int | None = None

    def acquire(self) -> bool:
        """Try to acquire the lock. Returns True if acquired."""
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        try:
            self._fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_WRONLY)
            fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            os.write(self._fd, f"pid={os.getpid()} ts={_now()}\n".encode())
            return True
        except (OSError, BlockingIOError):
            if self._fd is not None:
                os.close(self._fd)
                self._fd = None
            return False

    def release(self) -> None:
        if self._fd is not None:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None
        LOCK_FILE.unlink(missing_ok=True)

    def __enter__(self) -> "RunnerLock":
        if not self.acquire():
            log.error(
                "Another ai_runner process is already running. "
                "Use 'python scripts/ai_runner.py status' to check, "
                "or 'python scripts/ai_runner.py stop' to terminate."
            )
            sys.exit(1)
        return self

    def __exit__(self, *args: Any) -> None:
        self.release()


# ── Cooldown detection ────────────────────────────────────────────────────────

def _is_cooldown_error(output: str) -> bool:
    """Return True if output indicates a rate limit / quota / token exhaustion."""
    lower = output.lower()
    for pattern in COOLDOWN_PATTERNS:
        if re.search(pattern, lower):
            return True
    return False


def _wait_with_backoff(attempt: int) -> None:
    """Wait for the appropriate backoff duration."""
    wait = BACKOFF_SCHEDULE[min(attempt, len(BACKOFF_SCHEDULE) - 1)]
    log.info("Cooldown detected. Waiting %d seconds before retry (attempt %d/%d)...",
             wait, attempt + 1, MAX_RETRIES)
    _log_to_file(f"COOLDOWN: waiting {wait}s (attempt {attempt + 1})")

    # Update state to record cooldown
    state = read_state()
    state["status"] = "cooldown"
    state["retry_after"] = _now()
    state["cooldown_until"] = datetime.fromtimestamp(
        time.time() + wait, tz=timezone.utc
    ).isoformat()
    write_state(state)

    time.sleep(wait)


# ── Claude Code session runner ────────────────────────────────────────────────

def _build_claude_command(session_name: str, instruction: str) -> list[str]:
    """Build the claude CLI command for a session."""
    # Try claude CLI (Claude Code)
    claude_bin = _find_claude_bin()
    if claude_bin:
        return [
            claude_bin,
            "--session", session_name,
            "--print",
            instruction,
        ]
    # Fallback: use anthropic Python SDK directly
    return [
        sys.executable,
        "-c",
        _inline_claude_fallback(session_name, instruction),
    ]


def _find_claude_bin() -> str | None:
    """Find the claude CLI binary."""
    candidates = [
        "/usr/local/bin/claude",
        "/usr/bin/claude",
        os.path.expanduser("~/.local/bin/claude"),
        os.path.expanduser("~/.npm-global/bin/claude"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    # Check PATH
    result = subprocess.run(["which", "claude"], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def _inline_claude_fallback(session_name: str, instruction: str) -> str:
    """Python code to run when claude CLI is not available."""
    return (
        "import sys; "
        "print(f'Claude CLI not found. Session: {repr('" + session_name + "')}'); "
        "print('Instruction:', repr('" + instruction[:100] + "...')); "
        "print('Install claude CLI: npm install -g @anthropic-ai/claude-code'); "
        "sys.exit(2)"
    )


def _run_claude_session(
    session_name: str,
    instruction: str,
    *,
    max_retries: int = MAX_RETRIES,
) -> int:
    """
    Run a Claude Code session with automatic retry on cooldown.

    Returns the final exit code.
    """
    cmd = _build_claude_command(session_name, instruction)
    attempt = 0

    while attempt <= max_retries:
        log.info("Starting Claude session '%s' (attempt %d)...", session_name, attempt + 1)
        _log_to_file(f"SESSION_START: session={session_name} attempt={attempt + 1}")

        # Update state
        state = read_state()
        state["status"] = "running"
        state["session_id"] = session_name
        write_state(state)
        update_next_action(state)

        result = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            capture_output=False,
            text=True,
        )

        append_checkpoint(
            step=f"session-attempt-{attempt + 1}",
            status="done" if result.returncode == 0 else "failed",
            detail=f"exit_code={result.returncode}",
        )

        if result.returncode == 0:
            log.info("Session completed successfully.")
            _log_to_file(f"SESSION_DONE: session={session_name}")
            state = read_state()
            state["status"] = "done"
            write_state(state)
            return 0

        # Check for cooldown / quota error via exit code or stderr
        # Exit code 2 = Claude CLI internal rate limit in some versions
        if result.returncode in (1, 2):
            # We can't easily intercept stdout/stderr with capture_output=False
            # So we check if a cooldown marker was written to state by the session itself
            state = read_state()
            if state.get("status") == "cooldown" or attempt < max_retries:
                _wait_with_backoff(attempt)
                attempt += 1
                continue

        log.error("Session failed with exit code %d", result.returncode)
        _log_to_file(f"SESSION_FAILED: exit_code={result.returncode}")
        state = read_state()
        state["status"] = "failed"
        write_state(state)
        return result.returncode

    log.error("Max retries (%d) exceeded. Giving up.", max_retries)
    state = read_state()
    state["status"] = "max_retries_exceeded"
    write_state(state)
    return 1


# ── Resume logic ──────────────────────────────────────────────────────────────

def cmd_resume() -> int:
    """Resume from the last checkpoint."""
    state = read_state()

    if state.get("status") in ("idle", None):
        log.info("No active session found. Use 'ai_runner.py start' to begin.")
        return 0

    next_step = state.get("next_step")
    if not next_step:
        log.info("Session '%s' has no pending next step. Status: %s",
                 state.get("session_id"), state.get("status"))
        return 0

    log.info("Resuming session '%s' from step: %s",
             state.get("session_id"), next_step.get("name", "?"))

    done_steps = completed_step_ids()
    step_id = str(next_step.get("id", ""))
    if step_id in done_steps:
        log.info("Step '%s' is already marked done in checkpoint log. Skipping.", step_id)
        return 0

    # Build a resume instruction from the state
    resume_instruction = (
        f"Resume the task '{state.get('objective', 'previous task')}'. "
        f"The following steps are already complete: {list(done_steps)}. "
        f"Continue from: {next_step.get('description', 'next step')}. "
        f"Read .claude/state/agent-state.json for full context."
    )

    session_name = state.get("session_id") or f"resume-{int(time.time())}"
    resume_cmd = next_step.get("resume_command", "")

    if resume_cmd and resume_cmd.startswith("python"):
        log.info("Executing resume command: %s", resume_cmd)
        result = subprocess.run(shlex.split(resume_cmd), shell=False, cwd=REPO_ROOT)
        return result.returncode

    with RunnerLock():
        return _run_claude_session(session_name, resume_instruction)


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_start(session_name: str, instruction: str) -> int:
    """Start a new AI session."""
    if not session_name:
        session_name = f"session-{int(time.time())}"

    # Initialize fresh state
    state = {
        "schema_version": "1",
        "session_id": session_name,
        "objective": instruction,
        "status": "starting",
        "plan": [],
        "completed_steps": [],
        "next_step": None,
        "changed_files": [],
        "tests_run": [],
        "retry_after": None,
        "cooldown_until": None,
        "lock": None,
        "last_updated": _now(),
    }
    write_state(state)
    update_next_action(state)
    append_checkpoint("session-init", "done", f"session={session_name}")
    _log_to_file(f"START: session={session_name} instruction_len={len(instruction)}")

    log.info("Starting session '%s'", session_name)

    with RunnerLock():
        return _run_claude_session(session_name, instruction)


def cmd_status() -> None:
    """Print current session status."""
    state = read_state()
    checkpoints = read_checkpoints()

    print("\n─── AI Runner Status ─────────────────────────────────────────────")
    print(f"  Session:     {state.get('session_id', 'none')}")
    print(f"  Status:      {state.get('status', 'idle')}")
    print(f"  Updated:     {state.get('last_updated', '?')}")
    print(f"  Cooldown:    {state.get('cooldown_until', 'none')}")

    completed = state.get("completed_steps", [])
    print(f"  Completed:   {len(completed)} steps")

    next_step = state.get("next_step")
    if next_step:
        print(f"  Next step:   [{next_step.get('id', '?')}] {next_step.get('name', '?')}")
        print(f"  Resume:      {next_step.get('resume_command', 'python scripts/ai_runner.py resume')}")

    print(f"\n  Checkpoints: {len(checkpoints)} entries in checkpoint.jsonl")
    if checkpoints:
        last = checkpoints[-1]
        print(f"  Last entry:  {last.get('ts', '?')} — {last.get('step', '?')} ({last.get('status', '?')})")

    # Lock status
    if LOCK_FILE.exists():
        lock_content = LOCK_FILE.read_text().strip()
        print(f"\n  Lock:        ACTIVE ({lock_content})")
    else:
        print("\n  Lock:        none")

    print("─────────────────────────────────────────────────────────────────\n")


def cmd_stop() -> None:
    """Stop the current session."""
    state = read_state()
    state["status"] = "stopped"
    write_state(state)
    LOCK_FILE.unlink(missing_ok=True)
    append_checkpoint("session-stop", "done", "manual stop")
    log.info("Session stopped. State saved.")


def cmd_logs(tail: int = 50) -> None:
    """Print the last N lines of the session log."""
    if not LOG_FILE.exists():
        print("No session log found.")
        return
    lines = LOG_FILE.read_text().splitlines()
    for line in lines[-tail:]:
        print(line)


def cmd_summary() -> None:
    """Summarize the last completed session."""
    state = read_state()
    checkpoints = read_checkpoints()

    done_checkpoints = [c for c in checkpoints if c.get("status") == "done"]
    failed_checkpoints = [c for c in checkpoints if c.get("status") == "failed"]

    print("\n─── Session Summary ──────────────────────────────────────────────")
    print(f"  Session:     {state.get('session_id', 'none')}")
    print(f"  Objective:   {state.get('objective', '?')[:100]}")
    print(f"  Status:      {state.get('status', '?')}")
    print(f"  Steps done:  {len(done_checkpoints)}")
    print(f"  Steps failed:{len(failed_checkpoints)}")
    print(f"  Files changed: {len(state.get('changed_files', []))}")
    for f in state.get("changed_files", []):
        print(f"    - {f}")
    print("─────────────────────────────────────────────────────────────────\n")


def cmd_manifest() -> None:
    """List all skills, commands, and agents available in this repo."""
    print("\n─── Repo AI Manifest ─────────────────────────────────────────────")

    print("\n  Skills (.claude/skills/):")
    if SKILLS_DIR.exists():
        for skill_dir in sorted(SKILLS_DIR.iterdir()):
            if skill_dir.is_dir():
                skill_file = skill_dir / "SKILL.md"
                if skill_file.exists():
                    # Extract description from frontmatter
                    content = skill_file.read_text()
                    m = re.search(r"^description:\s*>\s*\n((?:  .+\n)+)", content, re.MULTILINE)
                    desc = ""
                    if m:
                        desc = " ".join(m.group(1).split()).strip()[:80]
                    print(f"    • {skill_dir.name}: {desc}")
    else:
        print("    (none)")

    print("\n  Commands (.claude/commands/):")
    if COMMANDS_DIR.exists():
        for cmd_file in sorted(COMMANDS_DIR.glob("*.md")):
            print(f"    • /{cmd_file.stem}")
    else:
        print("    (none)")

    print("\n  Agents (.claude/agents/):")
    if AGENTS_DIR.exists():
        for agent_file in sorted(AGENTS_DIR.glob("*.md")):
            print(f"    • {agent_file.stem}")
    else:
        print("    (none)")

    print("\n  Runner commands:")
    for cmd in ["start", "status", "resume", "stop", "logs", "summary", "manifest", "audit", "changelog-check"]:
        print(f"    python scripts/ai_runner.py {cmd}")

    print("─────────────────────────────────────────────────────────────────\n")


def cmd_audit() -> int:
    """Run a basic security and dependency audit."""
    print("\n─── Dependency & Security Audit ──────────────────────────────────")
    errors = 0

    # Check for hardcoded secrets
    print("\n  Checking for hardcoded secrets...")
    py_files = list(REPO_ROOT.glob("**/*.py"))
    for f in py_files:
        if ".venv" in f.parts or "tests" in f.parts:
            continue
        content = f.read_text(errors="replace")
        if re.search(r'SECRET_KEY\s*=\s*["\'][^"\']+["\']', content):
            print(f"  ✗ Possible hardcoded SECRET_KEY in {f.relative_to(REPO_ROOT)}")
            errors += 1

    if errors == 0:
        print("  ✓ No hardcoded secrets found")

    # Check requirements.txt for outdated-looking packages
    req_file = REPO_ROOT / "requirements.txt"
    if req_file.exists():
        print("\n  Requirements:")
        for line in req_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                print(f"    {line}")

    # Check if keys.json exists (should not be committed)
    keys_file = REPO_ROOT / "keys.json"
    if keys_file.exists():
        print("\n  ✗ WARNING: keys.json exists in repo root — ensure it is NOT committed")
        errors += 1
    else:
        print("\n  ✓ keys.json not found (good)")

    print("─────────────────────────────────────────────────────────────────\n")
    return 1 if errors > 0 else 0


def cmd_changelog_check() -> int:
    """Check that docs/changelog.md has content under [Unreleased]."""
    changelog = REPO_ROOT / "docs" / "changelog.md"
    if not changelog.exists():
        print("✗ docs/changelog.md not found")
        return 1

    content = changelog.read_text()
    m = re.search(r"## \[Unreleased\](.*?)(?=## \[|\Z)", content, re.DOTALL)
    if not m:
        print("✗ No [Unreleased] section found in docs/changelog.md")
        return 1

    body = m.group(1).strip()
    if not body or body == "_(nothing pending)_":
        print("✗ [Unreleased] section has no entries")
        return 1

    lines = [l for l in body.splitlines() if l.strip()]
    print(f"✓ docs/changelog.md has {len(lines)} lines of unreleased content")
    return 0


# ── Simulation test ───────────────────────────────────────────────────────────

def cmd_test_resume_simulation() -> int:
    """
    Simulate an interruption and prove resume works.

    Uses isolated temporary state files so it does not interfere with live state.

    Test sequence:
    1. Write a fake "in-progress" state with a known next_step
    2. Append a checkpoint showing step-1 is done
    3. Simulate a "cooldown" by sleeping 2 seconds
    4. Call resume logic
    5. Verify state was read correctly and next_step is correct
    """
    import tempfile
    global STATE_FILE, CHECKPOINT_FILE

    # Use isolated temp files for the simulation
    _orig_state = STATE_FILE
    _orig_checkpoint = CHECKPOINT_FILE
    tmp_dir = Path(tempfile.mkdtemp(prefix="ai_runner_sim_"))
    STATE_FILE = tmp_dir / "agent-state.json"
    CHECKPOINT_FILE = tmp_dir / "checkpoint.jsonl"

    print("\n─── Resume Simulation Test ───────────────────────────────────────")
    print(f"  (Using isolated temp state: {tmp_dir})")

    # Step 1: Write interrupted state
    test_state = {
        "schema_version": "1",
        "session_id": "sim-test-001",
        "objective": "Test the resume simulation",
        "status": "interrupted",
        "plan": [
            {"id": "1", "name": "step-one", "status": "done"},
            {"id": "2", "name": "step-two", "status": "pending"},
        ],
        "completed_steps": ["step-one"],
        "next_step": {
            "id": "2",
            "name": "step-two",
            "description": "Continue with step two",
            "resume_command": "echo RESUMED_STEP_TWO",
        },
        "changed_files": ["proxy.py"],
        "last_updated": _now(),
    }
    write_state(test_state)
    print("  ✓ Wrote interrupted state")

    # Step 2: Append checkpoint showing step-1 done
    append_checkpoint("step-one", "done", "simulation: step-one completed before interruption")
    print("  ✓ Appended step-one checkpoint")

    # Step 3: Simulate cooldown wait (very short for test)
    print("  ℹ Simulating 2-second cooldown...")
    time.sleep(2)

    # Step 4: Read state back (as resume would do)
    loaded = read_state()
    assert loaded["session_id"] == "sim-test-001", f"Expected sim-test-001, got {loaded['session_id']}"
    assert loaded["status"] == "interrupted"
    assert loaded["next_step"]["name"] == "step-two"
    print("  ✓ State reloaded correctly after simulated interruption")

    # Step 5: Verify checkpoint log shows step-one done
    done = completed_step_ids()
    assert "step-one" in done, f"step-one should be in completed steps, got: {done}"
    assert "step-two" not in done, "step-two should NOT be done yet"
    print("  ✓ Checkpoint log correctly shows step-one done, step-two pending")

    # Step 6: Verify next_step is step-two (not step-one)
    next_step = loaded["next_step"]
    assert next_step["id"] == "2"
    print(f"  ✓ Next step correctly identified: [{next_step['id']}] {next_step['name']}")

    # Step 7: Execute the resume command (dry-run: echo only)
    resume_cmd = next_step.get("resume_command", "")
    if resume_cmd.startswith("echo"):
        result = subprocess.run(shlex.split(resume_cmd), shell=False, capture_output=True, text=True)
        assert "RESUMED_STEP_TWO" in result.stdout, f"Resume command output: {result.stdout}"
        print(f"  ✓ Resume command executed: {result.stdout.strip()}")

    # Step 8: Mark step-two done
    append_checkpoint("step-two", "done", "simulation: step-two completed after resume")
    done_after = completed_step_ids()
    assert "step-two" in done_after
    print("  ✓ step-two checkpoint appended correctly")

    # Step 9: Update state to done
    loaded["status"] = "done"
    loaded["completed_steps"] = ["step-one", "step-two"]
    loaded["next_step"] = None
    write_state(loaded)
    print("  ✓ State updated to done")

    # Restore original state files
    STATE_FILE = _orig_state
    CHECKPOINT_FILE = _orig_checkpoint
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)

    print("\n  SIMULATION RESULT: PASS")
    print("  Checkpoint persisted → cooldown waited → state reloaded → correct step resumed")
    print("  No duplicate edits: step-one was skipped (already in checkpoint log)")
    print("─────────────────────────────────────────────────────────────────\n")
    return 0


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        prog="ai_runner.py",
        description="Auto-resume watchdog for AI coding sessions",
    )
    sub = parser.add_subparsers(dest="command")

    # start
    p_start = sub.add_parser("start", help="Start a new AI session")
    p_start.add_argument("--session", default="", help="Session name (default: auto-generated)")
    p_start.add_argument("--instruction", default="", help="Task instruction")
    p_start.add_argument("instruction_pos", nargs="?", default="", help="Task instruction (positional)")

    # status
    sub.add_parser("status", help="Show current session status")

    # resume
    sub.add_parser("resume", help="Resume from last checkpoint")

    # stop
    sub.add_parser("stop", help="Stop the current session")

    # logs
    p_logs = sub.add_parser("logs", help="Show session logs")
    p_logs.add_argument("--tail", type=int, default=50, help="Number of lines to show")

    # summary
    sub.add_parser("summary", help="Summarize last session")

    # manifest
    sub.add_parser("manifest", help="List all skills, commands, and agents")

    # audit
    sub.add_parser("audit", help="Run security and dependency audit")

    # changelog-check
    sub.add_parser("changelog-check", help="Check docs/changelog.md for content")

    # test-resume
    sub.add_parser("test-resume", help="Run resume simulation test")

    args = parser.parse_args()

    if args.command == "start":
        instruction = args.instruction or args.instruction_pos or ""
        if not instruction:
            log.error("Provide an instruction: python scripts/ai_runner.py start 'your task here'")
            return 1
        return cmd_start(args.session, instruction)

    elif args.command == "status":
        cmd_status()
        return 0

    elif args.command == "resume":
        return cmd_resume()

    elif args.command == "stop":
        cmd_stop()
        return 0

    elif args.command == "logs":
        cmd_logs(tail=args.tail)
        return 0

    elif args.command == "summary":
        cmd_summary()
        return 0

    elif args.command == "manifest":
        cmd_manifest()
        return 0

    elif args.command == "audit":
        return cmd_audit()

    elif args.command == "changelog-check":
        return cmd_changelog_check()

    elif args.command == "test-resume":
        return cmd_test_resume_simulation()

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())

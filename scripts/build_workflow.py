#!/usr/bin/env python3
"""build-workflow — CRISPY multi-agent build system CLI.

Run a deterministic, multi-agent coding workflow on any project.
Works from any directory. Streams live progress to your terminal.

Usage
-----
  # Simplest form — task as argument
  build-workflow "Add comprehensive unit tests to the router module"

  # Interactive mode (prompts for task)
  build-workflow

  # With explicit model overrides
  CRISPY_CODER_MODEL=qwen3-coder:30b \\
  CRISPY_REVIEWER_MODEL=deepseek-r1:32b \\
  build-workflow "Refactor the auth module"

  # Target a specific project directory
  build-workflow --workspace /path/to/project "Add REST API for users"

  # Against a remote server
  LLM_BASE_URL=https://your-tunnel.trycloudflare.com \\
  LLM_API_KEY=your-key \\
  build-workflow "Add feature X"

Configuration (via environment variables)
-----------------------------------------
  LLM_BASE_URL          Proxy base URL (default: http://localhost:8000)
  LLM_API_KEY           API key (required when server auth is enabled)
  CRISPY_ARCHITECT_MODEL  Model for planning phases
  CRISPY_SCOUT_MODEL      Model for research phases
  CRISPY_CODER_MODEL      Model for implementation (default: qwen3-coder:30b)
  CRISPY_REVIEWER_MODEL   Model for review — SHOULD differ from CODER
  CRISPY_VERIFIER_MODEL   Model for generating verify commands

Agent Team (default)
--------------------
  Scout     [deepseek-r1:32b]     — research, read-only
  Architect [qwen3-coder:30b]     — planning, structure, report
  Coder     [qwen3-coder:30b]     — implementation (write-permitted)
  Reviewer  [deepseek-r1:32b]     — adversarial review, DIFFERENT model
  Verifier  [qwen3-coder:7b]      — generates test commands, execution only

Workflow Lifecycle
------------------
  request → context → research → investigate → structure → plan
  ──────── HUMAN APPROVAL GATE (hard stop) ────────────────────
  → execute (per slice) → review (different model) → verify → report
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import json
from pathlib import Path

# ── Colour helpers ─────────────────────────────────────────────────────────────

RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BLUE   = "\033[94m"
WHITE  = "\033[97m"

def _c(color: str, text: str) -> str:
    """Apply ANSI color if stdout is a tty."""
    if not sys.stdout.isatty():
        return text
    return f"{color}{text}{RESET}"

def _rule(char: str = "─", width: int = 65) -> str:
    return _c(DIM, char * width)

def _header(text: str) -> None:
    print(f"\n{_rule()}")
    print(f"  {_c(BOLD + CYAN, text)}")
    print(_rule())

def _phase_icon(status: str) -> str:
    return {"done": "✓", "running": "▶", "failed": "✗", "pending": "·", "skipped": "⊘"}.get(status, "?")

def _status_color(status: str) -> str:
    return {
        "done": GREEN, "applied": GREEN, "awaiting_approval": YELLOW,
        "failed": RED, "cancelled": RED, "running": CYAN, "executing": CYAN,
    }.get(status, WHITE)


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _make_headers(api_key: str) -> dict[str, str]:
    h: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        h["Authorization"] = f"Bearer {api_key}"
    return h


def _get(base: str, path: str, api_key: str, params: str = "") -> dict:
    """Synchronous GET — no external dependencies beyond stdlib."""
    import urllib.request, urllib.error
    url = f"{base}{path}{'?' + params if params else ''}"
    req = urllib.request.Request(url, headers=_make_headers(api_key))
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(_c(RED, f"HTTP {e.code} on GET {path}: {body[:200]}"))
        sys.exit(1)
    except Exception as e:
        print(_c(RED, f"Connection error on GET {path}: {e}"))
        print(_c(DIM, f"Is the proxy running at {base}?"))
        sys.exit(1)


def _post(base: str, path: str, api_key: str, body: dict) -> dict:
    import urllib.request, urllib.error
    url = f"{base}{path}"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=_make_headers(api_key), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        print(_c(RED, f"HTTP {e.code} on POST {path}: {body_text[:300]}"))
        sys.exit(1)
    except Exception as e:
        print(_c(RED, f"Connection error on POST {path}: {e}"))
        sys.exit(1)


# ── Display helpers ────────────────────────────────────────────────────────────

def _print_team(agents: list[dict]) -> None:
    print(f"\n  {_c(BOLD, 'Agent Team:')}")
    for a in agents:
        icon = "✎" if a.get("can_write") else ("⚡" if a.get("can_execute") else ("👁" if a.get("can_review") else "🔍"))
        print(
            f"  {icon}  {_c(BOLD, a['name']):18s} "
            f"{_c(DIM, '[' + a['role'] + ']'):15s} "
            f"{_c(CYAN, a['model'])}"
        )


def _print_phases(phases: list[dict]) -> None:
    for p in phases:
        icon = _phase_icon(p["status"])
        color = _status_color(p["status"])
        role = p.get("agent_role", "?")
        print(f"  {_c(color, icon)}  {p['name']:15s} {_c(DIM, '[' + role + ']')}")


def _print_plan(base: str, run_id: str, api_key: str) -> None:
    _header("PLAN — Review before approving")
    try:
        result = _get(base, f"/workflow/{run_id}/artifacts/plan.md", api_key)
        content = result.get("content") or ""
        # Truncate at 4000 chars for terminal display
        if len(content) > 4000:
            content = content[:4000] + "\n\n... [truncated — full plan at GET /workflow/{run_id}/artifacts/plan.md]"
        print(content)
    except SystemExit:
        print(_c(YELLOW, "  (plan.md not available yet)"))


def _print_slices(slices: list[dict]) -> None:
    if not slices:
        return
    print(f"\n  {_c(BOLD, 'Slices:')}")
    for s in slices:
        icon = {"applied": "✓", "failed": "✗", "running": "▶", "pending": "·"}.get(s["status"], "?")
        color = _status_color(s["status"])
        files = ", ".join(s.get("files", [])[:3]) or "(files TBD)"
        check = s.get("check_run") or {}
        passed = "✓" if check.get("passed") else ("✗" if check.get("passed") is False else "")
        print(
            f"  {_c(color, icon)}  [{s['index']:02d}] {_c(BOLD, s['title'][:50])}"
            f"  {_c(DIM, files[:40])}"
            f"  {_c(GREEN if passed == '✓' else RED, passed)}"
        )


# ── Main workflow loop ────────────────────────────────────────────────────────

def run_workflow(
    task: str,
    *,
    base: str,
    api_key: str,
    workspace: str | None,
    model_routing: dict,
) -> None:
    # 1. Show agent team
    _header("CRISPY Multi-Agent Build System")
    print(f"\n  {_c(BOLD, 'Task:')} {task[:100]}")
    print(f"  {_c(BOLD, 'Server:')} {base}")
    if workspace:
        print(f"  {_c(BOLD, 'Workspace:')} {workspace}")

    team_data = _get(base, "/workflow/agents", api_key)
    _print_team(team_data.get("agents", []))
    agents = team_data.get("agents", [])
    coder = next((a for a in agents if a["role"] == "coder"), {})
    reviewer = next((a for a in agents if a["role"] == "reviewer"), {})
    if coder.get("model") and reviewer.get("model") and coder["model"] != reviewer["model"]:
        print(f"\n  {_c(GREEN, '✓')} Dual-model review active: "
              f"{_c(CYAN, coder['model'])} → {_c(YELLOW, reviewer['model'])}")
    else:
        print(f"\n  {_c(YELLOW, '⚠')}  Coder and Reviewer use the same model. "
              f"Set CRISPY_REVIEWER_MODEL for better coverage.")

    # 2. Create workflow run
    print(f"\n{_rule()}")
    print(f"  {_c(BOLD, 'Starting workflow...')}")
    build_body: dict = {"request": task, "title": task[:80]}
    if workspace:
        build_body["workspace_root"] = workspace
    if model_routing:
        build_body["model_routing"] = model_routing

    result = _post(base, "/workflow/build", api_key, build_body)
    run_id = result["run_id"]
    print(f"  {_c(GREEN, '✓')} Created  {_c(BOLD, run_id)}\n")

    # 3. Stream pre-gate phases
    _header("Pre-Gate Phases (Scout → Architect)")
    last_pos = 0
    deadline = time.monotonic() + 1800  # 30 min max for pre-gate

    while time.monotonic() < deadline:
        run_data = _get(base, f"/workflow/{run_id}", api_key)
        status = run_data["status"]

        # Emit new events
        events = _get(base, f"/workflow/{run_id}/events", api_key, f"from_position={last_pos}&limit=50")
        for ev in events.get("events", []):
            last_pos = ev["position"] + 1
            etype = ev["event_type"]
            payload = ev.get("payload", {})

            if etype == "phase_started":
                phase = payload.get("phase", "?")
                role = payload.get("role", "")
                print(f"  ▶  {_c(CYAN, phase):20s} {_c(DIM, '[' + role + ']' if role else '')}", end="", flush=True)
            elif etype == "phase_complete":
                phase = payload.get("phase", "?")
                art = payload.get("artifact", "")
                print(f"\r  {_c(GREEN, '✓')}  {phase:20s} {_c(DIM, '→ ' + art)}")
            elif etype == "phase_failed":
                phase = payload.get("phase", "?")
                err = payload.get("error", "")[:80]
                print(f"\n  {_c(RED, '✗')}  {phase:20s} {_c(RED, 'FAILED: ' + err)}")

        if status == "awaiting_approval":
            break
        if status in ("done", "failed", "cancelled"):
            break
        time.sleep(2)

    # 4. Show phases summary
    run_data = _get(base, f"/workflow/{run_id}", api_key)
    _print_phases(run_data.get("phases", []))

    if run_data["status"] in ("failed", "cancelled"):
        print(f"\n  {_c(RED, '✗')} Workflow ended with status: {run_data['status']}")
        sys.exit(1)

    # 5. Show plan and ask for approval
    _print_plan(base, run_id, api_key)

    _header("AWAITING YOUR APPROVAL")
    print(f"\n  Run ID:  {_c(BOLD + CYAN, run_id)}")
    print(f"\n  {_c(YELLOW, 'No code has been written yet.')}")
    print(f"  Review the plan above, then choose:")
    print(f"\n  {_c(GREEN, '[y]')} Approve — start execution")
    print(f"  {_c(RED, '[n]')} Reject  — cancel workflow")
    print(f"  {_c(DIM, '[q]')} Quit this terminal (workflow will pause; resume later)")

    while True:
        try:
            choice = input(f"\n  {_c(BOLD, 'Approve? [y/n/q]: ')}").strip().lower()
        except (KeyboardInterrupt, EOFError):
            choice = "q"

        if choice in ("y", "yes"):
            approver = os.environ.get("USER") or os.environ.get("USERNAME") or "human"
            approve_result = _post(
                base, f"/workflow/{run_id}/approve", api_key,
                {"approved_by": approver}
            )
            print(f"\n  {_c(GREEN, '✓')} Approved by {approver}")
            print(f"  Status: {_c(CYAN, approve_result.get('status', '?'))}")
            break
        elif choice in ("n", "no"):
            reason = input(f"  {_c(DIM, 'Rejection reason (optional): ')}").strip() or "Rejected via CLI"
            _post(base, f"/workflow/{run_id}/reject", api_key, {"reason": reason})
            print(f"\n  {_c(RED, '🚫')} Workflow rejected.")
            sys.exit(0)
        elif choice in ("q", "quit", "exit"):
            print(f"\n  {_c(YELLOW, '⏸')} Paused. Resume with:")
            print(f"     build-workflow --resume {run_id}")
            print(f"  Or approve via API:")
            print(f"     curl -X POST {base}/workflow/{run_id}/approve \\")
            print(f"       -H 'Authorization: Bearer {api_key or 'YOUR_KEY'}' \\")
            print(f"       -d '{{\"approved_by\": \"human\"}}'")
            sys.exit(0)
        else:
            print(f"  {_c(RED, 'Please enter y, n, or q')}")

    # 6. Stream post-gate execution
    _header("Execution (Coder → Reviewer → Verifier)")
    last_pos_exec = last_pos
    deadline = time.monotonic() + 7200  # 2 hours max

    while time.monotonic() < deadline:
        events = _get(base, f"/workflow/{run_id}/events", api_key, f"from_position={last_pos_exec}&limit=50")
        for ev in events.get("events", []):
            last_pos_exec = ev["position"] + 1
            etype = ev["event_type"]
            payload = ev.get("payload", {})

            if etype == "slices_registered":
                count = payload.get("count", "?")
                print(f"\n  📦 {count} slice(s) to execute\n")
            elif etype == "slice_started":
                sid = payload.get("slice_id", "?")
                print(f"  ▶  Slice {_c(BOLD, sid[:12])}", end="", flush=True)
            elif etype == "slice_complete":
                passed = payload.get("check_passed")
                icon = _c(GREEN, "✓") if passed else _c(RED, "✗")
                label = "applied" if passed else "FAILED"
                print(f"\r  {icon}  Slice {payload.get('slice_id', '?')[:12]}  {label}")
            elif etype == "slice_failed":
                err = payload.get("error", "")[:80]
                print(f"\n  {_c(RED, '✗')} Slice failed: {err}")
            elif etype == "phase_started":
                phase = payload.get("phase", "")
                if phase == "report":
                    print(f"\n  ▶  Generating final report...")
            elif etype == "phase_complete":
                if payload.get("phase") == "report":
                    print(f"  {_c(GREEN, '✓')}  Report complete  → {payload.get('artifact', 'final-report.md')}")
            elif etype == "workflow_done":
                break

        run_data = _get(base, f"/workflow/{run_id}", api_key)
        if run_data["status"] in ("done", "failed", "cancelled"):
            break
        time.sleep(2)

    # 7. Final summary
    run_data = _get(base, f"/workflow/{run_id}", api_key)
    _header("Summary")
    status = run_data["status"]
    status_icon = _c(GREEN, "🎉 DONE") if status == "done" else _c(RED, f"✗ {status.upper()}")
    print(f"\n  {status_icon}  —  {_c(BOLD, run_id)}")
    _print_slices(run_data.get("slices", []))
    checks = [s["check_run"] for s in run_data.get("slices", []) if s.get("check_run")]
    passed_checks = sum(1 for c in checks if c and c.get("passed"))
    print(f"\n  Verification: {_c(GREEN, str(passed_checks))}/{len(checks)} passed")
    print(f"\n  Artifacts:")
    for art in run_data.get("artifacts", []):
        print(f"    {_c(DIM, '·')} {art['name']:35s} {_c(DIM, str(art['size_bytes']) + 'B')}")
    print()
    print(f"  Full report:   GET /workflow/{run_id}/artifacts/final-report.md")
    print(f"  Event log:     GET /workflow/{run_id}/events")
    print()


def resume_workflow(run_id: str, *, base: str, api_key: str) -> None:
    """Resume or approve an existing run from the CLI."""
    run_data = _get(base, f"/workflow/{run_id}", api_key)
    status = run_data["status"]
    print(f"\n  {_c(BOLD, 'Resume:')} {run_id}  —  status: {_c(_status_color(status), status)}")

    if status == "awaiting_approval":
        _print_plan(base, run_id, api_key)
        run_workflow.__wrapped__ = True  # type: ignore
        # Jump straight to approval prompt
        task = run_data.get("request", "")
        workspace = run_data.get("workspace_root")
        _header("AWAITING YOUR APPROVAL")
        print(f"  Task: {task[:100]}")
        # re-use the approval logic inline
        while True:
            try:
                choice = input(f"\n  {_c(BOLD, 'Approve? [y/n/q]: ')}").strip().lower()
            except (KeyboardInterrupt, EOFError):
                choice = "q"
            if choice in ("y", "yes"):
                approver = os.environ.get("USER") or "human"
                _post(base, f"/workflow/{run_id}/approve", api_key, {"approved_by": approver})
                print(f"\n  {_c(GREEN, '✓')} Approved.")
                break
            elif choice in ("n", "no"):
                reason = input("  Rejection reason: ").strip() or "Rejected"
                _post(base, f"/workflow/{run_id}/reject", api_key, {"reason": reason})
                print(f"\n  {_c(RED, '🚫')} Rejected.")
                return
            else:
                return
        # Stream post-gate
        run_workflow(task, base=base, api_key=api_key, workspace=workspace, model_routing={})
    elif status in ("done", "failed", "cancelled"):
        print(f"  Run is already terminal ({status}).")
        _print_slices(run_data.get("slices", []))
    else:
        # Running — just tail events
        _post(base, f"/workflow/{run_id}/resume", api_key, {})
        print(f"  {_c(CYAN, 'Resumed.')}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="build-workflow",
        description="CRISPY multi-agent build system — run from any project directory.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Usage")[0].strip(),
    )
    parser.add_argument(
        "task",
        nargs="?",
        help="Task description. If omitted, prompted interactively.",
    )
    parser.add_argument(
        "--workspace", "-w",
        metavar="PATH",
        help="Workspace root (default: CWD)",
    )
    parser.add_argument(
        "--resume",
        metavar="RUN_ID",
        help="Resume or approve an existing run",
    )
    parser.add_argument(
        "--server",
        metavar="URL",
        help="Proxy base URL (overrides LLM_BASE_URL env var)",
    )
    parser.add_argument(
        "--key",
        metavar="KEY",
        help="API key (overrides LLM_API_KEY env var)",
    )
    parser.add_argument(
        "--coder-model",
        metavar="MODEL",
        help="Override coder model (e.g. qwen3-coder:30b)",
    )
    parser.add_argument(
        "--reviewer-model",
        metavar="MODEL",
        help="Override reviewer model — should differ from coder",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List recent workflow runs and exit",
    )
    args = parser.parse_args()

    base = (args.server or os.environ.get("LLM_BASE_URL", "http://localhost:8000")).rstrip("/")
    api_key = args.key or os.environ.get("LLM_API_KEY", "")

    if args.list:
        runs = _get(base, "/workflow/", api_key)
        print(f"\n  {_c(BOLD, 'Recent workflow runs')}  ({runs.get('count', 0)} total)\n")
        for r in runs.get("runs", []):
            status = r["status"]
            icon = {"done": "✅", "failed": "❌", "awaiting_approval": "⏸", "cancelled": "🚫"}.get(status, "▶")
            print(f"  {icon}  {r['run_id']}  {_c(_status_color(status), status):20s}  {r['title'][:55]}")
        print()
        return

    if args.resume:
        resume_workflow(args.resume, base=base, api_key=api_key)
        return

    task = args.task
    if not task:
        print(_c(BOLD + CYAN, "\n  🏗  CRISPY Multi-Agent Build System\n"))
        print("  Team: Scout (research) → Architect (plan) → Coder + Reviewer → Verifier")
        print("  Your approval is required before any code is written.\n")
        try:
            task = input(_c(BOLD, "  What should I build? ") + _c(DIM, "(describe the feature/task)\n  > ")).strip()
        except (KeyboardInterrupt, EOFError):
            print("\n  Cancelled.")
            sys.exit(0)
        if not task:
            print("  No task provided. Exiting.")
            sys.exit(1)

    if len(task) < 10:
        print(_c(RED, f"  Task description too short ({len(task)} chars). Please be more specific."))
        sys.exit(1)

    workspace = args.workspace or str(Path.cwd())

    # Build model routing overrides from args / env
    model_routing: dict = {}
    if args.coder_model:
        model_routing["coder"] = args.coder_model
        os.environ["CRISPY_CODER_MODEL"] = args.coder_model
    if args.reviewer_model:
        model_routing["reviewer"] = args.reviewer_model
        os.environ["CRISPY_REVIEWER_MODEL"] = args.reviewer_model

    run_workflow(task, base=base, api_key=api_key, workspace=workspace, model_routing=model_routing)


if __name__ == "__main__":
    main()

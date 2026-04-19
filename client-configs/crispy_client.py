"""CRISPY Workflow IDE Client — Python example.

Drop this script alongside your project to trigger and monitor
CRISPY workflow runs from any terminal or CI pipeline.

Usage:
    python crispy_client.py build "Add unit tests to the router module"
    python crispy_client.py status
    python crispy_client.py status wf_abc123
    python crispy_client.py approve wf_abc123
    python crispy_client.py reject wf_abc123 "Plan is incomplete"
    python crispy_client.py artifacts wf_abc123
    python crispy_client.py events wf_abc123
    python crispy_client.py watch wf_abc123   # stream events until done

Environment:
    LLM_BASE_URL   — Base URL of the proxy (default: http://localhost:8000)
    LLM_API_KEY    — API key (required)
"""
from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

try:
    import httpx
except ImportError:
    print("Install httpx: pip install httpx")
    sys.exit(1)

BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.environ.get("LLM_API_KEY", "")

if not API_KEY:
    print(
        "Set LLM_API_KEY env var to your proxy API key.\n"
        "Example:  export LLM_API_KEY=your-key-here"
    )
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


def _get(path: str) -> dict[str, Any]:
    url = f"{BASE_URL}{path}"
    with httpx.Client(timeout=30) as client:
        resp = client.get(url, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


def _post(path: str, body: dict[str, Any]) -> dict[str, Any]:
    url = f"{BASE_URL}{path}"
    with httpx.Client(timeout=60) as client:
        resp = client.post(url, headers=HEADERS, json=body)
    resp.raise_for_status()
    return resp.json()


# ── Commands ─────────────────────────────────────────────────────────────────

def cmd_build(task: str) -> None:
    """Create a new CRISPY workflow run."""
    print(f"🚀 Starting workflow: {task[:80]!r}")
    data = _post("/workflow/build", {"request": task, "title": task[:80]})
    run_id = data["run_id"]
    print(f"✅ Created: run_id={run_id}  status={data['status']}")
    print(f"\nMonitor: python crispy_client.py watch {run_id}")
    print(f"Approve: python crispy_client.py approve {run_id}")


def cmd_status(run_id: str | None = None) -> None:
    """List runs or get run status."""
    if run_id:
        run = _get(f"/workflow/{run_id}")
        print(f"\nWorkflow {run['run_id']} — {run['status']}")
        print(f"  title:   {run['title']}")
        print(f"  created: {run['created_at']}")
        print(f"\nPhases:")
        for p in run.get("phases", []):
            icon = {"done": "✓", "failed": "✗", "running": "▶", "pending": "·"}.get(p["status"], "?")
            print(f"  {icon} {p['name']:15s} {p['status']}")
        print(f"\nSlices ({len(run.get('slices', []))}):")
        for s in run.get("slices", []):
            icon = {"applied": "✓", "failed": "✗", "running": "▶", "pending": "·"}.get(s["status"], "?")
            print(f"  {icon} [{s['index']:02d}] {s['title'][:60]} — {s['status']}")
        if run.get("approval_gate"):
            gate = run["approval_gate"]
            print(f"\nGate: {gate['status']}")
    else:
        runs = _get("/workflow/")
        print(f"\nRecent workflow runs ({runs['count']} total):")
        for r in runs.get("runs", [])[:10]:
            icon = {"done": "✅", "failed": "❌", "awaiting_approval": "⏸", "cancelled": "🚫"}.get(r["status"], "▶")
            print(f"  {icon} {r['run_id']}  {r['status']:20s}  {r['title'][:50]}")


def cmd_approve(run_id: str) -> None:
    """Approve the plan gate for a run."""
    data = _post(f"/workflow/{run_id}/approve", {"approved_by": os.environ.get("USER", "human")})
    print(f"✅ Approved {run_id} — status: {data['status']}")
    print(f"\nExecution has begun. Monitor: python crispy_client.py watch {run_id}")


def cmd_reject(run_id: str, reason: str = "Rejected via CLI") -> None:
    """Reject the plan for a run."""
    data = _post(f"/workflow/{run_id}/reject", {"reason": reason, "rejected_by": os.environ.get("USER", "human")})
    print(f"🚫 Rejected {run_id} — status: {data['status']}")


def cmd_artifacts(run_id: str) -> None:
    """List artifacts for a run."""
    data = _get(f"/workflow/{run_id}/artifacts")
    print(f"\nArtifacts for {run_id} ({data['count']} total):")
    for a in data.get("artifacts", []):
        print(f"  {a['name']:35s} {a['size_bytes']:6d}B  {a['phase']}")


def cmd_events(run_id: str, from_pos: int = 0) -> None:
    """Print events for a run."""
    data = _get(f"/workflow/{run_id}/events?from_position={from_pos}")
    print(f"\nEvents for {run_id} ({data['count']} events):")
    for ev in data.get("events", []):
        print(f"  [{ev['position']:3d}] {ev['timestamp']}  {ev['event_type']:25s} {json.dumps(ev['payload'])[:60]}")


def cmd_watch(run_id: str) -> None:
    """Poll and display live status until the run reaches a terminal state."""
    print(f"\n👁  Watching {run_id} (Ctrl+C to stop)\n")
    last_pos = 0
    last_status = ""
    try:
        while True:
            run = _get(f"/workflow/{run_id}")
            status = run["status"]

            if status != last_status:
                print(f"\n  ● Status: {status}")
                last_status = status

            events_data = _get(f"/workflow/{run_id}/events?from_position={last_pos}&limit=50")
            for ev in events_data.get("events", []):
                last_pos = ev["position"] + 1
                etype = ev["event_type"]
                payload = ev.get("payload", {})
                if etype == "phase_started":
                    print(f"    ▶ Phase {payload.get('phase')}")
                elif etype == "phase_complete":
                    print(f"    ✓ Phase {payload.get('phase')} → {payload.get('artifact')}")
                elif etype == "phase_failed":
                    print(f"    ✗ Phase {payload.get('phase')} FAILED: {payload.get('error', '')[:80]}")
                elif etype == "gate_created":
                    print(f"\n  ⏸  AWAITING APPROVAL")
                    print(f"     Run: python crispy_client.py approve {run_id}")
                elif etype == "slices_registered":
                    print(f"    📦 {payload.get('count')} slice(s) registered")
                elif etype == "slice_complete":
                    passed = "✓" if payload.get("check_passed") else "✗"
                    print(f"    {passed} Slice {payload.get('slice_id')}")
                elif etype == "workflow_done":
                    print(f"\n  🎉 DONE — {run_id}")

            if status in ("done", "failed", "cancelled", "awaiting_approval"):
                print(f"\nFinal status: {status}")
                break

            time.sleep(2)
    except KeyboardInterrupt:
        print("\n\nStopped watching.")


# ── Entrypoint ────────────────────────────────────────────────────────────────

COMMANDS = {
    "build": (cmd_build, "build <task>", "Start a workflow"),
    "status": (cmd_status, "status [run_id]", "List runs or get status"),
    "approve": (cmd_approve, "approve <run_id>", "Approve the plan gate"),
    "reject": (cmd_reject, "reject <run_id> [reason]", "Reject the plan"),
    "artifacts": (cmd_artifacts, "artifacts <run_id>", "List artifacts"),
    "events": (cmd_events, "events <run_id>", "Show event log"),
    "watch": (cmd_watch, "watch <run_id>", "Stream live status"),
}


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print("CRISPY Workflow CLI\n")
        print(f"  Base URL: {BASE_URL}")
        print(f"  API Key:  {'set' if API_KEY else '❌ NOT SET (LLM_API_KEY)'}\n")
        for cmd, (_, usage, desc) in COMMANDS.items():
            print(f"  python crispy_client.py {usage:35s} {desc}")
        return

    cmd = args[0]
    if cmd not in COMMANDS:
        print(f"Unknown command: {cmd}. Use --help.")
        sys.exit(1)

    fn, _, _ = COMMANDS[cmd]
    fn_args = args[1:]
    fn(*fn_args)  # type: ignore[call-arg]


if __name__ == "__main__":
    main()

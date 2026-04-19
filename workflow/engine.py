"""workflow/engine.py — WorkflowEngine: CRISPY phase sequencer.

The engine is the single orchestrator of a WorkflowRun lifecycle.  It:
  1. Creates and persists WorkflowRuns in SQLite.
  2. Sequences phases (context → research → … → plan).
  3. HARD-STOPS at the ApprovalGate (status=awaiting_approval).
  4. Resumes execution only after POST /workflow/{id}/approve.
  5. Sequences slices through execute → review → verify.
  6. Records every state transition as an event in the event log.

Persistence model
-----------------
WorkflowRuns are stored in a SQLite table (workflow_runs) as JSON blobs.
This is intentionally simple — the entire WorkflowRun is serialised to
JSON because it already contains typed sub-objects (Phase, Slice, etc.)
that Pydantic handles cleanly.  For large deployments a proper relational
schema would be preferable; for local-first use this is sufficient.

The event log reuses agent/state.py's AgentSessionStore because it is
already a battle-tested, SQLite-backed, append-only stream.  We create
one AgentSession per WorkflowRun and write workflow events into it.

Thread safety
-------------
A reentrant lock (self._lock) guards all DB writes and in-memory dict
mutations.  Phase execution and LLM calls happen outside the lock,
keeping it coarse-grained but safe.

Usage::

    engine = WorkflowEngine(ollama_base="http://localhost:11434")
    run = await engine.create_run(request="...", title="...")
    # Background task starts phase execution automatically.
    # Workflow pauses at awaiting_approval.
    run = engine.get(run.run_id)
    engine.approve(run.run_id, approved_by="human")
    # Execution resumes automatically.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import secrets
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from workflow.artifact_store import ArtifactStore
from workflow.models import (
    ApprovalGate,
    Artifact,
    CheckRun,
    ModelRoutingConfig,
    Phase,
    PhaseType,
    Slice,
    WorkflowBuildRequest,
    WorkflowRun,
    WorkflowStatus,
    _now,
)
from workflow.phases import PhaseRunner

log = logging.getLogger("crispy-engine")

_DEFAULT_DB = os.environ.get("CRISPY_WORKFLOW_DB", ".data/workflow/workflow.db")

# Ordered phase sequence (before the gate)
_PRE_GATE_PHASES: list[PhaseType] = [
    "context",
    "research",
    "investigate",
    "structure",
    "plan",
]

# Phases executed after approval
_POST_GATE_PHASES: list[PhaseType] = ["report"]

# Mapping each phase to the correct agent role (mirrors phases.py)
_PHASE_ROLE = {
    "context": "scout",
    "research": "scout",
    "investigate": "scout",
    "structure": "architect",
    "plan": "architect",
    "execute": "coder",
    "review": "reviewer",
    "verify": "verifier",
    "report": "architect",
}


class WorkflowEngine:
    """CRISPY workflow engine — phase sequencer + gate controller.

    One engine instance manages all workflow runs for the server process.
    Use ``get_engine()`` to obtain the shared singleton.
    """

    def __init__(
        self,
        *,
        ollama_base: str | None = None,
        db_path: str | Path | None = None,
        artifacts_root: str | Path | None = None,
        workspace_root: str | Path | None = None,
    ) -> None:
        self._base = (
            (ollama_base or os.environ.get("OLLAMA_BASE", "http://localhost:11434"))
            .rstrip("/")
        )
        self._workspace = Path(workspace_root or Path.cwd())
        self._db_path = str(Path(db_path or _DEFAULT_DB))
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

        self._artifact_store = ArtifactStore(
            artifacts_root=artifacts_root,
            db_path=db_path or _DEFAULT_DB,
        )
        self._phase_runner = PhaseRunner(
            ollama_base=self._base,
            artifact_store=self._artifact_store,
            workspace_root=self._workspace,
        )
        # AgentSwarm sits above PhaseRunner and enforces:
        #   • role-locked permissions (write, execute, review)
        #   • coder model ≠ reviewer model invariant
        # Import lazily so the agents package is optional when running tests
        # that only exercise the engine in isolation.
        try:
            from agents.swarm import AgentSwarm
            self._swarm: AgentSwarm | None = AgentSwarm(
                ollama_base=self._base,
                artifact_store=self._artifact_store,
                workspace_root=self._workspace,
            )
        except ImportError:
            self._swarm = None
        self._lock = threading.RLock()
        self._runs: dict[str, WorkflowRun] = {}
        self._init_db()
        self._load_all()
        log.info(
            "WorkflowEngine ready: base=%s db=%s runs=%d swarm=%s",
            self._base, self._db_path, len(self._runs),
            "yes" if self._swarm else "no (agents package not found)",
        )

    @property
    def swarm(self):
        """Return the AgentSwarm singleton if available, else None."""
        return self._swarm

    # ── DB internals ─────────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_runs (
                    run_id      TEXT PRIMARY KEY,
                    status      TEXT NOT NULL,
                    data        TEXT NOT NULL,
                    created_at  TEXT NOT NULL,
                    updated_at  TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_events (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id      TEXT NOT NULL,
                    position    INTEGER NOT NULL,
                    event_type  TEXT NOT NULL,
                    payload     TEXT NOT NULL,
                    timestamp   TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_wf_events "
                "ON workflow_events (run_id, position)"
            )
            conn.commit()

    def _load_all(self) -> None:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT data FROM workflow_runs ORDER BY created_at"
            ).fetchall()
        for row in rows:
            try:
                run = WorkflowRun.model_validate_json(row["data"])
                self._runs[run.run_id] = run
            except Exception as exc:
                log.warning("Could not deserialize workflow run: %s", exc)
        log.info("Loaded %d workflow run(s) from DB", len(self._runs))

    def _save(self, run: WorkflowRun) -> None:
        run.updated_at = _now()
        data = run.model_dump_json()
        with self._lock:
            self._runs[run.run_id] = run
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO workflow_runs
                        (run_id, status, data, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (run.run_id, run.status, data, run.created_at, run.updated_at),
                )
                conn.commit()

    def _log_event(
        self, run_id: str, event_type: str, payload: dict[str, Any]
    ) -> None:
        """Append an event to the workflow event log."""
        try:
            run = self._runs.get(run_id)
            position = run.event_count if run else 0
            now = _now()
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO workflow_events
                        (run_id, position, event_type, payload, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (run_id, position, event_type, json.dumps(payload), now),
                )
                conn.commit()
            if run:
                run.event_count += 1
        except Exception as exc:
            log.debug("Event log write failed (non-fatal): %s", exc)

    # ── Public API ────────────────────────────────────────────────────────────

    async def create_run(self, req: WorkflowBuildRequest) -> WorkflowRun:
        """Create a new WorkflowRun and begin pre-gate phase execution.

        The run is immediately persisted and returned.  Phase execution
        starts asynchronously in the background — the caller does not block
        on LLM calls.
        """
        run_id = "wf_" + secrets.token_hex(8)
        now = _now()

        # Build Phase records for pre-gate phases
        phases: list[Phase] = []
        for i, ptype in enumerate(_PRE_GATE_PHASES):
            phases.append(
                Phase(
                    phase_id=f"ph_{run_id}_{i}",
                    run_id=run_id,
                    name=ptype,
                    status="pending",
                    agent_role=_PHASE_ROLE[ptype],  # type: ignore[arg-type]
                )
            )
        # Add post-gate report phase
        phases.append(
            Phase(
                phase_id=f"ph_{run_id}_report",
                run_id=run_id,
                name="report",
                status="pending",
                agent_role="architect",
            )
        )

        run = WorkflowRun(
            run_id=run_id,
            title=req.title or req.request[:80],
            request=req.request,
            status="pending",
            phases=phases,
            slices=[],
            artifacts=[],
            approval_gate=None,
            model_routing=req.model_routing,
            workspace_root=req.workspace_root or str(self._workspace),
            created_at=now,
            updated_at=now,
        )

        with self._lock:
            self._save(run)

        self._log_event(run_id, "workflow_created", {"request": req.request[:200]})
        log.info("WorkflowRun created: id=%s title=%r", run_id, run.title)

        # Kick off pre-gate execution in the background
        asyncio.create_task(self._run_pre_gate_phases(run_id))

        return run

    def get(self, run_id: str) -> WorkflowRun | None:
        """Return current WorkflowRun snapshot or None."""
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return None
            return WorkflowRun.model_validate(run.model_dump())

    def list_runs(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        status: WorkflowStatus | None = None,
    ) -> list[WorkflowRun]:
        """Return a paginated list of runs, newest first."""
        with self._lock:
            runs = sorted(
                self._runs.values(),
                key=lambda r: r.created_at,
                reverse=True,
            )
        if status:
            runs = [r for r in runs if r.status == status]
        return [WorkflowRun.model_validate(r.model_dump()) for r in runs[offset : offset + limit]]

    def approve(self, run_id: str, *, approved_by: str = "human") -> WorkflowRun:
        """Approve the plan — lifts the ApprovalGate and resumes execution.

        Raises ValueError if the run is not in awaiting_approval state or
        the gate does not exist.
        """
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                raise KeyError(f"WorkflowRun {run_id!r} not found")
            if run.status != "awaiting_approval":
                raise ValueError(
                    f"Cannot approve run {run_id}: status is {run.status!r}, "
                    f"expected 'awaiting_approval'"
                )
            if run.approval_gate is None:
                raise ValueError(f"Run {run_id} has no approval gate")
            run.approval_gate.status = "approved"
            run.approval_gate.approved_by = approved_by
            run.approval_gate.approved_at = _now()
            run.status = "executing"
            self._save(run)

        self._log_event(run_id, "gate_approved", {"approved_by": approved_by})
        log.info("ApprovalGate approved: run=%s by=%s", run_id, approved_by)

        # Resume post-gate execution
        asyncio.create_task(self._run_post_gate(run_id))
        return self.get(run_id)  # type: ignore[return-value]

    def reject(
        self, run_id: str, *, reason: str, rejected_by: str = "human"
    ) -> WorkflowRun:
        """Reject the plan — marks run as failed."""
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                raise KeyError(f"WorkflowRun {run_id!r} not found")
            if run.status != "awaiting_approval":
                raise ValueError(
                    f"Cannot reject run {run_id}: status is {run.status!r}"
                )
            if run.approval_gate:
                run.approval_gate.status = "rejected"
                run.approval_gate.rejection_reason = reason
            run.status = "failed"
            self._save(run)

        self._log_event(run_id, "gate_rejected", {"reason": reason, "by": rejected_by})
        log.info("ApprovalGate rejected: run=%s reason=%r", run_id, reason[:80])
        return self.get(run_id)  # type: ignore[return-value]

    def cancel(self, run_id: str) -> WorkflowRun:
        """Cancel a non-terminal run."""
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                raise KeyError(f"WorkflowRun {run_id!r} not found")
            if run.status in ("done", "failed", "cancelled"):
                raise ValueError(f"Run {run_id} is already terminal: {run.status}")
            run.status = "cancelled"
            self._save(run)

        self._log_event(run_id, "workflow_cancelled", {})
        log.info("WorkflowRun cancelled: id=%s", run_id)
        return self.get(run_id)  # type: ignore[return-value]

    def resume(self, run_id: str) -> WorkflowRun:
        """Resume a paused or failed run from its last completed phase."""
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                raise KeyError(f"WorkflowRun {run_id!r} not found")
            if run.status == "done":
                raise ValueError(f"Run {run_id} is already done")
            if run.status == "cancelled":
                raise ValueError(f"Cancelled runs cannot be resumed")

        # Determine where to restart
        if run.status == "awaiting_approval":
            log.info("Run %s is awaiting approval, nothing to resume", run_id)
            return self.get(run_id)  # type: ignore[return-value]

        pre_gate_done = all(
            p.status == "done"
            for p in run.phases
            if p.name in _PRE_GATE_PHASES
        )
        if not pre_gate_done:
            asyncio.create_task(self._run_pre_gate_phases(run_id))
        else:
            asyncio.create_task(self._run_post_gate(run_id))

        self._log_event(run_id, "workflow_resumed", {})
        return self.get(run_id)  # type: ignore[return-value]

    def get_events(
        self, run_id: str, *, from_position: int = 0, limit: int = 200
    ) -> list[dict[str, Any]]:
        """Return a positional slice of the event log for a run."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT position, event_type, payload, timestamp
                FROM workflow_events
                WHERE run_id=? AND position>=?
                ORDER BY position
                LIMIT ?
                """,
                (run_id, from_position, limit),
            ).fetchall()
        return [
            {
                "position": row["position"],
                "event_type": row["event_type"],
                "payload": json.loads(row["payload"]),
                "timestamp": row["timestamp"],
            }
            for row in rows
        ]

    # ── Slice execution ───────────────────────────────────────────────────────

    async def run_slice(self, run_id: str, slice_id: str, *, force: bool = False) -> Slice:
        """Execute, review, and verify a single slice.

        Returns the updated Slice.  Raises ValueError on constraint violations.
        """
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                raise KeyError(f"WorkflowRun {run_id!r} not found")
            sl = run.slice_by_id(slice_id)
            if sl is None:
                raise KeyError(f"Slice {slice_id!r} not found in run {run_id}")
            if sl.status == "applied" and not force:
                return WorkflowRun.model_validate(run.model_dump()).slice_by_id(slice_id)  # type: ignore[return-value]

        await self._execute_slice(run_id, slice_id)
        with self._lock:
            run = self._runs[run_id]
            return run.slice_by_id(slice_id)  # type: ignore[return-value]

    async def run_verify(self, run_id: str) -> list[CheckRun]:
        """Trigger verification for all applied-but-unverified slices."""
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                raise KeyError(f"WorkflowRun {run_id!r} not found")
            unverified = [
                s for s in run.slices
                if s.status == "applied" and s.check_run is None
            ]

        results: list[CheckRun] = []
        for sl in unverified:
            cr = await self._verify_slice(run_id, sl.slice_id)
            if cr:
                results.append(cr)
        return results

    # ── Phase orchestration ───────────────────────────────────────────────────

    async def _run_pre_gate_phases(self, run_id: str) -> None:
        """Execute all phases up to (but not including) the ApprovalGate."""
        for phase_type in _PRE_GATE_PHASES:
            run = self.get(run_id)
            if run is None or run.status in ("cancelled", "failed"):
                return
            await self._run_single_phase(run_id, phase_type)

        # After plan phase, erect the approval gate
        with self._lock:
            run = self._runs.get(run_id)
            if run is None or run.status in ("cancelled", "failed"):
                return
            gate = ApprovalGate(
                gate_id="gate_" + secrets.token_hex(6),
                run_id=run_id,
                status="pending",
            )
            run.approval_gate = gate
            run.status = "awaiting_approval"
            self._save(run)

        self._log_event(
            run_id,
            "gate_created",
            {"gate_id": run.approval_gate.gate_id},  # type: ignore[union-attr]
        )
        log.info(
            "WorkflowRun %s paused at ApprovalGate — awaiting human approval", run_id
        )

    async def _run_post_gate(self, run_id: str) -> None:
        """Execute slices, then review, verify, and report."""
        run = self.get(run_id)
        if run is None:
            return

        # Parse slices from the plan artifact
        await self._parse_and_register_slices(run_id)

        # Execute each slice in sequence
        run = self.get(run_id)  # type: ignore[assignment]
        for sl in (run.slices if run else []):
            cur = self.get(run_id)
            if cur is None or cur.status in ("cancelled", "failed"):
                return
            await self._execute_slice(run_id, sl.slice_id)

        # Final report phase
        run = self.get(run_id)
        if run and run.status not in ("cancelled", "failed"):
            await self._run_single_phase(run_id, "report")
            with self._lock:
                r = self._runs.get(run_id)
                if r:
                    r.status = "done"
                    self._save(r)
            self._log_event(run_id, "workflow_done", {})
            log.info("WorkflowRun %s completed successfully", run_id)

    async def _run_single_phase(self, run_id: str, phase_type: PhaseType) -> None:
        """Run one phase, update its status, and persist the artifact."""
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return
            phase = run.phase_by_type(phase_type)
            if phase is None:
                return
            phase.status = "running"
            phase.started_at = _now()
            run.status = phase_type  # type: ignore[assignment]
            self._save(run)

        self._log_event(run_id, "phase_started", {"phase": phase_type})
        log.info("Phase started: run=%s phase=%s", run_id, phase_type)

        try:
            run = self.get(run_id)  # type: ignore[assignment]
            prior_artifacts = list(run.artifacts) if run else []  # type: ignore[union-attr]
            # Use AgentSwarm if available (enforces role permissions + coder≠reviewer)
            if self._swarm is not None:
                art = await self._swarm.run_phase(
                    run_id=run_id,
                    phase=phase_type,
                    request=run.request,  # type: ignore[union-attr]
                    routing=run.model_routing,  # type: ignore[union-attr]
                    prior_artifacts=prior_artifacts,
                )
            else:
                art = await self._phase_runner.run_phase(
                    run_id=run_id,
                    phase=phase_type,
                    request=run.request,  # type: ignore[union-attr]
                    routing=run.model_routing,  # type: ignore[union-attr]
                    prior_artifacts=prior_artifacts,
                )
            with self._lock:
                r = self._runs[run_id]
                ph = r.phase_by_type(phase_type)
                if ph:
                    ph.status = "done"
                    ph.finished_at = _now()
                    ph.artifact_paths.append(art.path)
                r.artifacts.append(art)
                self._save(r)
            self._log_event(
                run_id,
                "phase_complete",
                {"phase": phase_type, "artifact": art.name},
            )
            log.info("Phase complete: run=%s phase=%s", run_id, phase_type)

        except Exception as exc:
            log.exception("Phase failed: run=%s phase=%s error=%s", run_id, phase_type, exc)
            with self._lock:
                r = self._runs.get(run_id)
                if r:
                    ph = r.phase_by_type(phase_type)
                    if ph:
                        ph.status = "failed"
                        ph.finished_at = _now()
                        ph.error = str(exc)
                    r.status = "failed"
                    self._save(r)
            self._log_event(
                run_id, "phase_failed", {"phase": phase_type, "error": str(exc)}
            )

    async def _parse_and_register_slices(self, run_id: str) -> None:
        """Extract slice breakdown from plan.md and create Slice records."""
        plan_content = self._artifact_store.content_by_name(run_id, "plan.md") or ""
        slices = _extract_slices_from_plan(run_id, plan_content)

        if not slices:
            log.warning(
                "No slices found in plan.md for run=%s — creating single default slice",
                run_id,
            )
            slices = [
                Slice(
                    slice_id="sl_" + secrets.token_hex(6),
                    run_id=run_id,
                    index=1,
                    title="Full implementation",
                    description=f"Implement the requested change as described in plan.md",
                    files=[],
                )
            ]

        with self._lock:
            run = self._runs.get(run_id)
            if run:
                run.slices = slices
                self._save(run)

        self._log_event(run_id, "slices_registered", {"count": len(slices)})
        log.info("Slices registered: run=%s count=%d", run_id, len(slices))

    async def _execute_slice(self, run_id: str, slice_id: str) -> None:
        """Execute → Review → Verify a single slice."""
        # --- EXECUTE ---
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return
            sl = run.slice_by_id(slice_id)
            if sl is None:
                return
            sl.status = "running"
            sl.started_at = _now()
            self._save(run)

        self._log_event(run_id, "slice_started", {"slice_id": slice_id})

        try:
            run_snap = self.get(run_id)
            if run_snap is None:
                return
            sl_snap = run_snap.slice_by_id(slice_id)
            if sl_snap is None:
                return
            # Use AgentSwarm (enforces coder≠reviewer model invariant)
            if self._swarm is not None:
                slice_art = await self._swarm.run_slice_execute(
                    run_id=run_id, sl=sl_snap,
                    routing=run_snap.model_routing,
                    prior_artifacts=run_snap.artifacts,
                )
                review_art = await self._swarm.run_slice_review(
                    run_id=run_id, sl=sl_snap,
                    routing=run_snap.model_routing,
                    slice_artifact=slice_art,
                )
                check_run = await self._swarm.run_slice_verify(
                    run_id=run_id, sl=sl_snap,
                    routing=run_snap.model_routing,
                )
            else:
                slice_art = await self._phase_runner.run_slice_execute(
                    run_id=run_id, sl=sl_snap,
                    routing=run_snap.model_routing,
                    prior_artifacts=run_snap.artifacts,
                )
                review_art = await self._phase_runner.run_slice_review(
                    run_id=run_id, sl=sl_snap,
                    routing=run_snap.model_routing,
                    slice_artifact=slice_art,
                )
                ws = Path(run_snap.workspace_root or str(self._workspace))
                check_run = await self._phase_runner.run_slice_verify(
                    run_id=run_id, sl=sl_snap,
                    routing=run_snap.model_routing,
                    workspace_root=ws,
                )

            with self._lock:
                r = self._runs[run_id]
                s = r.slice_by_id(slice_id)
                if s:
                    s.status = "applied" if check_run.passed else "failed"
                    s.finished_at = _now()
                    s.check_run = check_run
                    s.artifact_paths.extend([slice_art.path, review_art.path])
                    s.error = None if check_run.passed else f"Verification failed (exit_code={check_run.exit_code})"
                r.artifacts.extend([slice_art, review_art])
                self._save(r)

            status = "applied" if check_run.passed else "failed"
            self._log_event(
                run_id,
                "slice_complete",
                {
                    "slice_id": slice_id,
                    "status": status,
                    "check_passed": check_run.passed,
                    "exit_code": check_run.exit_code,
                },
            )
            log.info(
                "Slice complete: run=%s slice=%s status=%s", run_id, slice_id, status
            )

        except Exception as exc:
            log.exception(
                "Slice execution failed: run=%s slice=%s error=%s", run_id, slice_id, exc
            )
            with self._lock:
                r = self._runs.get(run_id)
                if r:
                    s = r.slice_by_id(slice_id)
                    if s:
                        s.status = "failed"
                        s.finished_at = _now()
                        s.error = str(exc)
                    self._save(r)
            self._log_event(
                run_id, "slice_failed", {"slice_id": slice_id, "error": str(exc)}
            )

    async def _verify_slice(self, run_id: str, slice_id: str) -> CheckRun | None:
        """Verify a single slice (no execute/review, just verify)."""
        run = self.get(run_id)
        if run is None:
            return None
        sl = run.slice_by_id(slice_id)
        if sl is None:
            return None
        ws = Path(run.workspace_root or str(self._workspace))
        try:
            check_run = await self._phase_runner.run_slice_verify(
                run_id=run_id,
                sl=sl,
                routing=run.model_routing,
                workspace_root=ws,
            )
            with self._lock:
                r = self._runs[run_id]
                s = r.slice_by_id(slice_id)
                if s:
                    s.check_run = check_run
                self._save(r)
            return check_run
        except Exception as exc:
            log.warning("Verify slice failed: %s", exc)
            return None


# ── Slice extraction helper ───────────────────────────────────────────────────

def _extract_slices_from_plan(run_id: str, plan_content: str) -> list[Slice]:
    """Extract slice definitions from a plan.md artifact.

    Looks for sections matching:
      ## Slice N: <title>
      <description>
      Files: file1.py, file2.py

    Returns a list of Slice objects.  Returns empty list if no slices found
    (caller will create a single default slice).
    """
    import re

    slices: list[Slice] = []
    # Match ## Slice N: Title patterns
    pattern = re.compile(
        r"##\s+Slice\s+(\d+)[:\.]?\s*([^\n]+)\n(.*?)(?=##\s+Slice\s+\d+|\Z)",
        re.S | re.I,
    )
    for m in pattern.finditer(plan_content):
        index = int(m.group(1))
        title = m.group(2).strip()
        body = m.group(3).strip()
        # Extract files from "Files: ..." line
        files: list[str] = []
        files_match = re.search(r"[Ff]iles?[:\s]+([^\n]+)", body)
        if files_match:
            raw_files = files_match.group(1)
            files = [f.strip().strip("`") for f in raw_files.split(",") if f.strip()]
        slices.append(
            Slice(
                slice_id="sl_" + secrets.token_hex(6),
                run_id=run_id,
                index=index,
                title=title,
                description=body[:2000],
                files=files,
            )
        )

    return sorted(slices, key=lambda s: s.index)


# ── Singleton ─────────────────────────────────────────────────────────────────

_engine: WorkflowEngine | None = None


def get_engine() -> WorkflowEngine:
    """Return the shared WorkflowEngine singleton (lazy-init)."""
    global _engine
    if _engine is None:
        _engine = WorkflowEngine()
    return _engine


def reset_engine() -> None:
    """Reset the singleton (test helper)."""
    global _engine
    _engine = None

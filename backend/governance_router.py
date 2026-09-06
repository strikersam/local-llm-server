"""backend/governance_router.py — read and operate the governance layer.

Mounted on ``backend.server.app`` via ``build_governance_router(get_current_user)``.
Follows the builder pattern already used by ``spec_router`` and ``ceo_router``
so authentication stays injected rather than imported, which is what keeps
this module testable without booting the whole server.

Routes::

    GET  /api/governance/status              backend, isolation posture, sandboxes
    GET  /api/governance/policy              the effective policy document
    GET  /api/governance/policy/raw          the raw policy YAML (for the editor)
    POST /api/governance/policy/reload       re-read the policy file (admin)
    POST /api/governance/policy/simulate     dry-run a decision (admin)
    POST /api/governance/policy/validate     validate a proposed policy + diff (admin)
    POST /api/governance/policy/propose      open a PR carrying a proposed policy (admin)
    GET  /api/governance/audit               recent audit events, filterable
    GET  /api/governance/metrics             counters for dashboards/Prometheus
    GET  /api/governance/approvals           pending approvals
    GET  /api/governance/approvals/all       recent approvals incl. resolved
    POST /api/governance/approvals/{id}/approve
    POST /api/governance/approvals/{id}/deny
    GET  /api/governance/sandboxes           live sandboxes
    POST /api/governance/sandboxes/reap      destroy expired sandboxes (admin)
    DELETE /api/governance/sandboxes/{id}    destroy one sandbox (admin)
    GET  /api/governance/budget              all live session budgets (per-tool breakdown)
    GET  /api/governance/budget/{session_id} one session's live budget

Every route requires an authenticated user; mutating routes additionally
require ``role=admin``. Reads are admin-gated too, because an audit trail
names repositories, branches, file paths, and agent owners — an inventory of
what the platform touches is exactly what an attacker wants first.

This API never exposes secret values (the credential surface governs secret
*names* only) and never rewrites the live policy file over HTTP. In-product
authoring goes the safe way instead: ``/policy/validate`` checks a proposed
document against the real engine and the org baseline, and ``/policy/propose``
opens a pull request carrying it. Policy still reaches production the way every
other change does — review, CI, merge — so the audit trail's "who changed the
rules" question stays answerable (the proposer is recorded, and the merge is a
reviewed git commit), and no compromised admin session can silently disable the
controls: it can only open a PR that a human must still merge. The baseline
guardrails can be tightened from the dashboard but never loosened.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

from fastapi import APIRouter, Body, Depends, HTTPException, Query

log = logging.getLogger("governance.api")


def _require_admin(user: dict) -> dict:
    """Reject non-admin callers.

    Mirrors the RBAC check used elsewhere in this backend rather than
    inventing a second notion of "admin" — one auth system, per the
    constitution's no-duplicate-authentication rule.
    """
    role = str((user or {}).get("role", "")).lower()
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


def build_governance_router(get_current_user: Callable[..., Any]) -> APIRouter:
    router = APIRouter(prefix="/api/governance", tags=["governance"])

    # ── Status ───────────────────────────────────────────────────────────

    @router.get("/status")
    async def governance_status(user: dict = Depends(get_current_user)) -> dict:
        """What is actually in force right now.

        Reports the live sandbox backend and its real isolation properties —
        including ``isolation: none`` on the local backend and a rootful
        Docker daemon. A governance dashboard that overstates containment is
        worse than no dashboard, because it converts an unknown risk into a
        believed-safe one.
        """
        _require_admin(user)
        from packages.config import settings
        from packages.governance.policy import get_policy_engine
        from packages.governance.sandbox import get_sandbox_manager

        engine = get_policy_engine()
        try:
            sandbox_status = await get_sandbox_manager().status()
        except Exception as exc:  # noqa: BLE001 - a probe failure must not 500 the page
            log.warning("Sandbox status probe failed: %s", exc)
            sandbox_status = {"backend": "unknown", "error": str(exc)}

        return {
            "enabled": settings.governance_enabled,
            "mode": engine.mode.value,
            "enforcing": engine.mode.value == "enforce",
            "policy_source": engine.source,
            "policy_version": engine.version,
            "groups": engine.group_names(),
            "auto_approve": settings.governance_auto_approve,
            "sandbox": sandbox_status,
        }

    # ── Policy ───────────────────────────────────────────────────────────

    @router.get("/policy")
    async def get_policy(user: dict = Depends(get_current_user)) -> dict:
        _require_admin(user)
        from packages.governance.policy import get_policy_engine

        return get_policy_engine().describe()

    @router.post("/policy/reload")
    async def reload_policy(user: dict = Depends(get_current_user)) -> dict:
        """Re-read the policy file without restarting the process.

        Matters operationally: the response to a bad rule discovered at 3am
        should be a one-line edit and a reload, not a redeploy of a platform
        that takes 30 seconds to cold-start.
        """
        _require_admin(user)
        from packages.config import settings
        from packages.governance.policy import get_policy_engine

        engine = get_policy_engine()
        applied = engine.reload(settings.governance_policy_path)
        log.info("Governance policy reloaded (applied=%s, mode=%s)", applied, engine.mode.value)
        return {
            "reloaded": applied,
            "mode": engine.mode.value,
            "source": engine.source,
            "version": engine.version,
            "note": None if applied else "file missing or invalid — embedded default is active",
        }

    @router.post("/policy/simulate")
    async def simulate_policy(
        body: dict = Body(...), user: dict = Depends(get_current_user)
    ) -> dict:
        """Dry-run a decision without performing the action.

        The tool that makes ``mode: enforce`` safe to adopt: it answers "what
        would this policy do to this call?" without waiting for an agent to
        make it. Purely evaluative — no action is taken and no budget is
        charged.
        """
        _require_admin(user)
        from packages.governance.enforcement import evaluate_call
        from packages.governance.identity import resolve_identity
        from packages.governance.policy import Surface, get_policy_engine

        tool = str(body.get("tool") or "")
        if not tool:
            raise HTTPException(status_code=400, detail="'tool' is required")
        args = body.get("args") or {}
        if not isinstance(args, dict):
            raise HTTPException(status_code=400, detail="'args' must be an object")

        surface_override: Surface | None = None
        if body.get("surface"):
            try:
                surface_override = Surface(str(body["surface"]))
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"unknown surface; valid: {[s.value for s in Surface]}",
                ) from None

        identity = resolve_identity(
            agent_name=body.get("agent_name") or "simulated-agent",
            owner=str(user.get("email") or "operator"),
            policy_group=body.get("policy_group"),
        )
        # Shares one implementation with the live enforcement path: a
        # simulator that judged differently from the enforcer would mislead
        # exactly the operator trying to decide whether enforcement is safe.
        decision, surface, action = evaluate_call(
            get_policy_engine(), identity, tool, args, surface=surface_override
        )
        return {
            "tool": tool,
            "classified_surface": surface.value,
            "classified_action": action,
            "identity": identity.to_dict(),
            "decision": decision.to_dict(),
            "would_block": decision.would_block,
        }

    @router.get("/policy/raw")
    async def get_policy_raw(user: dict = Depends(get_current_user)) -> dict:
        """The raw policy YAML the editor loads.

        ``/policy`` returns the compiled document; the authoring editor needs
        the source file verbatim (comments and all) so an operator edits what
        they see. Falls back to an empty string when the file is missing — the
        embedded default is in force and the editor starts from a blank slate.
        """
        _require_admin(user)
        from pathlib import Path

        from packages.config import settings

        path = Path(settings.governance_policy_path)
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            text = ""
        return {"path": str(path), "text": text, "exists": bool(text)}

    @router.post("/policy/validate")
    async def validate_policy(
        body: dict = Body(...), user: dict = Depends(get_current_user)
    ) -> dict:
        """Validate a proposed policy without applying it, and return a diff.

        Powers the editor's live feedback: parse errors, a document the engine
        cannot compile, and — the load-bearing check — any loosening of the org
        baseline are all reported here before the operator opens a PR.
        """
        _require_admin(user)
        from pathlib import Path

        from packages.config import settings
        from packages.governance.authoring import diff_policy, parse_policy_text, validate_policy_text

        text = body.get("text")
        if not isinstance(text, str) or not text.strip():
            raise HTTPException(status_code=400, detail="'text' (policy YAML) is required")

        try:
            current_text = Path(settings.governance_policy_path).read_text(encoding="utf-8")
        except FileNotFoundError:
            current_text = ""
        current_document, _ = parse_policy_text(current_text) if current_text else (None, None)

        result = validate_policy_text(text, current_document=current_document)
        return {**result.to_dict(), "diff": diff_policy(current_text, text)}

    @router.post("/policy/propose")
    async def propose_policy(
        body: dict = Body(...), user: dict = Depends(get_current_user)
    ) -> dict:
        """Open a pull request carrying a proposed policy change.

        The live policy file is never written from here. The proposal is
        validated, committed to a new branch, and turned into a PR that a human
        reviews and merges — the same path as any other change. Requires a
        GitHub credential; without one there is no way to open the PR and the
        route reports that rather than pretending to have queued the change.
        """
        _require_admin(user)
        from packages.config import settings
        from packages.governance.authoring import propose_policy_change

        text = body.get("text")
        if not isinstance(text, str) or not text.strip():
            raise HTTPException(status_code=400, detail="'text' (policy YAML) is required")
        reason = str(body.get("reason") or "").strip()

        if not settings.gh_pat:
            raise HTTPException(
                status_code=503,
                detail="No GitHub credential configured; cannot open a policy proposal PR",
            )

        from pathlib import Path

        from agent.github_tools import GitHubTools

        try:
            current_text = Path(settings.governance_policy_path).read_text(encoding="utf-8")
        except FileNotFoundError:
            current_text = ""

        actor = str(user.get("email") or user.get("id") or "operator")
        gh = GitHubTools(token=settings.gh_pat)
        try:
            return await propose_policy_change(
                text,
                actor=actor,
                reason=reason,
                gh=gh,
                repo=settings.github_repository,
                current_text=current_text,
            )
        except ValueError as exc:
            # Validation failed — a bad proposal, not a server fault.
            raise HTTPException(status_code=400, detail="Internal server error") from None
        except Exception as exc:  # noqa: BLE001 - GitHub API failure, etc.
            log.exception("Policy proposal PR failed")
            raise HTTPException(status_code=502, detail="Failed to open policy proposal PR") from None

    # ── Audit ────────────────────────────────────────────────────────────

    @router.get("/audit")
    async def get_audit(
        limit: int = Query(default=100, ge=1, le=1000),
        agent_id: str | None = Query(default=None),
        session_id: str | None = Query(default=None),
        surface: str | None = Query(default=None),
        decision: str | None = Query(default=None),
        user: dict = Depends(get_current_user),
    ) -> dict:
        """Recent audit events, newest first.

        Arguments and results in these events were redacted at write time, so
        this response cannot leak a secret that reached a tool argument.
        """
        _require_admin(user)
        from packages.governance.audit import get_audit_log

        events = get_audit_log().recent(
            limit=limit, agent_id=agent_id, session_id=session_id,
            surface=surface, decision=decision,
        )
        return {"events": events, "count": len(events)}

    @router.get("/metrics")
    async def get_metrics(user: dict = Depends(get_current_user)) -> dict:
        """Counters for dashboards and alerting.

        ``would_block`` is the number that decides whether ``enforce`` is safe
        to turn on: sustained zero means the rules only catch what you meant
        them to catch.
        """
        _require_admin(user)
        from packages.governance.audit import get_audit_log
        from packages.governance.enforcement import get_gate
        from packages.governance.policy import get_policy_engine

        return {
            "mode": get_policy_engine().mode.value,
            "audit": get_audit_log().summary(),
            "budgets": get_gate().budgets.all(),
        }

    # ── Approvals ────────────────────────────────────────────────────────

    @router.get("/approvals")
    async def list_pending(user: dict = Depends(get_current_user)) -> dict:
        _require_admin(user)
        from packages.governance.approvals import get_approval_store

        pending = get_approval_store().pending()
        return {"approvals": pending, "count": len(pending)}

    @router.get("/approvals/all")
    async def list_all_approvals(
        limit: int = Query(default=100, ge=1, le=500),
        user: dict = Depends(get_current_user),
    ) -> dict:
        _require_admin(user)
        from packages.governance.approvals import get_approval_store

        approvals = get_approval_store().all(limit=limit)
        return {"approvals": approvals, "count": len(approvals)}

    async def _decide(approval_id: str, approved: bool, user: dict, note: str | None) -> dict:
        from packages.governance.approvals import get_approval_store

        # The operator's identity is recorded on the request itself, which is
        # the correct audit surface for identity — it is deliberately not
        # written to the application log (AGENTS.md logging rule).
        decided_by = str(user.get("email") or user.get("id") or "operator")
        request = get_approval_store().resolve(
            approval_id, approved=approved, resolved_by=decided_by, note=note
        )
        if request is None:
            raise HTTPException(status_code=404, detail="Approval request not found")
        log.info("Approval %s resolved: %s", approval_id, request.status.value)
        return request.to_dict()

    @router.post("/approvals/{approval_id}/approve")
    async def approve(
        approval_id: str,
        body: dict = Body(default_factory=dict),
        user: dict = Depends(get_current_user),
    ) -> dict:
        _require_admin(user)
        return await _decide(approval_id, True, user, body.get("note"))

    @router.post("/approvals/{approval_id}/deny")
    async def deny(
        approval_id: str,
        body: dict = Body(default_factory=dict),
        user: dict = Depends(get_current_user),
    ) -> dict:
        _require_admin(user)
        return await _decide(approval_id, False, user, body.get("note"))

    # ── Sandboxes ────────────────────────────────────────────────────────

    @router.get("/sandboxes")
    async def list_sandboxes(user: dict = Depends(get_current_user)) -> dict:
        _require_admin(user)
        from packages.governance.sandbox import get_sandbox_manager

        manager = get_sandbox_manager()
        sandboxes = manager.list()
        return {
            "sandboxes": sandboxes,
            "count": len(sandboxes),
            "profiles": manager.profile_names(),
        }

    @router.post("/sandboxes/reap")
    async def reap_sandboxes(user: dict = Depends(get_current_user)) -> dict:
        """Destroy every sandbox past its TTL.

        The manager reaps on its own; this is the manual lever for when an
        operator wants the resources back now rather than at the next TTL.
        """
        _require_admin(user)
        from packages.governance.sandbox import get_sandbox_manager

        reaped = await get_sandbox_manager().reap()
        return {"reaped": reaped, "count": len(reaped)}

    @router.delete("/sandboxes/{sandbox_id}")
    async def destroy_sandbox(
        sandbox_id: str, user: dict = Depends(get_current_user)
    ) -> dict:
        _require_admin(user)
        from packages.governance.sandbox import get_sandbox_manager

        destroyed = await get_sandbox_manager().destroy(sandbox_id, reason="operator-request")
        if not destroyed:
            raise HTTPException(status_code=404, detail="Sandbox not found or already destroyed")
        return {"destroyed": True, "sandbox_id": sandbox_id}

    # ── Session budgets ───────────────────────────────────────────────────

    @router.get("/budget")
    async def list_budgets(user: dict = Depends(get_current_user)) -> dict:
        """All active session budgets — live per-session tool-call and cost counters.

        Surfaces the per-tool call breakdown (per_tool_calls) and the ceilings
        (limits) so an operator can see which sessions are approaching their
        caps without a ``curl`` to the audit log. Admin-only: the per-tool
        breakdown names every tool an agent has called, which is an inventory
        of what the agent has been doing.
        """
        _require_admin(user)
        from packages.governance.enforcement import get_gate

        budgets = get_gate().budgets.all()
        return {"budgets": budgets, "count": len(budgets)}

    @router.get("/budget/{session_id}")
    async def get_budget(
        session_id: str, user: dict = Depends(get_current_user)
    ) -> dict:
        """One session's live budget — counters and ceilings.

        Returns 404 when the session is not tracked (never made a governed
        tool call, or was evicted from the in-process tracker).
        """
        _require_admin(user)
        from packages.governance.enforcement import get_gate

        budgets = {b["session_id"]: b for b in get_gate().budgets.all()}
        if session_id not in budgets:
            raise HTTPException(status_code=404, detail="Session not found in budget tracker")
        return budgets[session_id]

    return router

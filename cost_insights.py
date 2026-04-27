"""cost_insights.py — Per-user/workspace/time savings aggregation.

Tracks:
  - Token usage per user, per model, per time period
  - Infrastructure cost per request (from infra_cost.py)
  - Commercial equivalent cost avoided (from commercial_equivalent.py)
  - Cumulative savings: "You've saved $X vs cloud APIs this month"

FastAPI router: /api/observability/
Routes:
  GET /api/observability/savings                 overall savings summary
  GET /api/observability/savings/{user_id}       per-user savings (admin only)
  GET /api/observability/usage                   token usage breakdown
  POST /api/observability/record                 record a request (internal use)
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from rbac import UserRole, get_user_role, require_admin, has_permission, Permission

log = logging.getLogger("qwen-proxy")

observability_router = APIRouter(prefix="/api/observability", tags=["observability"])


# ── Usage record ──────────────────────────────────────────────────────────────

@dataclass
class UsageRecord:
    """A single request's cost and usage data."""
    timestamp:           float
    user_id:             str
    model:               str
    provider:            str        # "local" | "openai" | "anthropic" | ...
    prompt_tokens:       int
    completion_tokens:   int
    total_tokens:        int
    infra_cost_usd:      float      # actual local infra cost
    commercial_eq_usd:   float      # what this would cost on cloud
    savings_usd:         float      # commercial_eq - infra_cost (clamped ≥ 0)
    latency_ms:          int
    task_id:             str | None = None
    agent_id:            str | None = None
    runtime_id:          str | None = None


# ── In-memory store ───────────────────────────────────────────────────────────

_records: list[UsageRecord] = []
_MAX_RECORDS = 50_000


def record_usage(
    *,
    user_id: str,
    model: str,
    provider: str = "local",
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    infra_cost_usd: float = 0.0,
    commercial_eq_usd: float = 0.0,
    latency_ms: int = 0,
    task_id: str | None = None,
    agent_id: str | None = None,
    runtime_id: str | None = None,
) -> UsageRecord:
    """Append a usage record.  Call this from the inference hot path."""
    total_tokens = prompt_tokens + completion_tokens
    savings      = max(0.0, commercial_eq_usd - infra_cost_usd)

    rec = UsageRecord(
        timestamp=time.time(),
        user_id=user_id,
        model=model,
        provider=provider,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        infra_cost_usd=infra_cost_usd,
        commercial_eq_usd=commercial_eq_usd,
        savings_usd=savings,
        latency_ms=latency_ms,
        task_id=task_id,
        agent_id=agent_id,
        runtime_id=runtime_id,
    )
    _records.append(rec)
    while len(_records) > _MAX_RECORDS:
        _records.pop(0)
    return rec


# ── Aggregation helpers ───────────────────────────────────────────────────────

def _period_start(period: str) -> float:
    """Return epoch timestamp for start of period (day/week/month/all)."""
    now = time.time()
    if period == "day":
        return now - 86400
    elif period == "week":
        return now - 7 * 86400
    elif period == "month":
        return now - 30 * 86400
    else:
        return 0.0


@dataclass
class SavingsSummary:
    period:              str
    user_id:             str | None
    total_requests:      int
    total_tokens:        int
    total_infra_cost:    float
    total_commercial_eq: float
    total_savings:       float
    savings_by_model:    dict[str, float] = field(default_factory=dict)
    requests_by_model:   dict[str, int]   = field(default_factory=dict)
    top_models:          list[dict]       = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "period":              self.period,
            "user_id":             self.user_id,
            "total_requests":      self.total_requests,
            "total_tokens":        self.total_tokens,
            "total_infra_cost_usd":    round(self.total_infra_cost, 4),
            "total_commercial_eq_usd": round(self.total_commercial_eq, 4),
            "total_savings_usd":       round(self.total_savings, 4),
            "savings_by_model":    {k: round(v, 4) for k, v in self.savings_by_model.items()},
            "requests_by_model":   self.requests_by_model,
            "top_models":          self.top_models,
        }


def compute_savings(
    period: str = "month",
    user_id: str | None = None,
) -> SavingsSummary:
    """Aggregate savings for the given period and optional user filter."""
    cutoff  = _period_start(period)
    recs    = [r for r in _records if r.timestamp >= cutoff]
    if user_id:
        recs = [r for r in recs if r.user_id == user_id]

    total_requests      = len(recs)
    total_tokens        = sum(r.total_tokens for r in recs)
    total_infra_cost    = sum(r.infra_cost_usd for r in recs)
    total_commercial_eq = sum(r.commercial_eq_usd for r in recs)
    total_savings       = sum(r.savings_usd for r in recs)

    savings_by_model:  dict[str, float] = defaultdict(float)
    requests_by_model: dict[str, int]   = defaultdict(int)

    for r in recs:
        savings_by_model[r.model]  += r.savings_usd
        requests_by_model[r.model] += 1

    top_models = sorted(
        [
            {"model": m, "requests": requests_by_model[m], "savings_usd": round(savings_by_model[m], 4)}
            for m in savings_by_model
        ],
        key=lambda x: x["savings_usd"],
        reverse=True,
    )[:10]

    return SavingsSummary(
        period=period,
        user_id=user_id,
        total_requests=total_requests,
        total_tokens=total_tokens,
        total_infra_cost=total_infra_cost,
        total_commercial_eq=total_commercial_eq,
        total_savings=total_savings,
        savings_by_model=dict(savings_by_model),
        requests_by_model=dict(requests_by_model),
        top_models=top_models,
    )


def compute_time_series(
    period: str = "month",
    user_id: str | None = None,
    bucket: str = "day",         # "hour" | "day"
) -> list[dict]:
    """Return a time-bucketed series of savings for charting."""
    cutoff    = _period_start(period)
    recs      = [r for r in _records if r.timestamp >= cutoff]
    if user_id:
        recs = [r for r in recs if r.user_id == user_id]

    bucket_secs = 3600 if bucket == "hour" else 86400
    buckets: dict[int, dict] = {}

    for r in recs:
        key = int(r.timestamp // bucket_secs) * bucket_secs
        if key not in buckets:
            buckets[key] = {
                "timestamp":    key,
                "requests":     0,
                "tokens":       0,
                "savings_usd":  0.0,
                "infra_usd":    0.0,
            }
        buckets[key]["requests"]    += 1
        buckets[key]["tokens"]      += r.total_tokens
        buckets[key]["savings_usd"] += r.savings_usd
        buckets[key]["infra_usd"]   += r.infra_cost_usd

    result = sorted(buckets.values(), key=lambda x: x["timestamp"])
    for b in result:
        b["savings_usd"] = round(b["savings_usd"], 4)
        b["infra_usd"]   = round(b["infra_usd"], 4)
    return result


# ── Internal record endpoint (called by inference path) ──────────────────────

class UsageRecordRequest(BaseModel):
    user_id:           str
    model:             str
    provider:          str   = "local"
    prompt_tokens:     int   = 0
    completion_tokens: int   = 0
    infra_cost_usd:    float = 0.0
    commercial_eq_usd: float = 0.0
    latency_ms:        int   = 0
    task_id:           str | None = None
    agent_id:          str | None = None
    runtime_id:        str | None = None


@observability_router.post("/record", include_in_schema=False)
async def record_usage_endpoint(body: UsageRecordRequest, request: Request):
    """Internal: record a usage event.  Called by inference handlers."""
    record_usage(**body.model_dump())
    return {"recorded": True}


# ── Public savings endpoints ──────────────────────────────────────────────────

@observability_router.get("/savings")
async def get_savings(
    request: Request,
    period: str = "month",
    bucket: str = "day",
):
    """Return savings summary for the current user (or all users for admins)."""
    user = getattr(request.state, "user", None) or {}
    uid  = user.get("email") or user.get("_id") if isinstance(user, dict) else None
    role = get_user_role(user)

    # Admins/power users see aggregate; standard users see own
    if role in (UserRole.ADMIN, UserRole.POWER_USER):
        summary = compute_savings(period=period)
        series  = compute_time_series(period=period, bucket=bucket)
    else:
        summary = compute_savings(period=period, user_id=uid)
        series  = compute_time_series(period=period, user_id=uid, bucket=bucket)

    return {
        "summary":     summary.as_dict(),
        "time_series": series,
    }


@observability_router.get("/savings/{target_user_id}")
async def get_user_savings(target_user_id: str, request: Request, period: str = "month"):
    """Return savings for a specific user.  Admin only."""
    require_admin(request)
    summary = compute_savings(period=period, user_id=target_user_id)
    series  = compute_time_series(period=period, user_id=target_user_id)
    return {"summary": summary.as_dict(), "time_series": series}


@observability_router.get("/usage")
async def get_usage(request: Request, period: str = "month"):
    """Return token usage breakdown."""
    user = getattr(request.state, "user", None) or {}
    uid  = user.get("email") or user.get("_id") if isinstance(user, dict) else None
    role = get_user_role(user)

    cutoff = _period_start(period)
    recs   = [r for r in _records if r.timestamp >= cutoff]
    if role not in (UserRole.ADMIN, UserRole.POWER_USER):
        recs = [r for r in recs if r.user_id == uid]

    by_model: dict[str, dict] = defaultdict(lambda: {"requests": 0, "tokens": 0, "savings_usd": 0.0})
    for r in recs:
        by_model[r.model]["requests"] += 1
        by_model[r.model]["tokens"]   += r.total_tokens
        by_model[r.model]["savings_usd"] += r.savings_usd

    return {
        "period":           period,
        "total_requests":   len(recs),
        "total_tokens":     sum(r.total_tokens for r in recs),
        "by_model":         {k: {**v, "savings_usd": round(v["savings_usd"], 4)} for k, v in by_model.items()},
    }

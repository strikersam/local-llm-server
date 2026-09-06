"""packages/governance/audit.py — the evidence trail for every governed action.

Docker AI Governance frames the audit trail as "the evidence CISOs need to
approve AI usage at scale", and is specific about the shape: every policy
evaluation emits a structured event carrying user identity, timestamp, session
context, and the triggering rule, exportable to a SIEM. This module is that
emitter for this platform.

An :class:`AuditEvent` answers, for one action: **who** (agent identity, owner,
session), **what** (surface, action, tool, redacted arguments), **when**
(timestamp, duration), **why** (the policy rule that fired, the task the run
serves), **where** (repo, branch, commit, sandbox, container, source IP), and
**what it cost** (provider, model, tokens, USD).

Three properties are non-negotiable and each is tested:

**Arguments are redacted before they are stored, not before they are read.**
Tool arguments routinely carry tokens — ``clone_repo`` takes a
``github_token``, ``run_command`` can carry an inline secret. Redacting at
render time would mean the secret is sitting in memory in the ring buffer, one
serialisation bug away from a response body. This repo has already leaked a
live MongoDB password into a log line once (CHANGELOG, 2026-08-01), so
redaction happens in ``__post_init__`` — before the event is stored anywhere.

**Emitting an audit event can never break the action it describes.**
:meth:`AuditLog.record` catches everything. An audit sink that can raise turns
observability into an outage, and a governance layer that takes the platform
down when its logging backend hiccups will simply be switched off.

**The buffer is bounded.** The backend is a long-lived process running 34
autonomous loops; an unbounded audit list is a memory leak with a security
justification. The ring buffer holds the most recent N events for the
dashboard, while the structured log line is the durable, exportable record.
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

log = logging.getLogger("governance.audit")

# A dedicated logger so operators can route the audit stream to its own
# handler/file/SIEM shipper without also capturing application chatter.
audit_log = logging.getLogger("governance.audit.events")

# Argument keys whose values are secrets regardless of content. Matched as a
# substring against the lower-cased key, so `github_token`, `api_key_value`
# and `X-Auth-Password` are all covered by short entries.
_SECRET_KEY_MARKERS = (
    "token", "secret", "password", "passwd", "pwd", "api_key", "apikey",
    "authorization", "auth", "credential", "private_key", "session_key",
    "access_key", "client_secret", "bearer",
)

# Secret-shaped values that appear inside otherwise innocent strings — a shell
# command, a URL, a diff. Keyed on the vendor prefixes this repo actually
# handles plus generic bearer/assignment forms.
_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{16,}"),            # GitHub tokens
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bsk-[A-Za-z0-9\-_]{16,}"),                 # OpenAI-style
    re.compile(r"\bnvapi-[A-Za-z0-9\-_]{16,}"),              # NVIDIA NIM
    re.compile(r"\bcsk-[A-Za-z0-9\-_]{16,}"),                # Cerebras
    re.compile(r"\bgsk_[A-Za-z0-9]{16,}"),                   # Groq
    re.compile(r"\be2b_[A-Za-z0-9]{16,}"),                   # E2B
    re.compile(r"\bsk-ant-[A-Za-z0-9\-_]{16,}"),             # Anthropic
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9\-._~+/]{16,}"),
    re.compile(
        r"(?i)\b(?:token|secret|password|api[_-]?key)\b\s*[=:]\s*[\"']?([^\s\"'&]{8,})"
    ),
)

# Values longer than this are truncated in the stored event. A 2 MB file body
# in an audit row is not evidence, it is a memory leak.
_MAX_VALUE_CHARS = 2000
_MAX_RESULT_CHARS = 4000

# Personally-identifiable values that are not secrets but must not linger in a
# stored audit row. Kept deliberately narrow: a US SSN and a payment-card
# number. Email and phone are *excluded* on purpose — the audit event
# legitimately records an owner identity (frequently an email), so a blanket
# email/phone redaction would gut the trail's debuggability for near-zero gain,
# and both shapes are far too common in ordinary tool arguments to redact
# safely. SSNs are matched only in their separated form (a bare run of nine
# digits collides with too many innocent ids), and card numbers are
# Luhn-validated so a 16-digit order ref or snowflake id is not mistaken for a
# PAN.
_SSN_RE = re.compile(r"\b\d{3}[-\s]\d{2}[-\s]\d{4}\b")
_CARD_CANDIDATE_RE = re.compile(r"\b(?:\d[ -]?){13,19}\b")


def _luhn_ok(digits: str) -> bool:
    """True when ``digits`` (bare, no separators) satisfies the Luhn checksum."""
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = ord(ch) - 48
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def _redact_pii(text: str) -> str:
    """Redact SSNs and Luhn-valid payment-card numbers from a string.

    Runs after the secret-value pass in :func:`_scrub_text`. A card candidate
    is only redacted when its digits (separators stripped) pass Luhn, keeping
    false positives on ordinary long numbers negligible.
    """

    def _card(match: re.Match[str]) -> str:
        digits = re.sub(r"[ -]", "", match.group(0))
        if 13 <= len(digits) <= 19 and _luhn_ok(digits):
            return "***"
        return match.group(0)

    redacted = _CARD_CANDIDATE_RE.sub(_card, text)
    redacted = _SSN_RE.sub("***", redacted)
    return redacted


def scrub(value: Any) -> Any:
    """Recursively strip secrets from an arbitrary argument structure.

    Fails **closed**: if a value cannot be scrubbed for any reason, the value
    is replaced with a marker rather than passed through. A redactor that
    silently emits the original on error is worse than no redactor, because it
    is trusted.
    """
    try:
        return _scrub_inner(value, depth=0)
    except Exception as exc:  # noqa: BLE001 - never leak on a redaction bug
        log.warning("Audit redaction failed (%s); withholding value", type(exc).__name__)
        return "[redaction-failed:withheld]"


def _scrub_inner(value: Any, depth: int) -> Any:
    # Deeply nested structures are almost always accidental (a recursive
    # object graph in a tool arg). Cap rather than recurse forever.
    if depth > 6:
        return "[max-depth]"
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if any(marker in key_text.lower() for marker in _SECRET_KEY_MARKERS):
                out[key_text] = "***"
            else:
                out[key_text] = _scrub_inner(item, depth + 1)
        return out
    if isinstance(value, (list, tuple)):
        return [_scrub_inner(v, depth + 1) for v in value[:50]]
    if isinstance(value, str):
        return _scrub_text(value)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return _scrub_text(str(value))


def _scrub_text(text: str) -> str:
    """Redact secret-shaped substrings, then truncate."""
    redacted = text
    try:
        from packages.security.redact import redact_connection_url

        redacted = redact_connection_url(redacted)
    except Exception as exc:  # noqa: BLE001 - shared helper is optional at import time
        # Logged rather than swallowed: this helper is the only thing that
        # strips `user:pass@host` from a connection URI, so its absence means
        # the value-pattern pass below is redacting alone. That is a weaker
        # guarantee than intended and an operator should be able to see it.
        log.warning("redact_connection_url unavailable (%s); URI credentials "
                    "rely on the value patterns alone", type(exc).__name__)
    for pattern in _VALUE_PATTERNS:
        redacted = pattern.sub(
            lambda m: m.group(0).replace(m.group(1), "***") if m.groups() else "***",
            redacted,
        )
    redacted = _redact_pii(redacted)
    if len(redacted) > _MAX_VALUE_CHARS:
        return redacted[:_MAX_VALUE_CHARS] + f"...[truncated {len(redacted)} chars]"
    return redacted


@dataclass
class AuditEvent:
    """One governed action, fully described.

    Field order follows the who/what/when/why/where/cost grouping the audit
    requirement asks for, so a raw JSON line stays readable without a schema.
    """

    # ── who ──
    agent_id: str = "agent:unknown"
    display_name: str = "unknown"
    owner: str = "system"
    session_id: str = ""
    roles: list[str] = field(default_factory=list)
    policy_group: str = "default"

    # ── what ──
    surface: str = "tool"
    action: str = ""
    tool: str | None = None
    arguments: dict[str, Any] = field(default_factory=dict)
    result_status: str = "unknown"
    result: str = ""
    error: str | None = None

    # ── when ──
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    duration_ms: float = 0.0

    # ── why ──
    decision: str = "allow"
    effective: str = "allow"
    reason: str = ""
    rule_id: str = ""
    mode: str = "observe"
    task_id: str | None = None
    approval_id: str | None = None

    # ── where ──
    repo: str | None = None
    branch: str | None = None
    commit: str | None = None
    sandbox_id: str | None = None
    sandbox_backend: str | None = None
    container_id: str | None = None
    runtime: str | None = None
    source_ip: str | None = None

    # ── cost ──
    llm_provider: str | None = None
    llm_model: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0

    event_id: str = field(default_factory=lambda: f"evt_{int(time.time() * 1000):x}")

    def __post_init__(self) -> None:
        # Redact at construction: from here on, no field of this object holds
        # a secret, so every downstream sink is safe by default rather than
        # safe-if-it-remembers.
        self.arguments = scrub(self.arguments) if self.arguments else {}
        self.result = _truncate(scrub(self.result) if self.result else "", _MAX_RESULT_CHARS)
        if self.error:
            self.error = _truncate(str(scrub(self.error)), _MAX_RESULT_CHARS)

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}

    def to_json(self) -> str:
        """One-line JSON, suitable for a SIEM shipper tailing the log."""
        try:
            return json.dumps(self.to_dict(), default=str, separators=(",", ":"))
        except (TypeError, ValueError):  # pragma: no cover - defensive
            return json.dumps(
                {"event_id": self.event_id, "error": "unserialisable audit event"}
            )


def _truncate(text: str, limit: int) -> str:
    if not text:
        return ""
    return text if len(text) <= limit else text[:limit] + f"...[truncated {len(text)} chars]"


class AuditLog:
    """Bounded in-memory ring buffer plus a structured log stream.

    The ring buffer serves the dashboard and the API; the log stream is the
    durable record. Additional sinks (a database collection, an HTTP shipper)
    attach via :meth:`add_sink` — each is called defensively, so one broken
    sink cannot suppress the others or the action being audited.
    """

    def __init__(self, capacity: int = 2000) -> None:
        self._events: deque[AuditEvent] = deque(maxlen=max(1, capacity))
        self._lock = threading.Lock()
        self._sinks: list[Callable[[AuditEvent], None]] = []
        self._counters: dict[str, int] = {}
        # All-time accumulators. The ring buffer only holds the most recent N
        # events, so aggregating over it silently undercounts once the buffer
        # wraps — a summary that labels a windowed sum "total_cost_usd" is stale
        # the moment the (N+1)th event lands. These are updated at record() time
        # so the summary reports true totals independent of the buffer window.
        self._total_recorded = 0
        self._total_blocked = 0
        self._total_cost_usd = 0.0
        self._total_tokens = 0
        self._by_agent_total: dict[str, int] = {}

    def add_sink(self, sink: Callable[[AuditEvent], None]) -> None:
        with self._lock:
            self._sinks.append(sink)

    def record(self, event: AuditEvent) -> AuditEvent:
        """Store and emit *event*. Never raises."""
        try:
            with self._lock:
                self._events.append(event)
                self._bump(f"decision.{event.decision}")
                self._bump(f"surface.{event.surface}")
                if event.result_status:
                    self._bump(f"status.{event.result_status}")
                # All-time accumulators — survive ring-buffer eviction.
                self._total_recorded += 1
                if event.decision in ("deny", "require_approval"):
                    self._total_blocked += 1
                self._total_cost_usd += event.cost_usd or 0.0
                self._total_tokens += event.total_tokens or 0
                self._by_agent_total[event.agent_id] = (
                    self._by_agent_total.get(event.agent_id, 0) + 1
                )
                sinks = list(self._sinks)
            audit_log.info("%s", event.to_json())
            for sink in sinks:
                try:
                    sink(event)
                except Exception as exc:  # noqa: BLE001
                    log.warning("Audit sink %r failed: %s", getattr(sink, "__name__", sink), exc)
        except Exception as exc:  # noqa: BLE001 - auditing must not break the action
            log.warning("Audit record failed: %s", exc)
        return event

    def _bump(self, key: str) -> None:
        self._counters[key] = self._counters.get(key, 0) + 1

    def recent(
        self,
        limit: int = 100,
        *,
        agent_id: str | None = None,
        session_id: str | None = None,
        surface: str | None = None,
        decision: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return the most recent events, newest first, optionally filtered."""
        with self._lock:
            events = list(self._events)
        selected: list[dict[str, Any]] = []
        for event in reversed(events):
            if agent_id and event.agent_id != agent_id:
                continue
            if session_id and event.session_id != session_id:
                continue
            if surface and event.surface != surface:
                continue
            if decision and event.decision != decision:
                continue
            selected.append(event.to_dict())
            if len(selected) >= max(1, limit):
                break
        return selected

    def counters(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counters)

    def summary(self) -> dict[str, Any]:
        """Aggregate view for the dashboard and the metrics endpoint.

        ``would_block`` is the number that decides whether ``enforce`` mode is
        safe to turn on: it counts decisions that blocked, or that *would*
        have blocked had the engine been enforcing.

        The ``total_*``/``would_block``/``by_agent`` figures are **all-time**
        accumulators, not sums over the bounded ring buffer — the buffer only
        keeps the most recent ``capacity`` events, so aggregating over it would
        silently undercount once it wraps. ``buffered_events`` reports how many
        events the in-memory window currently holds (for the recent-events view),
        while ``total_recorded`` is the true all-time count.
        """
        with self._lock:
            counters = dict(self._counters)
            buffered = len(self._events)
            total_recorded = self._total_recorded
            total_blocked = self._total_blocked
            total_cost = self._total_cost_usd
            total_tokens = self._total_tokens
            by_agent = dict(self._by_agent_total)
        return {
            "buffered_events": buffered,
            "total_recorded": total_recorded,
            "capacity": self._events.maxlen,
            "would_block": total_blocked,
            "total_cost_usd": round(total_cost, 6),
            "total_tokens": total_tokens,
            "by_agent": by_agent,
            "counters": counters,
        }

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
            self._counters.clear()
            self._total_recorded = 0
            self._total_blocked = 0
            self._total_cost_usd = 0.0
            self._total_tokens = 0
            self._by_agent_total.clear()


_AUDIT_LOG: AuditLog | None = None
_AUDIT_LOCK = threading.Lock()


def get_audit_log() -> AuditLog:
    """Return the process-wide audit log, created on first use."""
    global _AUDIT_LOG
    with _AUDIT_LOCK:
        if _AUDIT_LOG is None:
            from packages.config import settings

            _AUDIT_LOG = AuditLog(capacity=settings.governance_audit_capacity)
        return _AUDIT_LOG


def reset_audit_log(audit: AuditLog | None = None) -> None:
    """Replace the process-wide audit log. Tests only."""
    global _AUDIT_LOG
    with _AUDIT_LOCK:
        _AUDIT_LOG = audit


def record_event(**fields: Any) -> AuditEvent:
    """Convenience: build and record an event in one call."""
    known = {k: v for k, v in fields.items() if k in AuditEvent.__dataclass_fields__}
    return get_audit_log().record(AuditEvent(**known))


def events_from_identity(identity: Any) -> dict[str, Any]:
    """Extract the identity-derived audit fields from an AgentIdentity.

    Kept here rather than on the identity so :mod:`identity` stays free of any
    dependency on the audit schema — the identity describes a principal, the
    audit decides which parts of it are worth recording.
    """
    if identity is None:
        return {}
    getter: Callable[[str], Any] = lambda name: getattr(identity, name, None)  # noqa: E731
    roles = getter("roles") or ()
    return {
        "agent_id": getter("agent_id") or "agent:unknown",
        "display_name": getter("display_name") or "unknown",
        "owner": getter("owner") or "system",
        "session_id": getter("session_id") or "",
        "roles": list(roles) if isinstance(roles, Iterable) and not isinstance(roles, str) else [],
        "policy_group": getter("policy_group") or "default",
        "task_id": getter("task_id"),
        "repo": getter("repo"),
        "branch": getter("branch"),
        "commit": getter("commit"),
        "sandbox_id": getter("sandbox_id"),
        "runtime": getter("runtime"),
        "source_ip": getter("source_ip"),
    }

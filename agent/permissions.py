"""agent/permissions.py — Adaptive Permission Classifier

Reads the session transcript and infers the appropriate permission level
so the agent can avoid asking for approval on actions the session has
already been authorised for.

Levels:
  read_only   — only inspection/reading actions detected
  read_write  — file modifications, edits, commits detected
  full_access — destructive or privileged operations detected
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Literal

log = logging.getLogger("qwen-permissions")

PermissionLevel = Literal["read_only", "read_write", "full_access"]

# Signal word sets (lower-case, matched against tokenised message content)
_WRITE_SIGNALS = frozenset(
    {
        "create", "write", "update", "modify", "delete", "edit", "apply",
        "commit", "push", "deploy", "install", "remove", "overwrite", "patch",
        "replace", "save", "migrate", "add",
    }
)

_READ_SIGNALS = frozenset(
    {
        "read", "view", "list", "search", "inspect", "check", "show",
        "find", "describe", "explain", "analyze", "analyse", "summarize",
        "summarise", "display", "fetch", "get",
    }
)

_RISKY_SIGNALS = frozenset(
    {
        "rm", "drop", "truncate", "purge", "wipe", "format", "sudo",
        "exec", "eval", "shell", "destroy", "nuke", "force", "reset",
    }
)


@dataclass
class PermissionAssessment:
    level: PermissionLevel
    confidence: float  # 0.0 – 1.0
    write_signals: list[str] = field(default_factory=list)
    read_signals: list[str] = field(default_factory=list)
    risky_signals: list[str] = field(default_factory=list)
    summary: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "confidence": round(self.confidence, 2),
            "write_signals": self.write_signals,
            "read_signals": self.read_signals,
            "risky_signals": self.risky_signals,
            "summary": self.summary,
        }


class AdaptivePermissions:
    """Infer permission level from a list of chat messages (session transcript).

    Usage::

        ap = AdaptivePermissions()
        assessment = ap.assess(session.history)
        if ap.has_write_permission(session.history):
            # proceed without asking
    """

    def assess(self, messages: list[dict[str, Any]]) -> PermissionAssessment:
        """Analyse *messages* and return a :class:`PermissionAssessment`."""
        write_hits: list[str] = []
        read_hits: list[str] = []
        risky_hits: list[str] = []

        for msg in messages:
            words = set(str(msg.get("content", "")).lower().split())
            write_hits.extend(w for w in _WRITE_SIGNALS if w in words)
            read_hits.extend(w for w in _READ_SIGNALS if w in words)
            risky_hits.extend(w for w in _RISKY_SIGNALS if w in words)

        # Deduplicate while preserving first-seen order
        write_hits = list(dict.fromkeys(write_hits))
        read_hits = list(dict.fromkeys(read_hits))
        risky_hits = list(dict.fromkeys(risky_hits))

        if risky_hits:
            level: PermissionLevel = "full_access"
            confidence = 0.9
            summary = (
                f"Risky operations detected ({', '.join(risky_hits[:3])}). "
                "Full-access permission inferred."
            )
        elif write_hits:
            level = "read_write"
            confidence = min(0.9, 0.5 + len(write_hits) * 0.08)
            summary = (
                f"Write operations detected ({', '.join(write_hits[:3])}). "
                "Read-write permission inferred."
            )
        elif read_hits:
            level = "read_only"
            confidence = min(0.9, 0.5 + len(read_hits) * 0.08)
            summary = "Read-only operations detected. Read-only permission inferred."
        else:
            level = "read_only"
            confidence = 0.3
            summary = "No clear signals detected. Defaulting to read-only."

        log.debug("Permission assessment: level=%s confidence=%.2f", level, confidence)
        return PermissionAssessment(
            level=level,
            confidence=confidence,
            write_signals=write_hits,
            read_signals=read_hits,
            risky_signals=risky_hits,
            summary=summary,
        )

    def has_write_permission(self, messages: list[dict[str, Any]]) -> bool:
        """Convenience helper — True when the inferred level is read_write or full_access."""
        return self.assess(messages).level in ("read_write", "full_access")

"""agents/profiles.py — Role-locked AgentProfile definitions.

Every agent in the CRISPY system has a profile that specifies:
  • which model it uses (env-var overridable)
  • what it is allowed to do (read / write / execute / review)
  • its system prompt (role identity, hard constraints)

The key design invariant:
  CODER model ≠ REVIEWER model (by default — Qwen3 vs DeepSeek-R1)

This asymmetry is the core of the dual-model review: the reviewer
sees the coder's output with fresh eyes and a different reasoning
style, catching blind spots the original author-model would miss.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Literal

AgentRole = Literal["architect", "scout", "coder", "reviewer", "verifier"]

# ── Environment variable names ───────────────────────────────────────────────

_ENV: dict[str, str] = {
    "architect": "CRISPY_ARCHITECT_MODEL",
    "scout":     "CRISPY_SCOUT_MODEL",
    "coder":     "CRISPY_CODER_MODEL",
    "reviewer":  "CRISPY_REVIEWER_MODEL",
    "verifier":  "CRISPY_VERIFIER_MODEL",
}

# ── Hard-coded defaults (distinct coder ≠ reviewer by design) ────────────────

_DEFAULTS: dict[str, str] = {
    "architect": "qwen3-coder:30b",
    "scout":     "deepseek-r1:32b",
    "coder":     "qwen3-coder:30b",   # ← implementation model
    "reviewer":  "deepseek-r1:32b",   # ← intentionally DIFFERENT
    "verifier":  "qwen3-coder:7b",    # only asked for CLI commands, not verdicts
}

# ── System prompts ────────────────────────────────────────────────────────────

SCOUT_SYSTEM = """\
You are SCOUT, a read-only research agent.

HARD RULES:
  • You MUST NOT suggest code changes or patches.
  • You MUST NOT write new files or modify existing ones.
  • Your output is always a well-structured Markdown document.

Your job: gather context faithfully. Read files, understand structure,
summarise findings. Leave judgement to the Architect."""

ARCHITECT_SYSTEM = """\
You are ARCHITECT, a senior engineering lead.

HARD RULES:
  • You MUST NOT write executable code.
  • You design, plan, and produce structured markdown.
  • Every plan MUST be decomposed into numbered vertical slices.
  • Each slice MUST list: Title, Description, Files (target paths), Tests.

Slice format (mandatory):
## Slice N: <Title>
**Description**: ...
**Files**: path/to/file.py, tests/test_file.py
**Tests**: describe what must pass

Plans that list no slices or vague files will be rejected."""

CODER_SYSTEM = """\
You are CODER, the implementation engine.

HARD RULES:
  • You implement EXACTLY ONE vertical slice per invocation.
  • You MUST include tests alongside every code change.
  • You MUST use the exact file paths specified.
  • Output format:
      ## What changed
      ## Why
      ## Files modified
      <one fenced code block per file, with filename as caption>

Do not modify files outside your slice specification."""

REVIEWER_SYSTEM = """\
You are REVIEWER, an adversarial code reviewer.

HARD RULES:
  • You are READ-ONLY. You MUST NOT apply changes.
  • You use a different model than the Coder — your job is catching blind spots.
  • You MUST categorise every finding:
      BLOCKING   — must fix before verification
      SUGGESTION — non-blocking, nice-to-have

Output format (mandatory):
## BLOCKING Issues
<list or "(none)">

## SUGGESTIONS
<list or "(none)">

## Verdict
PASS (no blocking) | FAIL (blocking issues found)

Be adversarial. Assume the Coder left bugs."""

VERIFIER_SYSTEM = """\
You are VERIFIER, a test-command oracle.

HARD RULES:
  • You output ONLY a JSON array of shell commands.
  • No prose. No markdown fences. No explanation.
  • Commands must be read-only (no rm, no git commit, no pip install).
  • Always include at minimum: pytest -x

Example output:
["pytest -x", "ruff check .", "mypy workflow/"]"""

_SYSTEM_PROMPTS: dict[str, str] = {
    "architect": ARCHITECT_SYSTEM,
    "scout":     SCOUT_SYSTEM,
    "coder":     CODER_SYSTEM,
    "reviewer":  REVIEWER_SYSTEM,
    "verifier":  VERIFIER_SYSTEM,
}

# ── AgentProfile dataclass ────────────────────────────────────────────────────


@dataclass
class AgentProfile:
    """Immutable description of a CRISPY agent role.

    Attributes
    ----------
    role:         The agent's role identifier.
    name:         Human-readable agent name.
    model:        Resolved model name (env var → default fallback).
    system_prompt: Role-specific system prompt with hard constraints.
    can_read:     May read files and prior artifacts.
    can_write:    May produce executable code / file edits.
    can_execute:  May run shell commands.
    can_review:   May produce blocking/non-blocking verdicts.
    """

    role: str
    name: str
    model: str
    system_prompt: str
    can_read: bool = True
    can_write: bool = False
    can_execute: bool = False
    can_review: bool = False

    def __post_init__(self) -> None:
        # Coerce model from env at construction time so tests can override env
        env_key = _ENV.get(self.role, "")
        from_env = os.environ.get(env_key, "").strip() if env_key else ""
        if from_env:
            object.__setattr__(self, "model", from_env)

    @property
    def label(self) -> str:
        """Short label for TUI display: {NAME}:{model}"""
        return f"{self.name}[{self.model}]"


# ── Factory functions ─────────────────────────────────────────────────────────


def make_scout_profile() -> AgentProfile:
    return AgentProfile(
        role="scout",
        name="Scout",
        model=os.environ.get(_ENV["scout"], _DEFAULTS["scout"]),
        system_prompt=SCOUT_SYSTEM,
        can_read=True,
        can_write=False,
        can_execute=False,
        can_review=False,
    )


def make_architect_profile() -> AgentProfile:
    return AgentProfile(
        role="architect",
        name="Architect",
        model=os.environ.get(_ENV["architect"], _DEFAULTS["architect"]),
        system_prompt=ARCHITECT_SYSTEM,
        can_read=True,
        can_write=False,
        can_execute=False,
        can_review=False,
    )


def make_coder_profile() -> AgentProfile:
    return AgentProfile(
        role="coder",
        name="Coder",
        model=os.environ.get(_ENV["coder"], _DEFAULTS["coder"]),
        system_prompt=CODER_SYSTEM,
        can_read=True,
        can_write=True,
        can_execute=False,
        can_review=False,
    )


def make_reviewer_profile() -> AgentProfile:
    return AgentProfile(
        role="reviewer",
        name="Reviewer",
        model=os.environ.get(_ENV["reviewer"], _DEFAULTS["reviewer"]),
        system_prompt=REVIEWER_SYSTEM,
        can_read=True,
        can_write=False,
        can_execute=False,
        can_review=True,
    )


def make_verifier_profile() -> AgentProfile:
    return AgentProfile(
        role="verifier",
        name="Verifier",
        model=os.environ.get(_ENV["verifier"], _DEFAULTS["verifier"]),
        system_prompt=VERIFIER_SYSTEM,
        can_read=True,
        can_write=False,
        can_execute=True,
        can_review=False,
    )


def load_all_profiles() -> dict[str, AgentProfile]:
    """Return a mapping of role → AgentProfile for all five roles."""
    return {
        "scout":     make_scout_profile(),
        "architect": make_architect_profile(),
        "coder":     make_coder_profile(),
        "reviewer":  make_reviewer_profile(),
        "verifier":  make_verifier_profile(),
    }

# ADR 003: Multi-Agent Orchestration with Plan-Execute-Verify Loop

**Status:** Accepted
**Date:** 2026-04-01

## Context

Single-agent coding loops tend to produce incorrect results on complex, multi-file changes.
We need a more robust agentic pattern that separates planning from execution, and execution
from evaluation. We also need this to be resumable after interruption.

## Decision

Implement a **four-role agent system** with the following structure:

1. **Planner** — produces a structured plan before any code is written
2. **Implementer** — executes each step with a bounded tool loop
3. **Reviewer (Verifier)** — evaluates each change before it is written to disk
4. **Judge** — release-readiness gate after the session completes

Key properties:
- Each role uses the best-fit model for its cognitive task
- State is persisted to `.claude/state/` before every handoff
- `scripts/ai_runner.py` provides automatic resume after interruption
- The verifier uses a local syntax check + LLM review before any file write
- The judge runs the full `council-review` skill (4 reviewer perspectives)

## Alternatives Considered

**Single-agent loop:** Simpler, but produces more errors on complex changes. No role separation means
the same model that generated the code also evaluates it — a known bias problem.

**Separate process per agent:** More isolation, but adds process orchestration complexity and
makes state sharing harder. Not worth the overhead for this repo's scale.

**LLM-as-judge only (no local syntax check):** Tried. LLMs miss syntax errors occasionally.
Local `ast.parse()` is deterministic and free — always run it before the LLM verifier call.

## Consequences

### Positive
- Higher-quality code changes (Reviewer catches errors before they reach disk)
- Resumable sessions — no work lost on interruption
- Clean separation of concerns enables independent model upgrades per role
- The Judge prevents incomplete work from being released

### Negative
- 3 LLM calls per step instead of 1 (planner + implementer + verifier)
- Higher latency per step (~3-9x compared to direct LLM call)
- More complex failure modes (need to handle Planner failing, Verifier cycling, etc.)

### Neutral
- The `max_steps` limit and retry bounds prevent runaway execution
- This pattern is clean-room inspired by, but not derived from, any proprietary code

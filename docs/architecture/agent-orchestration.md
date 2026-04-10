# Agent Orchestration Design

## Overview

The agent system in `agent/` implements a **clean-room multi-agent orchestration pattern**
inspired by generator/reviewer/council separation used in modern AI engineering systems.

## Four-Agent Structure

| Agent | Role | Model | Handoff |
|-------|------|-------|---------|
| Planner | Decompose instruction into ordered steps | deepseek-r1:32b | → Implementer |
| Implementer | Execute each step via tool loop + LLM | qwen3-coder:30b | → Reviewer |
| Reviewer (Verifier) | Verify each file change before apply | deepseek-r1:32b | pass→apply, fail→retry |
| Judge | Release gate after session completes | deepseek-r1:32b | → done/blocked |

## Shared State

All agents share state through:
1. `.claude/state/agent-state.json` — full session plan and status
2. `.claude/state/checkpoint.jsonl` — append-only completed-step log
3. The filesystem — applied changes are visible immediately to all agents

## Plan-First Pathway

```
POST /v1/agent/run {instruction, auto_commit, max_steps}
    │
    ▼
AgentRunner.run()
    │
    ├─ _generate_plan()      ← Planner agent call
    │    Uses: build_planning_prompt() → LLM → AgentPlan.model_validate()
    │
    └─ for step in plan.steps[:max_steps]:
           _execute_step()   ← Implementer + Reviewer agents
```

## Tool Loop (Implementer)

The implementer uses a bounded tool loop before generating file content.
This ensures it has sufficient context to make accurate changes:

```
for remaining in range(4, 0, -1):
    tool_call = LLM(goal, step, observations, remaining)
    if tool_call.tool == "finish": break
    result = run_tool(tool_call.tool, tool_call.args)
    observations.append(result)
```

Available tools: `read_file`, `list_files`, `search_code`, `finish`.

## Execution Pathway

```
For each target_file:
    original = read(target_file)
    retries = 0
    while retries <= 2:
        new_content = Implementer(goal, step, context)
        syntax_issues = local_syntax_check(new_content)
        safety_issues = local_safety_check(new_content)
        verdict = Reviewer(original, new_content, syntax_issues + safety_issues)
        if verdict.status == "pass":
            apply_diff(target_file, new_content)
            break
        retries += 1
        feedback_issues = syntax_issues + verdict.issues
```

## Review Pathway (Council Mode)

For pre-merge review, the `council-review` skill runs four sequential reviewer roles:
1. Security (auth, key exposure, path traversal)
2. Correctness (logic, edge cases, type safety)
3. Performance (async paths, caching, loops per request)
4. Maintainability (coupling, naming, abstraction level)

This is implemented as a skill (`.claude/skills/council-review/SKILL.md`) rather than
a live agent call, since it runs on diffs rather than during the generation loop.

## Release-Readiness Pathway

The Judge agent (`.claude/agents/judge.md`) runs the release-readiness skill at session end:
- Verifies all steps completed
- Runs `pytest -x`
- Checks changelog
- Produces `judge-verdict.json` with APPROVED / APPROVED_WITH_CONDITIONS / BLOCKED

## Worktree Isolation (Future)

For parallel agent execution, git worktrees can isolate each agent's working tree:

```bash
git worktree add .worktrees/agent-1 HEAD
git worktree add .worktrees/agent-2 HEAD
```

Each agent writes to its own worktree; the Judge merges results.
This is documented as a future capability — the current implementation is sequential.

## Relationship to the Anthropic Advisor Strategy

The Anthropic [advisor strategy](https://claude.com/blog/the-advisor-strategy) (`advisor_20260301`
beta tool) uses the same structural insight: a cheaper executor model does most of the token
generation, while a higher-intelligence model provides strategic guidance at key decision points.

| Anthropic advisor strategy | This repo's local equivalent |
|---|---|
| Sonnet / Haiku executor | `qwen3-coder:30b` |
| Opus advisor (on-demand, mid-generation) | `deepseek-r1:32b` Planner (pre-execution) + Verifier (post-write) |
| Single `/v1/messages` round-trip | `AgentRunner.run()` — sequential plan → execute → verify loop |

The main difference: the Anthropic advisor is invoked *on demand* by the executor mid-generation;
the local pattern runs the reasoning model *up-front* (planning) and *after* each write (verification).
Both achieve a similar cost/quality tradeoff.

Because this proxy cannot execute the server-side Opus sub-inference, the `handlers/anthropic_compat.py`
layer strips `advisor_20260301` from tool arrays before forwarding to Ollama, and converts any
advisor result blocks in message history to plain text. See
`docs/architecture/advisor-strategy.md` for details.

---

## OSS Inspirations (Clean-Room)

This design was inspired by:
- open-multi-agent patterns (generator/reviewer separation)
- openclaw-claude-code council/ultraplan/ultrareview patterns
- Microsoft AutoGen-style role separation

No proprietary code was copied. Architecture was re-implemented independently.

## Key Invariants

1. Planner runs before any Implementer call — no execution without a plan.
2. Verifier approves before any `apply_diff` — no writes bypass review.
3. `max_steps` is always respected — no unbounded loops.
4. Retry limit per file is 3 — agents don't loop forever on failures.
5. All state changes are written to disk before the next LLM call.

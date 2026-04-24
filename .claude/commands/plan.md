# Command: /plan

**Trigger:** `/plan <instruction>`

Invoke the Planner agent to produce a structured implementation plan before any code is written.

## What It Does

1. Reads the relevant module CLAUDE.md files
2. Inspects the current repo state
3. Produces a step-by-step plan with file targets, risks, and acceptance criteria
4. Saves the plan to `.claude/state/agent-state.json`
5. Does NOT write any code — plan only

## When to Use

- Before any multi-file change
- Before any new feature
- When you need to understand the impact of a change before committing

## Usage

```
/plan Add a new /v1/embed endpoint to proxy.py that routes to an embedding model
/plan Refactor the rate limiter out of proxy.py into its own module
/plan Add test coverage for the health check fallback path in router/health.py
```

## References

- `.claude/agents/planner.md`
- `.claude/skills/implementation-planner/SKILL.md`

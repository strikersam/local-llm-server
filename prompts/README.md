# Prompt Library

> Inspired by [CL4R1T4S](https://github.com/elder-plinius/CL4R1T4S) — a project dedicated to
> AI system prompt transparency. This library maintains a public, versioned record of every
> behavioral instruction active in this repository's AI agents.

## What Is This?

Every AI agent in this repository operates according to explicit behavioral instructions —
system prompts, skill definitions, and agent personas. This library makes all of those
instructions **visible, browsable, and auditable** by anyone.

No hidden behaviors. No opaque instructions. Full clarity.

---

## Agents

| Agent | Role | Source |
|-------|------|--------|
| **implementer** | Executes implementation tasks from plans | [`.claude/agents/implementer.md`](../.claude/agents/implementer.md) |
| **judge** | Evaluates quality and correctness of outputs | [`.claude/agents/judge.md`](../.claude/agents/judge.md) |
| **planner** | Breaks down tasks into structured implementation plans | [`.claude/agents/planner.md`](../.claude/agents/planner.md) |
| **reviewer** | Reviews code and implementation for issues | [`.claude/agents/reviewer.md`](../.claude/agents/reviewer.md) |
| **scout** | Researches and gathers context before implementation | [`.claude/agents/scout.md`](../.claude/agents/scout.md) |

---

## Skills

| Skill | Purpose | Trigger |
|-------|---------|---------|
| `agent-harness` | Run and coordinate multiple agents | On demand |
| `auto-fix` | Automatically fix common code issues | On demand / CI |
| `brain-dump` | Capture and structure unstructured thoughts | On demand |
| `changelog-enforcer` | Enforce changelog discipline | Pre-commit / review |
| `context-prime` | Load relevant context before a task | Session start |
| `cooldown-resume` | Resume after a context window cooldown | On context limit |
| `council-review` | Multi-agent review council | Pre-merge |
| `debug-tracer` | Trace and debug unexpected behaviors | On bug report |
| `dependency-audit` | Audit project dependencies for risk | Release / on demand |
| `deslop` | Remove AI slop and improve output quality | Post-generation |
| `docs-sync` | Keep documentation in sync with code | Post-change |
| `email-triage` | Triage and prioritize email/issues | On demand |
| `feature-flag` | Manage feature flags safely | Feature development |
| `implementation-planner` | Generate detailed implementation plans | Pre-implementation |
| `insights` | Generate insights from data or logs | On demand |
| `learn-rule` | Learn and codify new project rules | Post-incident |
| `local-ai-query` | Query local AI models | On demand |
| `modularity-review` | Review code for modularity and coupling | Pre-merge |
| `parallel-agents` | Run agents in parallel for speed | Large tasks |
| `parallel-worktrees` | Use git worktrees for parallel work | Large features |
| `pro-workflow` | Professional-grade workflow execution | Complex tasks |
| `prompt-library` | Maintain this prompt library | Post-agent-change |
| `prompt-transparency` | Generate transparency reports | Governance / release |
| `release-readiness` | Gate releases with quality checks | Pre-release |
| `replay-learnings` | Replay and apply past learnings | Session start |
| `repo-memory-updater` | Keep repo memory current | Post-session |
| `research` | Deep research on a topic | Pre-implementation |
| `risky-module-review` | Review high-risk code modules | Pre-merge |
| `sandboxed-exec` | Execute code in a safe sandbox | Testing |
| `scope-guard` | Prevent scope creep | During implementation |
| `session-handoff` | Hand off context between sessions | Session end |
| `smart-commit` | Generate meaningful commit messages | Post-implementation |
| `system-prompt-audit` | Audit all system prompts for consistency | Governance / release |
| `test-first-executor` | TDD-style test-first implementation | Feature development |
| `ticket-to-pr` | Convert a ticket/issue into a PR | Issue workflow |
| `wrap-up` | Clean session wrap-up and handoff | Session end |

---

## Commands

| Command | Description | Source |
|---------|-------------|--------|
| `/plan` | Generate an implementation plan | [`.claude/commands/plan.md`](../.claude/commands/plan.md) |
| `/resume` | Resume from a previous session | [`.claude/commands/resume.md`](../.claude/commands/resume.md) |
| `/review` | Run a full review cycle | [`.claude/commands/review.md`](../.claude/commands/review.md) |

---

## Transparency

See [`TRANSPARENCY.md`](./TRANSPARENCY.md) for a plain-language explanation of how
these agents behave and what guardrails are in place.

---

## How This Library Is Maintained

This library is updated by the `prompt-library` skill whenever:
1. A new agent or skill is added
2. An existing agent's behavior changes
3. A release is being prepared

Changes are tracked in [`CHANGELOG.md`](./CHANGELOG.md).

---

## Philosophy

> *"The most powerful thing you can do with a system prompt is publish it."*
>
> Inspired by [CL4R1T4S](https://github.com/elder-plinius/CL4R1T4S) by Elder Plinius —
> collecting and publishing AI system prompts so the world can see exactly how
> AI assistants are instructed to behave.

# Skill: parallel-agents

## Purpose
Decompose a large task into N independent subtasks and dispatch them as parallel subagents, then aggregate results. Inspired by the Modal + OpenAI Agents SDK pattern of spawning multiple coding agents simultaneously — each working in its own sandbox — to discover solutions faster through parallelism.

## When to Use
- A task has multiple independent sub-problems (e.g. "try 5 different approaches to optimise this function").
- You want competitive parallel exploration (like Parameter Golf — many agents racing to find the best solution).
- Long-running background work that should not block the main conversation.
- Fan-out research: gather information from many sources simultaneously.

## Core Concepts (from the Modal/OpenAI Agents SDK pattern)

| Concept | Description |
|---------|-------------|
| **Harness** | The outer loop that owns the task, spawns subagents, and collects results |
| **Subagent** | An isolated agent instance working on one subtask with its own tool set |
| **Capability** | A bound set of tools attached to a specific subagent instance (stateful) |
| **Aggregator** | Logic that merges/ranks subagent outputs into a final result |

## Usage

```
@parallel-agents
task: <high-level goal>
subtasks:
  - <subtask 1>
  - <subtask 2>
  - <subtask N>
strategy: <first-wins | collect-all | best-of>
```

### Strategies
- **first-wins** — return as soon as any subagent succeeds (good for speculative execution).
- **collect-all** — wait for all subagents, return all results.
- **best-of** — collect all, then score/rank and return the top result.

### Example — parallel approach exploration
```
@parallel-agents
task: Optimise the tokenizer for throughput
subtasks:
  - Try a Rust rewrite of the hot path
  - Try SIMD intrinsics in C via cffi
  - Try batching + async I/O in Python
  - Try a pre-computed lookup table approach
strategy: best-of
```

### Example — parallel research
```
@parallel-agents
task: Summarise competing approaches to RAG chunking
subtasks:
  - Fixed-size chunking strategies
  - Semantic / sentence-boundary chunking
  - Recursive character splitting
  - Document-structure-aware chunking
strategy: collect-all
```

## Steps (for Claude to follow)

### Phase 1 — Decompose
1. Break the top-level `task` into the listed `subtasks`.
2. Confirm each subtask is **independent** (no shared mutable state).
3. Assign each subtask a short ID: `agent-1`, `agent-2`, … `agent-N`.

### Phase 2 — Dispatch (simulate parallelism)
For each subtask, run it as a focused sub-problem:
- State the subtask clearly.
- Use `sandboxed-exec` if code execution is needed.
- Record outputs under the agent ID.

### Phase 3 — Aggregate
Apply the chosen strategy:
- **first-wins**: stop at first success, report winner.
- **collect-all**: present all results in a structured table.
- **best-of**: score each result against the original goal, declare winner with rationale.

## Output Format

```
PARALLEL AGENTS REPORT
======================
Task     : <task>
Strategy : <strategy>
Agents   : <N>

RESULTS
-------
[agent-1] Status: ✅ | Summary: ...
[agent-2] Status: ✅ | Summary: ...
[agent-3] Status: ❌ | Error:   ...

AGGREGATED OUTCOME
------------------
<Winner / all results / ranked list depending on strategy>

NEXT STEPS
----------
<Recommended follow-up actions>
```

## Combining with Other Skills
- Use `sandboxed-exec` per subagent to isolate execution.
- Use `research` skill for subtasks that are information-gathering.
- Use `implementation-planner` to break a feature into subtasks before handing off to this skill.
- Use `council-review` on the aggregated output for a final quality pass.

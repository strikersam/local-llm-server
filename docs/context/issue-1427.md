# Issue #1427: quick-note:https://github.com/bingreeky/JIT

_Generated: 2026-09-05 (Claude Code session, manual pickup — the autonomous
pipeline never fetched the source; see "Why this was written by hand" below)._

## Context Plan — Issue #1427: quick-note:https://github.com/bingreeky/JIT

> Architect pass for the quick-note. Grounds the source against this repo and
> gives a bounded recommendation, per the issue's own instruction: *"Add context
> from the url corresponding to this repo which will benefit enhancing this repo
> instead of adding random features."*

---

## Source Grounding

| | |
|---|---|
| Source URL | https://github.com/bingreeky/JIT |
| Fetch status | ✅ **FETCHED** — read via `WebFetch` in this session (the automated `fetch_url` strategies all returned empty for this repo, which is why every prior run proceeded blind) |
| Read by | Claude (Opus 4.8), this session |
| Project name | **JIT-Agent** — "writes your agent harness on the fly" |

---

## What the source actually is

**JIT-Agent** is a research **meta-agent**: instead of shipping one static,
general-purpose scaffold and hoping it transfers across tasks, it takes a task
specification, protocol, tool registry, and prior harnesses and **generates
task-specific harness code on the fly**. Its thesis is that *the scaffold itself
is a trainable, transferable axis of agent intelligence — orthogonal to scaling
the base model.*

It factors every generated harness into **four modular components** behind shared
interfaces (a `HarnessFactory`):

1. **Memory management**
2. **Planning strategy**
3. **Action execution**
4. **Capability orchestration**

The generator stays **frozen**; the generated harness improves **at test time**
from execution traces and feedback. Candidate harnesses are chosen by a
judge-based or logprob-based selection step, and it is evaluated across xbench,
DeepSearchQA, AgentIF, OfficeBench, Odyssey, and others.

This is genuinely adjacent to what this repository is — a multi-agent execution
platform — so it is **not** a "reject, nothing here belongs" case. The tension is
scope, not relevance.

---

## How its four axes map onto what this repo already has

The important finding for an architect: **this repo already implements all four
of JIT-Agent's axes** — they are just **statically wired** into one loop
(`AgentRunner`, `agent/loop.py`) rather than generated per task.

| JIT-Agent component | Already in this repo |
|---|---|
| Memory management | `agent/memory.py`, `agent/persistent_memory.py`, `agent/procedural_memory.py`, `agent/user_memory.py`, `agent/context_manager.py`, `agent/context_pruner.py`, `agent/rag_context.py` |
| Planning strategy | `AgentRunner._plan` / the Planner role (`DEFAULT_PLANNER_MODEL`, `agent/loop.py`) |
| Action execution | `AgentRunner._execute_step` / the Executor role (`agent/loop.py`) |
| Capability orchestration | `agent/capability_registry.py` (+ `build_tool_prompt` in `agent/prompts.py`, CLAUDE.md rule 19) |
| Test-time improvement from traces | `agent/improvement_loop.py`, `agent/self_healing.py` |
| Candidate/role selection | `router/` + the brain failover chain (`packages/ai/failover_client.py`); role→model presets in `agents/profiles.py` |

The **one thing JIT-Agent adds that this repo does not have** is the meta-level
move: *generating a fresh, task-shaped harness per task* instead of running the
same fixed Planner→Executor→Verifier loop for every task.

---

## Decision

🟡 **ADOPT-PARTIAL — one bounded idea is worth proposing; full adoption is a
human-sign-off item, not an autonomous change.**

**Do not** port JIT-Agent wholesale. Replacing the fixed three-role loop with a
per-task harness generator is a breaking architectural change to `agent/loop.py`
and the agent package — squarely CLAUDE.md **rule 40** (stop and ask a human
before a change spanning more than 5 files in `agent/loop.py`, or any breaking
change) and **rule 1** (do not change user-visible behaviour that was not
requested). Bolting on a half-built generator would be exactly the "random
features" this issue tells us to avoid.

**The adoptable slice** — small, in-scope, and true to the paper's actual insight
("the scaffold is a transferable axis; pick/refine it from traces"):

- **Harness-selection memory.** Record, per completed task, which harness
  configuration was used (planner/executor/verifier model + step count + any
  strategy flags) alongside the outcome (verified pass / fail / retries), and
  let the planner **prefer the configuration that has worked for that task
  shape**. This reuses `agent/procedural_memory.py` (which already exists for
  "what worked before") and feeds `agent/improvement_loop.py`. It is additive,
  behind a flag, and changes no default behaviour — it only biases model/role
  selection when prior evidence exists.

This is a **proposal, not an implemented change**: it still touches the agent
loop's hot path, so it needs an explicit go-ahead and an `implementation-planner`
pass before code, per rule 40.

---

## What was considered and rejected

- **Full `HarnessFactory` / per-task code generation** — rejected for this repo
  now: rule 40 breaking change; the Verifier/`apply_diff` safety invariants
  (rules 16–20) assume a fixed loop shape, and a generated loop would have to
  re-establish every one of them.
- **The four-component interface refactor** — rejected as an autonomous change:
  the components already exist as concrete modules; formalising them into
  swappable interfaces is a large refactor with real behaviour-change risk
  (rule 1) and no requested user-facing benefit on its own.
- **Adding the benchmark harnesses (xbench, OfficeBench, …)** — rejected: they
  are JIT-Agent's evaluation targets, not features of a proxy/agency platform.

---

## Why this was written by hand

Every automated attempt on #1427 failed before producing context: the context
generator ran on a dead NVIDIA model list (fixed in #1431), the implement
pipeline then exhausted every free provider (NVIDIA 404/429, Cerebras 402/403,
Groq 413, Mistral 429 — a keys/quota outage, correctly labelled
`blocked:infrastructure`), and `fetch_url` returned empty for this GitHub repo on
every try, so the agent never actually read the source it was asked to assess.
This document is the architect pass done directly, with the source genuinely
read.

---

## Recommendation to the maintainer

1. Close #1427 as **contextualised** — the source is understood and grounded.
2. If the harness-selection-memory idea is wanted, open a fresh, scoped issue and
   run it through `implementation-planner` + a rule-40 confirmation before any
   code lands in `agent/`.
3. The provider-exhaustion that blocked the automation is unchanged by this
   document — it needs a key rotation / tier bump or an enabled paid fallback
   (`PROVIDER_POLICY_ALLOW_PAID`), which is a spend decision for the maintainer.

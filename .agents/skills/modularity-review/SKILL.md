---
name: modularity-review
description: >
  Review codebase or design for modularity problems and produce actionable
  improvement recommendations. Also guides design of new modular boundaries
  from functional requirements. Inspired by Vlad Khononov's balanced-coupling
  model and golden-age-of-modularity principles.

  NOTE: Full upstream plugin at https://github.com/vladikk/modularity
  Install it for the complete experience: follow instructions at that URL.
  This skill is a clean-room local adaptation for this repo.
triggers:
  - "review for modularity"
  - "is this modular?"
  - "improve the design"
  - "too much coupling"
  - "design a new module"
  - "how should I split this?"
  - any module with >3 direct imports from unrelated parts of the system
references:
  - docs/architecture/overview.md
  - docs/adrs/
  - AGENTS.md (Codebase Map)
---

# Skill: modularity-review

## The Core Principle

> **Modularity is about change.** A codebase is modular when it is crystal-clear
> which components need to change for a given requirement, and ideally that number
> is small — preferably one. If change radiates unpredictably, the system is coupled.

A secondary modern concern: **modularity makes code accessible to AI**. LLMs have
finite context windows. Tightly coupled codebases force large, entangled contexts
onto every reasoning task. Well-modularized code lets AI (and humans) reason about
one bounded piece at a time.

## When to Use

- Before designing a new module, service, or capability
- When a change requires touching 5+ files across unrelated modules
- When tests are hard to write because of dependency tangles
- When a new team member can't understand a module without reading 3 others
- When the AI agent loop requires large context to accomplish a focused task

---

## Part A: Reviewing Existing Code for Modularity Problems

### Step 1 — Map the dependency graph

For each module in the repo, list what it imports:

```bash
# Python: list all internal imports
grep -r "^from\|^import" --include="*.py" . | grep -v ".venv" | grep -v "test_"
```

Build a mental (or written) graph: which modules depend on which.

### Step 2 — Identify coupling smells

Look for these patterns:

| Smell | Description | Example in this repo |
|-------|-------------|----------------------|
| **Feature envy** | Module A uses many internals of module B | `proxy.py` reaching into `agent/loop.py` internals |
| **Shotgun surgery** | One change requires edits in 5+ files | Adding a new model type requires editing registry, classifier, router, and tests |
| **Divergent change** | One module changes for many unrelated reasons | `proxy.py` handles auth, routing, streaming, rate limiting all at once |
| **Improper abstraction** | Implementation detail leaks through module boundary | Caller knows which HTTP client the callee uses |
| **Circular dependency** | A imports B, B imports A | Usually causes import errors in Python |
| **God module** | One file does everything | `proxy.py` risks becoming this |

### Step 3 — Apply the balanced-coupling test

For each module boundary, ask:
1. **Cohesion** — Do the functions inside this module all serve the same purpose?
   - High cohesion = good. Mixed concerns = split candidate.
2. **Coupling** — When this module changes, how many other modules must change?
   - Low coupling = good. High coupling = refactor candidate.
3. **Change locality** — When a real business requirement changes, does the change
   stay local to one module? If not, where does it leak?

### Step 4 — Produce findings

For each finding, use this format:

```
## Finding: <smell name>
**Severity:** Low / Medium / High
**Location:** `<file>:<line-range or function>`
**Problem:** What is wrong and why it matters.
**Impact:** How many files must change together when this is touched.
**Recommendation:** Specific change to improve this boundary.
```

### Step 5 — Prioritize by change frequency

High-change, high-coupling areas are the most damaging. Prioritize:
1. Files changed in the last 10 commits (check `git log --stat`)
2. Files with the most imports from other modules
3. Files where test setup is hardest (usually over-coupled)

---

## Part B: Designing New Modular Boundaries

When adding a new capability, use this process before writing code:

### Step 1 — State the bounded context

Write one sentence: "This module is responsible for _____ and nothing else."

If you cannot write that sentence, the scope is unclear. Narrow it.

### Step 2 — Define the interface (contract first)

Before writing implementation, define:
- What data goes in (types/shapes)
- What data comes out (types/shapes)
- What errors it can raise
- What it must NOT know about (its ignorance contract)

For Python: write the class/function signatures and Pydantic models first.

### Step 3 — Identify dependencies

List everything this new module needs from outside.
For each dependency, ask: "Could this be injected rather than imported?"
Prefer dependency injection over direct import for anything that could vary.

### Step 4 — Validate with the change test

Imagine 3 future requirements that would reasonably be added later.
For each: would the change stay inside this module, or leak into callers?
If leaks in 2/3 cases: redesign the boundary now.

### Step 5 — AI-accessibility check

Imagine this module must be understood by an AI agent with a 2000-token context.
Can the module's purpose, interface, and invariants be understood from:
- Its `AGENTS.md` (or docstring), and
- Its public function/class signatures?

If yes: the module is well-bounded. If no: add a module `AGENTS.md` or simplify.

---

## Modularity Findings Template

```markdown
# Modularity Review — <date>

## Summary
<1-3 sentences on overall state>

## High-Priority Findings
(findings that should be addressed before next major feature)

## Medium-Priority Findings
(technical debt worth tracking)

## Low-Priority Findings
(nice to have, not urgent)

## Recommended Module Splits or Extractions
(if any)

## AI Accessibility Assessment
<Are the module boundaries clear enough for AI-assisted development?>
```

---

## Applying to This Repo

**Current modularity strengths:**
- `router/` is well-bounded: routing in, `RoutingDecision` out, no side effects
- `agent/` is reasonably bounded with clear plan→execute→verify flow

**Known coupling risks:**
- `proxy.py` is large (~27k bytes) and handles auth, routing, rate limiting, streaming, and agent requests — candidate for incremental decomposition
- `chat_handlers.py` knows about Langfuse, routing, and streaming — mixed concerns

**Recommended first steps:**
1. Extract rate limiting from `proxy.py` into `rate_limiter.py`
2. Extract auth middleware from `proxy.py` into `auth_middleware.py`
3. Add module docstrings to each package `__init__.py` stating the bounded context

---

## Acceptance Checks

- [ ] Dependency graph reviewed
- [ ] Coupling smells identified and documented
- [ ] Balanced-coupling test applied to changed/new module
- [ ] Findings prioritized by change frequency
- [ ] Module boundary stated in one sentence
- [ ] Interface defined before implementation (for new modules)
- [ ] AI-accessibility check passed (readable in ~2000 tokens)
- [ ] Findings documented in `docs/adrs/` if architectural decision made

---

## Further Reading

- Vlad Khononov's blog: https://vladikk.com (see "The Golden Age of Modularity")
- Full upstream modularity plugin: https://github.com/vladikk/modularity
- ADR 003 in this repo: `docs/adrs/003-multi-agent-orchestration.md`

# Skill: Skill Composer

## Purpose
Enables the agent to combine multiple existing skills into a coordinated workflow for complex tasks that no single skill covers. Acts as an orchestration layer over the skill library.

## When to Use
- When a task clearly requires multiple skills in sequence
- When a skill's process says "see also" another skill
- When parallel execution of skills would improve throughput (pair with `parallel-agents`)
- When building a new repeatable multi-step workflow worth capturing as a composed skill

## Process

### 1. Decompose the Task
- Break the task into discrete sub-tasks
- Map each sub-task to an existing skill if one exists
- Note sub-tasks with no matching skill (candidates for `self-improve`)

### 2. Sequence the Skills
- Determine dependencies between sub-tasks (what must complete before what)
- Identify which sub-tasks can run in parallel
- Draft an execution order

### 3. Execute in Order
- Invoke each skill in sequence, following its SKILL.md instructions fully
- Pass outputs from one skill as inputs to the next where applicable
- Log progress at each step

### 4. Handle Failures
- If a skill step fails, apply `auto-fix` or `debug-tracer` before continuing
- Do not skip steps unless explicitly allowed
- If a step is truly blocked, document why and continue with remaining steps

### 5. Synthesize Output
- Combine outputs from all skills into a coherent final result
- Ensure no conflicts between outputs (e.g., duplicate changelog entries)
- Run a final validation pass

### 6. Document the Composition
- If this skill composition was valuable and repeatable, consider creating a new skill with `self-improve`
- Add a changelog entry

## Output
- All outputs defined by each composed skill
- A unified, non-conflicting result
- Optional: a new composed skill definition if the pattern is reusable

## Example Compositions
- `context-prime` → `implementation-planner` → `issue-resolver` → `changelog-enforcer`
- `dependency-audit` → `risky-module-review` → `council-review`
- `research` → `brain-dump` → `implementation-planner` → `parallel-agents`

## Notes
- Do not compose skills that contradict each other
- Respect cooldown and checkpoint patterns when composing long workflows
- Keep the composition lean — more skills is not always better

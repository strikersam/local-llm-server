# Skill: Task Scoper

## Purpose
Prevents scope creep by explicitly defining the boundaries of a task before implementation begins. Ensures the agent works on exactly what was asked — no more, no less.

## When to Use
- At the start of any non-trivial implementation task
- When an issue or instruction is broad or ambiguous
- When tempted to "clean up" or "improve" things unrelated to the task
- Before invoking `implementation-planner` or `parallel-agents`

## Process

### 1. Read the Task Carefully
- Identify the single core ask
- List explicit requirements stated in the task
- List implicit requirements (things obviously needed but not stated)
- List things explicitly excluded (if any)

### 2. Define the Boundary
Write a one-paragraph scope statement:
> "This task will [do X] by [method Y]. It will NOT [do Z] even if Z seems related."

### 3. Identify Temptations
- List things you might be tempted to change that are out of scope
- Examples: refactoring unrelated code, updating docs not touched by the change, fixing unrelated bugs noticed along the way

### 4. Lock the Scope
- Commit to the scope statement before writing any code
- If during implementation you discover the scope was wrong, stop and re-scope rather than expanding silently

### 5. Out-of-Scope Findings
- Log any out-of-scope issues found during implementation as separate notes
- These can become new issues or tasks — do not fold them into the current task
- Use `learn-rule` if the out-of-scope finding is a pattern worth capturing

## Output
- A clear scope statement (can be inline reasoning)
- A list of intentionally excluded items
- A focused implementation that respects the defined boundaries

## Notes
- Scope creep is one of the most common failure modes for AI agents
- A smaller, correctly-scoped change is always better than a larger, drifted one
- When in doubt, do less and document what was left out

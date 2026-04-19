# Skill: context-prime

## Purpose
Prime Claude with deep repository context before starting any significant task. Ensures Claude has a full mental model of the codebase architecture, conventions, and constraints before writing a single line of code.

## Trigger
Use at the start of:
- A new coding session on an unfamiliar area
- A complex feature that touches many files
- A debugging session for a hard-to-reproduce bug
- Onboarding to a new repository

## Process

### Step 1: Read Core Docs
In order:
1. `CLAUDE.md` — primary instructions and conventions
2. `README.md` — project overview and purpose
3. `TOOLS.md` — available tooling
4. `agent/CLAUDE.md` — agent-specific context (if exists)
5. Any `docs/` folder overview files

### Step 2: Map the Architecture
Scan the top-level directory structure. For each major directory:
- Identify its purpose
- Note key files within it
- Understand how it connects to other directories

Build a mental map: `[module] → [responsibility] → [interfaces with]`

### Step 3: Find Conventions
Look for patterns across 5-10 representative files:
- Naming conventions (files, functions, classes, variables)
- Import organization style
- Error handling patterns
- Testing patterns (test file location, naming, fixtures)
- Comment/docstring style
- Type annotation usage

### Step 4: Understand Data Flow
Trace the main data flow through the system:
- Entry points (API routes, CLI commands, event handlers)
- Core processing logic
- Storage/persistence layer
- Output/response formation

### Step 5: Identify Constraints
Note any explicit constraints from CLAUDE.md or comments:
- Performance-sensitive areas
- Security boundaries
- Deprecated patterns to avoid
- In-progress refactors to be aware of

### Step 6: Declare Readiness
Output a structured context summary:

```
## Context Prime Complete

### Project
[1-2 sentence description of what this project does]

### Architecture
- [Layer/Module]: [responsibility]
- [Layer/Module]: [responsibility]

### Key Conventions
- [Convention]: [example]
- [Convention]: [example]

### Data Flow
[Entry] → [Processing] → [Storage] → [Output]

### Constraints to Respect
- [Constraint]
- [Constraint]

### Ready for Task
I have sufficient context to begin. Proceeding with: [task description]
```

## Rules
- Do NOT start implementing before completing this skill
- If CLAUDE.md contradicts README.md, CLAUDE.md wins
- Note areas of uncertainty explicitly rather than assuming
- Re-prime if switching to a completely different part of the codebase
- Keep the summary concise — this is a mental model, not a transcript

## Value
This skill prevents the most common failure mode: writing code that technically works but violates project conventions, misunderstands architecture, or duplicates existing functionality.

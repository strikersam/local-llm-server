# Skill: system-prompt-audit

## Purpose
Audit all system-level instructions embedded in this repository's Claude configuration,
surface them as a structured inventory, and validate them for consistency, safety,
and alignment with project goals.

Inspired by CL4R1T4S (Latin: "clarity") — the open-source project that collects and
publishes AI system prompts to promote transparency.

## When to Use
- Run before merging changes to `.claude/` directory
- Run as part of release readiness checks
- Run when a new agent or skill is added
- Run on-demand for governance audits

## Steps

### 1. Inventory Collection
```
Scan the following paths:
  .claude/agents/       → agent persona definitions
  .claude/skills/       → skill behavioral specs
  .claude/commands/     → command implementations
  CLAUDE.md             → root-level project instructions
```

For each file, record:
- File path
- Word count (proxy for complexity)
- Presence of: role definition, constraints, examples, output format

### 2. Consistency Check
Cross-reference all files for:
- **Duplicate roles**: two agents claiming the same responsibility
- **Contradictory constraints**: one skill allows X, another forbids X
- **Missing output formats**: skills that don't specify what they produce
- **Undocumented side effects**: skills that write files/commit without stating so

### 3. Safety Check
Flag any instructions that:
- Allow unrestricted file system writes
- Allow network calls without validation
- Grant escalated permissions
- Lack human-in-the-loop checkpoints for destructive operations

### 4. Generate Audit Report
Write `docs/system-prompt-audit.md` with:

```markdown
# System Prompt Audit Report
Generated: <timestamp>

## Summary
- Total components audited: N
- Agents: N | Skills: N | Commands: N
- Issues found: N (critical: N, warnings: N, info: N)

## Inventory Table
| Component | Type | Role | Has Constraints | Has Examples |
|-----------|------|------|-----------------|--------------|

## Issues
### Critical
...
### Warnings
...
### Info
...

## Full Behavioral Inventory
[per-component breakdown]
```

### 5. Exit Codes
- **0**: No issues found
- **1**: Warnings found (non-blocking)
- **2**: Critical issues found (should block merge)

## Integration
Add to `.claude/commands/review.md` as an optional step:
```
- [ ] Run system-prompt-audit before final review sign-off
```

## Related Skills
- `prompt-transparency` — generates human-facing transparency docs
- `release-readiness` — broader release gate checks
- `council-review` — multi-agent review process

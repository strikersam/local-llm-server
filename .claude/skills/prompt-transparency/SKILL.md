# Skill: prompt-transparency

## Purpose
Inspired by the CL4R1T4S project (github.com/elder-plinius/CL4R1T4S), this skill audits and surfaces all implicit behavioral instructions, system prompts, and agent directives embedded in this repository. It generates a human-readable transparency report so anyone can understand *exactly* how the AI agents in this repo are instructed to behave.

## When to Use
- When onboarding new contributors who want to understand agent behavior
- Before a release to document what behavioral rules are active
- When debugging unexpected agent behavior
- Periodically as a governance/transparency checkpoint

## Steps

### 1. Collect All Agent & Skill Definitions
Scan and read every file that contains behavioral instructions:
- `.claude/agents/*.md` — named agent personas and their directives
- `.claude/skills/*/SKILL.md` — skill behavioral definitions
- `.claude/commands/*.md` — slash command behaviors
- `CLAUDE.md` (root) — global project-level instructions (if present)
- `.claude/state/*` — current runtime state

### 2. Extract Key Behavioral Dimensions
For each file found, extract:
- **Role/Persona**: What role does this agent/skill play?
- **Constraints**: What is it explicitly told NOT to do?
- **Capabilities**: What is it allowed/instructed to do?
- **Tone/Style**: Any communication style directives?
- **Decision Rules**: Any if/then behavioral rules?

### 3. Generate Transparency Report
Output a structured report to `docs/prompt-transparency-report.md` with:
- Summary table of all active agents and skills
- Full behavioral inventory per component
- Conflict detection (contradictory instructions across agents)
- Coverage gaps (areas with no behavioral guidance)

### 4. Flag Risks
Highlight any instructions that:
- Grant broad permissions without guardrails
- Could conflict with each other
- Are ambiguous or underspecified

### 5. Commit the Report
Use the `smart-commit` skill to push the report with a clear commit message.

## Output Format

```
docs/prompt-transparency-report.md
```

## Example Usage
```
/project:prompt-transparency
```

## Inspiration
CL4R1T4S by Elder Plinius — a project dedicated to publishing AI system prompts
for public transparency. This skill applies that same philosophy internally:
every repo using AI agents should be able to show exactly what behavioral
instructions are active at any given time.

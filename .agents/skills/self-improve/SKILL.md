# Skill: Self-Improve

## Purpose
Enables the agent to analyze its own skill library, identify gaps or weaknesses, and propose or implement improvements to existing skills or new skill definitions.

## When to Use
- After completing a complex task where no existing skill quite fit
- When patterns emerge across multiple issues/tasks that aren't yet captured as skills
- When a skill's instructions led to suboptimal results
- Periodically as a meta-maintenance task

## Process

### 1. Audit Existing Skills
- Read all `.agents/skills/*/SKILL.md` files
- Note skills that are vague, outdated, or missing key steps
- Identify overlapping skills that could be merged

### 2. Identify Gaps
- Review recent issue resolutions and pull requests
- List patterns that recurred but lacked a matching skill
- Consider what skills would have saved time or improved quality

### 3. Propose Improvements
- For each gap or weakness, draft a new or updated SKILL.md
- Follow the existing skill format (Purpose, When to Use, Process, Output, Notes)
- Keep skills atomic and composable — one concern per skill

### 4. Implement
- Write new skill files to `.agents/skills/<skill-name>/SKILL.md`
- Update existing skills in place if improving them
- Do not delete skills without a clear reason documented in the changelog

### 5. Validate
- Confirm new skills follow repository conventions
- Cross-reference new skills with existing ones to avoid duplication
- Add changelog entry under `[Unreleased]`

## Output
- One or more new or updated `.agents/skills/*/SKILL.md` files
- A changelog entry summarizing what was added or changed

## Notes
- Skills should be written for an AI agent audience, not human developers
- Prefer explicit step-by-step instructions over abstract descriptions
- When improving a skill, preserve its original intent unless the intent itself was wrong

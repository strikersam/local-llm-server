# Skill: Brain Dump

## Purpose
Convert a chaotic list of scattered ideas, notes, or thoughts into a structured, prioritized action plan. Transforms raw cognitive output into organized tasks with clear next steps.

## When to Use
- You have a messy list of ideas and need structure
- Starting a new project and need to organize your thinking
- After a brainstorming session that needs to be actionable
- When feeling overwhelmed by too many loose threads

## Instructions

### Step 1: Capture Everything
Ask the user to dump all their thoughts without filtering. Accept bullet points, sentences, fragments — anything goes.

### Step 2: Categorize
Group the raw input into logical buckets:
- **Now** — urgent or blocking items
- **Soon** — important but not immediate
- **Later** — good ideas to revisit
- **Discard** — noise or duplicates

### Step 3: Structure Each Item
For each retained item, define:
- A clear **action title** (verb + object, e.g., "Write onboarding doc")
- The **outcome** if completed
- Any **dependencies** on other items
- Estimated **effort** (S/M/L)

### Step 4: Produce the Plan
Output a structured markdown document:

```markdown
## Action Plan — [Date]

### 🔴 Now
- [ ] [Action] — [Why urgent] (Effort: S/M/L)

### 🟡 Soon
- [ ] [Action] — [Outcome] (Effort: S/M/L)

### 🟢 Later
- [ ] [Action] — [Outcome] (Effort: S/M/L)

### 🗑️ Discarded
- [Item] — [Reason discarded]
```

### Step 5: Confirm & Save
Ask the user to confirm the plan. If working inside the repo, offer to save to `docs/plans/brain-dump-YYYY-MM-DD.md`.

## Example Prompt to Trigger
```
/brain-dump
Here's everything on my mind: [paste messy notes]
```

## Output Format
- Structured markdown action plan
- Grouped by priority tier
- Each item has effort estimate and outcome
- Discarded items documented with reason

## Notes
- Don't judge the quality of the input — organize it as-is
- Keep action titles under 10 words
- If an item is vague, flag it with a ❓ and ask a clarifying question
- Cross-link items that depend on each other

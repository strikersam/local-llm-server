---
name: fabric-patterns
description: >
  Implements a Fabric-like reusable prompt pattern system. Allows storing,
  retrieving, and composing prompt patterns for consistent AI interactions.
triggers:
  - "use fabric pattern"
  - "apply pattern"
  - "stitch patterns"
references:
  - .claude/skills/prompt-library/SKILL.md
---

# Skill: fabric-patterns

## Purpose
Provides a reusable prompt pattern system inspired by Fabric (danielmiessler/fabric).
Enables agents to store, retrieve, and compose prompt patterns for consistent
and efficient AI interactions.

## When to Use
- When you need to reuse a specific prompt structure multiple times
- When you want to compose complex prompts from simpler patterns (stitching)
- When implementing agent behaviors that benefit from standardized prompt templates
- Before creating ad-hoc prompts that could be standardized

## Directory Structure
This skill creates and manages:
```
.claude/skills/fabric-patterns/
  patterns/                 ← Directory for storing pattern files
    summarize.md            ← Example pattern: summarize content
    extract_wisdom.md       ← Example pattern: extract key insights
    ...                     ← Other patterns
  PATTERN_INDEX.md          ← Index of all available patterns
```

## Pattern File Format
Each pattern is a Markdown file with optional YAML frontmatter:

```yaml
---
name: pattern_name
description: Human-readable description of what the pattern does
version: "1.0.0"
---
```

The content after the frontmatter is the prompt template. Template variables
can be used with {{variable_name}} syntax.

## Steps

### 1. Ensure Pattern Directory Exists
The skill ensures `.claude/skills/fabric-patterns/patterns/` exists.

### 2. List Available Patterns
Use the `list_patterns` tool to see all available patterns.

### 3. Retrieve a Pattern
Use the `get_pattern` tool to retrieve a pattern's content.

### 4. Apply a Pattern with Variables
Use the `apply_pattern` tool to render a pattern with specific variable values.

### 5. Stitch Patterns Together
Use the `stitch_patterns` tool to combine multiple patterns in sequence,
where the output of one pattern becomes the input to the next.

### 6. Create New Patterns
Create new Markdown files in the patterns directory following the format above.

## Tools Provided
This skill provides the following tools (to be implemented in agent/tools.py):
- `list_patterns()`: Lists all available pattern names and descriptions
- `get_pattern(name)`: Retrieves the raw content of a pattern
- `apply_pattern(name, variables)`: Applies a pattern with variable substitution
- `stitch_patterns(pattern_names, initial_input)`: Chains patterns together

## Example Patterns
### summarize.md
```yaml
---
name: summarize
description: Create a concise summary of the provided content
version: "1.0.0"
---
```
{{content}}

Please provide a concise summary of the above content, capturing the main points
in 3-5 sentences or less.
```

### extract_wisdom.md
```yaml
---
name: extract_wisdom
description: Extract key insights, quotes, and actionable ideas from content
version: "1.0.0"
---
```
{{content}}

From the above content, extract:
- Key insights and main ideas
- Notable quotes
- Actionable recommendations or takeaways
- Important references or citations

Format as a structured list.
```

## Integration with Agent System
Patterns can be used by any agent through the provided tools. For example:
- The Planner agent might use patterns to structure its planning prompts
- The Implementer agent might apply patterns when generating code comments
- The Reviewer agent might use patterns for consistent review criteria

## Related Skills
- `prompt-library`: Snapshots of agent and skill prompts for transparency
- `prompt-transparency`: Generates plain-language explanations of agent behaviors
- `system-prompt-audit`: Audits prompts for consistency and safety

## Acceptance Checks
- [ ] Pattern directory exists at `.claude/skills/fabric-patterns/patterns/`
- [ ] At least two example patterns exist (summarize, extract_wisdom)
- [ ] Tools for listing, getting, applying, and stitching patterns are implemented
- [ ] Pattern template variable substitution works correctly
- [ ] Stitching chains patterns properly (output of one becomes input to next)

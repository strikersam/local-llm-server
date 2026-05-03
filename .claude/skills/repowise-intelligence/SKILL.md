---
name: repowise-intelligence
description: >
  Implements codebase intelligence layers similar to repowise-dev/repowise.
  Provides dependency graph, git history, auto-generated documentation,
  and architectural decisions intelligence for AI agents.
triggers:
  - "use codebase intelligence"
  - "get code context"
  - "analyze repository"
references:
  - .claude/skills/prompt-library/SKILL.md
  - .claude/skills/system-prompt-audit/SKILL.md
---

# Skill: repowise-intelligence

## Purpose
Provides codebase intelligence layers inspired by repowise (https://github.com/repowise-dev/repowise).
Enables AI agents to understand the repository at a deeper level through:
- Dependency graph intelligence (file and symbol relationships)
- Git intelligence (history, ownership, co-changes)
- Documentation intelligence (auto-generated docs with freshness scoring)
- Decision intelligence (architectural decisions from git history)

## When to Use
- When an agent needs to understand "why" code was built a certain way
- Before making significant changes to understand impact and relationships
- When trying to reduce token usage by getting targeted context instead of reading full files
- When implementing features that benefit from understanding code ownership and change patterns
- When needing to answer complex questions about the codebase efficiently

## Directory Structure
This skill creates and manages:
```
.claude/skills/repowise-intelligence/
  intelligence/             ← Intelligence data storage
    dependency_graph.json   ← File and symbol dependency graph
    git_history.json        ← Git history analysis (hotspots, ownership, co-changes)
    documentation/          ← Auto-generated documentation for modules/files
    decisions.json          ← Architectural decisions extracted from git history
  INDEX.md                  ← Overview of available intelligence
```

## Intelligence Layers

### 1. Graph Intelligence (Dependency Graph)
- Parses files to build file-level and symbol-level dependency graphs
- Handles import aliases, barrel re-exports, namespace imports
- Tracks heritage (extends, implements, etc.)
- Uses community detection to find logical modules
- Calculates centrality measures (PageRank, betweenness) to identify important code

### 2. Git Intelligence
- Analyzes git history for:
  - Hotspot files (high churn × high complexity)
  - Ownership percentages per contributor
  - Co-change pairs (files that change together without import links)
  - Significant commit messages explaining evolution

### 3. Documentation Intelligence
- Auto-generated documentation for modules and files
- Rebuilt incrementally on changes
- Includes coverage tracking and freshness scoring
- Supports semantic search

### 4. Decision Intelligence
- Extracts architectural decisions from:
  - Git history (commit messages with WHY/DECISION/TRADEOFF patterns)
  - Inline markers in code
  - Explicit decision records
- Links decisions to the code they govern
- Tracks decision staleness as code evolves

## MCP Tools Provided
This skill provides the following tools (to be implemented in agent/tools.py):
- `get_overview()`: Architecture summary, module map, entry points, git health
- `get_answer(question)`: One-call RAG over documentation with confidence gating
- `get_context(targets, include?)`: Workhorse tool for docs, symbols, ownership, freshness
- `search_codebase(query)`: Semantic search over documentation
- `get_risk(targets?, changed_files?)`: Hotspot scores, dependents, co-change pairs
- `get_why(target)`: Get architectural decisions related to targets
- `get_decision_flownodes()`: Extract decision-linked flow nodes

## Tool Parameters
- `targets`: Can be files, symbols, or modules (supports wildcards and globs)
- `include`: Options for get_context: "source", "callers", "callees", "metrics", "community"
- In multi-repo mode: `repo` parameter to target specific repository

## Example Usage
```python
# Get overview of the codebase
overview = get_overview()

# Understand why auth works a certain way
why_auth = get_why(["auth/*.py", "key_store.py"])

# Get context for modifying a specific function
context = get_context(["agent.tools:build_planning_prompt"], 
                     include=["source", "callers", "callees"])

# Get an answer to a specific question
answer = get_answer("How does the agent planning system work?")

# Find risky areas before making changes
risk = get_risk(changed_files=["proxy.py"])
```

## Implementation Approach
1. **Initial Analysis**: Run comprehensive analysis to build all four intelligence layers
2. **Incremental Updates**: On each change, update only affected intelligence components
3. **Efficient Storage**: Use efficient data structures (JSON, SQLite) for quick retrieval
4. **Integration**: Hook into file change events to keep intelligence current
5. **Agent Access**: Provide tools that agents can call to access intelligence

## Related Skills
- `dependency-audit`: Reviews and validates dependencies (complements graph intelligence)
- `docs-sync`: Keeps documentation current (complements documentation intelligence)
- `system-prompt-audit`: Audits prompts for consistency and safety
- `repo-memory-updater`: Keeps CLAUDE.md and .claude/state/ in sync

## Acceptance Checks
- [ ] Intelligence directory structure exists
- [ ] Tools for all six intelligence functions are implemented
- [ ] Dependency graph intelligence layer functional
- [ ] Git intelligence layer functional  
- [ ] Documentation intelligence layer functional
- [ ] Decision intelligence layer functional
- [ ] Tools demonstrate significant token reduction vs naive approaches
- [ ] Integration with agent system demonstrated

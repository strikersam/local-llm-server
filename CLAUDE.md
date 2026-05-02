# CLAUDE.md

## Project Overview

**Name**: local-llm-server
**Type**: agent_system
**Description**: <div align="center">
**Key Technologies**: python

## Project Structure

- agent
- agents
- backend
- client-configs
- config-export
- docker
- docs
- frontend
- handlers
- hardware

**Key Files**:
- =0.23.0
- AGENTS.md
- AUTO-LAUNCHER-GUIDE.md
- AUTO-LAUNCHER-QUICK-START.txt
- AUTO-SETUP-GUIDE.txt
- AUTO-SETUP-READY.md
- CLAUDE-CODE-CLI-SETUP.md
- CLAUDE-CODE-COMMAND-LINE.md
- CLAUDE-CODE-QUICKSTART.md
- CLAUDE-CODE-SETUP-COMPLETE.md

## Agent System
This repository uses an agent-based system with the following agents:
- implementer
- judge
- planner
- reviewer

Total skills available: 70

The agent system includes:
- Planner: Creates structured plans from instructions
- Implementer: Executes file changes based on plans
- Reviewer: Verifies changes before application
- Judge: Provides final release gate approval

Agents can use skills from the .agents/skills/ and .claude/skills/ directories for specialized capabilities.

## Development Workflows

### Standard Workflow
1. **Planning**: Use the `/plan` command to break down tasks
2. **Implementation**: Agent executes the planned steps
3. **Review**: Changes are reviewed before application
4. **Checkpoint**: Progress is saved to `.claude/state/`
5. **Validation**: Tests are run to ensure quality

### Available Commands
- `/plan` - Create a plan for a task
- `/resume` - Resume interrupted work
- `/review` - Review code before committing

## Agent Guidelines

### When Working with Agents
1. Always start with clear instructions
2. Use skills for complex or repetitive tasks
3. Write to `.claude/state/` after each milestone
4. Run tests before and after code changes
5. Update documentation as needed

### Skill Usage
Skills provide reusable capabilities. To use a skill:
1. Ensure the skill is installed in `.agents/skills/` or `.claude/skills/`
2. The agent will automatically make skill tools available
3. Refer to the skill's documentation for specific usage

## File Conventions

### Text Files
- Use UTF-8 encoding
- Prefer Markdown (.md) for documentation
- Keep line lengths reasonable (< 100 characters when possible)

### Code Files
- Follow language-specific formatting conventions
- Include appropriate error handling
- Add comments for complex logic
- Write tests for new functionality

## State Management

The agent system uses `.claude/state/` for:
- `agent-state.json`: Full session state
- `NEXT_ACTION.md`: Next step to execute
- `checkpoint.jsonl`: Ordered log of completed steps
- `runner.lock`: Active session lock
- `session.log`: Session activity log

## Getting Started

To begin working with the agent system:
1. Ensure you have the necessary dependencies installed
2. Check that `.claude/agents/` contains agent definitions
3. Verify skills are available in `.agents/skills/` and `.claude/skills/`
4. Start with a simple task using the `/plan` command

---
*This CLAUDE.md file was generated automatically based on codebase analysis.*

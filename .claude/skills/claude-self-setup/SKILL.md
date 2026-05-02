---
name: claude-self-setup
description: >
  Implements Claude Code self-setup capabilities: self-audit, automated MCP server
  setup, skill installation, and CLAUDE.md generation - inspired by the XDA article
  on using Claude Code to set up Claude Code better.
triggers:
  - "self audit"
  - "setup myself"
  - "configure claude"
  - "self improve setup"
references:
  - .agents/skills/self-improve/SKILL.md
  - .claude/skills/fabric-patterns/SKILL.md
  - .claude/skills/repowise-intelligence/SKILL.md
---

# Skill: claude-self-setup

## Purpose
Provides self-setup capabilities inspired by the XDA article "I use Claude Code to set up Claude Code better".
Enables the agent to audit its own configuration, automatically set up MCP servers, install skills,
and generate/update CLAUDE.md files - essentially using the agent to improve its own setup.

## When to Use
- When setting up a new development environment or workspace
- After significant changes to understand current configuration gaps
- When wanting to automate repetitive setup tasks
- Before starting complex work to ensure optimal agent configuration
- Periodically to maintain and improve the agent's self-awareness and capabilities

## Key Features from XDA Article
1. **Self-audit capability** - Ask the agent to audit its current setup and identify missing configurations
2. **Automated MCP server setup** - Agent finds, installs, and configures MCP servers for external services
3. **Skill installation automation** - Agent creates, formats, and installs skills automatically
4. **CLAUDE.md generation** - Agent reads codebase and generates proper CLAUDE.md based on findings

## Directory Structure
This skill works with existing directories:
```
.claude/                        ← Existing agent configuration
  agents/                       ← Agent definitions (planner, implementer, etc.)
  skills/                       ← Skill definitions
  state/                        ← Session state and checkpoints
  commands/                     ← Agent commands (/plan, /resume, /review)
```

## Self-Audit Process
The self-audit capability follows this process:
1. **Configuration Analysis**: Examines current agent setup, skills, and configuration
2. **Gap Identification**: Compares against known beneficial configurations (MCP servers, skills, etc.)
3. **Recommendation Generation**: Suggests specific improvements with setup instructions
4. **Automated Fix Application** (optional): Can apply recommended changes automatically

## MCP Server Setup Automation
For MCP server setup, the agent can:
1. Identify desired external services (GitHub, Slack, Notion, etc.)
2. Search for official or community MCP servers
3. Install the MCP server package/service
4. Configure the agent to use the MCP server
5. Test the connection and report status

## Skill Installation Automation
For skill installation, the agent can:
1. Accept a skill description or GitHub URL
2. Create properly formatted SKILL.md file
3. Install it in the correct directory (.agents/skills/ or .claude/skills/)
4. Validate the skill follows repository conventions
5. Make the skill available for immediate use

## CLAUDE.md Generation
For CLAUDE.md generation, the agent can:
1. Analyze the codebase structure, patterns, and conventions
2. Identify key files, architectures, and workflows
3. Generate a comprehensive CLAUDE.md file documenting:
   - Project overview and purpose
   - Key directories and file types
   - Common development workflows
   - Coding standards and conventions
   - Agent-specific instructions and tips
   - Available skills and how to use them

## Tools Provided
This skill provides the following tools (to be implemented in agent/tools.py):
- `self_audit()`: Performs comprehensive self-audit of agent configuration
- `setup_mcp_server(service_name, config?)`: Automates MCP server setup for a service
- `install_skill(skill_source, skill_name?)`: Automates skill installation from various sources
- `generate_claude_md(target_path?)`: Generates CLAUDE.md based on codebase analysis
- `apply_recommendations(audit_results)`: Applies recommended improvements from audit

## Self-Audit Implementation
The self_audit() tool should check:
- Currently loaded skills and their effectiveness
- Available MCP servers and their configurations
- Agent command availability and usage
- State management and checkpointing
- Prompt library and transparency
- Integration with external tools (GitHub, etc.)
- Performance and optimization opportunities

## MCP Server Setup Implementation
The setup_mcp_server() tool should:
1. Maintain a registry of known MCP servers (GitHub, Notion, Slack, etc.)
2. For unknown services, search GitHub/MCP registry
3. Handle installation (pip, uv, manual download)
4. Configure MCP server in agent settings
5. Verify connection and report capabilities

## Skill Installation Implementation
The install_skill() tool should:
1. Accept skill source: GitHub URL, local file, or skill description
2. If description, generate proper SKILL.md format
3. Validate required sections: Purpose, When to Use, Process, Output
4. Install to appropriate skills directory
5. Register the skill for immediate use
6. Optionally run validation tests

## CLAUDE.md Generation Implementation
The generate_claude_md() tool should:
1. Analyze project structure using file_index and search_code
2. Identify key documentation (README, AGENTS.md, etc.)
3. Extract agent and skill information
4. Identify common patterns and workflows
5. Generate markdown following standard CLAUDE.md conventions
6. Optionally compare with existing CLAUDE.md and suggest updates

## Integration with Agent System
Self-setup features can be used by any agent:
- Planner: Use self-audit to understand capabilities before planning complex tasks
- Implementer: Automatically install needed skills before implementation
- Reviewer: Check if reviewer skill needs updating based on recent reviews
- All agents: Keep CLAUDE.md current with actual agent behaviors

## Related Skills
- `self-improve`: Agent self-improvement skill (foundation for this skill)
- `fabric-patterns`: Reusable prompt patterns (can be installed/updated via this skill)
- `repowise-intelligence`: Codebase intelligence (powers the analysis capabilities)
- `issue-resolver`: For resolving setup-related issues
- `skill-composer`: For combining multiple setup operations

## Acceptance Checks
- [ ] Self-audit tool provides meaningful configuration insights
- [ ] MCP server setup works for at least one service (e.g., GitHub)
- [ ] Skill installation works from GitHub URL and description
- [ ] CLAUDE.md generation produces useful documentation
- [ ] All tools integrate properly with existing agent system
- [ ] Error handling and edge cases are addressed

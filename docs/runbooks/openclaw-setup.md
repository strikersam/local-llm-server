# OpenClaw Setup and Integration

## What is OpenClaw?

OpenClaw (https://github.com/getmoss/openclaw-claude-code) is an open-source local
control plane for Claude Code sessions. It provides:
- Persistent session management
- Workspace-aware prompt injection
- Session resume after process restart
- Optional supervision / orchestration layer
- Local-first, no paid cloud dependency beyond the Claude API itself

## Integration Status for This Repo

**What is implemented (repo-native):**
- `.claude/state/` checkpoint system (fully functional, proven by simulation test)
- `scripts/ai_runner.py` watchdog with automatic cooldown detection and backoff
- `AGENTS.md` and `TOOLS.md` workspace context files
- `.claude/skills/` and `.claude/agents/` persona definitions

**What OpenClaw adds on top (install separately):**
- A daemon that wraps claude CLI sessions persistently
- Web UI for session management
- Cross-session memory and tool manifest serving
- Background council runs with transcripts

## Installing OpenClaw

```bash
# Prerequisites: Node.js 18+, claude CLI installed
npm install -g @anthropic-ai/claude-code    # if not already installed

# Install OpenClaw
git clone https://github.com/getmoss/openclaw-claude-code
cd openclaw-claude-code
npm install

# Start the OpenClaw daemon
npm start
```

## Linking This Repo as an OpenClaw Workspace

Once OpenClaw is running:

1. In the OpenClaw UI or config, add this repo as a workspace:
   ```json
   {
     "workspace_root": "/path/to/local-llm-server",
     "agents_file": "docs/AGENTS_REFERENCE.md",
     "tools_file": "TOOLS.md",
     "claude_md": "CLAUDE.md",
     "state_dir": ".claude/state"
   }
   ```

2. OpenClaw will read `docs/AGENTS_REFERENCE.md` for agent role definitions and `TOOLS.md` for
   the tool manifest.

3. Existing `.claude/skills/` skills will be used by Claude Code sessions started
   through OpenClaw.

## Persistent Sessions with OpenClaw

OpenClaw wraps `claude --session <name>` to provide persistent named sessions.
The `scripts/ai_runner.py` script already uses session naming compatible with this:

```bash
# Start a named session through ai_runner (OpenClaw compatible)
python scripts/ai_runner.py start --session my-feature "implement X"

# OpenClaw can then resume this same session by name
openclaw resume my-feature
```

## Shared vs Personal Memory

| Memory type | Location | OpenClaw behaviour |
|-------------|----------|-------------------|
| Repo instructions | `CLAUDE.md`, `agent/CLAUDE.md`, etc. | Shared, committed |
| Skills / agents | `.claude/skills/`, `.claude/agents/` | Shared, committed |
| Session state | `.claude/state/*.json` | Shared (but ephemeral, gitignored in some configs) |
| Personal notes | `~/.claude/` (outside repo) | Local only, not committed |

## Clean Separation

This repo's `.claude/` directory contains **project-level** AI engineering files
that should be committed and shared with the team. They are NOT personal settings.

Personal, machine-local notes should go in `~/.claude/CLAUDE.md` (Claude Code global config).

## Alternative: Without OpenClaw

If you don't want to install OpenClaw, the repo-native `scripts/ai_runner.py`
provides equivalent resume semantics using on-disk state. The main difference is
that OpenClaw also handles the claude CLI process lifecycle (restart, session
reconnection via claude session IDs), while `ai_runner.py` uses subprocess calls.

For most use cases, `scripts/ai_runner.py` is sufficient.

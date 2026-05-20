# Direct Chat Evolution: Seamless Assistant Architecture

## Overview
Direct Chat has evolved from a modal tool into a **unified intelligent assistant**. This document describes the orchestration, memory, and UX layers that enable this experience.

## Core Pillars

### 1. Unified Intent Orchestration
The system uses an **Intent Classification Layer** (`agent/intent.py`) to automatically detect if a user request requires:
- **Conversation**: General Q&A (routed to standard LLM chat).
- **Analysis**: Code review or repo inspection (promoted to Agent Mode).
- **Execution**: Writing code, running tests, or opening PRs (promoted to Agent Mode).
- **Clarification**: Vague technical requests (triggers an interactive clarification turn).

This removes the need for an explicit "Agent Mode" toggle.

### 2. Deep Sticky Memory
Assistant continuity is maintained through persistent session storage in SQLite (`agent_sessions` table):
- **Repo Context**: Remembers `repo_url` and `repo_ref` across turns.
- **Active Objective**: Tracks the current high-level goal (e.g., "fixing the auth bug").
- **Task Momentum**: Persists progress even if the conversation drifts, allowing for context-aware follow-ups like "now open a PR for that".

### 3. Execution Cognition Flow
Tasks follow a formal cognitive lifecycle within the `_handle_agent_mode` flow:
1. **Clarify**: Ensures instructions are actionable.
2. **Preflight (Doctor)**: Validates environment health (Git, GitHub, Providers).
3. **Bootstrap**: Transparently clones and initializes workspaces.
4. **Plan**: Decomposes the goal into an `AgentPlan`.
5. **Execute**: Selects the optimal runtime via the **Support Matrix**.
6. **Validate**: Verifies outcomes before summarizing.

### 4. Progress Humanization
Internal technical phases and tool identifiers are abstracted into conversational progress events:
- "Tool: read_file" → "Reading relevant source files"
- "phase: execution" → "Executing the planned changes"
- **Momentum detection**: Triggers updates like "Still working on..." for long-running operations.

## Runtime Selection Policy
The orchestrator queries the `RuntimeCapabilityRegistry` to match task requirements with available runtimes:
- **Stable first**: Prefers vetted runtimes like `InternalAgentAdapter`.
- **Health aware**: Avoids runtimes currently on circuit-breaker cooldown.
- **Capability driven**: Ensures the selected runtime supports required operations (e.g., `git_operations`).

## Failure Recovery
Errors are intercepted by the **Direct Chat Doctor** and translated into guidance:
- **Access issues**: "I hit an access issue... check your GitHub token in Settings."
- **Preflight failures**: Conversational fix hints instead of raw HTTP 412s.

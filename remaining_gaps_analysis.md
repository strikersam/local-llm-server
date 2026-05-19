# Gap Analysis: Direct Chat Evolution (Post-PR 198)

## Accomplished in PR 198
- **Intent Detection**: Basic regex-based promotion to Agent Mode.
- **Conversational States**: `DirectChatState` enum and basic humanized progress mapping.
- **Sticky Context**: Persistence of `repo_url` and `repo_ref` in SQLite.
- **Health Doctor**: Centralized checks in `DirectChatDoctor`.
- **Failure Recovery**: Conversion of preflight 412s into conversational guidance.
- **Auto-Bootstrap**: Automated cloning via `WorkspaceManager`.

## Remaining Gaps & Friction Points
1. **Execution Cognition Flow**:
   - The flow is currently: User -> Intent Detection -> Agent Job.
   - Missing: A "Clarify" stage where the assistant can ask questions if the intent is clear but the instructions are ambiguous, *before* committing to an async job.
   - Missing: Persistent "Current Objective" memory across turns.

2. **Runtime Selection Intelligence**:
   - Currently uses hardcoded defaults (`DEFAULT_PLANNER_MODEL`, etc.) or simple provider priority.
   - Missing: Awareness of the "support matrix" (which runtimes support which capabilities) and "health-aware" selection (beyond simple circuit breakers).

3. **Invisible Workspace Lifecycle Recovery**:
   - Bootstrap failures currently fall back to local isolated workspaces but don't inform the user how to fix the underlying repo issue conversationally.

4. **Humanized Progress Depth**:
   - Progress is humanized but still tied to discrete technical phases. Needs to feel more like a continuous "assistant is thinking/working" flow.

5. **Deep Sticky Memory**:
   - Only remembers repo/branch. Needs to remember "Active Task" and "Workspace State" to continue work seamlessly.

6. **Unified Orchestration**:
   - Distinction between `_handle_regular_chat` and `_handle_agent_mode` is still quite sharp internally.

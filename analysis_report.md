# Direct Chat Architecture Analysis

## Current Architecture
- **Router-based dispatch**: `direct_chat.py` routes requests to either `_handle_regular_chat` or `_handle_agent_mode` based on an explicit `agent_mode` flag in the request.
- **Job-based execution**: Agent mode triggers an asynchronous job managed by `AgentJobManager`.
- **Polling-based UI**: The frontend polls `/api/chat/agent-status` to get updates on the running job, including tool calls and phases.
- **Workspace Management**: Workspaces are created per job (or per session/job in `WorkspaceManager`).
- **Preflight Checks**: Manual preflight checks in `direct_chat.py` for Git/GitHub credentials and environment.
- **Triviality Filter**: A heuristic-based filter (`_is_trivial_message`) to avoid triggering agent mode for simple "hello" messages even if the flag is set.

## Execution Flow
1. User sends message with `agent_mode=True`.
2. Backend performs preflight (Git, GitHub token, Repo validation).
3. Backend creates an `AgentJob` and starts an async task.
4. Async task runs `AgentRunner`.
5. `AgentRunner` goes through planning -> execution -> verification phases.
6. Frontend polls for status and displays tool calls and summary.

## Current User Experience
- **Fragmented**: Users must manually toggle "Agent Mode".
- **Technical**: Progress is shown as "phases" and "tool calls", which feels like a developer tool rather than an assistant.
- **Modal**: Switching between chat and agent mode feels like switching between two different systems.
- **Context Loss**: Repo information (`repo_url`, `repo_ref`) is passed per request and not naturally persisted as "sticky" context in the session.

## Weak Points
- **Backend Leakage**: Job IDs, polling status, and raw technical phases are visible to the frontend and potentially the user.
- **Duplicated Logic**: Preflight and workspace setup are somewhat scattered between `direct_chat.py` and the agent loop.
- **Unstable Execution Paths**: Fallback and error handling for preflight are complex and can lead to opaque failures.
- **Runtime Selection**: Tied to specific flags rather than capability-based or environment-aware selection.
- **Error Handling**: Raw HTTP errors (e.g., 412) are used for preflight failures, which may not be gracefully handled by all clients as "conversational" feedback.

## Duplicated Logic
- Workspace creation exists in both legacy (`make_isolated_workspace`) and new (`WorkspaceManager`) forms.
- GitHub token resolution is repeated or slightly different in various places.

## Mode Switching Problems
- The distinction between "Regular Chat" and "Agent Mode" is a hard barrier. If a user asks a coding question in regular chat, they have to re-ask it in agent mode to get it executed.

## Repo Context Limitations
- No automatic persistence of the "current repository" within a session. Each request needs to specify it or rely on the frontend sending it back.

# PRD — LLM Relay Runtime, Task Routing, and Fallback Fixes

## Original Problem Statement
- Fix remote runtime control so deployed/non-local environments do not fail with a hard Docker-only error.
- Restore seamless task auto-allocation so tasks can pick an available agent when none is manually assigned.
- Fix provider fallback/chat so it follows the intended hierarchy and fails gracefully instead of crashing.
- Require explicit user permission before switching to commercial models when the policy is configured that way.

## Architecture Snapshot
- Frontend: React dashboard in `/app/frontend`
- Backend: FastAPI app in `/app/backend/server.py`
- Shared backend modules:
  - Provider routing: `/app/provider_router.py`
  - Agent loop: `/app/agent/loop.py`
  - Tasks: `/app/tasks/api.py`, `/app/tasks/service.py`
  - Runtimes: `/app/runtimes/api.py`, `/app/runtimes/control.py`

## Implemented in This Fork
### 2026-04-26
- Added task auto-assignment in `TaskWorkflowService.create_task()` with task-type-aware ranking and execution log entries.
- Added execution-time auto-assignment fallback in `TaskExecutionCoordinator._resolve_agent()`.
- Refactored runtime lifecycle control to return informational remote/no-Docker payloads instead of hard failures.
- Added provider tier classification in `provider_router.py` for:
  - local
  - windows/remote self-hosted
  - free cloud
  - commercial
- Added `CommercialFallbackRequiredError` and approval-aware provider fallback handling.
- Updated chat backend flow to:
  - build provider chains from configured providers only
  - skip unconfigured providers
  - return `approval_required` before commercial escalation when policy demands it
  - keep chat failures controlled instead of crashing the endpoint
- Updated `AgentRunner` to accept provider chains and approval-aware fallback behavior.
- Added frontend approval modal for commercial fallback on Chat page.
- Updated Runtimes page messaging so remote-management/no-Docker states are treated as informational, not hard UI errors.
- Fixed auth wiring for task/runtime API verification after backend restart and shared-module reload.
- Testing agent also updated frontend proxy target to `http://localhost:8001` in `frontend/package.json`.

## Verification Status
- Targeted pytest from main agent: `16 passed`
- Testing agent report: `/app/test_reports/iteration_6.json`
  - Backend: `35/35 passed`
  - Frontend: verified for runtime notices and chat approval modal structure
- Manual curl verification by main agent:
  - authenticated task creation stores real owner id
  - task auto-assignment assigns an available agent
  - runtime start returns non-blocking informational payload in no-Docker environment
  - commercial approval path returns `409 approval_required` when policy allows paid escalation and a commercial provider is present

## Current Functional Notes
- Task auto-assignment: WORKING
- Remote runtime informational handling: WORKING
- Commercial approval gate: WORKING
- Baseline chat now returns a controlled provider failure instead of crashing when no usable live provider is available.
- No APIs were MOCKED.

## Known Environment Limitation
- In this preview environment, currently configured live provider access is still limited, so baseline chat may return a controlled provider failure message until real provider connectivity/keys are available.
- Approval behavior itself was verified using a temporary configured commercial provider during testing, then cleaned up.

## Prioritized Backlog
### P0
- Verify live chat success with the user’s actual working provider credentials/environment (not just graceful failure + approval gate).

### P1
- Expand frontend E2E coverage for the full approval-confirmation path after a real commercial provider is configured.
- Add clearer provider-health indicators on the chat/setup surfaces.

### P2
- Add fallback health and task timeline dashboard enhancements.

## Next Suggested Task
- Wire in the user’s active provider credentials/environment for a final live-chat success pass across local/free/commercial tiers.
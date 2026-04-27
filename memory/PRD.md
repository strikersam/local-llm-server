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
- Added real commercial fallback support via `EMERGENT_LLM_KEY` in ignored local file `/app/backend/.env`.
- Seeded a real provider record `anthropic-universal` (`emergent-anthropic`) and verified it is used only after approval.
- Set local runtime policy default to allow paid fallback with approval (`RUNTIME_NEVER_PAID=false`, `require_approval_before_paid_escalation=true`).

## Verification Status
- Targeted pytest from main agent: `18 passed`
- Testing agent reports:
  - `/app/test_reports/iteration_6.json` — backend `35/35 passed`, frontend verified
  - `/app/test_reports/iteration_7.json` — backend `10/10 passed`, frontend `100% verified`
- Manual curl verification by main agent:
  - authenticated task creation stores real owner id
  - task auto-assignment assigns an available agent
  - runtime start returns non-blocking informational payload in no-Docker environment
  - commercial approval path returns `409 approval_required`
  - approved commercial retry returns `200` with a real live response

## Current Functional Notes
- Task auto-assignment: WORKING
- Remote runtime informational handling: WORKING
- Commercial approval gate: WORKING
- Live commercial fallback now works in this preview via `anthropic-universal` after approval.
- Baseline chat now returns an approval prompt instead of crashing when paid escalation is needed.
- No APIs were MOCKED.

## Known Environment Limitation
- The live provider setup currently depends on the ignored local file `/app/backend/.env`. To reproduce this behavior in another environment, add `EMERGENT_LLM_KEY` there or configure your own provider keys.

## Prioritized Backlog
### P1
- Expand frontend E2E coverage for the full approval-confirmation path after a real commercial provider is configured.
- Add clearer provider-health indicators on the chat/setup surfaces.

### P2
- Add fallback health and task timeline dashboard enhancements.

## Next Suggested Task
- Add a provider-health panel so users can see which tier is currently available before sending a message.
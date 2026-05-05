# Agent job lifecycle

Direct chat now has two paths:

- **direct chat**: synchronous request/response
- **agent mode**: async background job

## States

- `queued`
- `running`
- `succeeded`
- `failed`
- `cancelled`

## Progress phases

- `queued`
- `starting`
- `planning`
- `execution`
- `verification`
- `completed`
- `failed`
- `cancelled`

## API

- `POST /api/chat/send` with `agent_mode=true` → `202 Accepted`
- `GET /api/chat/agent-jobs/{job_id}` → job status, heartbeat, progress events, result/error
- `POST /api/chat/agent-jobs/{job_id}/cancel` → cancel queued/running job

This keeps direct chat fast while long-running agent work progresses out-of-band.

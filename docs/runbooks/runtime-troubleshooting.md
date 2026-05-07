# Runtime troubleshooting

## Missing binary / task harness

If preflight returns `missing_binary`:

- inspect `detail.issues[*].details.binary`
- check `detail.issues[*].details.config_var`
- install the binary or point the config variable at it

Example: when `TASK_HARNESS_REQUIRED=true`, set `TASK_HARNESS_BIN` to the compatible harness binary.

## Agent mode timeout

Direct chat agent mode no longer runs inline.

- submit with `agent_mode=true`
- capture the returned `job_id`
- poll `/api/chat/agent-jobs/{job_id}`

If the job stalls, inspect:

- `status`
- `phase`
- `heartbeat_at`
- latest `progress_events`

## Workspace validation failures

If preflight reports workspace errors:

- ensure the path exists or can be created
- ensure it is a directory
- ensure the runtime user can write to it

# Workspace Isolation Architecture

## Overview

Every agent session/job gets its own **isolated, validated workspace** under a single configured base directory. The workspace system provides strong boundaries between sessions, safe path handling, structured manifests, and lifecycle management.

## WorkspaceManager

The `workspace.manager.WorkspaceManager` is the central component:

- **Deterministic workspace roots**: Each session/job pair maps to a unique directory derived from validated, opaque IDs plus a stable SHA-256 hash. Raw user-provided IDs are never used as directory names.
- **Path safety**: All paths are canonicalized. Traversal attempts (`../`) and symlink escapes are rejected. Session/job IDs are validated against a strict regex.
- **Session/job ownership**: A job can only access its own workspace. Session resume operates only inside the correct session namespace. Concurrent mutation is guarded with an `RLock`.
- **Lifecycle states**: Workspaces transition through explicit states: `creating → ready → active → paused → completed → failed → cancelling → cancelled → archived → cleaned`.
- **Structured manifest**: Each workspace has a `manifest.json` with session ID, job ID, creation time, heartbeat, runtime type, status, root paths, artifact paths, cleanup eligibility, and schema version.
- **Retention and cleanup**: Workspaces past their retention TTL in a cleanable state (completed/failed/cancelled/archived) are eligible for cleanup. Active or locked workspaces are never cleaned.

## Directory Layout

```
<base_root>/
  <session_hash_24chars>/
    <job_hash_24chars>/
      manifest.json
      source/        # Source/work tree
      checkpoints/   # State/checkpoints
      logs/          # Execution logs
      artifacts/     # Output artifacts
      temp/          # Temporary files
```

## Path Derivation

```python
session_dir = sha256(session_id)[:24]
job_dir = sha256(job_id)[:24]
workspace_root = base_root / session_dir / job_dir
```

The hash ensures:
- No raw session/job IDs appear as directory names
- Predictability attacks are prevented
- The same ID always maps to the same directory

## Path Safety

All workspace paths are resolved (`.resolve()`) and checked:

```python
resolved = path.resolve()
root_resolved = base_root.resolve()
resolved.relative_to(root_resolved)  # Raises ValueError if escaped
```

This blocks:
- `../` traversal in IDs (rejected by regex)
- Symlink escape (resolved path must stay under base root)
- Absolute path injection (rejected by regex)

## Workspace Manifest Schema

```json
{
  "session_id": "session-abc",
  "job_id": "aj_1234",
  "created_at": "2026-05-08T12:00:00Z",
  "last_heartbeat": "2026-05-08T12:05:00Z",
  "runtime_type": "local",
  "status": "active",
  "root_path": "/path/to/workspace",
  "source_path": "/path/to/workspace/source",
  "checkpoints_path": "/path/to/workspace/checkpoints",
  "logs_path": "/path/to/workspace/logs",
  "artifacts_path": "/path/to/workspace/artifacts",
  "temp_path": "/path/to/workspace/temp",
  "repo_url": null,
  "cleanup_eligible": false,
  "schema_version": 1
}
```

## Lifecycle States

| State | Description | Resumable | Cleanable |
|-------|-------------|-----------|-----------|
| creating | Workspace being initialized | No | No |
| ready | Workspace created, not yet used | Yes | No |
| active | Currently in use | Yes | No |
| paused | Temporarily suspended | Yes | No |
| completed | Job finished successfully | No | Yes |
| failed | Job finished with error | No | Yes |
| cancelling | Cancel in progress | No | No |
| cancelled | Job was cancelled | No | Yes |
| archived | Archived for retention | No | Yes |
| cleaned | Files removed | No | No |

## Runtime Integration

The `AgentJobManager` integrates with `WorkspaceManager`:

1. On `create_job()` — if no explicit `workspace_path`, provisions an isolated workspace
2. On `start_job()` — activates the workspace
3. On job completion/failure — marks the workspace as completed/failed
4. On `cancel_job()` — marks the workspace as cancelled

The legacy `make_isolated_workspace()` function is preserved for backward compatibility but the preferred path is through `WorkspaceManager`.

## Error Handling

All workspace errors are structured with machine-readable codes:

| Error | Code | Fix Hint |
|-------|------|----------|
| InvalidSessionIdError | `invalid_session_id` | Use 1-128 alphanumeric chars |
| InvalidJobIdError | `invalid_job_id` | Use 1-128 alphanumeric chars |
| WorkspaceNotFoundError | `workspace_not_found` | Check session/job ID |
| WorkspaceOutsideRootError | `workspace_outside_root` | Check for traversal/symlink |
| WorkspaceNotResumableError | `workspace_not_resumable` | Only ready/active/paused can resume |
| WorkspaceCleanupBlockedError | `workspace_cleanup_blocked` | Wait for completion or cancel |
| WorkspaceManifestCorruptionError | `workspace_manifest_corrupt` | Repair or delete manifest |
| WorkspacePermissionError | `workspace_permission_error` | Check filesystem permissions |

## Metrics

The `WorkspaceMetrics` class tracks:
- `active_count` — workspaces in active/creating/ready/paused state
- `expired_count` — workspaces past retention TTL
- `cleanup_count` — workspaces successfully cleaned
- `cleanup_skipped_active` — cleanup attempts that skipped active workspaces
- `resume_success` / `resume_failure` — resume attempt counts

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `WORKSPACE_BASE_ROOT` | `.data/workspaces` | Base directory for all workspaces |
| `WORKSPACE_RETENTION_TTL_SECONDS` | `604800` (7 days) | Time before completed workspaces are eligible for cleanup |
| `DIRECT_CHAT_AGENT_WORKSPACE_ROOT` | `.data/direct-chat-agent-workspaces` | Override for direct chat agent workspaces |

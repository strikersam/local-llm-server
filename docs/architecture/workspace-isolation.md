# Workspace Isolation

Every agent session/job gets its own **isolated workspace** under a single
configured base directory.  No two jobs share a work tree, checkpoint store,
logs directory, artifact output, or temp space.

---

## Directory Layout

```text
<AGENT_WORKSPACE_BASE>/
  <session_hash>/              # SHA-256(session_id)[:24]
    <job_hash>/                # SHA-256(job_id)[:24]
      workspace.json           # manifest (see below)
      source/                  # work tree — agent reads/writes here
      checkpoints/             # durable state snapshots for resume
      logs/                    # per-job log files
      artifacts/               # outputs the caller may retrieve
      tmp/                     # scratch; always deleted on cleanup
```

Directory names are derived from a **stable SHA-256 hash** of the opaque ID —
never from raw user-supplied strings.  The raw IDs never appear in any
filesystem path.

---

## ID Validation

Session IDs and job IDs are validated against a strict regex before use:

```text
^[A-Za-z0-9][A-Za-z0-9._-]{1,63}$
```

Invalid IDs (empty, path separators, spaces, leading hyphens, too long) are
rejected with a structured `WorkspaceIDError` before any filesystem operation.

---

## Path Safety

`WorkspaceManager.safe_path(ws, relative)` resolves a relative path inside the
job's `source/` directory and rejects attempts to escape it:

| Attempt | What happens |
|---------|-------------|
| `../../etc/passwd` | `WorkspaceEscapeError` — `relative_to` fails after resolve |
| `/etc/shadow` (absolute) | `WorkspaceEscapeError` — absolute path wins over source prefix |
| `symlink → /outside` | `WorkspaceEscapeError` — resolve() follows the symlink |
| `..` alone | `WorkspaceEscapeError` — resolves to parent of source |

The error message deliberately **omits** internal filesystem paths to avoid
leaking server layout information through API error responses.

---

## Lifecycle States

```text
creating → ready → active ↔ paused → completed ┐
                          → failed              ├→ archived → cleaned
                          → cancelling → cancelled ┘
```

| State | Meaning |
|-------|---------|
| `creating` | Workspace directories being set up |
| `ready` | Created and ready to start work |
| `active` | A worker is running in this workspace |
| `paused` | Work suspended; workspace may be resumed |
| `completed` | Job finished successfully |
| `failed` | Job finished with an error |
| `cancelling` | Cancellation requested |
| `cancelled` | Cancellation confirmed |
| `archived` | Terminal; manifest retained for audit |
| `cleaned` | Directories removed; only metadata may remain |

Only `ready` and `paused` workspaces can be **resumed**.

Terminal states (`completed`, `failed`, `cancelled`, `archived`, `cleaned`)
set `cleanup_eligible = true` in the manifest.

---

## Workspace Manifest

Each job root contains `workspace.json` with schema version `"1"`:

```json5
{
  "schema_version": "1",
  "session_id": "as_abc123",
  "job_id": "aj_def456",
  "created_at": "2026-05-08T12:00:00Z",
  "updated_at": "2026-05-08T12:05:00Z",
  "last_heartbeat": "2026-05-08T12:05:00Z",
  "runtime_type": "internal_agent",
  "status": "completed",
  "root": "/data/workspaces/3e55c03b.../e8b92a62...",
  "source_path": "…/source",
  "checkpoints_path": "…/checkpoints",
  "logs_path": "…/logs",
  "artifacts_path": "…/artifacts",
  "tmp_path": "…/tmp",
  "source_repo": null,
  "cleanup_eligible": true,
  "cleanup_after": "2026-05-09T12:00:00Z",
  "metadata": {}
}
```

Writes are **atomic** (write to `.tmp` then `rename`).

---

## Session/Job Ownership

A workspace records the `session_id` that created it.  Operations that
resume or access a workspace validate that the requesting session matches
the recorded owner.

`WorkspaceManager.assert_session_owns(ws, requesting_session_id)` raises
`WorkspaceAccessDeniedError` if the session IDs differ.

`WorkspaceManager.resume(session_id, job_id)` performs this check
automatically before transitioning the workspace to `active`.

Concurrent mutation is guarded by an **asyncio.Lock** per workspace instance.
`acquire_lock` / `release_lock` are available for explicit locking.
The lock times out after `lock_timeout_sec` (default 30 s) and raises
`WorkspaceLockError` if the lock cannot be acquired.

---

## Cleanup Policy

`WorkspaceManager.cleanup_expired()` scans the base directory and removes
workspaces that are:

1. `cleanup_eligible == true` (i.e. in a terminal state)
2. Past their `cleanup_after` timestamp

Workspaces in `creating` or `active` state are **never deleted** even if
past their TTL.

`cleanup_expired(dry_run=True)` reports what would be cleaned without
deleting anything.

The default TTL is controlled by `WORKSPACE_TTL_HOURS` (default: 24 h).

---

## Configuration

| Env var | Default | Description |
|---------|---------|-------------|
| `AGENT_WORKSPACE_BASE` | `.workspaces/` next to `proxy.py` | Base root for all job workspaces |
| `WORKSPACE_TTL_HOURS` | `24` | Hours until a terminal workspace becomes cleanup-eligible |

---

## Structured Errors

All workspace errors carry a `code` field suitable for API error responses:

| Exception | `code` | Cause |
|-----------|--------|-------|
| `WorkspaceIDError` | `invalid_id` | Session/job ID fails validation |
| `WorkspaceNotFoundError` | `workspace_not_found` | Directory or manifest absent |
| `WorkspaceEscapeError` | `workspace_escape` | Path traversal outside source root |
| `WorkspaceAccessDeniedError` | `workspace_access_denied` | Session mismatch |
| `WorkspaceNotResumableError` | `workspace_not_resumable` | Status is not READY/PAUSED |
| `WorkspaceLockError` | `workspace_locked` | Lock timeout |
| `WorkspaceManifestError` | `workspace_manifest_corrupt` | workspace.json parse failure |

---

## Admin API

`GET /admin/api/workspaces/metrics`  (requires admin auth)

Returns workspace counts grouped by status — useful for detecting orphaned
or stale jobs:

```json5
{
  "workspace_base": "/data/workspaces",
  "metrics": {
    "ready": 2,
    "active": 1,
    "completed": 45,
    "failed": 3
  }
}
```

---

## Runtime Integration

`WorkspaceManager` is accessed via the module-level singleton
`agent.workspace.get_workspace_manager()`.  Configure the base path before
first call via `AGENT_WORKSPACE_BASE`.

The legacy `make_isolated_workspace()` in `agent/job_manager.py` remains for
backward compatibility.  New code should use `WorkspaceManager`.

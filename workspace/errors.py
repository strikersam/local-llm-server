"""workspace/errors.py — Structured, actionable workspace errors.

Every error carries a machine-readable code, a human-readable message,
and optional fix hints so callers (API, CLI, UI) can surface guidance
without parsing free-form text.
"""

from __future__ import annotations


class WorkspaceError(Exception):
    """Base class for all workspace errors."""

    code: str = "workspace_error"
    fix_hint: str = ""

    def __init__(self, message: str, *, code: str | None = None, fix_hint: str | None = None) -> None:
        self.code = code or self.code
        self.fix_hint = fix_hint or self.fix_hint
        super().__init__(message)

    def as_dict(self) -> dict:
        return {
            "code": self.code,
            "message": str(self),
            "fix_hint": self.fix_hint,
        }


class InvalidSessionIdError(WorkspaceError):
    code = "invalid_session_id"
    fix_hint = "Session IDs must be 1-128 alphanumeric/dash/underscore characters."

    def __init__(self, session_id: str) -> None:
        super().__init__(
            f"Invalid session ID: {session_id!r}",
            code=self.code,
            fix_hint=self.fix_hint,
        )
        self.session_id = session_id


class InvalidJobIdError(WorkspaceError):
    code = "invalid_job_id"
    fix_hint = "Job IDs must be 1-128 alphanumeric/dash/underscore characters."

    def __init__(self, job_id: str) -> None:
        super().__init__(
            f"Invalid job ID: {job_id!r}",
            code=self.code,
            fix_hint=self.fix_hint,
        )
        self.job_id = job_id


class WorkspaceNotFoundError(WorkspaceError):
    code = "workspace_not_found"
    fix_hint = "Check the session/job ID or list active workspaces."

    def __init__(self, session_id: str, job_id: str | None = None) -> None:
        label = f"session={session_id!r}"
        if job_id:
            label += f" job={job_id!r}"
        super().__init__(
            f"Workspace not found for {label}",
            code=self.code,
            fix_hint=self.fix_hint,
        )
        self.session_id = session_id
        self.job_id = job_id


class WorkspaceOutsideRootError(WorkspaceError):
    code = "workspace_outside_root"
    fix_hint = "The resolved workspace path escapes the configured base root. Check for traversal or symlink attacks."

    def __init__(self, path: str, root: str) -> None:
        super().__init__(
            f"Workspace path {path!r} is outside allowed root {root!r}",
            code=self.code,
            fix_hint=self.fix_hint,
        )
        self.path = path
        self.root = root


class WorkspaceNotResumableError(WorkspaceError):
    code = "workspace_not_resumable"
    fix_hint = "Only workspaces in active, paused, or ready state can be resumed."

    def __init__(self, session_id: str, status: str) -> None:
        super().__init__(
            f"Workspace for session {session_id!r} cannot be resumed (status={status!r})",
            code=self.code,
            fix_hint=self.fix_hint,
        )
        self.session_id = session_id
        self.status = status


class WorkspaceCleanupBlockedError(WorkspaceError):
    code = "workspace_cleanup_blocked"
    fix_hint = "The workspace is locked by an active session/job. Wait for it to complete or cancel first."

    def __init__(self, session_id: str, job_id: str | None = None) -> None:
        label = f"session={session_id!r}"
        if job_id:
            label += f" job={job_id!r}"
        super().__init__(
            f"Cannot clean up workspace for {label} — it is still active or locked",
            code=self.code,
            fix_hint=self.fix_hint,
        )
        self.session_id = session_id
        self.job_id = job_id


class WorkspaceManifestCorruptionError(WorkspaceError):
    code = "workspace_manifest_corrupt"
    fix_hint = "Delete or repair the workspace manifest file and re-initialize."

    def __init__(self, path: str, detail: str = "") -> None:
        msg = f"Workspace manifest at {path!r} is corrupt"
        if detail:
            msg += f": {detail}"
        super().__init__(msg, code=self.code, fix_hint=self.fix_hint)
        self.path = path


class WorkspacePermissionError(WorkspaceError):
    code = "workspace_permission_error"
    fix_hint = "Check filesystem permissions on the workspace root directory."

    def __init__(self, path: str, detail: str = "") -> None:
        msg = f"Permission error on workspace path {path!r}"
        if detail:
            msg += f": {detail}"
        super().__init__(msg, code=self.code, fix_hint=self.fix_hint)
        self.path = path

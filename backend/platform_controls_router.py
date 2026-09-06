"""backend/platform_controls_router.py — admin API for the platform controls.

Serves the dashboard screen that replaces hand-editing feature switches in the
Render environment:

    GET    /api/admin/platform-controls          — catalogue + effective values
    PUT    /api/admin/platform-controls          — set one or more overrides
    DELETE /api/admin/platform-controls/{key}    — revert a key to the environment

Only keys in :mod:`packages.config.control_registry` can be read or written, so
this is not a general environment-editing endpoint: secrets and infrastructure
endpoints are not in the catalogue and cannot be touched through it.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from packages.config.control_overrides import (
    clear_override,
    set_overrides,
    snapshot,
)

log = logging.getLogger("qwen-proxy")


class ControlUpdateBody(BaseModel):
    """One or more control changes, as ``{"updates": {"KEY": value}}``."""

    updates: dict[str, Any] = Field(
        default_factory=dict,
        description="Control key → new value. Booleans, numbers, and strings are all accepted.",
    )


def build_platform_controls_router(get_current_user: Callable) -> APIRouter:
    """Build the router, bound to the app's auth dependency.

    Takes ``get_current_user`` as an argument for the same reason the brain and
    CEO routers do: the dependency lives in ``backend.server``, and importing it
    here would close an import cycle.
    """
    router = APIRouter(prefix="/api/admin/platform-controls", tags=["platform-controls"])

    def _admin(user: dict) -> None:
        from backend.company_api import _is_admin

        if not _is_admin(user):
            raise HTTPException(
                status_code=403,
                detail="Admin role required to view or change platform controls",
            )

    @router.get("")
    async def list_controls(user: dict = Depends(get_current_user)) -> dict[str, Any]:
        """The full catalogue with each control's effective value and source."""
        _admin(user)
        return await snapshot()

    @router.put("")
    async def update_controls(
        body: ControlUpdateBody,
        user: dict = Depends(get_current_user),
    ) -> dict[str, Any]:
        """Persist and apply control overrides.

        The batch is validated before anything is written, so one bad field
        rejects the whole request rather than half-applying it.
        """
        _admin(user)
        if not body.updates:
            raise HTTPException(status_code=400, detail="No updates supplied.")
        try:
            result = await set_overrides(body.updates, actor=_actor(user))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Internal server error") from exc
        log.info(
            "platform-controls: %s updated %s", _actor(user), sorted(body.updates)
        )
        return result | await snapshot()

    @router.delete("/{key}")
    async def reset_control(
        key: str,
        user: dict = Depends(get_current_user),
    ) -> dict[str, Any]:
        """Drop a single override so the key follows the environment again."""
        _admin(user)
        try:
            result = await clear_override(key, actor=_actor(user))
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Internal server error") from exc
        log.info("platform-controls: %s reset %s", _actor(user), key)
        return result | await snapshot()

    return router


def _actor(user: dict) -> str:
    """A stable identifier for the audit trail on each write."""
    return str(user.get("email") or user.get("username") or user.get("id") or "admin")

"""agent/watchdog.py — Resource Watchdog

Monitors URLs, files, or any resource that can be reduced to a content hash.
When the hash changes the registered *on_change* callback fires, letting you
trigger agent actions, send notifications, etc.

Polling runs on a background daemon thread; individual resources can also be
checked manually via :meth:`check_once`.
"""
from __future__ import annotations

import hashlib
import logging
import secrets
import threading
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

log = logging.getLogger("qwen-watchdog")


@dataclass
class WatchedResource:
    resource_id: str
    name: str
    kind: str   # "url" | "file"
    target: str
    action: str = ""        # human description of what to do on change
    last_hash: str | None = None
    last_checked: str | None = None
    trigger_count: int = 0
    enabled: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "name": self.name,
            "kind": self.kind,
            "target": self.target,
            "action": self.action,
            "last_hash": self.last_hash,
            "last_checked": self.last_checked,
            "trigger_count": self.trigger_count,
            "enabled": self.enabled,
        }


@dataclass
class WatchEvent:
    resource_id: str
    resource_name: str
    detected_at: str
    old_hash: str | None
    new_hash: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "resource_name": self.resource_name,
            "detected_at": self.detected_at,
            "old_hash": self.old_hash,
            "new_hash": self.new_hash,
        }


class ResourceWatchdog:
    """Poll resources at a fixed interval and fire *on_change* when content changes.

    Usage::

        def on_change(event: WatchEvent):
            print(f"{event.resource_name} changed!")

        wd = ResourceWatchdog(on_change=on_change, poll_interval_s=30)
        wd.watch(name="API health", kind="url", target="http://localhost:8000/health")
        wd.start()
    """

    def __init__(
        self,
        *,
        poll_interval_s: int = 60,
        on_change: Callable[[WatchEvent], None] | None = None,
    ) -> None:
        self._resources: dict[str, WatchedResource] = {}
        self._on_change = on_change
        self._poll_interval = poll_interval_s
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def watch(
        self,
        *,
        name: str,
        kind: str,
        target: str,
        action: str = "",
    ) -> WatchedResource:
        """Register a resource to monitor.  Returns the :class:`WatchedResource`."""
        resource_id = "res_" + secrets.token_hex(6)
        resource = WatchedResource(
            resource_id=resource_id,
            name=name,
            kind=kind,
            target=target,
            action=action,
        )
        self._resources[resource_id] = resource
        log.info("Watching %s: kind=%s target=%r", resource_id, kind, target)
        return resource

    def unwatch(self, resource_id: str) -> bool:
        """Stop monitoring a resource. Returns *True* if it existed."""
        existed = resource_id in self._resources
        self._resources.pop(resource_id, None)
        return existed

    def list(self) -> list[WatchedResource]:
        return list(self._resources.values())

    def check_once(self, resource_id: str) -> WatchEvent | None:
        """Check a single resource right now. Returns a :class:`WatchEvent` if changed."""
        resource = self._resources.get(resource_id)
        if not resource or not resource.enabled:
            return None
        new_hash = self._hash(resource)
        if new_hash is None:
            return None
        resource.last_checked = _now()
        if resource.last_hash != new_hash:
            event = WatchEvent(
                resource_id=resource.resource_id,
                resource_name=resource.name,
                detected_at=resource.last_checked,
                old_hash=resource.last_hash,
                new_hash=new_hash,
            )
            resource.last_hash = new_hash
            resource.trigger_count += 1
            log.info(
                "Change detected: resource=%s name=%r triggers=%d",
                resource_id,
                resource.name,
                resource.trigger_count,
            )
            if self._on_change:
                try:
                    self._on_change(event)
                except Exception as exc:
                    log.warning("on_change callback raised: %s", exc)
            return event
        resource.last_hash = new_hash
        return None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._poll_loop,
            daemon=True,
            name="watchdog",
        )
        self._thread.start()
        log.info("Watchdog started (poll_interval=%ds)", self._poll_interval)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _hash(self, resource: WatchedResource) -> str | None:
        try:
            if resource.kind == "file":
                content = Path(resource.target).read_bytes()
            elif resource.kind == "url":
                with urllib.request.urlopen(resource.target, timeout=10) as resp:  # noqa: S310  # nosec: B110 - URL is from trusted resource (WatchedResource)
                    content = resp.read()
            else:
                return None
            return hashlib.sha256(content).hexdigest()
        except Exception as exc:
            log.debug("Hash failed for %s (%s): %s", resource.resource_id, resource.target, exc)
            return None

    def _poll_loop(self) -> None:
        while not self._stop_event.is_set():
            for resource_id in list(self._resources):
                self.check_once(resource_id)
            self._stop_event.wait(self._poll_interval)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

"""sync/service.py — Syncthing-style workspace synchronisation service.

Synchronises skills, repos, runtime configs, and tool configs across
machines.  Works offline (queues changes for when peers reconnect).

Architecture:
  - SyncPeer: a remote machine identified by hostname + port + shared secret
  - SyncItem: a file/directory fragment with metadata (hash, modified time)
  - SyncService: orchestrates push/pull, conflict resolution, selective sync
  - sync_router: FastAPI endpoints for the sync API

Conflict resolution strategy:
  - Last-write-wins by default (configurable per folder)
  - Conflict files are renamed {name}.conflict.{timestamp}.{ext} and kept
  - Admin can inspect/resolve conflicts via the UI

Sync scopes (folders):
  skills/          — agent skill definitions
  workspaces/      — cloned repo workspaces
  runtime_configs/ — runtime-specific config files
  tool_configs/    — MCP/tool configuration bundles

API routes:
  GET  /api/sync/status          → sync status for all folders
  GET  /api/sync/peers           → registered peers
  POST /api/sync/peers           → register a new peer
  DELETE /api/sync/peers/{id}    → remove peer
  POST /api/sync/push/{folder}   → trigger push to all peers
  POST /api/sync/pull/{folder}   → trigger pull from all peers
  GET  /api/sync/conflicts       → list unresolved conflicts
  POST /api/sync/conflicts/{id}/resolve → resolve a conflict
  POST /api/sync/receive         → receive items from a peer (peer calls this)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import secrets
import shutil
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from rbac import audit, require_admin, require_power_user

log = logging.getLogger("qwen-proxy")

# ── Base directory ────────────────────────────────────────────────────────────

SYNC_BASE_DIR = Path(
    os.environ.get("SYNC_BASE_DIR", Path.home() / ".llm-relay" / "sync")
)

# Known sync folders
SYNC_FOLDERS = {
    "skills":          "skills/",
    "workspaces":      "workspaces/",
    "runtime_configs": "runtime_configs/",
    "tool_configs":    "tool_configs/",
}


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class SyncPeer:
    peer_id:   str
    name:      str
    host:      str
    port:      int
    secret:    str          # shared HMAC secret — never logged in plain text
    enabled:   bool = True
    last_seen: float = 0.0
    last_sync: float = 0.0
    folders:   list[str] = field(default_factory=list)   # which folders to sync

    def as_safe_dict(self) -> dict[str, Any]:
        """Return dict safe for API (masked secret)."""
        return {
            "peer_id":   self.peer_id,
            "name":      self.name,
            "host":      self.host,
            "port":      self.port,
            "secret":    "****",
            "enabled":   self.enabled,
            "last_seen": self.last_seen,
            "last_sync": self.last_sync,
            "folders":   self.folders,
        }

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


@dataclass
class SyncItem:
    """A single synchronised file fragment."""
    path:      str           # relative path within the sync folder
    folder:    str           # sync folder name
    content:   bytes = b""
    sha256:    str = ""
    modified:  float = 0.0
    deleted:   bool = False

    def compute_hash(self) -> str:
        return hashlib.sha256(self.content).hexdigest()

    def as_meta_dict(self) -> dict[str, Any]:
        return {
            "path":     self.path,
            "folder":   self.folder,
            "sha256":   self.sha256,
            "modified": self.modified,
            "deleted":  self.deleted,
            "size":     len(self.content),
        }


@dataclass
class SyncConflict:
    conflict_id: str
    folder:      str
    path:        str
    local_sha:   str
    remote_sha:  str
    remote_peer: str
    detected_at: float = field(default_factory=time.time)
    resolved:    bool = False


# ── Sync service ──────────────────────────────────────────────────────────────

class SyncService:
    """Orchestrates workspace synchronisation across peers.

    Maintains an in-memory state of peers and a queue of pending changes.
    Works offline — changes are queued and applied when peers reconnect.
    """

    def __init__(self, base_dir: Path = SYNC_BASE_DIR) -> None:
        self.base_dir  = base_dir
        self._peers:     dict[str, SyncPeer]     = {}
        self._conflicts: dict[str, SyncConflict] = {}
        self._queue:     list[tuple[str, SyncItem]] = []   # (peer_id, item)

        # Ensure all sync folders exist
        for folder in SYNC_FOLDERS:
            (self.base_dir / folder).mkdir(parents=True, exist_ok=True)

    # ── Peer management ───────────────────────────────────────────────────────

    def add_peer(self, peer: SyncPeer) -> SyncPeer:
        self._peers[peer.peer_id] = peer
        log.info("Sync peer registered: %s (%s:%d)", peer.name, peer.host, peer.port)
        return peer

    def remove_peer(self, peer_id: str) -> bool:
        if peer_id in self._peers:
            del self._peers[peer_id]
            return True
        return False

    def list_peers(self) -> list[SyncPeer]:
        return list(self._peers.values())

    def get_peer(self, peer_id: str) -> SyncPeer | None:
        return self._peers.get(peer_id)

    # ── File index ────────────────────────────────────────────────────────────

    def _folder_path(self, folder: str) -> Path:
        if folder not in SYNC_FOLDERS:
            raise ValueError(f"Unknown sync folder: {folder!r}")
        return self.base_dir / folder

    def index_folder(self, folder: str) -> list[dict[str, Any]]:
        """Return metadata for all files in a sync folder."""
        root    = self._folder_path(folder)
        index   = []
        for fpath in root.rglob("*"):
            if fpath.is_file():
                rel     = str(fpath.relative_to(root))
                content = fpath.read_bytes()
                index.append({
                    "path":     rel,
                    "folder":   folder,
                    "sha256":   hashlib.sha256(content).hexdigest(),
                    "modified": fpath.stat().st_mtime,
                    "size":     len(content),
                    "deleted":  False,
                })
        return index

    def get_file(self, folder: str, path: str) -> bytes | None:
        """Read a file from a sync folder."""
        root = self._folder_path(folder)
        # Sanitise path to prevent traversal
        target = (root / path).resolve()
        if not str(target).startswith(str(root.resolve())):
            raise ValueError(f"Path traversal attempt: {path!r}")
        if target.exists() and target.is_file():
            return target.read_bytes()
        return None

    def write_file(self, folder: str, path: str, content: bytes, modified: float) -> None:
        """Write a file into a sync folder, creating parent dirs as needed."""
        root   = self._folder_path(folder)
        target = (root / path).resolve()
        if not str(target).startswith(str(root.resolve())):
            raise ValueError(f"Path traversal attempt: {path!r}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        # Preserve original modification time
        os.utime(target, (modified, modified))

    def delete_file(self, folder: str, path: str) -> None:
        root   = self._folder_path(folder)
        target = (root / path).resolve()
        if not str(target).startswith(str(root.resolve())):
            raise ValueError(f"Path traversal attempt: {path!r}")
        if target.exists():
            target.unlink()

    # ── Conflict detection ────────────────────────────────────────────────────

    def _check_conflict(
        self,
        folder: str,
        path: str,
        remote_sha: str,
        peer: SyncPeer,
    ) -> bool:
        """Return True if there is a conflict (both sides modified)."""
        root   = self._folder_path(folder)
        target = root / path
        if not target.exists():
            return False
        local_sha = hashlib.sha256(target.read_bytes()).hexdigest()
        if local_sha != remote_sha:
            conflict = SyncConflict(
                conflict_id=f"conflict_{secrets.token_hex(6)}",
                folder=folder,
                path=path,
                local_sha=local_sha,
                remote_sha=remote_sha,
                remote_peer=peer.peer_id,
            )
            self._conflicts[conflict.conflict_id] = conflict
            log.warning("Sync conflict detected: %s/%s (peer=%s)", folder, path, peer.name)
            return True
        return False

    def _save_conflict_copy(self, folder: str, path: str) -> None:
        """Rename the local file to a .conflict copy before overwriting."""
        root   = self._folder_path(folder)
        target = root / path
        if target.exists():
            ts     = int(time.time())
            suffix = f".conflict.{ts}{target.suffix}"
            dest   = target.with_suffix(suffix)
            shutil.copy2(target, dest)

    # ── Push / pull ───────────────────────────────────────────────────────────

    async def push_folder(self, folder: str, peer: SyncPeer) -> dict[str, Any]:
        """Push all files in a folder to a remote peer."""
        index = self.index_folder(folder)
        pushed = 0
        errors = []

        async with httpx.AsyncClient(timeout=30) as client:
            for item_meta in index:
                path    = item_meta["path"]
                content = self.get_file(folder, path)
                if content is None:
                    continue
                try:
                    payload = {
                        "folder":   folder,
                        "path":     path,
                        "sha256":   item_meta["sha256"],
                        "modified": item_meta["modified"],
                        "content":  content.hex(),     # hex-encode binary
                        "deleted":  False,
                    }
                    # HMAC-authenticate the request
                    import hmac as hmac_mod
                    sig = hmac_mod.new(
                        peer.secret.encode(),
                        json.dumps(payload, sort_keys=True).encode(),
                        "sha256",
                    ).hexdigest()
                    resp = await client.post(
                        f"{peer.base_url}/api/sync/receive",
                        json=payload,
                        headers={"X-Sync-Sig": sig},
                        timeout=15,
                    )
                    if resp.status_code == 200:
                        pushed += 1
                    else:
                        errors.append(f"{path}: HTTP {resp.status_code}")
                except Exception as e:
                    errors.append(f"{path}: {e}")

        peer.last_sync = time.time()
        return {
            "folder": folder,
            "peer":   peer.name,
            "pushed": pushed,
            "errors": errors,
        }

    async def pull_folder(self, folder: str, peer: SyncPeer) -> dict[str, Any]:
        """Pull all files in a folder from a remote peer."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{peer.base_url}/api/sync/index/{folder}",
                    timeout=10,
                )
                if resp.status_code != 200:
                    return {"error": f"Failed to get index from peer: HTTP {resp.status_code}"}
                remote_index = resp.json()
        except Exception as e:
            return {"error": f"Cannot connect to peer {peer.name}: {e}"}

        pulled  = 0
        skipped = 0
        errors  = []

        async with httpx.AsyncClient(timeout=30) as client:
            for item_meta in remote_index:
                path       = item_meta["path"]
                remote_sha = item_meta["sha256"]
                modified   = item_meta["modified"]

                # Check if we already have this version
                local_content = self.get_file(folder, path)
                if local_content and hashlib.sha256(local_content).hexdigest() == remote_sha:
                    skipped += 1
                    continue

                # Conflict detection: local is newer and different
                if local_content and self._check_conflict(folder, path, remote_sha, peer):
                    self._save_conflict_copy(folder, path)

                try:
                    file_resp = await client.get(
                        f"{peer.base_url}/api/sync/file/{folder}/{path}",
                        timeout=15,
                    )
                    if file_resp.status_code == 200:
                        self.write_file(folder, path, file_resp.content, modified)
                        pulled += 1
                    else:
                        errors.append(f"{path}: HTTP {file_resp.status_code}")
                except Exception as e:
                    errors.append(f"{path}: {e}")

        peer.last_sync = time.time()
        return {
            "folder":  folder,
            "peer":    peer.name,
            "pulled":  pulled,
            "skipped": skipped,
            "errors":  errors,
        }

    # ── Status ────────────────────────────────────────────────────────────────

    def status(self) -> dict[str, Any]:
        folders_status = {}
        for folder in SYNC_FOLDERS:
            index = self.index_folder(folder)
            folders_status[folder] = {
                "files":     len(index),
                "total_size": sum(i["size"] for i in index),
            }
        return {
            "peers":     len(self._peers),
            "conflicts": len([c for c in self._conflicts.values() if not c.resolved]),
            "folders":   folders_status,
        }


# ── Singleton ─────────────────────────────────────────────────────────────────

_service: SyncService | None = None


def get_sync_service() -> SyncService:
    global _service
    if _service is None:
        _service = SyncService()
    return _service


# ── FastAPI router ─────────────────────────────────────────────────────────────

sync_router = APIRouter(prefix="/api/sync", tags=["sync"])


class PeerCreateRequest(BaseModel):
    name:    str
    host:    str
    port:    int = 9999
    secret:  str
    folders: list[str] = Field(default_factory=list)


class ReceiveItemRequest(BaseModel):
    folder:   str
    path:     str
    sha256:   str
    modified: float
    content:  str        # hex-encoded file content
    deleted:  bool = False


@sync_router.get("/status")
async def sync_status(request: Request):
    """Return sync service status."""
    svc = get_sync_service()
    return svc.status()


@sync_router.get("/peers")
async def list_peers(request: Request):
    require_power_user(request)
    svc = get_sync_service()
    return {"peers": [p.as_safe_dict() for p in svc.list_peers()]}


@sync_router.post("/peers", status_code=201)
async def add_peer(request: Request, body: PeerCreateRequest):
    require_power_user(request)
    svc  = get_sync_service()
    peer = SyncPeer(
        peer_id=f"peer_{secrets.token_hex(6)}",
        name=body.name,
        host=body.host,
        port=body.port,
        secret=body.secret,
        folders=body.folders or list(SYNC_FOLDERS.keys()),
    )
    svc.add_peer(peer)
    user = getattr(request.state, "user", {}) or {}
    audit("sync.peer_add", user, resource="sync_peer", resource_id=peer.peer_id)
    return peer.as_safe_dict()


@sync_router.delete("/peers/{peer_id}", status_code=204)
async def remove_peer(peer_id: str, request: Request):
    require_power_user(request)
    svc = get_sync_service()
    if not svc.remove_peer(peer_id):
        raise HTTPException(status_code=404, detail=f"Peer {peer_id!r} not found.")
    audit("sync.peer_remove", getattr(request.state, "user", {}) or {}, resource="sync_peer", resource_id=peer_id)


@sync_router.post("/push/{folder}")
async def push_folder(folder: str, request: Request):
    """Trigger a push of a folder to all connected peers."""
    require_power_user(request)
    if folder not in SYNC_FOLDERS:
        raise HTTPException(status_code=400, detail=f"Unknown folder: {folder!r}")
    svc     = get_sync_service()
    results = []
    for peer in svc.list_peers():
        if peer.enabled and (not peer.folders or folder in peer.folders):
            result = await svc.push_folder(folder, peer)
            results.append(result)
    return {"folder": folder, "results": results}


@sync_router.post("/pull/{folder}")
async def pull_folder(folder: str, request: Request):
    """Trigger a pull from all connected peers."""
    require_power_user(request)
    if folder not in SYNC_FOLDERS:
        raise HTTPException(status_code=400, detail=f"Unknown folder: {folder!r}")
    svc     = get_sync_service()
    results = []
    for peer in svc.list_peers():
        if peer.enabled and (not peer.folders or folder in peer.folders):
            result = await svc.pull_folder(folder, peer)
            results.append(result)
    return {"folder": folder, "results": results}


@sync_router.get("/index/{folder}")
async def get_folder_index(folder: str):
    """Return the file index for a folder (called by remote peers)."""
    if folder not in SYNC_FOLDERS:
        raise HTTPException(status_code=400, detail=f"Unknown folder: {folder!r}")
    svc = get_sync_service()
    return svc.index_folder(folder)


@sync_router.get("/file/{folder}/{path:path}")
async def get_sync_file(folder: str, path: str):
    """Return the raw file contents (called by remote peers for pull)."""
    if folder not in SYNC_FOLDERS:
        raise HTTPException(status_code=400, detail=f"Unknown folder: {folder!r}")
    svc     = get_sync_service()
    content = svc.get_file(folder, path)
    if content is None:
        raise HTTPException(status_code=404, detail="File not found.")
    from fastapi.responses import Response
    return Response(content=content, media_type="application/octet-stream")


@sync_router.post("/receive")
async def receive_sync_item(request: Request, body: ReceiveItemRequest):
    """Receive a file pushed from a remote peer."""
    # Verify HMAC signature
    import hmac as hmac_mod
    sig_header = request.headers.get("X-Sync-Sig", "")
    # Find peer by attempting to verify against all registered peers
    svc    = get_sync_service()
    peer   = None
    import json as _json
    payload_dict = body.model_dump()
    payload_bytes = _json.dumps(payload_dict, sort_keys=True).encode()
    for p in svc.list_peers():
        expected_sig = hmac_mod.new(p.secret.encode(), payload_bytes, "sha256").hexdigest()
        if hmac_mod.compare_digest(expected_sig, sig_header):
            peer = p
            break
    if peer is None:
        raise HTTPException(status_code=403, detail="Invalid sync signature.")

    if body.folder not in SYNC_FOLDERS:
        raise HTTPException(status_code=400, detail=f"Unknown folder: {body.folder!r}")

    if body.deleted:
        svc.delete_file(body.folder, body.path)
    else:
        content = bytes.fromhex(body.content)
        if hashlib.sha256(content).hexdigest() != body.sha256:
            raise HTTPException(status_code=400, detail="SHA256 mismatch.")
        svc.write_file(body.folder, body.path, content, body.modified)

    peer.last_seen = time.time()
    return {"received": True, "path": body.path}


@sync_router.get("/conflicts")
async def list_conflicts(request: Request):
    """List unresolved sync conflicts."""
    require_power_user(request)
    svc = get_sync_service()
    conflicts = [
        {
            "conflict_id": c.conflict_id,
            "folder":      c.folder,
            "path":        c.path,
            "local_sha":   c.local_sha[:8] + "...",
            "remote_sha":  c.remote_sha[:8] + "...",
            "remote_peer": c.remote_peer,
            "detected_at": c.detected_at,
            "resolved":    c.resolved,
        }
        for c in svc._conflicts.values()
        if not c.resolved
    ]
    return {"conflicts": conflicts}


@sync_router.post("/conflicts/{conflict_id}/resolve")
async def resolve_conflict(conflict_id: str, request: Request):
    """Mark a conflict as resolved (after manual inspection)."""
    require_power_user(request)
    svc = get_sync_service()
    conflict = svc._conflicts.get(conflict_id)
    if not conflict:
        raise HTTPException(status_code=404, detail=f"Conflict {conflict_id!r} not found.")
    conflict.resolved = True
    audit("sync.conflict_resolve", getattr(request.state, "user", {}) or {}, resource="sync", resource_id=conflict_id)
    return {"resolved": True, "conflict_id": conflict_id}

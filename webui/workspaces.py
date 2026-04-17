from __future__ import annotations

import secrets
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from agent.tools import WorkspaceTools
from webui.config_store import JsonConfigStore, get_data_dir
from webui.url_guard import validate_git_ref, validate_outbound_url


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    kind: Literal["local", "git"] = "local"
    path: str | None = Field(default=None, max_length=4096)
    git_url: str | None = Field(default=None, max_length=4096)
    git_ref: str | None = Field(default=None, max_length=200)


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    path: str | None = Field(default=None, max_length=4096)
    git_url: str | None = Field(default=None, max_length=4096)
    git_ref: str | None = Field(default=None, max_length=200)


class WorkspaceRecord(BaseModel):
    workspace_id: str
    name: str
    kind: Literal["local", "git"]
    path: str
    git_url: str | None = None
    git_ref: str | None = None
    created_at: str
    updated_at: str


def _normalize_path(path: str) -> str:
    return str(Path(path).expanduser().resolve())


class WorkspaceManager:
    def __init__(self, store: JsonConfigStore, *, default_local_root: Path) -> None:
        self._store = store
        self._default_local_root = default_local_root.resolve()

    def ensure_defaults(self) -> None:
        items = self._items()
        if items:
            return
        now = _now()
        self._store.save(
            "workspaces",
            [
                {
                    "workspace_id": "ws_current",
                    "name": "Current repo (bundled)",
                    "kind": "local",
                    "path": str(self._default_local_root),
                    "git_url": None,
                    "git_ref": None,
                    "created_at": now,
                    "updated_at": now,
                }
            ],
        )

    def list(self) -> list[WorkspaceRecord]:
        return [WorkspaceRecord.model_validate(item) for item in self._items()]

    def get(self, workspace_id: str) -> WorkspaceRecord | None:
        for item in self._items():
            if item.get("workspace_id") == workspace_id:
                return WorkspaceRecord.model_validate(item)
        return None

    def create(self, body: WorkspaceCreate) -> WorkspaceRecord:
        items = self._items()
        now = _now()
        workspace_id = "ws_" + secrets.token_hex(6)

        if body.kind == "local":
            if not body.path:
                raise ValueError("path is required for local workspace")
            path = _normalize_path(body.path)
            record = {
                "workspace_id": workspace_id,
                "name": body.name.strip(),
                "kind": "local",
                "path": path,
                "git_url": None,
                "git_ref": None,
                "created_at": now,
                "updated_at": now,
            }
        else:
            if not body.git_url:
                raise ValueError("git_url is required for git workspace")
            validate_outbound_url(body.git_url, scheme="git")
            ref = validate_git_ref(body.git_ref) if body.git_ref else None
            root = self._git_workspace_dir(workspace_id)
            root.parent.mkdir(parents=True, exist_ok=True)
            self._git_clone(body.git_url, root, ref=ref)
            record = {
                "workspace_id": workspace_id,
                "name": body.name.strip(),
                "kind": "git",
                "path": str(root),
                "git_url": body.git_url,
                "git_ref": body.git_ref,
                "created_at": now,
                "updated_at": now,
            }

        items.append(record)
        self._store.save("workspaces", items)
        return WorkspaceRecord.model_validate(record)

    def update(self, workspace_id: str, body: WorkspaceUpdate) -> WorkspaceRecord | None:
        items = self._items()
        for item in items:
            if item.get("workspace_id") != workspace_id:
                continue
            if body.name is not None:
                item["name"] = body.name.strip()
            if body.path is not None:
                item["path"] = _normalize_path(body.path)
            if body.git_url is not None:
                validate_outbound_url(body.git_url, scheme="git")
                item["git_url"] = body.git_url
            if body.git_ref is not None:
                item["git_ref"] = validate_git_ref(body.git_ref)
            item["updated_at"] = _now()
            self._store.save("workspaces", items)
            return WorkspaceRecord.model_validate(item)
        return None

    def delete(self, workspace_id: str) -> bool:
        items = self._items()
        target = None
        after: list[dict[str, Any]] = []
        for item in items:
            if item.get("workspace_id") == workspace_id:
                target = item
            else:
                after.append(item)
        if not target:
            return False
        self._store.save("workspaces", after)
        if target.get("kind") == "git":
            try:
                shutil.rmtree(target.get("path") or "")
            except OSError:
                pass
        return True

    def tools_for(self, workspace_id: str) -> WorkspaceTools:
        ws = self.get(workspace_id)
        if not ws:
            raise KeyError("unknown workspace")
        return WorkspaceTools(ws.path)

    def sync_git(self, workspace_id: str) -> dict[str, Any]:
        ws = self.get(workspace_id)
        if not ws:
            raise KeyError("unknown workspace")
        if ws.kind != "git":
            raise ValueError("workspace is not a git workspace")
        root = Path(ws.path)
        out = self._git_pull(root, ref=ws.git_ref)
        return {"workspace_id": ws.workspace_id, "output": out}

    def _items(self) -> list[dict[str, Any]]:
        raw = self._store.load("workspaces")
        items = raw.get("items")
        return items if isinstance(items, list) else []

    def _git_workspace_dir(self, workspace_id: str) -> Path:
        base = get_data_dir() / "workspaces"
        base.mkdir(parents=True, exist_ok=True)
        return base / workspace_id

    def _git_clone(self, url: str, dest: Path, *, ref: str | None) -> None:
        self._require_git()
        cmd = ["git", "clone", "--depth", "1"]
        if ref:
            cmd += ["--branch", ref]
        cmd += [url, str(dest)]
        subprocess.run(cmd, check=True, capture_output=True, text=True)

    def _git_pull(self, root: Path, *, ref: str | None) -> str:
        self._require_git()
        subprocess.run(["git", "fetch", "--all", "--prune"], cwd=root, check=True, capture_output=True, text=True)
        if ref:
            subprocess.run(["git", "checkout", ref], cwd=root, check=True, capture_output=True, text=True)
        proc = subprocess.run(["git", "pull", "--ff-only"], cwd=root, check=True, capture_output=True, text=True)
        return (proc.stdout or proc.stderr or "").strip()

    def _require_git(self) -> None:
        if shutil.which("git"):
            return
        raise RuntimeError("git is not available in this environment")

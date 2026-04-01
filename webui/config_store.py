from __future__ import annotations

import json
import os
import secrets
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log_name = "qwen-proxy"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def get_data_dir() -> Path:
    root = os.environ.get("WEBUI_DATA_DIR") or os.environ.get("DATA_DIR") or ".data"
    p = Path(root).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def _atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp-{secrets.token_hex(8)}")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


@dataclass(frozen=True)
class JsonStorePaths:
    providers: Path
    workspaces: Path


def default_store_paths() -> JsonStorePaths:
    data_dir = get_data_dir()
    return JsonStorePaths(
        providers=data_dir / "providers.json",
        workspaces=data_dir / "workspaces.json",
    )


class JsonConfigStore:
    """Simple JSON-backed store for admin-managed config (providers/workspaces).

    Notes:
    - This is server-side only; secrets are never returned verbatim from APIs.
    - Reads/writes are protected by an in-process lock.
    """

    def __init__(self, paths: JsonStorePaths | None = None) -> None:
        self._paths = paths or default_store_paths()
        self._lock = threading.RLock()

    def load(self, kind: str) -> dict[str, Any]:
        path = self._path_for(kind)
        with self._lock:
            if not path.exists():
                return {"schema_version": "1", "updated_at": _now(), "items": []}
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict) or "items" not in raw:
                return {"schema_version": "1", "updated_at": _now(), "items": []}
            return raw

    def save(self, kind: str, items: list[dict[str, Any]]) -> dict[str, Any]:
        path = self._path_for(kind)
        payload = {"schema_version": "1", "updated_at": _now(), "items": items}
        with self._lock:
            _atomic_write_json(path, payload)
        return payload

    def _path_for(self, kind: str) -> Path:
        if kind == "providers":
            return self._paths.providers
        if kind == "workspaces":
            return self._paths.workspaces
        raise ValueError(f"Unknown config kind: {kind}")


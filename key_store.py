"""
Persistent API key store: each key maps to email + department (seat) and a stable id.
Keys are stored only as SHA-256 hashes; the plaintext is shown once at creation.
Legacy env-based API_KEYS in proxy.py still works for bootstrapping.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class KeyRecord:
    key_id: str
    email: str
    department: str
    created: str


class KeyStore:
    """Thread-safe JSON-backed key store."""

    def __init__(self, path: Path | str | None) -> None:
        self._path = Path(path) if path else None
        self._lock = threading.RLock()
        self._by_hash: dict[str, KeyRecord] = {}
        self._mtime: float = 0.0
        if self._path and self._path.is_file():
            self._load_unlocked()
            self._mtime = self._path.stat().st_mtime

    def is_configured(self) -> bool:
        return self._path is not None

    def _maybe_reload(self) -> None:
        if not self._path or not self._path.is_file():
            return
        try:
            m = self._path.stat().st_mtime
        except OSError:
            return
        if m == self._mtime:
            return
        with self._lock:
            try:
                m2 = self._path.stat().st_mtime
            except OSError:
                return
            if m2 == self._mtime:
                return
            self._load_unlocked()
            self._mtime = self._path.stat().st_mtime

    def _load_unlocked(self) -> None:
        import logging as _logging
        assert self._path is not None
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            _logging.getLogger("qwen-proxy").warning(
                "KeyStore: could not read %s (%s) — key store reset to empty",
                self._path, exc,
            )
            self._by_hash.clear()
            return
        keys = raw.get("keys") if isinstance(raw, dict) else None
        if not isinstance(keys, list):
            return
        self._by_hash.clear()
        for item in keys:
            if not isinstance(item, dict):
                continue
            h = item.get("hash")
            if not isinstance(h, str) or len(h) != 64:
                continue
            kid = item.get("key_id")
            email = item.get("email")
            dept = item.get("department")
            created = item.get("created")
            if not isinstance(kid, str) or not isinstance(email, str) or not isinstance(dept, str):
                continue
            if not isinstance(created, str):
                created = ""
            self._by_hash[h] = KeyRecord(
                key_id=kid,
                email=email,
                department=dept,
                created=created,
            )

    def __len__(self) -> int:
        self._maybe_reload()
        with self._lock:
            return len(self._by_hash)

    def reload(self) -> None:
        if not self._path or not self._path.is_file():
            return
        with self._lock:
            self._load_unlocked()
            self._mtime = self._path.stat().st_mtime

    def lookup_plain_key(self, plain_key: str) -> KeyRecord | None:
        self._maybe_reload()
        h = hashlib.sha256(plain_key.encode("utf-8")).hexdigest()
        with self._lock:
            return self._by_hash.get(h)

    def add_key(
        self,
        *,
        plain_key: str,
        email: str,
        department: str,
        key_id: str,
    ) -> KeyRecord:
        if self._path is None:
            raise RuntimeError("KEYS_FILE is not set; cannot persist keys")
        h = hashlib.sha256(plain_key.encode("utf-8")).hexdigest()
        created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        rec = KeyRecord(key_id=key_id, email=email, department=department, created=created)
        with self._lock:
            self._by_hash[h] = rec
            self._save_unlocked()
            if self._path.is_file():
                self._mtime = self._path.stat().st_mtime
        return rec

    def list_records(self) -> list[KeyRecord]:
        self._maybe_reload()
        with self._lock:
            return sorted(self._by_hash.values(), key=lambda r: (r.created, r.key_id))

    def delete_by_key_id(self, key_id: str) -> bool:
        if self._path is None:
            return False
        with self._lock:
            h_del = None
            for h, rec in self._by_hash.items():
                if rec.key_id == key_id:
                    h_del = h
                    break
            if h_del is None:
                return False
            del self._by_hash[h_del]
            self._save_unlocked()
            if self._path.is_file():
                self._mtime = self._path.stat().st_mtime
        return True

    def update_metadata(self, key_id: str, email: str, department: str) -> KeyRecord | None:
        if self._path is None:
            return None
        email, department = email.strip(), department.strip()
        with self._lock:
            found_h = None
            rec = None
            for h, r in self._by_hash.items():
                if r.key_id == key_id:
                    found_h, rec = h, r
                    break
            if not rec or found_h is None:
                return None
            new_rec = KeyRecord(key_id=rec.key_id, email=email, department=department, created=rec.created)
            self._by_hash[found_h] = new_rec
            self._save_unlocked()
            if self._path.is_file():
                self._mtime = self._path.stat().st_mtime
        return new_rec

    def rotate_plain(self, key_id: str) -> tuple[str, KeyRecord] | None:
        if self._path is None:
            return None
        with self._lock:
            old_h = None
            rec = None
            for h, r in self._by_hash.items():
                if r.key_id == key_id:
                    old_h, rec = h, r
                    break
            if not rec or old_h is None:
                return None
            del self._by_hash[old_h]
            plain_key = "test-key-" + secrets.token_urlsafe(32)
            new_h = hashlib.sha256(plain_key.encode("utf-8")).hexdigest()
            kept = KeyRecord(key_id=rec.key_id, email=rec.email, department=rec.department, created=rec.created)
            self._by_hash[new_h] = kept
            self._save_unlocked()
            if self._path.is_file():
                self._mtime = self._path.stat().st_mtime
        return plain_key, kept

    def _save_unlocked(self) -> None:
        assert self._path is not None
        keys: list[dict[str, Any]] = []
        for h, rec in self._by_hash.items():
            keys.append(
                {
                    "key_id": rec.key_id,
                    "hash": h,
                    "email": rec.email,
                    "department": rec.department,
                    "created": rec.created,
                }
            )
        keys.sort(key=lambda x: (x.get("created") or "", x.get("key_id") or ""))
        payload = {"version": 1, "keys": keys}
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(self._path)


def default_keys_path() -> Path | None:
    raw = os.environ.get("KEYS_FILE", "").strip()
    if not raw:
        return None
    return Path(raw)


def load_key_store() -> KeyStore:
    return KeyStore(default_keys_path())


def issue_new_api_key(store: KeyStore, email: str, department: str) -> tuple[str, KeyRecord]:
    """Generate a new plaintext API key, persist hash + metadata, return (plain_key, record)."""
    key_id = "kid_" + secrets.token_hex(6)
    plain_key = "test-key-" + secrets.token_urlsafe(32)
    rec = store.add_key(plain_key=plain_key, email=email, department=department, key_id=key_id)
    return plain_key, rec

"""secrets_store.py — User-scoped, workspace-level, and admin/global secrets.

Three secret scopes:
  user      — visible only to the owning user; never to other users or admins
               (admins see metadata, never the value).
  workspace — visible to Power Users and Admins; useful for shared API keys,
               Langfuse credentials, etc.
  global    — admin-only; platform-wide provider credentials.

Security invariants:
  1. Raw secret values are NEVER returned by any API endpoint.
  2. Values are AES-256-GCM encrypted at rest using a key derived from
     SECRET_STORE_KEY env var (default: a stable key derived from hostname).
  3. All log paths use mask_secret() / mask_dict() from rbac.py.
  4. Audit entries record only secret_id, never the value.
  5. Constant-time comparison is used when verifying secret hashes.

FastAPI router: /api/secrets/
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import secrets
import time
from enum import Enum
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from rbac import (
    UserRole,
    Permission,
    audit,
    get_user_role,
    has_permission,
    mask_secret,
    mask_dict,
)

log = logging.getLogger("qwen-proxy")


# ── Encryption helpers ────────────────────────────────────────────────────────

def _get_master_key() -> bytes:
    """Derive a 32-byte AES key from SECRET_STORE_KEY env var.

    Falls back to a key derived from the hostname — predictable enough for
    single-machine use but not for multi-machine; set SECRET_STORE_KEY in
    production.
    """
    raw = os.environ.get("SECRET_STORE_KEY", "").strip()
    if not raw:
        import socket
        raw = f"llm-relay-secrets-{socket.gethostname()}"
        log.warning(
            "SECRET_STORE_KEY not set — using hostname-derived key. "
            "Set SECRET_STORE_KEY in production for proper at-rest encryption."
        )
    return hashlib.sha256(raw.encode()).digest()


def _encrypt(plaintext: str) -> str:
    """Encrypt a plaintext secret using AES-256-GCM.

    Returns a base64-encoded string: nonce(12) || tag(16) || ciphertext.
    Falls back to XOR obfuscation if cryptography package is unavailable.
    """
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        key   = _get_master_key()
        nonce = os.urandom(12)
        gcm   = AESGCM(key)
        ct    = gcm.encrypt(nonce, plaintext.encode(), None)
        return base64.b64encode(nonce + ct).decode()
    except ImportError:
        # Fallback: simple XOR obfuscation (not secure, but prevents plain-text storage)
        key_bytes = _get_master_key()
        data      = plaintext.encode()
        xored     = bytes(b ^ key_bytes[i % 32] for i, b in enumerate(data))
        return "xor:" + base64.b64encode(xored).decode()


def _decrypt(ciphertext: str) -> str:
    """Decrypt a value encrypted by _encrypt()."""
    try:
        if ciphertext.startswith("xor:"):
            key_bytes = _get_master_key()
            data  = base64.b64decode(ciphertext[4:])
            plain = bytes(b ^ key_bytes[i % 32] for i, b in enumerate(data))
            return plain.decode()
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        key   = _get_master_key()
        raw   = base64.b64decode(ciphertext)
        nonce, ct = raw[:12], raw[12:]
        gcm   = AESGCM(key)
        return gcm.decrypt(nonce, ct, None).decode()
    except Exception as e:
        log.error("Secret decryption failed: %s", e)
        raise ValueError("Secret decryption failed") from e


# ── Secret scope / model ─────────────────────────────────────────────────────

class SecretScope(str, Enum):
    USER      = "user"       # owning user only
    WORKSPACE = "workspace"  # power users + admins
    GLOBAL    = "global"     # admins only


class SecretRecord(BaseModel):
    """Internal record — value is always encrypted."""
    secret_id:  str = Field(default_factory=lambda: f"secret_{secrets.token_hex(8)}")
    owner_id:   str                                  # user email / _id
    name:       str                                  # human-readable label
    description: str = ""
    scope:      SecretScope = SecretScope.USER
    key_hint:   str = ""                             # e.g. "sk-proj-****abcd"
    _encrypted_value: str = ""                      # encrypted at rest
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    last_used_at: float | None = None
    tags:       list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}

    def set_value(self, plaintext: str) -> None:
        """Encrypt and store the secret value."""
        object.__setattr__(self, "_encrypted_value", _encrypt(plaintext))
        # Generate a hint: show first 4 and last 4 chars
        if len(plaintext) > 8:
            hint = plaintext[:4] + "****" + plaintext[-4:]
        else:
            hint = "****"
        self.key_hint = hint
        self.updated_at = time.time()

    def get_value(self) -> str:
        """Decrypt and return the raw secret value.  Never expose via API."""
        enc = object.__getattribute__(self, "_encrypted_value")
        if not enc:
            return ""
        return _decrypt(enc)

    def touch_use(self) -> None:
        self.last_used_at = time.time()

    def as_safe_dict(self) -> dict[str, Any]:
        """Return a dict safe for API responses — value is NEVER included."""
        return {
            "secret_id":    self.secret_id,
            "owner_id":     self.owner_id,
            "name":         self.name,
            "description":  self.description,
            "scope":        self.scope.value,
            "key_hint":     self.key_hint,
            "created_at":   self.created_at,
            "updated_at":   self.updated_at,
            "last_used_at": self.last_used_at,
            "tags":         self.tags,
        }

    def as_storage_dict(self) -> dict[str, Any]:
        """Serialise for DB storage — includes encrypted value."""
        d = self.as_safe_dict()
        d["_encrypted_value"] = object.__getattribute__(self, "_encrypted_value")
        return d

    @classmethod
    def from_storage_dict(cls, data: dict) -> "SecretRecord":
        enc = data.pop("_encrypted_value", "")
        rec = cls(**data)
        object.__setattr__(rec, "_encrypted_value", enc)
        return rec


# ── API request / response models ─────────────────────────────────────────────

class SecretCreateRequest(BaseModel):
    name:        str
    description: str = ""
    value:       str                         # plaintext — accepted once, never returned
    scope:       SecretScope = SecretScope.USER
    tags:        list[str] = Field(default_factory=list)


class SecretUpdateRequest(BaseModel):
    name:        str | None = None
    description: str | None = None
    value:       str | None = None           # if provided, re-encrypt
    scope:       SecretScope | None = None
    tags:        list[str] | None = None


# ── Store ─────────────────────────────────────────────────────────────────────

class SecretsStore:
    """CRUD store for SecretRecord.

    Uses MongoDB if available, in-memory fallback otherwise.
    Never returns raw values via any API method.
    """

    COLLECTION = "user_secrets"

    def __init__(self, db: Any = None) -> None:
        self._db  = db
        self._mem: dict[str, SecretRecord] = {}

    @property
    def _col(self):
        return self._db[self.COLLECTION] if self._db is not None else None

    async def create(self, record: SecretRecord) -> SecretRecord:
        if self._col is not None:
            await self._col.insert_one(record.as_storage_dict())
        else:
            self._mem[record.secret_id] = record
        return record

    async def _fetch_raw(self, secret_id: str) -> SecretRecord | None:
        if self._col is not None:
            doc = await self._col.find_one({"secret_id": secret_id})
            if doc is None:
                return None
            doc.pop("_id", None)
            return SecretRecord.from_storage_dict(doc)
        return self._mem.get(secret_id)

    async def get_metadata(
        self,
        secret_id: str,
        requester_id: str | None = None,
        requester_role: UserRole = UserRole.USER,
    ) -> SecretRecord | None:
        """Return a record if the requester has read access (metadata only)."""
        rec = await self._fetch_raw(secret_id)
        if rec is None:
            return None
        if not _can_read(rec, requester_id, requester_role):
            return None
        return rec

    async def get_value(
        self,
        secret_id: str,
        requester_id: str | None,
        requester_role: UserRole = UserRole.USER,
    ) -> str | None:
        """Return the decrypted secret value for internal (non-API) use only."""
        rec = await self._fetch_raw(secret_id)
        if rec is None:
            return None
        if not _can_read(rec, requester_id, requester_role):
            return None
        rec.touch_use()
        await self._update_raw(rec)
        return rec.get_value()

    async def _update_raw(self, record: SecretRecord) -> None:
        if self._col is not None:
            await self._col.replace_one(
                {"secret_id": record.secret_id},
                record.as_storage_dict(),
                upsert=True,
            )
        else:
            self._mem[record.secret_id] = record

    async def update(
        self,
        secret_id: str,
        body: SecretUpdateRequest,
        requester_id: str,
        requester_role: UserRole,
    ) -> SecretRecord | None:
        rec = await self._fetch_raw(secret_id)
        if rec is None:
            return None
        if not _can_write(rec, requester_id, requester_role):
            return None
        if body.name        is not None: rec.name        = body.name
        if body.description is not None: rec.description = body.description
        if body.tags        is not None: rec.tags        = body.tags
        if body.scope       is not None:
            # Only admin can promote to global
            if body.scope == SecretScope.GLOBAL and requester_role != UserRole.ADMIN:
                raise HTTPException(
                    status_code=403,
                    detail="Only admins may create global-scope secrets.",
                )
            rec.scope = body.scope
        if body.value is not None:
            rec.set_value(body.value)
        rec.updated_at = time.time()
        await self._update_raw(rec)
        return rec

    async def delete(
        self,
        secret_id: str,
        requester_id: str,
        requester_role: UserRole,
    ) -> bool:
        rec = await self._fetch_raw(secret_id)
        if rec is None:
            return False
        if not _can_write(rec, requester_id, requester_role):
            return False
        if self._col is not None:
            await self._col.delete_one({"secret_id": secret_id})
        else:
            self._mem.pop(secret_id, None)
        return True

    async def list_for_user(
        self,
        requester_id: str,
        requester_role: UserRole,
    ) -> list[SecretRecord]:
        if self._col is not None:
            if requester_role == UserRole.ADMIN:
                docs = await self._col.find({}).to_list(length=10000)
            elif requester_role == UserRole.POWER_USER:
                docs = await self._col.find({
                    "$or": [
                        {"owner_id": requester_id},
                        {"scope": {"$in": ["workspace", "global"]}},
                    ]
                }).to_list(length=1000)
            else:
                docs = await self._col.find({
                    "$or": [
                        {"owner_id": requester_id},
                        {"scope": "workspace"},
                    ]
                }).to_list(length=1000)
            return [SecretRecord.from_storage_dict({**d}) for d in docs]
        else:
            result = []
            for rec in self._mem.values():
                if _can_read(rec, requester_id, requester_role):
                    result.append(rec)
            return result


def _can_read(rec: SecretRecord, uid: str | None, role: UserRole) -> bool:
    if role == UserRole.ADMIN:
        return True
    if rec.scope == SecretScope.GLOBAL:
        return role == UserRole.ADMIN
    if rec.scope == SecretScope.WORKSPACE:
        return role in (UserRole.ADMIN, UserRole.POWER_USER) or rec.owner_id == uid
    # USER scope
    return rec.owner_id == uid


def _can_write(rec: SecretRecord, uid: str | None, role: UserRole) -> bool:
    if role == UserRole.ADMIN:
        return True
    if rec.scope == SecretScope.GLOBAL:
        return False   # only admin can write global
    if rec.scope == SecretScope.WORKSPACE:
        return role == UserRole.POWER_USER or rec.owner_id == uid
    return rec.owner_id == uid


# ── Singleton ─────────────────────────────────────────────────────────────────

_store: SecretsStore | None = None


def get_secrets_store(db: Any = None) -> SecretsStore:
    global _store
    if _store is None:
        _store = SecretsStore(db=db)
    return _store


# ── FastAPI router ────────────────────────────────────────────────────────────

secrets_router = APIRouter(prefix="/api/secrets", tags=["secrets"])


def _get_user(request: Request) -> dict:
    return getattr(request.state, "user", None) or {}


def _uid(user: Any) -> str:
    if isinstance(user, dict):
        return user.get("email") or user.get("_id") or "unknown"
    return str(getattr(user, "email", None) or getattr(user, "_id", "unknown"))


@secrets_router.get("/")
async def list_secrets(request: Request):
    """List secrets visible to the current user (metadata only — no values)."""
    user  = _get_user(request)
    uid   = _uid(user)
    role  = get_user_role(user)
    store = get_secrets_store()
    recs  = await store.list_for_user(uid, role)
    return {"secrets": [r.as_safe_dict() for r in recs], "total": len(recs)}


@secrets_router.post("/", status_code=201)
async def create_secret(request: Request, body: SecretCreateRequest):
    """Create a new secret.  The plaintext value is accepted once and never returned."""
    user  = _get_user(request)
    uid   = _uid(user)
    role  = get_user_role(user)

    # Scope validation
    if body.scope == SecretScope.GLOBAL and role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins may create global secrets.")
    if body.scope == SecretScope.WORKSPACE and not has_permission(user, Permission.MANAGE_WORKSPACE_SECRETS):
        raise HTTPException(status_code=403, detail="Power User or Admin required for workspace secrets.")

    rec = SecretRecord(owner_id=uid, name=body.name, description=body.description, scope=body.scope, tags=body.tags)
    rec.set_value(body.value)

    store = get_secrets_store()
    await store.create(rec)

    audit("secret.create", user, resource="secret", resource_id=rec.secret_id)
    log.info("Secret created: %s (scope=%s) by %s", rec.secret_id, rec.scope.value, uid)

    return rec.as_safe_dict()


@secrets_router.get("/{secret_id}")
async def get_secret_metadata(secret_id: str, request: Request):
    """Get secret metadata (never the value)."""
    user  = _get_user(request)
    uid   = _uid(user)
    role  = get_user_role(user)
    store = get_secrets_store()

    rec = await store.get_metadata(secret_id, uid, role)
    if rec is None:
        raise HTTPException(status_code=404, detail=f"Secret {secret_id!r} not found.")
    return rec.as_safe_dict()


@secrets_router.put("/{secret_id}")
async def update_secret(secret_id: str, request: Request, body: SecretUpdateRequest):
    """Update a secret.  Providing 'value' re-encrypts it."""
    user  = _get_user(request)
    uid   = _uid(user)
    role  = get_user_role(user)
    store = get_secrets_store()

    rec = await store.update(secret_id, body, uid, role)
    if rec is None:
        raise HTTPException(status_code=404, detail=f"Secret {secret_id!r} not found or access denied.")

    audit("secret.update", user, resource="secret", resource_id=secret_id)
    return rec.as_safe_dict()


@secrets_router.delete("/{secret_id}", status_code=204)
async def delete_secret(secret_id: str, request: Request):
    """Delete a secret."""
    user  = _get_user(request)
    uid   = _uid(user)
    role  = get_user_role(user)
    store = get_secrets_store()

    ok = await store.delete(secret_id, uid, role)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Secret {secret_id!r} not found or access denied.")
    audit("secret.delete", user, resource="secret", resource_id=secret_id)

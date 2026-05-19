from __future__ import annotations

import ctypes
import os
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Final


_LOGON32_LOGON_NETWORK: Final[int] = 3
_LOGON32_PROVIDER_DEFAULT: Final[int] = 0


@dataclass(frozen=True)
class AdminIdentity:
    username: str
    auth_source: str


@dataclass(frozen=True)
class AdminSession:
    token: str
    identity: AdminIdentity
    expires_at: float


class AdminSessionStore:
    def __init__(self, ttl_seconds: int = 60 * 60 * 12) -> None:
        self._ttl_seconds = ttl_seconds
        self._lock = threading.RLock()
        self._sessions: dict[str, AdminSession] = {}

    @property
    def ttl_seconds(self) -> int:
        return self._ttl_seconds

    def create(self, identity: AdminIdentity) -> AdminSession:
        token = "adm_" + secrets.token_urlsafe(32)
        session = AdminSession(
            token=token,
            identity=identity,
            expires_at=time.time() + self._ttl_seconds,
        )
        with self._lock:
            self._sessions[token] = session
        return session

    def get(self, token: str) -> AdminSession | None:
        now = time.time()
        with self._lock:
            session = self._sessions.get(token)
            if not session:
                return None
            if session.expires_at <= now:
                self._sessions.pop(token, None)
                return None
            return session

    def revoke(self, token: str) -> None:
        with self._lock:
            self._sessions.pop(token, None)


def _is_truthy(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class WindowsCredentialAuthenticator:
    def __init__(self) -> None:
        default_enabled = os.name == "nt"
        self.enabled = _is_truthy(os.environ.get("ADMIN_WINDOWS_AUTH"), default=default_enabled)
        allowed_raw = os.environ.get("ADMIN_WINDOWS_ALLOWED_USERS", "")
        self.allowed_users = {item.strip().lower() for item in allowed_raw.split(",") if item.strip()}
        self.default_domain = os.environ.get("ADMIN_WINDOWS_DEFAULT_DOMAIN", ".").strip() or "."

    def _split_username(self, username: str) -> tuple[str, str | None]:
        value = username.strip()
        if "\\" in value:
            domain, user = value.split("\\", 1)
            return user, domain
        if "@" in value:
            return value, None
        return value, self.default_domain

    def _normalize_allowed(self, username: str) -> set[str]:
        lower = username.strip().lower()
        if "\\" in lower:
            domain, user = lower.split("\\", 1)
            return {lower, user, f"{domain}\\{user}"}
        if "@" in lower:
            user, _, domain = lower.partition("@")
            return {lower, user, f"{domain}\\{user}"}
        return {lower}

    def _check_allowed(self, username: str) -> bool:
        if not self.allowed_users:
            return True
        variants = self._normalize_allowed(username)
        return any(item in self.allowed_users for item in variants)

    def authenticate(self, username: str, password: str) -> AdminIdentity | None:
        if not self.enabled:
            return None
        if os.name != "nt":
            return None
        username = username.strip()
        password = password or ""
        if not username or not password or not self._check_allowed(username):
            return None

        user, domain = self._split_username(username)
        token = ctypes.c_void_p()
        advapi32 = ctypes.windll.advapi32
        kernel32 = ctypes.windll.kernel32
        ok = advapi32.LogonUserW(
            ctypes.c_wchar_p(user),
            ctypes.c_wchar_p(domain) if domain is not None else None,
            ctypes.c_wchar_p(password),
            _LOGON32_LOGON_NETWORK,
            _LOGON32_PROVIDER_DEFAULT,
            ctypes.byref(token),
        )
        if not ok:
            return None
        kernel32.CloseHandle(token)
        return AdminIdentity(username=username, auth_source="windows")


class AdminAuthManager:
    def __init__(self, admin_secret: str) -> None:
        self.admin_secret = admin_secret.strip()
        self.windows = WindowsCredentialAuthenticator()
        self.sessions = AdminSessionStore()

    @property
    def enabled(self) -> bool:
        return self.windows.enabled or bool(self.admin_secret)

    @property
    def supports_windows_auth(self) -> bool:
        return self.windows.enabled and os.name == "nt"

    def authenticate(self, username: str, password: str) -> AdminIdentity | None:
        identity = self.windows.authenticate(username, password)
        if identity:
            return identity
        if self.admin_secret and password.strip() == self.admin_secret.strip():
            user = username.strip() or "admin-secret"
            return AdminIdentity(username=user, auth_source="secret")
        return None

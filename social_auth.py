"""social_auth.py — GitHub and Google OAuth social login.

Flow:
  1. Frontend redirects user to  GET /api/auth/{provider}/login
     → server redirects to GitHub/Google consent screen

  2. Provider redirects back to  GET /api/auth/{provider}/callback?code=...
     → server exchanges code for access token
     → server fetches user profile (email, name, avatar)
     → server upserts user in MongoDB (or in-memory store)
     → server issues a signed JWT session token
     → server redirects to frontend /auth/callback?token=<jwt>

  3. Frontend stores JWT in memory (never localStorage — XSS risk) and
     sends it as "Authorization: Bearer <jwt>" on every API request.

Environment variables:
  GITHUB_CLIENT_ID        GitHub OAuth app client ID
  GITHUB_CLIENT_SECRET    GitHub OAuth app client secret
  GOOGLE_CLIENT_ID        Google OAuth 2.0 client ID
  GOOGLE_CLIENT_SECRET    Google OAuth 2.0 client secret
  OAUTH_REDIRECT_BASE     Base URL of this server (e.g. https://myserver:9999)
  JWT_SECRET              Secret for signing session JWTs (generate with: openssl rand -hex 32)
  FRONTEND_URL            Frontend base URL for post-auth redirect

Security notes:
  - State parameter prevents CSRF on OAuth redirect
  - JWT_SECRET must be set in production (warning logged otherwise)
  - Tokens expire after JWT_EXPIRE_HOURS (default: 24)
  - All token exchanges use HTTPS in production (enforce via OAUTH_REDIRECT_BASE)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel

from rbac import UserRole, audit, mask_secret

log = logging.getLogger("qwen-proxy")

# ── Configuration ──────────────────────────────────────────────────────────────

def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, "").strip() or default


GITHUB_CLIENT_ID     = _env("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = _env("GITHUB_CLIENT_SECRET")
GOOGLE_CLIENT_ID     = _env("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = _env("GOOGLE_CLIENT_SECRET")
OAUTH_REDIRECT_BASE  = _env("OAUTH_REDIRECT_BASE", "http://localhost:9999")
FRONTEND_URL         = _env("FRONTEND_URL", "http://localhost:3000")
JWT_SECRET           = _env("JWT_SECRET") or secrets.token_hex(32)
JWT_EXPIRE_HOURS     = int(os.environ.get("JWT_EXPIRE_HOURS", "24"))

if not _env("JWT_SECRET"):
    log.warning(
        "JWT_SECRET not set — using a randomly generated secret. "
        "Sessions will be invalidated on every server restart. "
        "Set JWT_SECRET in production."
    )

# In-memory CSRF state store (key → expiry timestamp)
_oauth_states: dict[str, float] = {}
_STATE_TTL = 600  # 10 minutes


# ── User model ─────────────────────────────────────────────────────────────────

class SocialUser(BaseModel):
    """User record created/updated after successful OAuth login."""
    user_id:    str          # provider_prefix + provider_user_id (e.g. "gh_12345678")
    email:      str
    name:       str
    avatar_url: str = ""
    provider:   str          # "github" | "google"
    role:       str = UserRole.USER.value   # default: standard user
    created_at: float = 0.0
    updated_at: float = 0.0
    last_login: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump()


# ── In-memory user store (replace with MongoDB in production) ──────────────────

_user_store: dict[str, SocialUser] = {}


def _upsert_user(user: SocialUser) -> SocialUser:
    """Create or update a user.  Never downgrades role."""
    now = time.time()
    existing = _user_store.get(user.user_id)
    if existing:
        # Preserve existing role (never auto-downgrade)
        user.role = existing.role
        user.created_at = existing.created_at
    else:
        user.created_at = now
    user.updated_at = now
    user.last_login = now
    _user_store[user.user_id] = user
    return user


def get_user_by_id(user_id: str) -> SocialUser | None:
    return _user_store.get(user_id)


def get_user_by_email(email: str) -> SocialUser | None:
    return next((u for u in _user_store.values() if u.email == email), None)


def list_all_users() -> list[SocialUser]:
    return list(_user_store.values())


def set_user_role(user_id: str, new_role: str, requester: dict) -> bool:
    """Promote or demote a user's role.  Admin-only."""
    user = _user_store.get(user_id)
    if user is None:
        return False
    user.role = new_role
    user.updated_at = time.time()
    _user_store[user_id] = user
    audit(
        "user.role_change",
        requester,
        resource="user",
        resource_id=user_id,
        detail=f"role changed to {new_role}",
    )
    return True


# ── JWT helpers ────────────────────────────────────────────────────────────────

def _b64url_encode(data: bytes) -> str:
    import base64
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    import base64
    pad = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + "=" * (pad % 4))


def _issue_jwt(user: SocialUser) -> str:
    """Issue a signed HS256 JWT for the given user."""
    header  = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64url_encode(json.dumps({
        "sub":   user.user_id,
        "email": user.email,
        "name":  user.name,
        "role":  user.role,
        "iat":   int(time.time()),
        "exp":   int(time.time()) + JWT_EXPIRE_HOURS * 3600,
    }).encode())
    signing_input = f"{header}.{payload}"
    sig = hmac.new(
        JWT_SECRET.encode(),
        signing_input.encode(),
        hashlib.sha256,
    ).digest()
    return f"{signing_input}.{_b64url_encode(sig)}"


def verify_jwt(token: str) -> dict | None:
    """Verify a JWT and return the payload dict, or None if invalid/expired."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header, payload, sig_b64 = parts
        signing_input = f"{header}.{payload}"
        expected_sig = hmac.new(
            JWT_SECRET.encode(),
            signing_input.encode(),
            hashlib.sha256,
        ).digest()
        actual_sig = _b64url_decode(sig_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        claims = json.loads(_b64url_decode(payload))
        if claims.get("exp", 0) < time.time():
            return None
        return claims
    except Exception:
        return None


# ── CSRF state helpers ─────────────────────────────────────────────────────────

def _new_state() -> str:
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = time.time() + _STATE_TTL
    return state


def _validate_state(state: str) -> bool:
    expiry = _oauth_states.pop(state, None)
    if expiry is None:
        return False
    if time.time() > expiry:
        return False
    return True


# ── GitHub OAuth ───────────────────────────────────────────────────────────────

async def _github_exchange_code(code: str) -> str | None:
    """Exchange GitHub OAuth code for access token."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id":     GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code":          code,
            },
            headers={"Accept": "application/json"},
        )
        if resp.status_code != 200:
            return None
        return resp.json().get("access_token")


async def _github_fetch_user(access_token: str) -> SocialUser | None:
    """Fetch GitHub user profile using an access token."""
    async with httpx.AsyncClient(timeout=10) as client:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        user_resp  = await client.get("https://api.github.com/user", headers=headers)
        email_resp = await client.get("https://api.github.com/user/emails", headers=headers)

        if user_resp.status_code != 200:
            return None

        ud = user_resp.json()
        # Primary/verified email
        email = ud.get("email") or ""
        if not email and email_resp.status_code == 200:
            for e in email_resp.json():
                if e.get("primary") and e.get("verified"):
                    email = e["email"]
                    break

        if not email:
            log.warning("GitHub OAuth: no verified email for user %s", ud.get("login"))
            email = f"{ud['login']}@users.noreply.github.com"

        return SocialUser(
            user_id=f"gh_{ud['id']}",
            email=email.lower(),
            name=ud.get("name") or ud.get("login") or email,
            avatar_url=ud.get("avatar_url", ""),
            provider="github",
        )


# ── Google OAuth ───────────────────────────────────────────────────────────────

async def _google_exchange_code(code: str) -> str | None:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id":     GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code":          code,
                "grant_type":    "authorization_code",
                "redirect_uri":  f"{OAUTH_REDIRECT_BASE}/api/auth/google/callback",
            },
        )
        if resp.status_code != 200:
            return None
        return resp.json().get("access_token")


async def _google_fetch_user(access_token: str) -> SocialUser | None:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if resp.status_code != 200:
            return None
        ud = resp.json()
        return SocialUser(
            user_id=f"goog_{ud['id']}",
            email=ud.get("email", "").lower(),
            name=ud.get("name", ud.get("email", "")),
            avatar_url=ud.get("picture", ""),
            provider="google",
        )


# ── FastAPI router ─────────────────────────────────────────────────────────────

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── GitHub login ───────────────────────────────────────────────────────────────

@auth_router.get("/github/login")
async def github_login():
    """Redirect user to GitHub OAuth consent screen."""
    if not GITHUB_CLIENT_ID:
        raise HTTPException(status_code=501, detail="GitHub OAuth not configured (GITHUB_CLIENT_ID missing).")
    state = _new_state()
    url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={OAUTH_REDIRECT_BASE}/api/auth/github/callback"
        f"&scope=user:email"
        f"&state={state}"
    )
    return RedirectResponse(url=url, status_code=302)


@auth_router.get("/github/callback")
async def github_callback(code: str, state: str, request: Request):
    """Handle GitHub OAuth callback."""
    if not _validate_state(state):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state.")

    token = await _github_exchange_code(code)
    if not token:
        raise HTTPException(status_code=400, detail="GitHub token exchange failed.")

    user_data = await _github_fetch_user(token)
    if not user_data:
        raise HTTPException(status_code=400, detail="Failed to fetch GitHub user profile.")

    user = _upsert_user(user_data)
    jwt  = _issue_jwt(user)
    audit("auth.github.login", user.as_dict(), outcome="success")

    # Redirect to frontend with JWT as query param (frontend stores in memory)
    return RedirectResponse(
        url=f"{FRONTEND_URL}/auth/callback?token={jwt}&provider=github",
        status_code=302,
    )


# ── Google login ───────────────────────────────────────────────────────────────

@auth_router.get("/google/login")
async def google_login():
    """Redirect user to Google OAuth consent screen."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Google OAuth not configured (GOOGLE_CLIENT_ID missing).")
    state = _new_state()
    url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={OAUTH_REDIRECT_BASE}/api/auth/google/callback"
        f"&response_type=code"
        f"&scope=openid+email+profile"
        f"&state={state}"
    )
    return RedirectResponse(url=url, status_code=302)


@auth_router.get("/google/callback")
async def google_callback(code: str, state: str, request: Request):
    """Handle Google OAuth callback."""
    if not _validate_state(state):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state.")

    token = await _google_exchange_code(code)
    if not token:
        raise HTTPException(status_code=400, detail="Google token exchange failed.")

    user_data = await _google_fetch_user(token)
    if not user_data:
        raise HTTPException(status_code=400, detail="Failed to fetch Google user profile.")

    user = _upsert_user(user_data)
    jwt  = _issue_jwt(user)
    audit("auth.google.login", user.as_dict(), outcome="success")

    return RedirectResponse(
        url=f"{FRONTEND_URL}/auth/callback?token={jwt}&provider=google",
        status_code=302,
    )


# ── Token verification endpoint ───────────────────────────────────────────────

@auth_router.get("/me")
async def get_current_user(request: Request):
    """Return the current user's profile from the JWT.  No raw secrets."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required.")
    token = auth_header[7:]
    claims = verify_jwt(token)
    if claims is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    user = get_user_by_id(claims["sub"])
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return user.as_dict()


@auth_router.get("/users")
async def list_users(request: Request):
    """Admin endpoint: list all users."""
    from rbac import require_admin
    require_admin(request)
    return {"users": [u.as_dict() for u in list_all_users()]}


@auth_router.post("/users/{user_id}/role")
async def change_user_role(user_id: str, request: Request):
    """Admin/Power User endpoint: change a user's role."""
    from rbac import get_user_role, is_power_user_or_above
    user = getattr(request.state, "user", None) or {}
    if not is_power_user_or_above(user):
        raise HTTPException(status_code=403, detail="Power User or Admin required.")

    body = await request.json()
    new_role = body.get("role", "")
    if new_role not in [r.value for r in UserRole]:
        raise HTTPException(status_code=400, detail=f"Invalid role: {new_role!r}")

    # Power users can only promote to power_user; only admin can set admin
    if new_role == UserRole.ADMIN.value and get_user_role(user) != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins may grant admin role.")

    ok = set_user_role(user_id, new_role, user)
    if not ok:
        raise HTTPException(status_code=404, detail=f"User {user_id!r} not found.")
    return {"user_id": user_id, "role": new_role, "updated": True}

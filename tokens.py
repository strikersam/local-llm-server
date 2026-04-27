"""JWT token generation and validation for v3 API."""
from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pydantic import BaseModel


class TokenPayload(BaseModel):
    """JWT token payload."""
    sub: str  # user ID
    email: str
    name: str
    role: str
    exp: datetime
    iat: datetime
    type: str  # "access" or "refresh"


class TokenPair(BaseModel):
    """Access and refresh token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


def _get_secret() -> str:
    """Get or create JWT secret from environment."""
    secret = os.environ.get("V3_JWT_SECRET")
    if not secret:
        # Auto-generate if not set (warn user)
        secret = secrets.token_urlsafe(32)
        import logging
        log = logging.getLogger("tokens")
        log.warning(
            f"V3_JWT_SECRET not set. Generated: {secret}. "
            "Add to .env to persist across restarts."
        )
    return secret


def create_tokens(user_id: str, email: str, name: str, role: str = "admin") -> TokenPair:
    """Create access and refresh token pair."""
    secret = _get_secret()
    now = datetime.now(timezone.utc)

    # Access token: 1 hour
    access_exp = now + timedelta(hours=1)
    access_payload = {
        "sub": user_id,
        "email": email,
        "name": name,
        "role": role,
        "type": "access",
        "iat": now.timestamp(),
        "exp": access_exp.timestamp(),
    }
    access_token = jwt.encode(access_payload, secret, algorithm="HS256")

    # Refresh token: 7 days
    refresh_exp = now + timedelta(days=7)
    refresh_payload = {
        "sub": user_id,
        "email": email,
        "type": "refresh",
        "iat": now.timestamp(),
        "exp": refresh_exp.timestamp(),
    }
    refresh_token = jwt.encode(refresh_payload, secret, algorithm="HS256")

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int((access_exp - now).total_seconds()),
    )


def verify_token(token: str, token_type: str = "access") -> dict[str, Any] | None:
    """Verify and decode JWT token. Returns payload if valid, None if invalid."""
    secret = _get_secret()
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        if payload.get("type") != token_type:
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def refresh_access_token(refresh_token: str) -> TokenPair | None:
    """Create new access token from valid refresh token."""
    payload = verify_token(refresh_token, token_type="refresh")
    if not payload:
        return None

    user_id = payload.get("sub")
    email = payload.get("email")
    name = payload.get("name", "User")
    role = payload.get("role", "user")

    if not user_id or not email:
        return None

    return create_tokens(user_id, email, name, role)

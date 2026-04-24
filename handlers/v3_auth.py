"""V3 API authentication endpoints (/api/auth/*)."""
from __future__ import annotations

import os
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from tokens import TokenPair, create_tokens, refresh_access_token, verify_token


router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Login request body."""
    email: str
    password: str


class LoginResponse(BaseModel):
    """Login response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    id: str
    email: str
    name: str
    role: str


class RefreshRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str


class UserResponse(BaseModel):
    """Current user info."""
    id: str
    email: str
    name: str
    role: str


def _get_admin_email() -> str:
    """Get admin email from environment."""
    return os.environ.get("V3_ADMIN_EMAIL", "admin@localhost")


def _get_admin_name() -> str:
    """Get admin name from environment."""
    return os.environ.get("V3_ADMIN_NAME", "Administrator")


def _get_admin_secret() -> str:
    """Get admin secret (password) from environment."""
    return os.environ.get("V3_ADMIN_PASSWORD") or os.environ.get("ADMIN_SECRET", "")


def _validate_credentials(email: str, password: str) -> bool:
    """Validate login credentials against admin secret."""
    admin_secret = _get_admin_secret()
    admin_email = _get_admin_email()

    # For now: email must match admin email, password must match ADMIN_SECRET
    # This is a single-user system initially; can be expanded to multiple users
    if not admin_secret:
        raise HTTPException(
            status_code=500,
            detail="ADMIN_SECRET not configured. Set it in .env file.",
        )

    return email == admin_email and password == admin_secret


def _get_bearer_token(authorization: str | None = Header(None)) -> str:
    """Extract bearer token from Authorization header."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    return authorization[7:].strip()


async def _get_current_user(
    token: Annotated[str, Depends(_get_bearer_token)],
) -> UserResponse:
    """Extract and validate current user from token."""
    payload = verify_token(token, token_type="access")
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return UserResponse(
        id=payload.get("sub", ""),
        email=payload.get("email", ""),
        name=payload.get("name", ""),
        role=payload.get("role", "user"),
    )


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest) -> LoginResponse:
    """Login with email and password.

    Returns access and refresh tokens.
    """
    if not _validate_credentials(req.email, req.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    admin_email = _get_admin_email()
    admin_name = _get_admin_name()
    user_id = "admin_user_001"

    tokens = create_tokens(user_id, admin_email, admin_name, role="admin")

    return LoginResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in,
        id=user_id,
        email=admin_email,
        name=admin_name,
        role="admin",
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(user: Annotated[UserResponse, Depends(_get_current_user)]) -> UserResponse:
    """Get current authenticated user."""
    return user


@router.post("/refresh", response_model=LoginResponse)
async def refresh(req: RefreshRequest) -> LoginResponse:
    """Refresh access token using refresh token."""
    tokens = refresh_access_token(req.refresh_token)
    if not tokens:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    payload = verify_token(req.refresh_token, token_type="refresh")
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    return LoginResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in,
        id=payload.get("sub", ""),
        email=payload.get("email", ""),
        name=payload.get("name", ""),
        role=payload.get("role", "user"),
    )


@router.post("/logout")
async def logout(user: Annotated[UserResponse, Depends(_get_current_user)]) -> dict:
    """Logout (token invalidation happens on frontend by clearing localStorage)."""
    # Tokens are stateless JWTs, so logout is just frontend clearing the token.
    # This endpoint exists for API completeness and potential audit logging.
    return {"status": "logged out", "email": user.email}

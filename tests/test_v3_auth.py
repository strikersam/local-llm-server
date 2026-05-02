"""Tests for v3 API authentication."""
from __future__ import annotations

import os
import pytest
from fastapi.testclient import TestClient

from tokens import create_tokens, verify_token, refresh_access_token


def _configured_v3_password() -> str:
    return (
        os.environ.get("V3_ADMIN_PASSWORD")
        or os.environ.get("ADMIN_PASSWORD")
        or os.environ.get("ADMIN_SECRET", "")
    )


def test_token_creation_and_verification():
    """Test JWT token creation and verification."""
    tokens = create_tokens("user123", "test@example.com", "Test User", "admin")

    assert tokens.access_token
    assert tokens.refresh_token
    assert tokens.token_type == "bearer"
    assert tokens.expires_in > 0

    # Verify access token
    payload = verify_token(tokens.access_token, token_type="access")
    assert payload
    assert payload["sub"] == "user123"
    assert payload["email"] == "test@example.com"
    assert payload["name"] == "Test User"
    assert payload["role"] == "admin"
    assert payload["type"] == "access"


def test_refresh_token_creation():
    """Test refresh token creation and validation."""
    tokens = create_tokens("user123", "test@example.com", "Test User")

    # Verify refresh token
    payload = verify_token(tokens.refresh_token, token_type="refresh")
    assert payload
    assert payload["sub"] == "user123"
    assert payload["email"] == "test@example.com"
    assert payload["type"] == "refresh"
    # Refresh tokens don't include name/role
    assert payload.get("name") is None


def test_invalid_token_type():
    """Test that access token fails with refresh validation."""
    tokens = create_tokens("user123", "test@example.com", "Test User")

    # Try to verify access token as refresh token (should fail)
    payload = verify_token(tokens.access_token, token_type="refresh")
    assert payload is None

    # Try to verify refresh token as access token (should fail)
    payload = verify_token(tokens.refresh_token, token_type="access")
    assert payload is None


def test_refresh_access_token():
    """Test refreshing access token with refresh token."""
    original_tokens = create_tokens("user123", "test@example.com", "Test User", "admin")

    new_tokens = refresh_access_token(original_tokens.refresh_token)
    assert new_tokens
    assert new_tokens.access_token != original_tokens.access_token
    # Note: new refresh token will be different due to new timestamps

    # Verify new access token
    payload = verify_token(new_tokens.access_token, token_type="access")
    assert payload["sub"] == "user123"
    assert payload["email"] == "test@example.com"


def test_invalid_refresh_token():
    """Test that invalid refresh tokens fail gracefully."""
    result = refresh_access_token("invalid_token")
    assert result is None

    result = refresh_access_token("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.invalid")
    assert result is None


@pytest.mark.asyncio
async def test_v3_auth_login_endpoint(client: TestClient):
    """Test login endpoint returns valid tokens."""
    admin_email = os.environ.get("V3_ADMIN_EMAIL", "admin@localhost")
    admin_secret = _configured_v3_password()

    if not admin_secret:
        pytest.skip("V3 admin password not configured")

    response = client.post(
        "/api/auth/login",
        json={"email": admin_email, "password": admin_secret},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["email"] == admin_email
    assert data["_id"]
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_v3_auth_login_invalid_credentials(client: TestClient):
    """Test login with invalid credentials."""
    response = client.post(
        "/api/auth/login",
        json={"email": "wrong@example.com", "password": "wrong_password"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_v3_auth_me_endpoint(client: TestClient):
    """Test getting current user with valid token."""
    admin_email = os.environ.get("V3_ADMIN_EMAIL", "admin@localhost")
    admin_secret = _configured_v3_password()

    if not admin_secret:
        pytest.skip("V3 admin password not configured")

    # First, login
    login_response = client.post(
        "/api/auth/login",
        json={"email": admin_email, "password": admin_secret},
    )
    assert login_response.status_code == 200
    tokens = login_response.json()
    access_token = tokens["access_token"]

    # Then, get current user
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == admin_email
    assert data["id"]
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_v3_auth_me_invalid_token(client: TestClient):
    """Test /me endpoint with invalid token."""
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid_token"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_v3_auth_me_missing_token(client: TestClient):
    """Test /me endpoint without token."""
    response = client.get("/api/auth/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_v3_auth_refresh_endpoint(client: TestClient):
    """Test refreshing access token."""
    admin_email = os.environ.get("V3_ADMIN_EMAIL", "admin@localhost")
    admin_secret = _configured_v3_password()

    if not admin_secret:
        pytest.skip("V3 admin password not configured")

    # Login
    login_response = client.post(
        "/api/auth/login",
        json={"email": admin_email, "password": admin_secret},
    )
    assert login_response.status_code == 200
    tokens = login_response.json()

    # Refresh
    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["access_token"] != tokens["access_token"]  # New token


@pytest.mark.asyncio
async def test_v3_auth_refresh_invalid_token(client: TestClient):
    """Test refresh with invalid refresh token."""
    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": "invalid_token"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_v3_auth_logout_endpoint(client: TestClient):
    """Test logout endpoint."""
    admin_email = os.environ.get("V3_ADMIN_EMAIL", "admin@localhost")
    admin_secret = _configured_v3_password()

    if not admin_secret:
        pytest.skip("V3 admin password not configured")

    # Login
    login_response = client.post(
        "/api/auth/login",
        json={"email": admin_email, "password": admin_secret},
    )
    assert login_response.status_code == 200
    tokens = login_response.json()

    # Logout
    response = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "logged out"
    assert data["email"] == admin_email

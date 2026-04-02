"""
Tests for authentication endpoints.
"""

import pytest
from httpx import AsyncClient

from tests.conftest import get_auth_headers


@pytest.mark.asyncio
class TestRegister:
    """Tests for POST /api/v1/auth/register."""

    async def test_register_success(self, client: AsyncClient):
        """A valid registration should return 201 with user data."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@test.com",
                "username": "newuser",
                "password": "securepassword123",
                "full_name": "New User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@test.com"
        assert data["username"] == "newuser"
        assert data["role"] == "viewer"  # Default role
        assert data["status"] == "active"
        assert "hashed_password" not in data  # Security: never expose

    async def test_register_duplicate_email(self, client: AsyncClient):
        """Registering with an existing email should return 409."""
        payload = {
            "email": "duplicate@test.com",
            "username": "user1",
            "password": "securepassword123",
        }
        await client.post("/api/v1/auth/register", json=payload)
        # Try again with same email
        response = await client.post(
            "/api/v1/auth/register",
            json={**payload, "username": "user2"},
        )
        assert response.status_code == 409

    async def test_register_duplicate_username(self, client: AsyncClient):
        """Registering with an existing username should return 409."""
        payload = {
            "email": "first@test.com",
            "username": "sameusername",
            "password": "securepassword123",
        }
        await client.post("/api/v1/auth/register", json=payload)
        response = await client.post(
            "/api/v1/auth/register",
            json={**payload, "email": "second@test.com"},
        )
        assert response.status_code == 409

    async def test_register_invalid_email(self, client: AsyncClient):
        """Invalid email format should return 422."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "username": "validuser",
                "password": "securepassword123",
            },
        )
        assert response.status_code == 422

    async def test_register_short_password(self, client: AsyncClient):
        """Password shorter than 8 characters should return 422."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "valid@test.com",
                "username": "validuser",
                "password": "short",
            },
        )
        assert response.status_code == 422

    async def test_register_invalid_username(self, client: AsyncClient):
        """Username with special characters should return 422."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "valid@test.com",
                "username": "invalid user!",
                "password": "securepassword123",
            },
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestLogin:
    """Tests for POST /api/v1/auth/login."""

    async def test_login_success(self, client: AsyncClient, admin_user):
        """Valid credentials should return access and refresh tokens."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.com", "password": "adminpassword123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient, admin_user):
        """Wrong password should return 401."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.com", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Login with non-existent email should return 401."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "noone@test.com", "password": "anypassword"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
class TestRefreshToken:
    """Tests for POST /api/v1/auth/refresh."""

    async def test_refresh_success(self, client: AsyncClient, admin_user):
        """Valid refresh token should return a new access token."""
        # First login
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.com", "password": "adminpassword123"},
        )
        tokens = login_resp.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        # Refresh
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    async def test_refresh_without_auth(self, client: AsyncClient):
        """Refresh without auth header should return 401."""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "fake-token"},
        )
        assert response.status_code == 401

"""
Tests for user management endpoints — focuses on RBAC enforcement.
"""

import pytest
from httpx import AsyncClient

from tests.conftest import get_auth_headers


@pytest.mark.asyncio
class TestGetMe:
    """Tests for GET /api/v1/users/me."""

    async def test_get_me_admin(self, client: AsyncClient, admin_user):
        """Admin should be able to get their own profile."""
        headers = await get_auth_headers(client, "admin@test.com", "adminpassword123")
        response = await client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "admin@test.com"
        assert data["role"] == "admin"

    async def test_get_me_viewer(self, client: AsyncClient, viewer_user):
        """Viewer should be able to get their own profile."""
        headers = await get_auth_headers(client, "viewer@test.com", "viewerpassword123")
        response = await client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 200
        assert response.json()["role"] == "viewer"

    async def test_get_me_unauthenticated(self, client: AsyncClient):
        """Unauthenticated request should return 401."""
        response = await client.get("/api/v1/users/me")
        assert response.status_code == 401


@pytest.mark.asyncio
class TestListUsers:
    """Tests for GET /api/v1/users — RBAC enforcement."""

    async def test_admin_can_list_users(self, client: AsyncClient, admin_user):
        """Admin should see user list."""
        headers = await get_auth_headers(client, "admin@test.com", "adminpassword123")
        response = await client.get("/api/v1/users", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "total" in data

    async def test_viewer_cannot_list_users(self, client: AsyncClient, viewer_user):
        """Viewer should be denied access."""
        headers = await get_auth_headers(client, "viewer@test.com", "viewerpassword123")
        response = await client.get("/api/v1/users", headers=headers)
        assert response.status_code == 403

    async def test_analyst_cannot_list_users(self, client: AsyncClient, analyst_user):
        """Analyst should be denied access."""
        headers = await get_auth_headers(client, "analyst@test.com", "analystpassword123")
        response = await client.get("/api/v1/users", headers=headers)
        assert response.status_code == 403


@pytest.mark.asyncio
class TestRoleAssignment:
    """Tests for PATCH /api/v1/users/{id}/role."""

    async def test_admin_can_assign_role(
        self, client: AsyncClient, admin_user, viewer_user
    ):
        """Admin should be able to change a user's role."""
        headers = await get_auth_headers(client, "admin@test.com", "adminpassword123")
        response = await client.patch(
            f"/api/v1/users/{viewer_user.id}/role",
            json={"role": "analyst"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["role"] == "analyst"

    async def test_viewer_cannot_assign_role(
        self, client: AsyncClient, viewer_user, admin_user
    ):
        """Viewer should be denied role assignment."""
        headers = await get_auth_headers(client, "viewer@test.com", "viewerpassword123")
        response = await client.patch(
            f"/api/v1/users/{admin_user.id}/role",
            json={"role": "viewer"},
            headers=headers,
        )
        assert response.status_code == 403


@pytest.mark.asyncio
class TestStatusUpdate:
    """Tests for PATCH /api/v1/users/{id}/status."""

    async def test_admin_can_deactivate_user(
        self, client: AsyncClient, admin_user, viewer_user
    ):
        """Admin should be able to deactivate a user."""
        headers = await get_auth_headers(client, "admin@test.com", "adminpassword123")
        response = await client.patch(
            f"/api/v1/users/{viewer_user.id}/status",
            json={"status": "inactive"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "inactive"

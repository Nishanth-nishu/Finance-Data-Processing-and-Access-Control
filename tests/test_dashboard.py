"""
Tests for dashboard analytics endpoints — RBAC and data correctness.
"""

import pytest
from httpx import AsyncClient

from tests.conftest import get_auth_headers


@pytest.mark.asyncio
class TestDashboardSummary:
    """Tests for GET /api/v1/dashboard/summary."""

    async def test_admin_can_access_summary(self, client: AsyncClient, admin_user):
        """Admin should access dashboard summary."""
        headers = await get_auth_headers(client, "admin@test.com", "adminpassword123")

        # Create test records
        await client.post(
            "/api/v1/records",
            json={
                "amount": 5000.00,
                "type": "income",
                "category": "salary",
                "record_date": "2026-03-01",
            },
            headers=headers,
        )
        await client.post(
            "/api/v1/records",
            json={
                "amount": 200.00,
                "type": "expense",
                "category": "food",
                "record_date": "2026-03-05",
            },
            headers=headers,
        )

        response = await client.get("/api/v1/dashboard/summary", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_income"] == 5000.00
        assert data["total_expenses"] == 200.00
        assert data["net_balance"] == 4800.00

    async def test_analyst_can_access_summary(self, client: AsyncClient, analyst_user):
        """Analyst should access dashboard summary."""
        headers = await get_auth_headers(client, "analyst@test.com", "analystpassword123")
        response = await client.get("/api/v1/dashboard/summary", headers=headers)
        assert response.status_code == 200

    async def test_viewer_cannot_access_summary(self, client: AsyncClient, viewer_user):
        """Viewer should be denied access to summary."""
        headers = await get_auth_headers(client, "viewer@test.com", "viewerpassword123")
        response = await client.get("/api/v1/dashboard/summary", headers=headers)
        assert response.status_code == 403


@pytest.mark.asyncio
class TestCategoryBreakdown:
    """Tests for GET /api/v1/dashboard/categories."""

    async def test_admin_can_access_categories(self, client: AsyncClient, admin_user):
        """Admin should access category breakdown."""
        headers = await get_auth_headers(client, "admin@test.com", "adminpassword123")
        response = await client.get("/api/v1/dashboard/categories", headers=headers)
        assert response.status_code == 200
        assert "categories" in response.json()

    async def test_viewer_cannot_access_categories(
        self, client: AsyncClient, viewer_user
    ):
        """Viewer should be denied category breakdown."""
        headers = await get_auth_headers(client, "viewer@test.com", "viewerpassword123")
        response = await client.get("/api/v1/dashboard/categories", headers=headers)
        assert response.status_code == 403


@pytest.mark.asyncio
class TestRecentActivity:
    """Tests for GET /api/v1/dashboard/recent."""

    async def test_viewer_can_access_recent(self, client: AsyncClient, viewer_user):
        """Viewer should access recent activity."""
        headers = await get_auth_headers(client, "viewer@test.com", "viewerpassword123")
        response = await client.get("/api/v1/dashboard/recent", headers=headers)
        assert response.status_code == 200
        assert "records" in response.json()

    async def test_admin_can_access_recent(self, client: AsyncClient, admin_user):
        """Admin should access recent activity."""
        headers = await get_auth_headers(client, "admin@test.com", "adminpassword123")
        response = await client.get("/api/v1/dashboard/recent", headers=headers)
        assert response.status_code == 200


@pytest.mark.asyncio
class TestMonthlyTrends:
    """Tests for GET /api/v1/dashboard/trends."""

    async def test_analyst_can_access_trends(self, client: AsyncClient, analyst_user):
        """Analyst should access monthly trends."""
        headers = await get_auth_headers(client, "analyst@test.com", "analystpassword123")
        response = await client.get("/api/v1/dashboard/trends", headers=headers)
        assert response.status_code == 200
        assert "trends" in response.json()

    async def test_viewer_cannot_access_trends(self, client: AsyncClient, viewer_user):
        """Viewer should be denied trends access."""
        headers = await get_auth_headers(client, "viewer@test.com", "viewerpassword123")
        response = await client.get("/api/v1/dashboard/trends", headers=headers)
        assert response.status_code == 403

    async def test_unauthenticated_cannot_access_trends(self, client: AsyncClient):
        """Unauthenticated should return 401."""
        response = await client.get("/api/v1/dashboard/trends")
        assert response.status_code == 401

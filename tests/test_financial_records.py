"""
Tests for financial records endpoints — CRUD, filtering, and RBAC.
"""

import pytest
from httpx import AsyncClient

from tests.conftest import get_auth_headers


@pytest.mark.asyncio
class TestCreateRecord:
    """Tests for POST /api/v1/records."""

    async def test_admin_can_create_record(self, client: AsyncClient, admin_user):
        """Admin should be able to create financial records."""
        headers = await get_auth_headers(client, "admin@test.com", "adminpassword123")
        response = await client.post(
            "/api/v1/records",
            json={
                "amount": 5000.00,
                "type": "income",
                "category": "salary",
                "record_date": "2026-03-15",
                "description": "Monthly salary",
            },
            headers=headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["amount"] == 5000.00
        assert data["type"] == "income"
        assert data["category"] == "salary"

    async def test_viewer_cannot_create_record(self, client: AsyncClient, viewer_user):
        """Viewer should be denied record creation."""
        headers = await get_auth_headers(client, "viewer@test.com", "viewerpassword123")
        response = await client.post(
            "/api/v1/records",
            json={
                "amount": 100.00,
                "type": "expense",
                "category": "food",
                "record_date": "2026-03-15",
            },
            headers=headers,
        )
        assert response.status_code == 403

    async def test_analyst_cannot_create_record(self, client: AsyncClient, analyst_user):
        """Analyst should be denied record creation."""
        headers = await get_auth_headers(client, "analyst@test.com", "analystpassword123")
        response = await client.post(
            "/api/v1/records",
            json={
                "amount": 100.00,
                "type": "expense",
                "category": "food",
                "record_date": "2026-03-15",
            },
            headers=headers,
        )
        assert response.status_code == 403

    async def test_invalid_amount_rejected(self, client: AsyncClient, admin_user):
        """Negative or zero amount should return 422."""
        headers = await get_auth_headers(client, "admin@test.com", "adminpassword123")
        response = await client.post(
            "/api/v1/records",
            json={
                "amount": -100.00,
                "type": "expense",
                "category": "food",
                "record_date": "2026-03-15",
            },
            headers=headers,
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestListRecords:
    """Tests for GET /api/v1/records."""

    async def test_viewer_can_list_records(self, client: AsyncClient, viewer_user):
        """Viewer should be able to view records."""
        headers = await get_auth_headers(client, "viewer@test.com", "viewerpassword123")
        response = await client.get("/api/v1/records", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "records" in data
        assert "total" in data
        assert "page" in data
        assert "has_next" in data

    async def test_filtering_by_type(self, client: AsyncClient, admin_user):
        """Should be able to filter records by type."""
        headers = await get_auth_headers(client, "admin@test.com", "adminpassword123")

        # Create records
        await client.post(
            "/api/v1/records",
            json={
                "amount": 5000.00,
                "type": "income",
                "category": "salary",
                "record_date": "2026-03-15",
            },
            headers=headers,
        )
        await client.post(
            "/api/v1/records",
            json={
                "amount": 200.00,
                "type": "expense",
                "category": "food",
                "record_date": "2026-03-15",
            },
            headers=headers,
        )

        # Filter by income
        response = await client.get(
            "/api/v1/records?type=income", headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        for record in data["records"]:
            assert record["type"] == "income"

    async def test_unauthenticated_cannot_list(self, client: AsyncClient):
        """Unauthenticated should return 401."""
        response = await client.get("/api/v1/records")
        assert response.status_code == 401


@pytest.mark.asyncio
class TestUpdateRecord:
    """Tests for PUT /api/v1/records/{id}."""

    async def test_admin_can_update_record(self, client: AsyncClient, admin_user):
        """Admin should be able to update records."""
        headers = await get_auth_headers(client, "admin@test.com", "adminpassword123")

        # Create a record
        create_resp = await client.post(
            "/api/v1/records",
            json={
                "amount": 100.00,
                "type": "expense",
                "category": "food",
                "record_date": "2026-03-15",
            },
            headers=headers,
        )
        record_id = create_resp.json()["id"]

        # Update it
        response = await client.put(
            f"/api/v1/records/{record_id}",
            json={"amount": 150.00, "description": "Updated"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["amount"] == 150.00

    async def test_viewer_cannot_update_record(
        self, client: AsyncClient, admin_user, viewer_user
    ):
        """Viewer should be denied record updates."""
        admin_headers = await get_auth_headers(
            client, "admin@test.com", "adminpassword123"
        )
        viewer_headers = await get_auth_headers(
            client, "viewer@test.com", "viewerpassword123"
        )

        # Create as admin
        create_resp = await client.post(
            "/api/v1/records",
            json={
                "amount": 100.00,
                "type": "expense",
                "category": "food",
                "record_date": "2026-03-15",
            },
            headers=admin_headers,
        )
        record_id = create_resp.json()["id"]

        # Try to update as viewer
        response = await client.put(
            f"/api/v1/records/{record_id}",
            json={"amount": 999.00},
            headers=viewer_headers,
        )
        assert response.status_code == 403


@pytest.mark.asyncio
class TestDeleteRecord:
    """Tests for DELETE /api/v1/records/{id}."""

    async def test_admin_can_delete_record(self, client: AsyncClient, admin_user):
        """Admin should be able to soft-delete records."""
        headers = await get_auth_headers(client, "admin@test.com", "adminpassword123")

        # Create
        create_resp = await client.post(
            "/api/v1/records",
            json={
                "amount": 50.00,
                "type": "expense",
                "category": "utilities",
                "record_date": "2026-03-15",
            },
            headers=headers,
        )
        record_id = create_resp.json()["id"]

        # Delete
        response = await client.delete(
            f"/api/v1/records/{record_id}", headers=headers
        )
        assert response.status_code == 204

        # Verify it's gone from listings
        get_resp = await client.get(
            f"/api/v1/records/{record_id}", headers=headers
        )
        assert get_resp.status_code == 404

    async def test_delete_nonexistent_record(self, client: AsyncClient, admin_user):
        """Deleting a non-existent record should return 404."""
        headers = await get_auth_headers(client, "admin@test.com", "adminpassword123")
        response = await client.delete(
            "/api/v1/records/99999", headers=headers
        )
        assert response.status_code == 404

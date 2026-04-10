"""
Deep cross-validation tests — verifies data integrity, edge cases,
end-to-end flows, and inter-module consistency.

These go beyond basic CRUD/RBAC to validate the system holistically:
- Data integrity across create → read → update → delete lifecycle
- Dashboard accuracy after mutations
- Token security and expiration behavior
- Soft delete integrity (deleted records excluded from analytics)
- Pagination correctness
- Concurrent role changes and their effects
- Error response structure consistency
- Input boundary validation
"""

import pytest
from httpx import AsyncClient

from tests.conftest import get_auth_headers


# ============================================================
# 1. END-TO-END DATA LIFECYCLE
# ============================================================

class TestE2ERecordLifecycle:
    """Validates the full lifecycle: create → read → update → verify → delete → verify."""

    async def test_full_record_lifecycle(self, client: AsyncClient, admin_user):
        """A record should maintain integrity through create → read → update → delete."""
        headers = await get_auth_headers(client, "admin@test.com", "adminpassword123")

        # CREATE
        create_resp = await client.post(
            "/api/v1/records",
            json={
                "amount": 1500.75,
                "type": "income",
                "category": "Freelance",
                "record_date": "2026-03-10",
                "description": "Client project payment",
            },
            headers=headers,
        )
        assert create_resp.status_code == 201
        record = create_resp.json()
        record_id = record["id"]
        assert record["amount"] == 1500.75
        assert record["category"] == "freelance"  # Should be lowercased
        assert record["description"] == "Client project payment"

        # READ — verify same data comes back
        read_resp = await client.get(f"/api/v1/records/{record_id}", headers=headers)
        assert read_resp.status_code == 200
        assert read_resp.json() == record  # Exact match

        # UPDATE
        update_resp = await client.put(
            f"/api/v1/records/{record_id}",
            json={"amount": 2000.00, "description": "Updated payment"},
            headers=headers,
        )
        assert update_resp.status_code == 200
        updated = update_resp.json()
        assert updated["amount"] == 2000.00
        assert updated["description"] == "Updated payment"
        assert updated["type"] == "income"  # Unchanged fields preserved
        assert updated["category"] == "freelance"  # Unchanged

        # VERIFY — re-read to confirm persistence
        verify_resp = await client.get(f"/api/v1/records/{record_id}", headers=headers)
        assert verify_resp.json()["amount"] == 2000.00

        # DELETE (soft)
        del_resp = await client.delete(f"/api/v1/records/{record_id}", headers=headers)
        assert del_resp.status_code == 204

        # VERIFY DELETION — record should be gone from listings
        gone_resp = await client.get(f"/api/v1/records/{record_id}", headers=headers)
        assert gone_resp.status_code == 404

        # VERIFY — record excluded from list
        list_resp = await client.get("/api/v1/records", headers=headers)
        ids = [r["id"] for r in list_resp.json()["records"]]
        assert record_id not in ids


# ============================================================
# 2. DASHBOARD ACCURACY AFTER MUTATIONS
# ============================================================

class TestDashboardDataIntegrity:
    """Validates dashboard analytics reflect actual record state."""

    async def test_summary_accuracy_with_records(self, client: AsyncClient, admin_user):
        """Dashboard summary must match actual income/expense totals."""
        headers = await get_auth_headers(client, "admin@test.com", "adminpassword123")

        # Create known records
        records_to_create = [
            {"amount": 5000.00, "type": "income", "category": "salary", "record_date": "2026-03-01"},
            {"amount": 2000.00, "type": "income", "category": "freelance", "record_date": "2026-03-05"},
            {"amount": 500.00, "type": "expense", "category": "food", "record_date": "2026-03-03"},
            {"amount": 1200.00, "type": "expense", "category": "rent", "record_date": "2026-03-01"},
            {"amount": 300.00, "type": "expense", "category": "transport", "record_date": "2026-03-10"},
        ]
        for rec in records_to_create:
            resp = await client.post("/api/v1/records", json=rec, headers=headers)
            assert resp.status_code == 201

        # Verify summary
        summary_resp = await client.get("/api/v1/dashboard/summary", headers=headers)
        summary = summary_resp.json()
        assert summary["total_income"] == 7000.00  # 5000 + 2000
        assert summary["total_expenses"] == 2000.00  # 500 + 1200 + 300
        assert summary["net_balance"] == 5000.00  # 7000 - 2000
        assert summary["total_records"] == 5

    async def test_summary_after_soft_delete(self, client: AsyncClient, admin_user):
        """Soft-deleted records must be excluded from dashboard totals."""
        headers = await get_auth_headers(client, "admin@test.com", "adminpassword123")

        # Create records
        r1 = await client.post(
            "/api/v1/records",
            json={"amount": 1000.00, "type": "income", "category": "salary", "record_date": "2026-04-01"},
            headers=headers,
        )
        r2 = await client.post(
            "/api/v1/records",
            json={"amount": 500.00, "type": "income", "category": "bonus", "record_date": "2026-04-01"},
            headers=headers,
        )
        assert r1.status_code == 201
        assert r2.status_code == 201

        # Verify initial summary
        summary = (await client.get("/api/v1/dashboard/summary", headers=headers)).json()
        assert summary["total_income"] == 1500.00

        # Delete one record
        await client.delete(f"/api/v1/records/{r2.json()['id']}", headers=headers)

        # Verify updated summary
        summary = (await client.get("/api/v1/dashboard/summary", headers=headers)).json()
        assert summary["total_income"] == 1000.00  # Only r1 remains

    async def test_category_breakdown_correctness(self, client: AsyncClient, admin_user):
        """Category breakdown must group and sum correctly."""
        headers = await get_auth_headers(client, "admin@test.com", "adminpassword123")

        await client.post(
            "/api/v1/records",
            json={"amount": 200, "type": "expense", "category": "food", "record_date": "2026-03-01"},
            headers=headers,
        )
        await client.post(
            "/api/v1/records",
            json={"amount": 150, "type": "expense", "category": "food", "record_date": "2026-03-02"},
            headers=headers,
        )
        await client.post(
            "/api/v1/records",
            json={"amount": 100, "type": "expense", "category": "transport", "record_date": "2026-03-03"},
            headers=headers,
        )

        cat_resp = await client.get("/api/v1/dashboard/categories", headers=headers)
        categories = cat_resp.json()["categories"]

        food_cat = next((c for c in categories if c["category"] == "food"), None)
        transport_cat = next((c for c in categories if c["category"] == "transport"), None)

        assert food_cat is not None
        assert food_cat["total"] == 350.00  # 200 + 150
        assert food_cat["count"] == 2
        assert transport_cat is not None
        assert transport_cat["total"] == 100.00
        assert transport_cat["count"] == 1

    async def test_recent_activity_order(self, client: AsyncClient, admin_user):
        """Recent activity must be ordered by date descending."""
        headers = await get_auth_headers(client, "admin@test.com", "adminpassword123")

        dates = ["2026-01-15", "2026-03-20", "2026-02-10"]
        for d in dates:
            await client.post(
                "/api/v1/records",
                json={"amount": 100, "type": "expense", "category": "misc", "record_date": d},
                headers=headers,
            )

        recent = (await client.get("/api/v1/dashboard/recent", headers=headers)).json()
        record_dates = [r["record_date"] for r in recent["records"]]
        assert record_dates == sorted(record_dates, reverse=True)


# ============================================================
# 3. PAGINATION CORRECTNESS
# ============================================================

class TestPaginationIntegrity:
    """Validates pagination metadata and behavior."""

    async def test_pagination_metadata(self, client: AsyncClient, admin_user):
        """Pagination metadata (total, has_next, has_previous) must be accurate."""
        headers = await get_auth_headers(client, "admin@test.com", "adminpassword123")

        # Create 5 records
        for i in range(5):
            await client.post(
                "/api/v1/records",
                json={"amount": 100 + i, "type": "income", "category": "test", "record_date": f"2026-03-{10+i:02d}"},
                headers=headers,
            )

        # Page 1 of 2 (page_size=3)
        page1 = (await client.get("/api/v1/records?page=1&page_size=3", headers=headers)).json()
        assert page1["total"] == 5
        assert page1["page"] == 1
        assert page1["page_size"] == 3
        assert len(page1["records"]) == 3
        assert page1["has_next"] is True
        assert page1["has_previous"] is False

        # Page 2 of 2
        page2 = (await client.get("/api/v1/records?page=2&page_size=3", headers=headers)).json()
        assert page2["total"] == 5
        assert page2["page"] == 2
        assert len(page2["records"]) == 2
        assert page2["has_next"] is False
        assert page2["has_previous"] is True

    async def test_no_duplicate_records_across_pages(self, client: AsyncClient, admin_user):
        """Records should not appear on multiple pages."""
        headers = await get_auth_headers(client, "admin@test.com", "adminpassword123")

        for i in range(6):
            await client.post(
                "/api/v1/records",
                json={"amount": 100, "type": "expense", "category": f"cat{i}", "record_date": f"2026-03-{10+i:02d}"},
                headers=headers,
            )

        page1_ids = {r["id"] for r in (await client.get("/api/v1/records?page=1&page_size=3", headers=headers)).json()["records"]}
        page2_ids = {r["id"] for r in (await client.get("/api/v1/records?page=2&page_size=3", headers=headers)).json()["records"]}

        assert len(page1_ids & page2_ids) == 0, "Records duplicated across pages"
        assert len(page1_ids | page2_ids) == 6


# ============================================================
# 4. TOKEN SECURITY
# ============================================================

class TestTokenSecurity:
    """Validates JWT token behavior and security boundaries."""

    async def test_access_token_cannot_be_used_as_refresh(
        self, client: AsyncClient, admin_user
    ):
        """Using an access token as a refresh token should fail."""
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.com", "password": "adminpassword123"},
        )
        tokens = login_resp.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        # Try using access token as refresh
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["access_token"]},
            headers=headers,
        )
        assert resp.status_code == 401

    async def test_expired_or_invalid_token_rejected(self, client: AsyncClient):
        """A garbage token should get 401."""
        headers = {"Authorization": "Bearer this.is.not.a.valid.jwt"}
        resp = await client.get("/api/v1/users/me", headers=headers)
        assert resp.status_code == 401

    async def test_empty_bearer_rejected(self, client: AsyncClient):
        """Empty bearer token should get 401."""
        headers = {"Authorization": "Bearer "}
        resp = await client.get("/api/v1/users/me", headers=headers)
        assert resp.status_code == 401


# ============================================================
# 5. ERROR RESPONSE CONSISTENCY
# ============================================================

class TestErrorResponseStructure:
    """Validates all error responses follow the same JSON structure."""

    async def test_401_structure(self, client: AsyncClient):
        """Authentication errors must have consistent structure."""
        resp = await client.get("/api/v1/users/me")
        assert resp.status_code == 401
        body = resp.json()
        assert "error" in body
        assert "message" in body["error"]
        assert "type" in body["error"]

    async def test_403_structure(self, client: AsyncClient, viewer_user):
        """Authorization errors must have consistent structure."""
        headers = await get_auth_headers(client, "viewer@test.com", "viewerpassword123")
        resp = await client.get("/api/v1/users", headers=headers)
        assert resp.status_code == 403
        body = resp.json()
        assert "error" in body
        assert "message" in body["error"]
        assert body["error"]["type"] == "AuthorizationError"

    async def test_404_structure(self, client: AsyncClient, admin_user):
        """Not found errors must have consistent structure."""
        headers = await get_auth_headers(client, "admin@test.com", "adminpassword123")
        resp = await client.get("/api/v1/records/99999", headers=headers)
        assert resp.status_code == 404
        body = resp.json()
        assert "error" in body
        assert body["error"]["type"] == "EntityNotFoundError"

    async def test_409_structure(self, client: AsyncClient):
        """Duplicate entity errors must have consistent structure."""
        payload = {
            "email": "dup@test.com",
            "username": "dupuser",
            "password": "securepassword123",
        }
        await client.post("/api/v1/auth/register", json=payload)
        resp = await client.post("/api/v1/auth/register", json={**payload, "username": "other"})
        assert resp.status_code == 409
        body = resp.json()
        assert body["error"]["type"] == "DuplicateEntityError"

    async def test_422_pydantic_validation(self, client: AsyncClient, admin_user):
        """Pydantic validation errors should return 422."""
        headers = await get_auth_headers(client, "admin@test.com", "adminpassword123")
        resp = await client.post(
            "/api/v1/records",
            json={"amount": -10, "type": "invalid_type", "category": "", "record_date": "not-a-date"},
            headers=headers,
        )
        assert resp.status_code == 422


# ============================================================
# 6. RBAC CROSS-VALIDATION (FULL MATRIX)
# ============================================================

class TestFullRBACMatrix:
    """Exhaustively validates every endpoint against every role."""

    async def _create_test_record(self, client, headers):
        resp = await client.post(
            "/api/v1/records",
            json={"amount": 100, "type": "expense", "category": "test", "record_date": "2026-03-15"},
            headers=headers,
        )
        return resp.json()["id"] if resp.status_code == 201 else None

    async def test_viewer_full_restriction_matrix(
        self, client: AsyncClient, admin_user, viewer_user
    ):
        """Viewer: allowed ONLY record_view, recent_activity, and own profile."""
        admin_h = await get_auth_headers(client, "admin@test.com", "adminpassword123")
        viewer_h = await get_auth_headers(client, "viewer@test.com", "viewerpassword123")
        record_id = await self._create_test_record(client, admin_h)

        # ✅ ALLOWED
        assert (await client.get("/api/v1/users/me", headers=viewer_h)).status_code == 200
        assert (await client.get("/api/v1/records", headers=viewer_h)).status_code == 200
        assert (await client.get(f"/api/v1/records/{record_id}", headers=viewer_h)).status_code == 200
        assert (await client.get("/api/v1/dashboard/recent", headers=viewer_h)).status_code == 200

        # ❌ DENIED
        assert (await client.get("/api/v1/users", headers=viewer_h)).status_code == 403
        assert (await client.get("/api/v1/dashboard/summary", headers=viewer_h)).status_code == 403
        assert (await client.get("/api/v1/dashboard/trends", headers=viewer_h)).status_code == 403
        assert (await client.get("/api/v1/dashboard/categories", headers=viewer_h)).status_code == 403
        assert (await client.post("/api/v1/records", json={"amount": 1, "type": "income", "category": "x", "record_date": "2026-01-01"}, headers=viewer_h)).status_code == 403
        assert (await client.put(f"/api/v1/records/{record_id}", json={"amount": 999}, headers=viewer_h)).status_code == 403
        assert (await client.delete(f"/api/v1/records/{record_id}", headers=viewer_h)).status_code == 403

    async def test_analyst_full_restriction_matrix(
        self, client: AsyncClient, admin_user, analyst_user
    ):
        """Analyst: allowed record_view, all dashboard, but NOT record mutations or user management."""
        admin_h = await get_auth_headers(client, "admin@test.com", "adminpassword123")
        analyst_h = await get_auth_headers(client, "analyst@test.com", "analystpassword123")
        record_id = await self._create_test_record(client, admin_h)

        # ✅ ALLOWED
        assert (await client.get("/api/v1/users/me", headers=analyst_h)).status_code == 200
        assert (await client.get("/api/v1/records", headers=analyst_h)).status_code == 200
        assert (await client.get(f"/api/v1/records/{record_id}", headers=analyst_h)).status_code == 200
        assert (await client.get("/api/v1/dashboard/summary", headers=analyst_h)).status_code == 200
        assert (await client.get("/api/v1/dashboard/categories", headers=analyst_h)).status_code == 200
        assert (await client.get("/api/v1/dashboard/recent", headers=analyst_h)).status_code == 200
        assert (await client.get("/api/v1/dashboard/trends", headers=analyst_h)).status_code == 200

        # ❌ DENIED
        assert (await client.get("/api/v1/users", headers=analyst_h)).status_code == 403
        assert (await client.post("/api/v1/records", json={"amount": 1, "type": "income", "category": "x", "record_date": "2026-01-01"}, headers=analyst_h)).status_code == 403
        assert (await client.put(f"/api/v1/records/{record_id}", json={"amount": 999}, headers=analyst_h)).status_code == 403
        assert (await client.delete(f"/api/v1/records/{record_id}", headers=analyst_h)).status_code == 403

    async def test_admin_full_access(self, client: AsyncClient, admin_user, viewer_user):
        """Admin: full access to everything."""
        admin_h = await get_auth_headers(client, "admin@test.com", "adminpassword123")
        record_id = await self._create_test_record(client, admin_h)

        assert (await client.get("/api/v1/users/me", headers=admin_h)).status_code == 200
        assert (await client.get("/api/v1/users", headers=admin_h)).status_code == 200
        assert (await client.get(f"/api/v1/users/{viewer_user.id}", headers=admin_h)).status_code == 200
        assert (await client.get("/api/v1/records", headers=admin_h)).status_code == 200
        assert (await client.get(f"/api/v1/records/{record_id}", headers=admin_h)).status_code == 200
        assert (await client.put(f"/api/v1/records/{record_id}", json={"amount": 999}, headers=admin_h)).status_code == 200
        assert (await client.get("/api/v1/dashboard/summary", headers=admin_h)).status_code == 200
        assert (await client.get("/api/v1/dashboard/categories", headers=admin_h)).status_code == 200
        assert (await client.get("/api/v1/dashboard/recent", headers=admin_h)).status_code == 200
        assert (await client.get("/api/v1/dashboard/trends", headers=admin_h)).status_code == 200
        assert (await client.delete(f"/api/v1/records/{record_id}", headers=admin_h)).status_code == 204


# ============================================================
# 7. USER MANAGEMENT EDGE CASES
# ============================================================

class TestUserManagementEdgeCases:
    """Validates edge cases in user management."""

    async def test_role_change_reflected_in_next_login(
        self, client: AsyncClient, admin_user, viewer_user
    ):
        """After role change, new tokens should reflect the updated role."""
        admin_h = await get_auth_headers(client, "admin@test.com", "adminpassword123")

        # Promote viewer to analyst
        resp = await client.patch(
            f"/api/v1/users/{viewer_user.id}/role",
            json={"role": "analyst"},
            headers=admin_h,
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "analyst"

        # Login again as the promoted user — verify new role in token
        new_headers = await get_auth_headers(client, "viewer@test.com", "viewerpassword123")

        # Now should access analyst-level endpoints
        summary_resp = await client.get("/api/v1/dashboard/summary", headers=new_headers)
        assert summary_resp.status_code == 200

    async def test_deactivated_user_cannot_login(
        self, client: AsyncClient, admin_user, viewer_user
    ):
        """A deactivated user should get 403 on login."""
        admin_h = await get_auth_headers(client, "admin@test.com", "adminpassword123")

        # Deactivate
        await client.patch(
            f"/api/v1/users/{viewer_user.id}/status",
            json={"status": "inactive"},
            headers=admin_h,
        )

        # Try to login
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "viewer@test.com", "password": "viewerpassword123"},
        )
        assert login_resp.status_code == 403

    async def test_get_nonexistent_user_returns_404(self, client: AsyncClient, admin_user):
        """Getting a non-existent user should return 404."""
        headers = await get_auth_headers(client, "admin@test.com", "adminpassword123")
        resp = await client.get("/api/v1/users/99999", headers=headers)
        assert resp.status_code == 404


# ============================================================
# 8. INPUT BOUNDARY VALIDATION
# ============================================================

class TestInputBoundaryValidation:
    """Tests edge cases in input validation."""

    async def test_empty_body_on_required_fields(self, client: AsyncClient, admin_user):
        """Empty body on record creation should return 422."""
        headers = await get_auth_headers(client, "admin@test.com", "adminpassword123")
        resp = await client.post("/api/v1/records", json={}, headers=headers)
        assert resp.status_code == 422

    async def test_register_missing_required_fields(self, client: AsyncClient):
        """Register with missing fields should return 422."""
        resp = await client.post("/api/v1/auth/register", json={"email": "a@b.com"})
        assert resp.status_code == 422

    async def test_very_long_description_accepted(self, client: AsyncClient, admin_user):
        """Description up to 500 chars should be accepted."""
        headers = await get_auth_headers(client, "admin@test.com", "adminpassword123")
        resp = await client.post(
            "/api/v1/records",
            json={
                "amount": 100,
                "type": "expense",
                "category": "test",
                "record_date": "2026-03-01",
                "description": "a" * 500,
            },
            headers=headers,
        )
        assert resp.status_code == 201

    async def test_description_over_limit_rejected(self, client: AsyncClient, admin_user):
        """Description over 500 chars should return 422."""
        headers = await get_auth_headers(client, "admin@test.com", "adminpassword123")
        resp = await client.post(
            "/api/v1/records",
            json={
                "amount": 100,
                "type": "expense",
                "category": "test",
                "record_date": "2026-03-01",
                "description": "a" * 501,
            },
            headers=headers,
        )
        assert resp.status_code == 422

    async def test_page_size_boundary(self, client: AsyncClient, admin_user):
        """page_size above max (100) should return 422."""
        headers = await get_auth_headers(client, "admin@test.com", "adminpassword123")
        resp = await client.get("/api/v1/records?page_size=101", headers=headers)
        assert resp.status_code == 422

    async def test_page_zero_rejected(self, client: AsyncClient, admin_user):
        """Page 0 should return 422 (pages are 1-indexed)."""
        headers = await get_auth_headers(client, "admin@test.com", "adminpassword123")
        resp = await client.get("/api/v1/records?page=0", headers=headers)
        assert resp.status_code == 422


# ============================================================
# 9. FILTER CROSS-VALIDATION
# ============================================================

class TestFilterCrossValidation:
    """Validates that filters return correct subsets of data."""

    async def test_date_range_filter(self, client: AsyncClient, admin_user):
        """Date range filter should return only records within bounds."""
        headers = await get_auth_headers(client, "admin@test.com", "adminpassword123")

        for d in ["2026-01-15", "2026-02-15", "2026-03-15", "2026-04-15"]:
            await client.post(
                "/api/v1/records",
                json={"amount": 100, "type": "income", "category": "salary", "record_date": d},
                headers=headers,
            )

        resp = await client.get(
            "/api/v1/records?date_from=2026-02-01&date_to=2026-03-31",
            headers=headers,
        )
        records = resp.json()["records"]
        assert len(records) == 2
        for r in records:
            assert "2026-02" <= r["record_date"] <= "2026-03-31"

    async def test_combined_filters(self, client: AsyncClient, admin_user):
        """Multiple filters should combine (AND logic)."""
        headers = await get_auth_headers(client, "admin@test.com", "adminpassword123")

        await client.post("/api/v1/records", json={"amount": 100, "type": "income", "category": "salary", "record_date": "2026-03-01"}, headers=headers)
        await client.post("/api/v1/records", json={"amount": 100, "type": "expense", "category": "salary", "record_date": "2026-03-01"}, headers=headers)
        await client.post("/api/v1/records", json={"amount": 100, "type": "income", "category": "food", "record_date": "2026-03-01"}, headers=headers)

        resp = await client.get(
            "/api/v1/records?type=income&category=salary",
            headers=headers,
        )
        records = resp.json()["records"]
        assert len(records) == 1
        assert records[0]["type"] == "income"
        assert records[0]["category"] == "salary"

    async def test_search_filter_in_description(self, client: AsyncClient, admin_user):
        """Search filter should match against description field."""
        headers = await get_auth_headers(client, "admin@test.com", "adminpassword123")

        await client.post("/api/v1/records", json={"amount": 100, "type": "income", "category": "test", "record_date": "2026-03-01", "description": "Monthly salary payment"}, headers=headers)
        await client.post("/api/v1/records", json={"amount": 50, "type": "expense", "category": "test", "record_date": "2026-03-01", "description": "Coffee at cafe"}, headers=headers)

        resp = await client.get("/api/v1/records?search=salary", headers=headers)
        records = resp.json()["records"]
        assert len(records) == 1
        assert "salary" in records[0]["description"].lower()


# ============================================================
# 10. HEALTH & ROOT ENDPOINTS
# ============================================================

class TestHealthEndpoints:
    """Validates health and root endpoints work without auth."""

    async def test_root_returns_app_info(self, client: AsyncClient):
        resp = await client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "name" in data
        assert "version" in data
        assert data["status"] == "healthy"

    async def test_health_check(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

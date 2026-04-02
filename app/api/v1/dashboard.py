"""
Dashboard summary API routes — aggregated analytics for the finance dashboard.
"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import PermissionChecker
from app.api.schemas.dashboard import (
    CategoryBreakdown,
    CategoryBreakdownResponse,
    DashboardSummary,
    MonthlyTrend,
    MonthlyTrendsResponse,
    RecentActivityResponse,
)
from app.api.schemas.financial_record import RecordResponse
from app.core.constants import Permission
from app.domain.database import get_db
from app.domain.models.user import User
from app.repositories.financial_record_repository import FinancialRecordRepository
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard Analytics"])


def _get_dashboard_service(db: AsyncSession) -> DashboardService:
    """Factory for DashboardService — wires repository dependency."""
    return DashboardService(FinancialRecordRepository(db))


@router.get(
    "/summary",
    response_model=DashboardSummary,
    summary="Get financial summary (Analyst, Admin)",
    description="Returns total income, total expenses, net balance, and total record count.",
)
async def get_summary(
    date_from: date | None = Query(None, description="Start date for summary"),
    date_to: date | None = Query(None, description="End date for summary"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        PermissionChecker(Permission.DASHBOARD_VIEW_SUMMARY)
    ),
):
    service = _get_dashboard_service(db)
    return await service.get_summary(date_from=date_from, date_to=date_to)


@router.get(
    "/categories",
    response_model=CategoryBreakdownResponse,
    summary="Get category breakdown (Analyst, Admin)",
    description="Returns income/expense totals grouped by category.",
)
async def get_category_breakdown(
    date_from: date | None = Query(None, description="Start date"),
    date_to: date | None = Query(None, description="End date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        PermissionChecker(Permission.DASHBOARD_VIEW_CATEGORIES)
    ),
):
    service = _get_dashboard_service(db)
    data = await service.get_category_breakdown(date_from=date_from, date_to=date_to)
    return CategoryBreakdownResponse(
        categories=[CategoryBreakdown(**item) for item in data]
    )


@router.get(
    "/recent",
    response_model=RecentActivityResponse,
    summary="Get recent activity",
    description="Returns the most recent financial records. Available to all authenticated roles.",
)
async def get_recent_activity(
    limit: int = Query(10, ge=1, le=50, description="Number of recent records"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        PermissionChecker(Permission.DASHBOARD_VIEW_RECENT)
    ),
):
    service = _get_dashboard_service(db)
    records = await service.get_recent_activity(limit=limit)
    return RecentActivityResponse(
        records=[RecordResponse.model_validate(r) for r in records]
    )


@router.get(
    "/trends",
    response_model=MonthlyTrendsResponse,
    summary="Get monthly trends (Analyst, Admin)",
    description="Returns month-over-month income/expense trends.",
)
async def get_monthly_trends(
    months: int = Query(12, ge=1, le=24, description="Number of months to include"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        PermissionChecker(Permission.DASHBOARD_VIEW_TRENDS)
    ),
):
    service = _get_dashboard_service(db)
    data = await service.get_monthly_trends(months=months)
    return MonthlyTrendsResponse(
        trends=[MonthlyTrend(**item) for item in data]
    )

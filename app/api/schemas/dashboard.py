"""
Pydantic schemas (DTOs) for dashboard summary endpoints.
"""

from pydantic import BaseModel

from app.api.schemas.financial_record import RecordResponse


class DashboardSummary(BaseModel):
    """Overall financial summary."""
    total_income: float
    total_expenses: float
    net_balance: float
    total_records: int


class CategoryBreakdown(BaseModel):
    """Single category's financial breakdown."""
    category: str
    type: str
    total: float
    count: int


class CategoryBreakdownResponse(BaseModel):
    """List of category breakdowns."""
    categories: list[CategoryBreakdown]


class MonthlyTrend(BaseModel):
    """Single month's financial trend data."""
    month: str
    income: float
    expense: float
    net: float
    count: int


class MonthlyTrendsResponse(BaseModel):
    """List of monthly trends."""
    trends: list[MonthlyTrend]


class RecentActivityResponse(BaseModel):
    """Recent financial activity."""
    records: list[RecordResponse]

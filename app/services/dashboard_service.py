"""
Dashboard analytics service — computes summary data for the finance dashboard.
"""

from datetime import date

from app.core.constants import RecordType
from app.repositories.financial_record_repository import FinancialRecordRepository


class DashboardService:
    """Provides aggregated financial analytics."""

    def __init__(self, record_repo: FinancialRecordRepository):
        self._record_repo = record_repo

    async def get_summary(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict:
        """
        Calculate overall financial summary.

        Returns:
            Dict with total_income, total_expenses, net_balance, total_records.
        """
        total_income = await self._record_repo.get_total_by_type(
            RecordType.INCOME, date_from, date_to
        )
        total_expenses = await self._record_repo.get_total_by_type(
            RecordType.EXPENSE, date_from, date_to
        )
        total_records = await self._record_repo.count()

        return {
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net_balance": total_income - total_expenses,
            "total_records": total_records,
        }

    async def get_category_breakdown(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[dict]:
        """
        Get income/expense totals grouped by category.

        Returns:
            List of dicts with category, type, total, count.
        """
        return await self._record_repo.get_category_totals(date_from, date_to)

    async def get_recent_activity(self, limit: int = 10) -> list:
        """
        Get the most recent financial records.

        Returns:
            List of recent FinancialRecord entities.
        """
        return await self._record_repo.get_recent_records(limit=limit)

    async def get_monthly_trends(self, months: int = 12) -> list[dict]:
        """
        Get month-over-month income/expense trends.

        Returns:
            List of dicts with month, income, expense, net, count.
        """
        return await self._record_repo.get_monthly_trends(months=months)

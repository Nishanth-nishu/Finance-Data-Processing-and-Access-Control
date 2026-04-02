"""
Financial record repository — data access with filtering, aggregation, and soft delete.
"""

from datetime import date, datetime, timezone

from sqlalchemy import Date, case, cast, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import RecordType
from app.domain.models.financial_record import FinancialRecord
from app.repositories.base import BaseRepository


class FinancialRecordRepository(BaseRepository[FinancialRecord]):
    """Data access layer for FinancialRecord entities with advanced query support."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def create(self, entity: FinancialRecord) -> FinancialRecord:
        """Persist a new financial record."""
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def get_by_id(self, entity_id: int) -> FinancialRecord | None:
        """Retrieve a non-deleted record by ID."""
        result = await self.session.execute(
            select(FinancialRecord).where(
                FinancialRecord.id == entity_id,
                FinancialRecord.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def get_all(
        self, skip: int = 0, limit: int = 20
    ) -> list[FinancialRecord]:
        """Retrieve paginated non-deleted records."""
        result = await self.session.execute(
            select(FinancialRecord)
            .where(FinancialRecord.is_deleted == False)  # noqa: E712
            .offset(skip)
            .limit(limit)
            .order_by(FinancialRecord.record_date.desc())
        )
        return list(result.scalars().all())

    async def get_filtered(
        self,
        skip: int = 0,
        limit: int = 20,
        record_type: RecordType | None = None,
        category: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        search: str | None = None,
    ) -> tuple[list[FinancialRecord], int]:
        """
        Retrieve records with dynamic filtering and return total count.

        Returns:
            Tuple of (records, total_count) for pagination metadata.
        """
        query = select(FinancialRecord).where(
            FinancialRecord.is_deleted == False  # noqa: E712
        )
        count_query = select(func.count(FinancialRecord.id)).where(
            FinancialRecord.is_deleted == False  # noqa: E712
        )

        # Apply filters dynamically
        if record_type:
            query = query.where(FinancialRecord.type == record_type)
            count_query = count_query.where(FinancialRecord.type == record_type)

        if category:
            query = query.where(FinancialRecord.category == category)
            count_query = count_query.where(FinancialRecord.category == category)

        if date_from:
            query = query.where(FinancialRecord.record_date >= date_from)
            count_query = count_query.where(FinancialRecord.record_date >= date_from)

        if date_to:
            query = query.where(FinancialRecord.record_date <= date_to)
            count_query = count_query.where(FinancialRecord.record_date <= date_to)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(FinancialRecord.description.ilike(search_pattern))
            count_query = count_query.where(
                FinancialRecord.description.ilike(search_pattern)
            )

        # Get total count
        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()

        # Get paginated results
        query = query.offset(skip).limit(limit).order_by(
            FinancialRecord.record_date.desc()
        )
        result = await self.session.execute(query)
        records = list(result.scalars().all())

        return records, total

    async def update(self, entity_id: int, **kwargs) -> FinancialRecord | None:
        """Update record fields."""
        kwargs["updated_at"] = datetime.now(timezone.utc)
        await self.session.execute(
            update(FinancialRecord)
            .where(
                FinancialRecord.id == entity_id,
                FinancialRecord.is_deleted == False,  # noqa: E712
            )
            .values(**kwargs)
        )
        await self.session.flush()
        return await self.get_by_id(entity_id)

    async def soft_delete(self, entity_id: int) -> bool:
        """Soft delete a record (set is_deleted flag)."""
        record = await self.get_by_id(entity_id)
        if record:
            await self.session.execute(
                update(FinancialRecord)
                .where(FinancialRecord.id == entity_id)
                .values(
                    is_deleted=True,
                    updated_at=datetime.now(timezone.utc),
                )
            )
            await self.session.flush()
            return True
        return False

    async def delete(self, entity_id: int) -> bool:
        """Soft delete (alias for soft_delete — never hard-delete financial data)."""
        return await self.soft_delete(entity_id)

    async def count(self) -> int:
        """Count total non-deleted records."""
        result = await self.session.execute(
            select(func.count(FinancialRecord.id)).where(
                FinancialRecord.is_deleted == False  # noqa: E712
            )
        )
        return result.scalar_one()

    # --- Aggregation methods for Dashboard ---

    async def get_total_by_type(
        self,
        record_type: RecordType,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> float:
        """Get total amount for a specific record type."""
        query = select(func.coalesce(func.sum(FinancialRecord.amount), 0.0)).where(
            FinancialRecord.is_deleted == False,  # noqa: E712
            FinancialRecord.type == record_type,
        )
        if date_from:
            query = query.where(FinancialRecord.record_date >= date_from)
        if date_to:
            query = query.where(FinancialRecord.record_date <= date_to)

        result = await self.session.execute(query)
        return float(result.scalar_one())

    async def get_category_totals(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[dict]:
        """Get totals grouped by category and type."""
        query = (
            select(
                FinancialRecord.category,
                FinancialRecord.type,
                func.sum(FinancialRecord.amount).label("total"),
                func.count(FinancialRecord.id).label("count"),
            )
            .where(FinancialRecord.is_deleted == False)  # noqa: E712
            .group_by(FinancialRecord.category, FinancialRecord.type)
            .order_by(func.sum(FinancialRecord.amount).desc())
        )
        if date_from:
            query = query.where(FinancialRecord.record_date >= date_from)
        if date_to:
            query = query.where(FinancialRecord.record_date <= date_to)

        result = await self.session.execute(query)
        return [
            {
                "category": row.category,
                "type": row.type.value,
                "total": float(row.total),
                "count": row.count,
            }
            for row in result.all()
        ]

    async def get_recent_records(self, limit: int = 10) -> list[FinancialRecord]:
        """Get the most recent non-deleted records."""
        result = await self.session.execute(
            select(FinancialRecord)
            .where(FinancialRecord.is_deleted == False)  # noqa: E712
            .order_by(FinancialRecord.record_date.desc(), FinancialRecord.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_monthly_trends(
        self,
        months: int = 12,
    ) -> list[dict]:
        """
        Get monthly income/expense trends.
        Returns aggregated data for the last N months.
        """
        # Use strftime for SQLite date extraction
        query = (
            select(
                func.strftime("%Y-%m", FinancialRecord.record_date).label("month"),
                func.sum(
                    case(
                        (FinancialRecord.type == RecordType.INCOME, FinancialRecord.amount),
                        else_=0,
                    )
                ).label("income"),
                func.sum(
                    case(
                        (FinancialRecord.type == RecordType.EXPENSE, FinancialRecord.amount),
                        else_=0,
                    )
                ).label("expense"),
                func.count(FinancialRecord.id).label("count"),
            )
            .where(FinancialRecord.is_deleted == False)  # noqa: E712
            .group_by(func.strftime("%Y-%m", FinancialRecord.record_date))
            .order_by(func.strftime("%Y-%m", FinancialRecord.record_date).desc())
            .limit(months)
        )

        result = await self.session.execute(query)
        return [
            {
                "month": row.month,
                "income": float(row.income),
                "expense": float(row.expense),
                "net": float(row.income) - float(row.expense),
                "count": row.count,
            }
            for row in result.all()
        ]

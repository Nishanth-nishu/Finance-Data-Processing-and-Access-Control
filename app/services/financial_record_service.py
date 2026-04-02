"""
Financial record service — handles CRUD, filtering, and pagination.
"""

from datetime import date

from app.core.constants import RecordType
from app.core.exceptions import EntityNotFoundError
from app.domain.models.financial_record import FinancialRecord
from app.repositories.financial_record_repository import FinancialRecordRepository


class FinancialRecordService:
    """Orchestrates financial record workflows."""

    def __init__(self, record_repo: FinancialRecordRepository):
        self._record_repo = record_repo

    async def create_record(
        self,
        amount: float,
        record_type: RecordType,
        category: str,
        record_date: date,
        created_by: int,
        description: str | None = None,
    ) -> FinancialRecord:
        """Create a new financial record."""
        record = FinancialRecord(
            amount=amount,
            type=record_type,
            category=category.lower(),
            record_date=record_date,
            description=description,
            created_by=created_by,
        )
        return await self._record_repo.create(record)

    async def get_record(self, record_id: int) -> FinancialRecord:
        """
        Get a single record by ID.

        Raises:
            EntityNotFoundError: If record doesn't exist or is soft-deleted.
        """
        record = await self._record_repo.get_by_id(record_id)
        if not record:
            raise EntityNotFoundError("FinancialRecord", record_id)
        return record

    async def list_records(
        self,
        page: int = 1,
        page_size: int = 20,
        record_type: RecordType | None = None,
        category: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        search: str | None = None,
    ) -> tuple[list[FinancialRecord], int]:
        """
        Get paginated and filtered records.

        Returns:
            Tuple of (records list, total count).
        """
        skip = (page - 1) * page_size
        return await self._record_repo.get_filtered(
            skip=skip,
            limit=page_size,
            record_type=record_type,
            category=category.lower() if category else None,
            date_from=date_from,
            date_to=date_to,
            search=search,
        )

    async def update_record(
        self,
        record_id: int,
        amount: float | None = None,
        record_type: RecordType | None = None,
        category: str | None = None,
        record_date: date | None = None,
        description: str | None = None,
    ) -> FinancialRecord:
        """
        Update a financial record.

        Raises:
            EntityNotFoundError: If record doesn't exist or is soft-deleted.
        """
        # Verify record exists
        existing = await self._record_repo.get_by_id(record_id)
        if not existing:
            raise EntityNotFoundError("FinancialRecord", record_id)

        update_data = {}
        if amount is not None:
            update_data["amount"] = amount
        if record_type is not None:
            update_data["type"] = record_type
        if category is not None:
            update_data["category"] = category.lower()
        if record_date is not None:
            update_data["record_date"] = record_date
        if description is not None:
            update_data["description"] = description

        if not update_data:
            return existing

        updated = await self._record_repo.update(record_id, **update_data)
        if not updated:
            raise EntityNotFoundError("FinancialRecord", record_id)
        return updated

    async def delete_record(self, record_id: int) -> bool:
        """
        Soft delete a financial record.

        Raises:
            EntityNotFoundError: If record doesn't exist or is already deleted.
        """
        existing = await self._record_repo.get_by_id(record_id)
        if not existing:
            raise EntityNotFoundError("FinancialRecord", record_id)

        return await self._record_repo.soft_delete(record_id)

"""
Financial records API routes — CRUD with filtering and pagination.
"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import PermissionChecker, get_current_user
from app.api.schemas.financial_record import (
    RecordCreateRequest,
    RecordListResponse,
    RecordResponse,
    RecordUpdateRequest,
)
from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, Permission, RecordType
from app.domain.database import get_db
from app.domain.models.user import User
from app.repositories.financial_record_repository import FinancialRecordRepository
from app.services.financial_record_service import FinancialRecordService

router = APIRouter(prefix="/records", tags=["Financial Records"])


def _get_record_service(db: AsyncSession) -> FinancialRecordService:
    """Factory for FinancialRecordService — wires repository dependency."""
    return FinancialRecordService(FinancialRecordRepository(db))


@router.post(
    "",
    response_model=RecordResponse,
    status_code=201,
    summary="Create a financial record (Admin only)",
    description="Add a new income or expense record. Requires record creation permissions.",
)
async def create_record(
    request: RecordCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        PermissionChecker(Permission.RECORD_CREATE)
    ),
):
    service = _get_record_service(db)
    record = await service.create_record(
        amount=request.amount,
        record_type=request.type,
        category=request.category,
        record_date=request.record_date,
        description=request.description,
        created_by=current_user.id,
    )
    return record


@router.get(
    "",
    response_model=RecordListResponse,
    summary="List financial records",
    description="Retrieve a paginated, filterable list of financial records.",
)
async def list_records(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(
        DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Items per page"
    ),
    type: RecordType | None = Query(None, description="Filter by record type"),
    category: str | None = Query(None, description="Filter by category"),
    date_from: date | None = Query(None, description="Filter records from this date"),
    date_to: date | None = Query(None, description="Filter records up to this date"),
    search: str | None = Query(None, description="Search in description"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        PermissionChecker(Permission.RECORD_VIEW)
    ),
):
    service = _get_record_service(db)
    records, total = await service.list_records(
        page=page,
        page_size=page_size,
        record_type=type,
        category=category,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )
    return RecordListResponse(
        records=[RecordResponse.model_validate(r) for r in records],
        total=total,
        page=page,
        page_size=page_size,
        has_next=(page * page_size) < total,
        has_previous=page > 1,
    )


@router.get(
    "/{record_id}",
    response_model=RecordResponse,
    summary="Get a financial record",
    description="Retrieve a single financial record by its ID.",
)
async def get_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        PermissionChecker(Permission.RECORD_VIEW)
    ),
):
    service = _get_record_service(db)
    return await service.get_record(record_id)


@router.put(
    "/{record_id}",
    response_model=RecordResponse,
    summary="Update a financial record (Admin only)",
    description="Modify an existing financial record. Requires record update permissions.",
)
async def update_record(
    record_id: int,
    request: RecordUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        PermissionChecker(Permission.RECORD_UPDATE)
    ),
):
    service = _get_record_service(db)
    return await service.update_record(
        record_id=record_id,
        amount=request.amount,
        record_type=request.type,
        category=request.category,
        record_date=request.record_date,
        description=request.description,
    )


@router.delete(
    "/{record_id}",
    status_code=204,
    summary="Delete a financial record (Admin only)",
    description="Soft-delete a financial record. The record is marked as deleted but retained for audit.",
)
async def delete_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        PermissionChecker(Permission.RECORD_DELETE)
    ),
):
    service = _get_record_service(db)
    await service.delete_record(record_id)
    return None

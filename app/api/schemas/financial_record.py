"""
Pydantic schemas (DTOs) for financial record endpoints.
"""

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.core.constants import RecordType


class RecordCreateRequest(BaseModel):
    """Request schema for creating a financial record."""
    amount: float = Field(..., gt=0, description="Amount must be positive")
    type: RecordType
    category: str = Field(..., min_length=1, max_length=100)
    record_date: date
    description: str | None = Field(None, max_length=500)


class RecordUpdateRequest(BaseModel):
    """Request schema for updating a financial record."""
    amount: float | None = Field(None, gt=0)
    type: RecordType | None = None
    category: str | None = Field(None, min_length=1, max_length=100)
    record_date: date | None = None
    description: str | None = Field(None, max_length=500)


class RecordResponse(BaseModel):
    """Response schema for a financial record."""
    id: int
    amount: float
    type: RecordType
    category: str
    record_date: date
    description: str | None
    created_by: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RecordListResponse(BaseModel):
    """Paginated list of financial records."""
    records: list[RecordResponse]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool

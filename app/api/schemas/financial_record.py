"""
Pydantic schemas (DTOs) for financial record endpoints.

Strict type annotations are used selectively to block dangerous coercions:
- category and description use Annotated[str, Strict()] to prevent integers
  being silently accepted as strings.
- amount uses a plain float, which correctly accepts both int and float inputs
  (Python's natural numeric widening), while rejecting str like "100".
Response schemas remain fully permissive since they read from SQLAlchemy ORM.
"""

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, Field, Strict

from app.core.constants import RecordType

# StrictStr: rejects int/bool input in string fields; accepts only actual strings
StrictStr = Annotated[str, Strict()]


class RecordCreateRequest(BaseModel):
    """Request schema for creating a financial record."""
    amount: float = Field(..., gt=0, description="Amount must be positive")
    type: RecordType
    category: StrictStr = Field(..., min_length=1, max_length=100)
    record_date: date
    description: StrictStr | None = Field(None, max_length=500)


class RecordUpdateRequest(BaseModel):
    """Request schema for updating a financial record (all fields optional)."""
    amount: float | None = Field(None, gt=0)
    type: RecordType | None = None
    category: StrictStr | None = Field(None, min_length=1, max_length=100)
    record_date: date | None = None
    description: StrictStr | None = Field(None, max_length=500)



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

"""
Financial record ORM model — maps to the 'financial_records' table.
Supports soft delete for data retention compliance.

Performance improvements (composite indexes):
- (is_deleted, record_date)   — primary filter combo in most list queries
- (is_deleted, category)      — category breakdown queries
- (is_deleted, type)          — type-filtered list queries
- (is_deleted, type, record_date) — trend queries that filter by type + date
"""

from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import RecordType
from app.domain.database import Base


class FinancialRecord(Base):
    """Financial transaction/entry entity with soft delete support."""

    __tablename__ = "financial_records"

    # Composite indexes: placed here so SQLAlchemy emits them in CREATE TABLE
    __table_args__ = (
        # Most common query pattern: active records by date (list + date range)
        Index("ix_fr_active_date", "is_deleted", "record_date"),
        # Category breakdown dashboard query
        Index("ix_fr_active_category", "is_deleted", "category"),
        # Type-filtered list
        Index("ix_fr_active_type", "is_deleted", "type"),
        # Monthly trends: group by month, filter by type
        Index("ix_fr_active_type_date", "is_deleted", "type", "record_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    type: Mapped[RecordType] = mapped_column(
        Enum(RecordType), nullable=False
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )

    # Soft delete support — records are never physically removed
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return (
            f"<FinancialRecord(id={self.id}, type='{self.type.value}', "
            f"amount={self.amount}, category='{self.category}')>"
        )

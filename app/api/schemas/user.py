"""
Pydantic schemas (DTOs) for user management endpoints.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.core.constants import UserRole, UserStatus


class UserResponse(BaseModel):
    """Response schema for user data — never exposes sensitive fields."""
    id: int
    email: EmailStr
    username: str
    full_name: str | None
    role: UserRole
    status: UserStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    """Request schema for updating user profile."""
    full_name: str | None = Field(None, max_length=255)
    email: EmailStr | None = None
    username: str | None = Field(
        None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$"
    )


class RoleUpdateRequest(BaseModel):
    """Request schema for updating a user's role."""
    role: UserRole


class StatusUpdateRequest(BaseModel):
    """Request schema for updating a user's status."""
    status: UserStatus


class UserListResponse(BaseModel):
    """Paginated list of users."""
    users: list[UserResponse]
    total: int
    page: int
    page_size: int

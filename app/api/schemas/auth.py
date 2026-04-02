"""
Pydantic schemas (DTOs) for authentication endpoints.
Separates API contract from internal domain models (Interface Segregation).
"""

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Request schema for user registration."""
    email: EmailStr
    username: str = Field(
        ..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$"
    )
    password: str = Field(
        ..., min_length=8, max_length=128,
        description="Password must be at least 8 characters"
    )
    full_name: str | None = Field(None, max_length=255)


class LoginRequest(BaseModel):
    """Request schema for user login."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Response schema containing JWT tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Request schema for token refresh."""
    refresh_token: str


class TokenRefreshResponse(BaseModel):
    """Response schema for refreshed access token."""
    access_token: str
    token_type: str = "bearer"

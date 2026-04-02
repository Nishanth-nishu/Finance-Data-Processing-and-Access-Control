"""
Authentication API routes — register, login, and token refresh.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenRefreshResponse,
    TokenResponse,
)
from app.api.schemas.user import UserResponse
from app.domain.database import get_db
from app.domain.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _get_auth_service(db: AsyncSession) -> AuthService:
    """Factory for AuthService — wires repository dependency."""
    return AuthService(UserRepository(db))


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=201,
    summary="Register a new user",
    description="Create a new user account. Default role is 'viewer'.",
)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    service = _get_auth_service(db)
    user = await service.register(
        email=request.email,
        username=request.username,
        password=request.password,
        full_name=request.full_name,
    )
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login to get access tokens",
    description="Authenticate with email and password to receive JWT tokens.",
)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    service = _get_auth_service(db)
    return await service.login(email=request.email, password=request.password)


@router.post(
    "/refresh",
    response_model=TokenRefreshResponse,
    summary="Refresh access token",
    description="Use a valid refresh token to get a new access token.",
)
async def refresh_token(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    service = _get_auth_service(db)
    return await service.refresh_token(refresh_token=request.refresh_token)

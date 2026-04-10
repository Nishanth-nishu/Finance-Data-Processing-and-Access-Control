"""
Authentication API routes — register, login, and token refresh.

DI improvement: AuthService is injected via FastAPI Depends rather than
a factory function, making unit testing with mocks trivial.
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


# --- Service dependency (injectable for testing) ---

def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """Provide AuthService with its repository dependency injected."""
    return AuthService(UserRepository(db))


# --- Routes ---

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=201,
    summary="Register a new user",
    description="Create a new user account. Default role is 'viewer'.",
)
async def register(
    request: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
):
    return await service.register(
        email=request.email,
        username=request.username,
        password=request.password,
        full_name=request.full_name,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login to get access tokens",
    description="Authenticate with email and password to receive JWT tokens.",
)
async def login(
    request: LoginRequest,
    service: AuthService = Depends(get_auth_service),
):
    return await service.login(email=request.email, password=request.password)


@router.post(
    "/refresh",
    response_model=TokenRefreshResponse,
    summary="Refresh access token",
    description="Use a valid refresh token to get a new access token.",
)
async def refresh_token(
    request: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
    _current_user: User = Depends(get_current_user),
):
    return await service.refresh_token(refresh_token=request.refresh_token)

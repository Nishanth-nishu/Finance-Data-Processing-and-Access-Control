"""
User management API routes — RBAC-protected user operations.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import PermissionChecker, get_current_user
from app.api.schemas.user import (
    RoleUpdateRequest,
    StatusUpdateRequest,
    UserListResponse,
    UserResponse,
    UserUpdateRequest,
)
from app.core.constants import Permission
from app.domain.database import get_db
from app.domain.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["User Management"])


def _get_user_service(db: AsyncSession) -> UserService:
    """Factory for UserService — wires repository dependency."""
    return UserService(UserRepository(db))


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Retrieve the authenticated user's own profile data.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user


@router.get(
    "",
    response_model=UserListResponse,
    summary="List all users (Admin only)",
    description="Retrieve a paginated list of all users. Requires user management permissions.",
)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        PermissionChecker(Permission.USER_VIEW_ALL)
    ),
):
    service = _get_user_service(db)
    users, total = await service.list_users(page=page, page_size=page_size)
    return UserListResponse(
        users=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID (Admin only)",
    description="Retrieve a specific user's profile. Requires admin permissions.",
)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        PermissionChecker(Permission.USER_VIEW_ALL)
    ),
):
    service = _get_user_service(db)
    return await service.get_user(user_id)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user profile (Admin only)",
    description="Update a user's profile fields. Requires user management permissions.",
)
async def update_user(
    user_id: int,
    request: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        PermissionChecker(Permission.USER_MANAGE)
    ),
):
    service = _get_user_service(db)
    return await service.update_user(
        user_id,
        full_name=request.full_name,
        email=request.email,
        username=request.username,
    )


@router.patch(
    "/{user_id}/role",
    response_model=UserResponse,
    summary="Assign role to user (Admin only)",
    description="Change a user's role. Requires role assignment permissions.",
)
async def assign_role(
    user_id: int,
    request: RoleUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        PermissionChecker(Permission.USER_ASSIGN_ROLE)
    ),
):
    service = _get_user_service(db)
    return await service.assign_role(user_id, request.role)


@router.patch(
    "/{user_id}/status",
    response_model=UserResponse,
    summary="Update user status (Admin only)",
    description="Activate or deactivate a user account. Requires user management permissions.",
)
async def update_status(
    user_id: int,
    request: StatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        PermissionChecker(Permission.USER_MANAGE)
    ),
):
    service = _get_user_service(db)
    return await service.update_status(user_id, request.status)

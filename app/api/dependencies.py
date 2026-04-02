"""
API dependencies — JWT authentication and RBAC enforcement.
Uses FastAPI's dependency injection for composable auth checks.
"""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import Permission, UserRole, UserStatus, has_permission
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    InactiveUserError,
)
from app.core.security import decode_token
from app.domain.database import get_db
from app.domain.models.user import User
from app.repositories.user_repository import UserRepository

# HTTP Bearer scheme — extracts token from Authorization header
security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency that validates JWT and returns the authenticated user.

    Raises:
        AuthenticationError: If token is missing, invalid, or user not found.
        InactiveUserError: If user account is inactive.
    """
    if credentials is None:
        raise AuthenticationError("Missing authentication token")

    payload = decode_token(credentials.credentials)

    if payload.get("type") != "access":
        raise AuthenticationError("Invalid token type: expected access token")

    user_id = int(payload["sub"])
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise AuthenticationError("User not found")

    if user.status == UserStatus.INACTIVE:
        raise InactiveUserError()

    return user


class PermissionChecker:
    """
    Callable dependency that enforces permission-based access control.
    Uses the data-driven permission matrix from constants.py.

    Usage in routes:
        @router.get("/records", dependencies=[Depends(PermissionChecker(Permission.RECORD_VIEW))])
    """

    def __init__(self, required_permission: Permission):
        self.required_permission = required_permission

    async def __call__(
        self, current_user: User = Depends(get_current_user)
    ) -> User:
        if not has_permission(current_user.role, self.required_permission):
            raise AuthorizationError(
                f"Permission denied: {self.required_permission.value} "
                f"is not available for role '{current_user.role.value}'"
            )
        return current_user


class RoleChecker:
    """
    Callable dependency that enforces role-based access control.
    Simpler alternative to PermissionChecker for straightforward role checks.

    Usage in routes:
        @router.get("/admin", dependencies=[Depends(RoleChecker([UserRole.ADMIN]))])
    """

    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles

    async def __call__(
        self, current_user: User = Depends(get_current_user)
    ) -> User:
        if current_user.role not in self.allowed_roles:
            raise AuthorizationError(
                f"Access denied: role '{current_user.role.value}' "
                f"is not authorized for this action"
            )
        return current_user

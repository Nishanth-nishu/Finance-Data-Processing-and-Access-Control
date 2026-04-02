"""
User management service — handles user CRUD and role/status management.
"""

from app.core.constants import UserRole, UserStatus
from app.core.exceptions import (
    DuplicateEntityError,
    EntityNotFoundError,
    InvalidInputError,
)
from app.domain.models.user import User
from app.repositories.user_repository import UserRepository


class UserService:
    """Orchestrates user management workflows."""

    def __init__(self, user_repo: UserRepository):
        self._user_repo = user_repo

    async def get_user(self, user_id: int) -> User:
        """
        Get a user by ID.

        Raises:
            EntityNotFoundError: If user doesn't exist.
        """
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundError("User", user_id)
        return user

    async def list_users(
        self, page: int = 1, page_size: int = 20
    ) -> tuple[list[User], int]:
        """
        Get a paginated list of users.

        Returns:
            Tuple of (users list, total count).
        """
        skip = (page - 1) * page_size
        users = await self._user_repo.get_all(skip=skip, limit=page_size)
        total = await self._user_repo.count()
        return users, total

    async def update_user(
        self,
        user_id: int,
        full_name: str | None = None,
        email: str | None = None,
        username: str | None = None,
    ) -> User:
        """
        Update user profile fields.

        Raises:
            EntityNotFoundError: If user doesn't exist.
            DuplicateEntityError: If new email/username is taken.
        """
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundError("User", user_id)

        update_data = {}

        if email is not None and email != user.email:
            existing = await self._user_repo.get_by_email(email)
            if existing:
                raise DuplicateEntityError("User", "email", email)
            update_data["email"] = email

        if username is not None and username != user.username:
            existing = await self._user_repo.get_by_username(username)
            if existing:
                raise DuplicateEntityError("User", "username", username)
            update_data["username"] = username

        if full_name is not None:
            update_data["full_name"] = full_name

        if not update_data:
            return user

        updated = await self._user_repo.update(user_id, **update_data)
        if not updated:
            raise EntityNotFoundError("User", user_id)
        return updated

    async def assign_role(self, user_id: int, role: UserRole) -> User:
        """
        Assign a role to a user.

        Raises:
            EntityNotFoundError: If user doesn't exist.
        """
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundError("User", user_id)

        updated = await self._user_repo.update_role(user_id, role)
        if not updated:
            raise EntityNotFoundError("User", user_id)
        return updated

    async def update_status(self, user_id: int, status: UserStatus) -> User:
        """
        Update a user's active/inactive status.

        Raises:
            EntityNotFoundError: If user doesn't exist.
            InvalidInputError: If trying to deactivate the last admin.
        """
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundError("User", user_id)

        # Safety: prevent deactivating the last admin
        if (
            status == UserStatus.INACTIVE
            and user.role == UserRole.ADMIN
        ):
            all_users = await self._user_repo.get_all(skip=0, limit=1000)
            active_admins = [
                u for u in all_users
                if u.role == UserRole.ADMIN
                and u.status == UserStatus.ACTIVE
                and u.id != user_id
            ]
            if not active_admins:
                raise InvalidInputError(
                    "Cannot deactivate the last active admin",
                    "At least one admin must remain active in the system.",
                )

        updated = await self._user_repo.update_status(user_id, status)
        if not updated:
            raise EntityNotFoundError("User", user_id)
        return updated

"""
User repository — concrete implementation of data access for User entities.
"""

from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import UserRole, UserStatus
from app.domain.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Data access layer for User entities."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def create(self, entity: User) -> User:
        """Persist a new user."""
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def get_by_id(self, entity_id: int) -> User | None:
        """Retrieve a user by ID."""
        result = await self.session.execute(
            select(User).where(User.id == entity_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Retrieve a user by email address."""
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        """Retrieve a user by username."""
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self, skip: int = 0, limit: int = 20
    ) -> list[User]:
        """Retrieve a paginated list of users."""
        result = await self.session.execute(
            select(User).offset(skip).limit(limit).order_by(User.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(self, entity_id: int, **kwargs) -> User | None:
        """Update user fields."""
        kwargs["updated_at"] = datetime.now(timezone.utc)
        await self.session.execute(
            update(User).where(User.id == entity_id).values(**kwargs)
        )
        await self.session.flush()
        return await self.get_by_id(entity_id)

    async def update_role(self, entity_id: int, role: UserRole) -> User | None:
        """Update a user's role."""
        return await self.update(entity_id, role=role)

    async def update_status(self, entity_id: int, status: UserStatus) -> User | None:
        """Update a user's status (activate/deactivate)."""
        return await self.update(entity_id, status=status)

    async def delete(self, entity_id: int) -> bool:
        """Delete a user (hard delete)."""
        user = await self.get_by_id(entity_id)
        if user:
            await self.session.delete(user)
            await self.session.flush()
            return True
        return False

    async def count(self) -> int:
        """Count total users."""
        result = await self.session.execute(select(func.count(User.id)))
        return result.scalar_one()

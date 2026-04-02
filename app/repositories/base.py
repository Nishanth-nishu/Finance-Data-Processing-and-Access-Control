"""
Abstract base repository — defines the contract for all data access.
Follows the Repository Pattern for Dependency Inversion (SOLID - D).
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """
    Abstract repository interface.
    Concrete implementations provide database-specific logic.
    Services depend on this abstraction, not on concrete DB details.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    @abstractmethod
    async def create(self, entity: T) -> T:
        """Persist a new entity."""
        ...

    @abstractmethod
    async def get_by_id(self, entity_id: int) -> T | None:
        """Retrieve an entity by its primary key."""
        ...

    @abstractmethod
    async def get_all(
        self, skip: int = 0, limit: int = 20
    ) -> list[T]:
        """Retrieve a paginated list of entities."""
        ...

    @abstractmethod
    async def update(self, entity_id: int, **kwargs) -> T | None:
        """Update an entity's fields."""
        ...

    @abstractmethod
    async def delete(self, entity_id: int) -> bool:
        """Delete an entity by its primary key."""
        ...

    @abstractmethod
    async def count(self) -> int:
        """Count total entities."""
        ...

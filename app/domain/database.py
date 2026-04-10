"""
Database engine, session factory, and base model.
Uses async SQLAlchemy with aiosqlite (SQLite) or asyncpg (PostgreSQL).

Production improvements:
- Connection pooling with QueuePool tuning for PostgreSQL.
- Exponential backoff retry on startup DB connectivity.
- SQLite auto-detected and configured correctly (no pool_size args).
"""

import asyncio
import logging
from collections.abc import AsyncGenerator

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Detect DB backend from URL to configure pool correctly.
# SQLite (aiosqlite) is single-file and doesn't support QueuePool.
_db_url: str = settings.DATABASE_URL.get_secret_value()
_is_sqlite = _db_url.startswith("sqlite")

if _is_sqlite:
    # NullPool: every connection is a new file open — correct for SQLite.
    # No pool_size / max_overflow args needed.
    engine = create_async_engine(
        _db_url,
        echo=settings.DEBUG,
        future=True,
        poolclass=NullPool,
    )
else:
    # PostgreSQL (asyncpg): use QueuePool for connection reuse under load.
    engine = create_async_engine(
        _db_url,
        echo=settings.DEBUG,
        future=True,
        poolclass=QueuePool,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_pre_ping=True,  # Verify connection health before use
    )

# Session factory — one session per request, not per connection
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session.
    Ensures proper commit/rollback/cleanup lifecycle.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_connection() -> bool:
    """
    Probe the database with a lightweight query.
    Used by the /health endpoint to report real DB status.
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error("Database health check failed: %s", exc)
        return False


async def create_tables_with_retry() -> None:
    """
    Create all database tables at startup.
    Uses exponential backoff to handle transient DB unavailability
    (e.g., Docker Compose startup race between app and PostgreSQL containers).
    """
    max_attempts = settings.DB_CONNECT_RETRY_ATTEMPTS
    delay = settings.DB_CONNECT_RETRY_DELAY_SECONDS

    for attempt in range(1, max_attempts + 1):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables ready (attempt %d/%d)", attempt, max_attempts)
            return
        except Exception as exc:
            if attempt == max_attempts:
                logger.critical(
                    "Database connection failed after %d attempts: %s",
                    max_attempts,
                    exc,
                )
                raise
            wait = delay * (2 ** (attempt - 1))  # Exponential backoff: 1s, 2s, 4s…
            logger.warning(
                "DB unavailable (attempt %d/%d), retrying in %.1fs — %s",
                attempt,
                max_attempts,
                wait,
                exc,
            )
            await asyncio.sleep(wait)


# Keep drop_tables for test teardown
async def drop_tables() -> None:
    """Drop all tables — used in test teardown only."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

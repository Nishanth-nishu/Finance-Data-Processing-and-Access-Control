"""
Test configuration — shared fixtures for all tests.
Creates an isolated in-memory SQLite database for each test session.
"""

import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.constants import UserRole
from app.core.security import hash_password
from app.domain.database import Base, get_db
from app.domain.models.user import User
from main import app

# In-memory SQLite for test isolation
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_session_factory = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Create and tear down database tables for each test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a test database session."""
    async with test_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async test client with overridden DB dependency."""

    async def override_get_db():
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# --- Helper fixtures for authenticated requests ---

@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin user in the test database."""
    user = User(
        email="admin@test.com",
        username="admin_user",
        hashed_password=hash_password("adminpassword123"),
        full_name="Admin User",
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def analyst_user(db_session: AsyncSession) -> User:
    """Create an analyst user in the test database."""
    user = User(
        email="analyst@test.com",
        username="analyst_user",
        hashed_password=hash_password("analystpassword123"),
        full_name="Analyst User",
        role=UserRole.ANALYST,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def viewer_user(db_session: AsyncSession) -> User:
    """Create a viewer user in the test database."""
    user = User(
        email="viewer@test.com",
        username="viewer_user",
        hashed_password=hash_password("viewerpassword123"),
        full_name="Viewer User",
        role=UserRole.VIEWER,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


async def get_auth_headers(client: AsyncClient, email: str, password: str) -> dict:
    """Helper to login and return Authorization headers."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

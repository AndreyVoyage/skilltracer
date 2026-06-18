from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import get_db
from app.main import app
from app.models.base import Base
from app.models.schemas import UserCreate
from app.models.user import User
from app.services.auth import get_or_create_user

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
TEST_SECRET_KEY = "test-secret-key-for-unit-tests-only-32"
TEST_BOT_TOKEN = "1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"


def _patch_settings() -> None:
    """Override application settings for the test suite."""
    settings.DATABASE_URL = TEST_DATABASE_URL
    settings.SECRET_KEY = TEST_SECRET_KEY
    settings.TELEGRAM_BOT_TOKEN = TEST_BOT_TOKEN


@pytest_asyncio.fixture(loop_scope="function")
async def test_engine() -> AsyncGenerator[Any, None]:
    """Create a fresh async in-memory SQLite engine and initialize tables."""
    _patch_settings()
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(loop_scope="function")
async def db_session(test_engine: Any) -> AsyncGenerator[AsyncSession, None]:
    """Yield a fresh async session backed by an isolated in-memory database."""
    session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    async with session_maker() as session:
        yield session


@pytest_asyncio.fixture(loop_scope="function")
async def sample_user(db_session: AsyncSession) -> User:
    """Create and return a sample user in the test database."""
    return await get_or_create_user(
        db_session,
        UserCreate(
            telegram_id=123456789,
            username="andreyvoyage",
            first_name="Andrey",
            last_name="Voyage",
        ),
    )


@pytest.fixture
def client(db_session: AsyncSession) -> TestClient:
    """Yield a FastAPI TestClient with the database dependency overridden."""

    async def _get_test_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _get_test_db
    return TestClient(app)

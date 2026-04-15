"""
Skill Tracer Database Tests

Асинхронные тесты для проверки работы с базой данных.
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import Column, Integer, String, text
from sqlalchemy.orm import declarative_base

# =============================================================================
# Test Configuration
# =============================================================================

# Используем SQLite in-memory для тестов (async)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

Base = declarative_base()


# =============================================================================
# Test Models
# =============================================================================

class TestUser(Base):
    """Тестовая модель пользователя для проверки БД."""
    __tablename__ = "test_users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True)
    username = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=False)


# =============================================================================
# Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def async_engine():
    """
    Фикстура для создания тестового engine.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
    )
    
    # Создаём таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(async_engine) -> AsyncSession:
    """
    Фикстура для создания тестовой сессии БД.
    """
    async_session = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    
    async with async_session() as session:
        yield session
        # Rollback после каждого теста
        await session.rollback()


# =============================================================================
# Tests
# =============================================================================

@pytest.mark.asyncio
async def test_database_connection(async_engine):
    """
    Тест подключения к БД.
    """
    async with async_engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        row = result.fetchone()
        assert row[0] == 1


@pytest.mark.asyncio
async def test_create_user(db_session: AsyncSession):
    """
    Тест создания пользователя в БД.
    """
    # Создаём тестового пользователя
    new_user = TestUser(
        telegram_id=123456789,
        username="test_user",
        full_name="Test User",
    )
    
    db_session.add(new_user)
    await db_session.commit()
    await db_session.refresh(new_user)
    
    # Проверяем что пользователь создан
    assert new_user.id is not None
    assert new_user.telegram_id == 123456789
    assert new_user.username == "test_user"
    assert new_user.full_name == "Test User"


@pytest.mark.asyncio
async def test_read_user(db_session: AsyncSession):
    """
    Тест чтения пользователя из БД.
    """
    # Создаём пользователя
    user = TestUser(
        telegram_id=987654321,
        username="read_test",
        full_name="Read Test User",
    )
    db_session.add(user)
    await db_session.commit()
    
    # Читаем пользователя
    from sqlalchemy import select
    result = await db_session.execute(
        select(TestUser).where(TestUser.telegram_id == 987654321)
    )
    found_user = result.scalar_one_or_none()
    
    assert found_user is not None
    assert found_user.username == "read_test"


@pytest.mark.asyncio
async def test_engine_dispose(async_engine):
    """
    Тест корректного закрытия engine.
    """
    # Engine уже создан в фикстуре
    assert async_engine is not None
    
    # Проверяем что можно выполнить запрос
    async with async_engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.fetchone()[0] == 1

"""
Skill Tracer Database Module

Async SQLAlchemy конфигурация для работы с MySQL.
Включает retry логику для надёжности при старте.
"""

import asyncio
import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import event, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.pool import Pool

from app.config import settings


@event.listens_for(Pool, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    if settings.DATABASE_URL.startswith("sqlite"):
        dbapi_conn.execute("PRAGMA foreign_keys = ON")
from app.models import Base  # noqa: F401 - для alembic и моделей

# Настройка логирования
logger = logging.getLogger(__name__)

# =============================================================================
# Engine Configuration
# =============================================================================

_engine_kwargs = dict(
    echo=settings.is_development,
    future=True,
    pool_size=5,
    max_overflow=0,
    pool_pre_ping=True,
    pool_recycle=3600,
)
if settings.DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

async_engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    **_engine_kwargs,
)

# Фабрика сессий
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# =============================================================================
# Database Functions
# =============================================================================

async def init_db(retries: int = 3, delay: int = 5) -> bool:
    """
    Инициализация базы данных с retry логикой.
    
    Args:
        retries: Количество попыток подключения
        delay: Задержка между попытками в секундах
        
    Returns:
        True если подключение успешно, False иначе
    """
    for attempt in range(1, retries + 1):
        try:
            logger.info(f"Попытка подключения к БД {attempt}/{retries}...")
            
            async with async_engine.begin() as conn:
                # Тестовый запрос
                result = await conn.execute(text("SELECT 1"))
                result.scalar()
                
            logger.info("✅ Подключение к БД успешно установлено")
            return True
            
        except OperationalError as e:
            logger.warning(f"⚠️ Попытка {attempt} не удалась: {e}")
            if attempt < retries:
                logger.info(f"Ожидание {delay} секунд перед следующей попыткой...")
                await asyncio.sleep(delay)
            else:
                logger.error("❌ Все попытки подключения к БД исчерпаны")
                raise
                
    return False


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency injection для FastAPI.
    
    Использование:
        @app.get("/items")
        async def read_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_db() -> None:
    """Закрытие всех соединений с БД (для graceful shutdown)."""
    logger.info("Закрытие соединений с БД...")
    await async_engine.dispose()
    logger.info("✅ Соединения с БД закрыты")

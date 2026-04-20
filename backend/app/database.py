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


# =============================================================================
# Journal Entry CRUD (для бота)
# =============================================================================

from datetime import date
from typing import Optional

from sqlalchemy import select

from app.models import DailyEntry
from app.models.journal_entry import JournalEntry


async def get_journal_entry(
    db: AsyncSession,
    user_id: int,
    entry_date: date,
) -> Optional[JournalEntry]:
    """Получает запись пользователя за конкретную дату."""
    result = await db.execute(
        select(JournalEntry).where(
            JournalEntry.user_id == user_id,
            JournalEntry.entry_date == entry_date,
        )
    )
    return result.scalar_one_or_none()


async def get_journal_entries_dates(
    db: AsyncSession,
    user_id: int,
    start_date: date,
    end_date: date,
) -> list[date]:
    """Возвращает список дат, на которые есть записи за период."""
    result = await db.execute(
        select(JournalEntry.entry_date).where(
            JournalEntry.user_id == user_id,
            JournalEntry.entry_date >= start_date,
            JournalEntry.entry_date <= end_date,
        )
    )
    return [row[0] for row in result.all()]


async def get_or_create_daily_entry(
    db: AsyncSession,
    user_id: int,
    entry_date: date,
) -> DailyEntry:
    """Находит или создаёт DailyEntry для пользователя и даты."""
    result = await db.execute(
        select(DailyEntry).where(
            DailyEntry.user_id == user_id,
            DailyEntry.entry_date == entry_date,
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        entry = DailyEntry(user_id=user_id, entry_date=entry_date)
        db.add(entry)
        await db.flush()
    return entry


async def save_journal_entry(
    db: AsyncSession,
    user_id: int,
    entry_date: date,
    health_score: Optional[int] = None,
    sport_score: Optional[int] = None,
    study_score: Optional[int] = None,
    rest_score: Optional[int] = None,
    comment: Optional[str] = None,
    media_urls: Optional[list] = None,
) -> JournalEntry:
    """Создаёт или обновляет запись дня (upsert)."""
    entry = await get_journal_entry(db, user_id, entry_date)
    
    if entry is None:
        entry = JournalEntry(
            user_id=user_id,
            entry_date=entry_date,
            health_score=health_score,
            sport_score=sport_score,
            study_score=study_score,
            rest_score=rest_score,
            comment=comment,
            media_urls=media_urls or [],
        )
        db.add(entry)
    else:
        if health_score is not None:
            entry.health_score = health_score
        if sport_score is not None:
            entry.sport_score = sport_score
        if study_score is not None:
            entry.study_score = study_score
        if rest_score is not None:
            entry.rest_score = rest_score
        if comment is not None:
            entry.comment = comment
        if media_urls is not None:
            entry.media_urls = media_urls
    
    await db.flush()
    await db.commit()
    await db.refresh(entry)
    return entry

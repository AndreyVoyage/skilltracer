"""
Media Accumulation Test

Тест: при добавлении 3 фото подряд, все 3 должны быть в записи.
Запуск: cd backend && PYTHONPATH=... python tests/test_media_accumulation.py
"""
import asyncio
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.models.base import Base
from app.config import settings
from app.models import DailyEntry, User

TEST_DATABASE_URL = settings.DATABASE_URL.replace("/skilltracer", "/skilltracer_test")
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
AsyncSessionLocalTest = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False, autocommit=False
)


async def setup_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def teardown_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


async def test_media_accumulation():
    """Имитируем добавление 3 фото через бота (как в collection.py)."""
    async with AsyncSessionLocalTest() as session:
        user = User(id=888888, username="test_accumulation", first_name="Test")
        session.add(user)
        await session.commit()

        entry = DailyEntry(user_id=888888, entry_date=date.today(), media_files=[])
        session.add(entry)
        await session.commit()

        # Имитируем 3 фото подряд (как handle_photo)
        for i in range(3):
            result = await session.execute(
                select(DailyEntry).where(DailyEntry.id == entry.id)
            )
            current = result.scalar_one()

            if not current.media_files:
                current.media_files = []
            current.media_files.append({
                "id": f"photo_{i}",
                "type": "photo",
                "file_id": f"file_id_{i}",
                "created_at": "2026-04-18T20:00:00"
            })
            current.has_media = True
            await session.commit()

            print(f"  Добавлено фото {i+1}, всего: {len(current.media_files)}")

        # Проверка
        result = await session.execute(
            select(DailyEntry).where(DailyEntry.id == entry.id)
        )
        final = result.scalar_one()

        assert len(final.media_files) == 3, f"Ожидалось 3, получено {len(final.media_files)}"
        print(f"✅ test_media_accumulation passed: {len(final.media_files)} медиа")


async def test_get_or_create_reuses_entry():
    """Проверяем что _get_or_create_entry не создает новую запись."""
    async with AsyncSessionLocalTest() as session:
        user = User(id=888889, username="test_reuse", first_name="Test")
        session.add(user)
        await session.commit()

        # Создаем запись
        entry = DailyEntry(user_id=888889, entry_date=date.today(), media_files=[])
        session.add(entry)
        await session.commit()
        original_id = entry.id

        # Имитируем _get_or_create_entry
        from app.bot.handlers.collection import _get_or_create_entry
        from datetime import date as dt

        entry2 = await _get_or_create_entry(888889, dt.today(), session)
        assert entry2.id == original_id, f"Ожидался ID {original_id}, получен {entry2.id}"
        print(f"✅ test_get_or_create_reuses_entry passed: ID={entry2.id}")


async def test_journal_entry_media_accumulation():
    """Проверяем что save_journal_entry сохраняет все медиа."""
    async with AsyncSessionLocalTest() as session:
        user = User(id=888890, username="test_journal", first_name="Test")
        session.add(user)
        await session.commit()

        from app.database import save_journal_entry

        # Сохраняем запись с 2 медиа
        await save_journal_entry(
            db=session,
            user_id=888890,
            entry_date=date.today(),
            health_score=4,
            media_urls=[
                {"type": "photo", "file_id": "p1"},
                {"type": "voice", "file_id": "v1"},
            ],
        )

        from app.models import JournalEntry
        result = await session.execute(
            select(JournalEntry).where(
                JournalEntry.user_id == 888890,
                JournalEntry.entry_date == date.today(),
            )
        )
        entry = result.scalar_one()

        assert len(entry.media_urls) == 2, f"Ожидалось 2, получено {len(entry.media_urls)}"
        print(f"✅ test_journal_entry_media_accumulation passed: {len(entry.media_urls)} медиа")


async def main():
    await setup_tables()
    try:
        await test_media_accumulation()
        await test_get_or_create_reuses_entry()
        await test_journal_entry_media_accumulation()
        print("\n🎉 All accumulation tests passed!")
    finally:
        await teardown_tables()


if __name__ == "__main__":
    asyncio.run(main())

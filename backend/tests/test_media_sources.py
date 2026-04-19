"""
Media Sources Test

Проверяем что новые записи используют media_files, а не deprecated поля.
Запуск: cd backend && PYTHONPATH=... python tests/test_media_sources.py
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


async def test_new_entries_use_media_files_with_id():
    """Новые записи должны использовать media_files с UUID, а не photo_file_id."""
    async with AsyncSessionLocalTest() as session:
        user = User(id=777001, username="test_sources", first_name="Test")
        session.add(user)
        await session.commit()

        entry = DailyEntry(user_id=777001, entry_date=date.today(), media_files=[])
        session.add(entry)
        await session.commit()

        # Имитируем collection.py handle_photo
        entry.media_files.append({
            "id": "uuid-123",
            "type": "photo",
            "file_id": "file_abc",
            "created_at": "2026-04-19T10:00:00"
        })
        entry.has_media = True
        await session.commit()

        # Проверяем
        result = await session.execute(
            select(DailyEntry).where(DailyEntry.id == entry.id)
        )
        refreshed = result.scalar_one()

        assert len(refreshed.media_files) == 1, "media_files должен содержать 1 элемент"
        assert refreshed.media_files[0]["id"] == "uuid-123", "Должен быть ID"
        assert refreshed.photo_file_id is None, "photo_file_id должен быть NULL для новых записей"
        print("✅ test_new_entries_use_media_files_with_id passed")


async def test_legacy_fields_still_exist():
    """Deprecated поля должны существовать для обратной совместимости."""
    async with AsyncSessionLocalTest() as session:
        user = User(id=777002, username="test_legacy", first_name="Test")
        session.add(user)
        await session.commit()

        entry = DailyEntry(
            user_id=777002,
            entry_date=date.today(),
            photo_file_id="old_photo",
            media_files=[{"id": "1", "type": "photo", "file_id": "new_photo"}]
        )
        session.add(entry)
        await session.commit()

        result = await session.execute(
            select(DailyEntry).where(DailyEntry.id == entry.id)
        )
        refreshed = result.scalar_one()

        assert refreshed.photo_file_id == "old_photo"
        assert len(refreshed.media_files) == 1
        print("✅ test_legacy_fields_still_exist passed (смешанная система)")


async def test_delete_legacy_photo():
    """Legacy удаление через API (media_id=legacy-photo)."""
    async with AsyncSessionLocalTest() as session:
        user = User(id=777003, username="test_del_legacy", first_name="Test")
        session.add(user)
        await session.commit()

        entry = DailyEntry(
            user_id=777003,
            entry_date=date.today(),
            photo_file_id="legacy_photo_id",
            media_files=[],
            has_media=True,
        )
        session.add(entry)
        await session.commit()

        # Имитируем delete_media endpoint для legacy
        entry.photo_file_id = None
        entry.has_media = False
        await session.commit()

        result = await session.execute(
            select(DailyEntry).where(DailyEntry.id == entry.id)
        )
        refreshed = result.scalar_one()

        assert refreshed.photo_file_id is None
        assert refreshed.has_media is False
        print("✅ test_delete_legacy_photo passed")


async def main():
    await setup_tables()
    try:
        await test_new_entries_use_media_files_with_id()
        await test_legacy_fields_still_exist()
        await test_delete_legacy_photo()
        print("\n🎉 All media sources tests passed!")
    finally:
        await teardown_tables()


if __name__ == "__main__":
    asyncio.run(main())

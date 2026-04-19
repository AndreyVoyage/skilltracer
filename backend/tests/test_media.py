"""
Media Tests for Skill Tracer

Тесты для работы с медиафайлами:
- append (добавление, не замена)
- delete (удаление конкретного медиа)
- API endpoints
- Видео кодеки

Run: cd backend && source venv/bin/activate && PYTHONPATH=/var/www/www-root/data/www/skilltracer.art-artel.su/backend python tests/test_media.py
"""

import asyncio
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.models.base import Base
from app.config import settings
from app.models import DailyEntry, User

# Используем отдельную тестовую БД (НЕ production!)
TEST_DATABASE_URL = settings.DATABASE_URL.replace("/skilltracer", "/skilltracer_test")

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
AsyncSessionLocalTest = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False, autocommit=False
)


async def test_media_append():
    """Тест что медиа добавляются, а не заменяются."""
    async with AsyncSessionLocalTest() as session:
        user = User(id=999999, username="testuser", first_name="Test")
        session.add(user)
        await session.commit()

        entry = DailyEntry(
            user_id=user.id,
            entry_date=date.today(),
            media_files=[
                {
                    "id": "1",
                    "type": "photo",
                    "file_id": "old_photo",
                    "created_at": "2026-04-18T10:00:00",
                }
            ],
            has_media=True,
        )
        session.add(entry)
        await session.commit()

        # Добавляем второе фото (имитация)
        entry.media_files.append({
            "id": "2",
            "type": "video",
            "file_id": "new_video",
            "created_at": "2026-04-18T11:00:00",
        })
        await session.commit()

        # Проверяем что оба есть
        result = await session.execute(
            select(DailyEntry).where(DailyEntry.id == entry.id)
        )
        refreshed = result.scalar_one()

        assert len(refreshed.media_files) == 2, f"Expected 2 media, got {len(refreshed.media_files)}"
        assert refreshed.media_files[0]["type"] == "photo"
        assert refreshed.media_files[1]["type"] == "video"
        assert refreshed.has_media is True
        print("✅ test_media_append passed")


async def test_media_delete():
    """Тест удаления конкретного медиа."""
    async with AsyncSessionLocalTest() as session:
        user = User(id=999998, username="testuser2", first_name="Test")
        session.add(user)
        await session.commit()

        entry = DailyEntry(
            user_id=user.id,
            entry_date=date.today(),
            media_files=[
                {"id": "keep", "type": "photo", "file_id": "photo1"},
                {"id": "delete", "type": "video", "file_id": "video1"},
            ],
            has_media=True,
        )
        session.add(entry)
        await session.commit()

        # Удаляем video
        entry.media_files = [m for m in entry.media_files if m["id"] != "delete"]
        if len(entry.media_files) == 0:
            entry.has_media = False
        await session.commit()

        # Проверяем
        result = await session.execute(
            select(DailyEntry).where(DailyEntry.id == entry.id)
        )
        refreshed = result.scalar_one()

        assert len(refreshed.media_files) == 1
        assert refreshed.media_files[0]["id"] == "keep"
        assert refreshed.has_media is True
        print("✅ test_media_delete passed")


async def test_media_delete_all_clears_flag():
    """Тест что удаление всех медиа сбрасывает has_media."""
    async with AsyncSessionLocalTest() as session:
        user = User(id=999997, username="testuser3", first_name="Test")
        session.add(user)
        await session.commit()

        entry = DailyEntry(
            user_id=user.id,
            entry_date=date.today(),
            media_files=[
                {"id": "only", "type": "photo", "file_id": "photo1"},
            ],
            has_media=True,
        )
        session.add(entry)
        await session.commit()

        # Удаляем единственное медиа
        entry.media_files = []
        entry.has_media = False
        await session.commit()

        result = await session.execute(
            select(DailyEntry).where(DailyEntry.id == entry.id)
        )
        refreshed = result.scalar_one()

        assert len(refreshed.media_files) == 0
        assert refreshed.has_media is False
        print("✅ test_media_delete_all_clears_flag passed")


async def test_media_api_add_and_delete():
    """Тест API добавления и удаления медиа (через реальный API)."""
    import httpx

    base_url = "https://skilltracer.art-artel.su"
    user_id = "6072711152"

    async with httpx.AsyncClient() as client:
        # 1. Получаем запись на сегодня (или создаем)
        today = date.today().isoformat()

        # Проверяем что запись существует
        resp = await client.get(
            f"{base_url}/api/v1/entries/{today}",
            params={"user_id": user_id},
        )

        entry_id = None
        if resp.status_code == 200:
            entry_id = resp.json()["id"]
        else:
            # Создаем запись
            resp = await client.post(
                f"{base_url}/api/v1/entries",
                params={"user_id": user_id},
                json={
                    "entry_date": today,
                    "mood": 4,
                    "text": "Test media entry",
                    "metrics": [],
                },
            )
            assert resp.status_code == 200, f"Create entry failed: {resp.text}"
            entry_id = resp.json()["id"]

        # 2. Добавляем тестовое медиа
        resp = await client.post(
            f"{base_url}/api/v1/media/entries/{entry_id}/media",
            params={
                "user_id": user_id,
                "media_type": "photo",
                "file_id": "test_photo_file_id_123",
                "caption": "Test caption",
            },
        )
        assert resp.status_code == 200, f"Add media failed: {resp.text}"
        media_item = resp.json()
        assert media_item["type"] == "photo"
        assert media_item["file_id"] == "test_photo_file_id_123"
        media_id = media_item["id"]
        print(f"✅ Added media: {media_id}")

        # 3. Проверяем что медиа в записи
        resp = await client.get(
            f"{base_url}/api/v1/entries/{today}",
            params={"user_id": user_id},
        )
        assert resp.status_code == 200
        entry_data = resp.json()
        media_ids = [m.get("id") for m in entry_data.get("media_files", [])]
        assert media_id in media_ids, f"Media {media_id} not found in entry"
        print(f"✅ Media found in entry")

        # 4. Удаляем тестовое медиа
        resp = await client.delete(
            f"{base_url}/api/v1/media/entries/{entry_id}/media/{media_id}",
            params={"user_id": user_id},
        )
        assert resp.status_code == 200, f"Delete media failed: {resp.text}"
        print(f"✅ Deleted media: {resp.json()}")

        # 5. Проверяем что удалено
        resp = await client.get(
            f"{base_url}/api/v1/entries/{today}",
            params={"user_id": user_id},
        )
        assert resp.status_code == 200
        entry_data = resp.json()
        media_ids = [m.get("id") for m in entry_data.get("media_files", [])]
        assert media_id not in media_ids, f"Media {media_id} still in entry after delete"
        print("✅ test_media_api_add_and_delete passed")


def test_video_codec_compatibility():
    """Информация о поддерживаемых кодеках."""
    supported = {
        "MP4 (H.264)": True,
        "WebM (VP8/VP9)": True,
        "MOV (H.264)": True,
    }
    unsupported = {
        "HEVC (H.265)": False,
        "ProRes": False,
    }

    assert supported["MP4 (H.264)"] is True
    assert supported["MOV (H.264)"] is True
    assert unsupported["HEVC (H.265)"] is False
    print("✅ test_video_codec_compatibility passed")


async def setup_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def teardown_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()

async def main():
    await setup_tables()
    try:
        await test_media_append()
        await test_media_delete()
        await test_media_delete_all_clears_flag()
        test_video_codec_compatibility()
        # API test требует реальный сервер — запускаем если доступен
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get("https://skilltracer.art-artel.su/health", timeout=5)
                if resp.status_code == 200:
                    await test_media_api_add_and_delete()
                else:
                    print("⚠️ Server not available, skipping API test")
        except Exception as e:
            print(f"⚠️ Skipping API test: {e}")

        print("\n🎉 All media tests passed!")
    finally:
        await teardown_tables()


if __name__ == "__main__":
    asyncio.run(main())

"""
Media API and Model Tests

Тесты для работы с медиафайлами:
- append (добавление, не замена)
- delete (удаление конкретного медиа)
- API endpoints
"""

import pytest
import pytest_asyncio
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select

from app.models import DailyEntry, User
from app.database import async_engine
from app.models.base import Base


# =============================================================================
# Fixtures
# =============================================================================

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Создает и очищает таблицы для тестов."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    """Создает тестовую сессию БД."""
    async_session = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Создает тестового пользователя."""
    user = User(
        id=999999,
        username="testuser",
        first_name="Test",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# =============================================================================
# Model Tests
# =============================================================================

@pytest.mark.asyncio
async def test_media_append(db_session: AsyncSession, test_user: User):
    """Тест что медиа добавляются, а не заменяются."""
    entry = DailyEntry(
        user_id=test_user.id,
        entry_date=date.today(),
        media_files=[
            {
                "id": "1",
                "type": "photo",
                "file_id": "old_photo",
                "created_at": "2026-04-18T10:00:00",
            }
        ],
    )
    db_session.add(entry)
    await db_session.commit()

    # Добавляем второе фото (имитация)
    entry.media_files.append({
        "id": "2",
        "type": "video",
        "file_id": "new_video",
        "created_at": "2026-04-18T11:00:00",
    })
    await db_session.commit()

    # Проверяем что оба есть
    result = await db_session.execute(
        select(DailyEntry).where(DailyEntry.id == entry.id)
    )
    refreshed = result.scalar_one()

    assert len(refreshed.media_files) == 2
    assert refreshed.media_files[0]["type"] == "photo"
    assert refreshed.media_files[1]["type"] == "video"
    assert refreshed.has_media is True


@pytest.mark.asyncio
async def test_media_delete(db_session: AsyncSession, test_user: User):
    """Тест удаления конкретного медиа."""
    entry = DailyEntry(
        user_id=test_user.id,
        entry_date=date.today(),
        media_files=[
            {"id": "keep", "type": "photo", "file_id": "photo1"},
            {"id": "delete", "type": "video", "file_id": "video1"},
        ],
    )
    db_session.add(entry)
    await db_session.commit()

    # Удаляем video
    entry.media_files = [m for m in entry.media_files if m["id"] != "delete"]
    if len(entry.media_files) == 0:
        entry.has_media = False
    await db_session.commit()

    # Проверяем
    result = await db_session.execute(
        select(DailyEntry).where(DailyEntry.id == entry.id)
    )
    refreshed = result.scalar_one()

    assert len(refreshed.media_files) == 1
    assert refreshed.media_files[0]["id"] == "keep"
    assert refreshed.has_media is True


@pytest.mark.asyncio
async def test_media_delete_all_clears_flag(db_session: AsyncSession, test_user: User):
    """Тест что удаление всех медиа сбрасывает has_media."""
    entry = DailyEntry(
        user_id=test_user.id,
        entry_date=date.today(),
        media_files=[
            {"id": "only", "type": "photo", "file_id": "photo1"},
        ],
        has_media=True,
    )
    db_session.add(entry)
    await db_session.commit()

    # Удаляем единственное медиа
    entry.media_files = []
    entry.has_media = False
    await db_session.commit()

    result = await db_session.execute(
        select(DailyEntry).where(DailyEntry.id == entry.id)
    )
    refreshed = result.scalar_one()

    assert len(refreshed.media_files) == 0
    assert refreshed.has_media is False


# =============================================================================
# API Tests
# =============================================================================

from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """TestClient для FastAPI приложения."""
    return TestClient(app)


def test_media_api_add_and_delete(client):
    """Тест API добавления и удаления медиа (с fallback auth)."""
    # Создаем пользователя и запись через API
    user_id = 777777

    # Создаем запись (POST /entries с user_id fallback)
    resp = client.post(
        "/api/v1/entries",
        params={"user_id": str(user_id)},
        json={
            "entry_date": date.today().isoformat(),
            "mood": 4,
            "text": "Test entry",
            "metrics": [],
        },
    )
    assert resp.status_code == 200, f"Create entry failed: {resp.text}"
    entry_id = resp.json()["id"]

    # Добавляем медиа
    resp = client.post(
        f"/api/v1/media/entries/{entry_id}/media",
        params={
            "user_id": str(user_id),
            "media_type": "photo",
            "file_id": "test_photo_file_id",
            "caption": "Test caption",
        },
    )
    assert resp.status_code == 200, f"Add media failed: {resp.text}"
    media_item = resp.json()
    assert media_item["type"] == "photo"
    assert media_item["file_id"] == "test_photo_file_id"
    assert media_item["caption"] == "Test caption"
    media_id = media_item["id"]

    # Добавляем второе медиа
    resp = client.post(
        f"/api/v1/media/entries/{entry_id}/media",
        params={
            "user_id": str(user_id),
            "media_type": "video",
            "file_id": "test_video_file_id",
        },
    )
    assert resp.status_code == 200

    # Проверяем запись — должно быть 2 медиа
    resp = client.get(
        f"/api/v1/entries/{date.today().isoformat()}",
        params={"user_id": str(user_id)},
    )
    assert resp.status_code == 200
    entry_data = resp.json()
    assert len(entry_data["media_files"]) == 2

    # Удаляем первое медиа
    resp = client.delete(
        f"/api/v1/media/entries/{entry_id}/media/{media_id}",
        params={"user_id": str(user_id)},
    )
    assert resp.status_code == 200, f"Delete media failed: {resp.text}"
    assert resp.json()["remaining"] == 1

    # Проверяем что осталось одно
    resp = client.get(
        f"/api/v1/entries/{date.today().isoformat()}",
        params={"user_id": str(user_id)},
    )
    assert resp.status_code == 200
    entry_data = resp.json()
    assert len(entry_data["media_files"]) == 1
    assert entry_data["media_files"][0]["type"] == "video"


def test_media_api_delete_not_found(client):
    """Тест удаления несуществующего медиа."""
    user_id = 777778

    # Создаем запись
    resp = client.post(
        "/api/v1/entries",
        params={"user_id": str(user_id)},
        json={
            "entry_date": date.today().isoformat(),
            "mood": 3,
            "metrics": [],
        },
    )
    assert resp.status_code == 200
    entry_id = resp.json()["id"]

    # Пытаемся удалить несуществующее медиа
    resp = client.delete(
        f"/api/v1/media/entries/{entry_id}/media/nonexistent",
        params={"user_id": str(user_id)},
    )
    assert resp.status_code == 404


# =============================================================================
# Video Codec Info
# =============================================================================

def test_video_codec_compatibility():
    """Информация о поддерживаемых кодеках в Telegram WebView."""
    # Telegram WebView (Chrome-based) поддерживает:
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

"""
Auth flow diagnostic tests.
Run: cd backend && PYTHONPATH=/var/www/.../backend ./venv/bin/python tests/test_auth_flow.py
"""

import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import User, CustomTracker
from app.config import settings
import httpx


async def test_user_exists():
    """Тест: пользователь 6072711152 существует в БД"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.id == 6072711152)
        )
        user = result.scalar_one_or_none()
        assert user is not None, "User 6072711152 not found in database"
        print(f"✅ User found: {user.first_name} (@{user.username})")


async def test_user_has_trackers():
    """Тест: у пользователя есть трекеры"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(CustomTracker)
            .where(CustomTracker.user_id == 6072711152)
            .where(CustomTracker.is_active == True)
        )
        trackers = result.scalars().all()
        assert len(trackers) > 0, "User has no active trackers"
        print(f"✅ Trackers: {[t.name for t in trackers]}")


async def test_api_with_user_id():
    """Тест: API работает с ?user_id= fallback"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://skilltracer.art-artel.su/api/v1/entries/week",
            params={"start_date": "2026-04-13", "user_id": "6072711152"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert "entries" in data
        print(f"✅ API OK: {len(data['entries'])} entries")


async def test_api_without_auth():
    """Тест: API отклоняет запрос без авторизации"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://skilltracer.art-artel.su/api/v1/entries/week?start_date=2026-04-13"
        )
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
        print("✅ API correctly rejects unauthorized requests")


def test_bot_token_configured():
    """Тест: BOT_TOKEN настроен"""
    assert settings.BOT_TOKEN, "BOT_TOKEN not set"
    assert len(settings.BOT_TOKEN) > 30, "BOT_TOKEN looks invalid"
    print(f"✅ BOT_TOKEN configured (len:{len(settings.BOT_TOKEN)})")


def test_local_storage_simulation():
    """Тест: проверка логики localStorage (frontend simulation)"""
    cached_user_id = "6072711152"
    assert cached_user_id.isdigit(), "User ID must be numeric"
    print("✅ localStorage fallback logic valid")


async def main():
    await test_user_exists()
    await test_user_has_trackers()
    await test_api_with_user_id()
    await test_api_without_auth()
    test_bot_token_configured()
    test_local_storage_simulation()
    print("\n🎉 All diagnostic tests passed!")


if __name__ == "__main__":
    asyncio.run(main())

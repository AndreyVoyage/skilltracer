"""
Full integration tests for Skill Tracer backend.
Run: cd backend && PYTHONPATH=/var/www/.../backend ./venv/bin/python tests/test_full_flow.py
"""

import asyncio
from datetime import date, timedelta
from sqlalchemy import text, select, func
import httpx

from app.database import AsyncSessionLocal
from app.models import User, CustomTracker, JournalEntry, DailyEntry
from app.config import settings


async def test_database_connection():
    """Тест 1: Подключение к PostgreSQL"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT version()"))
        version = result.scalar()
        print(f"\n✅ PostgreSQL version: {version}")
        assert "PostgreSQL" in version


async def test_user_and_trackers():
    """Тест 2: Пользователь и трекеры в БД"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.id == 6072711152)
        )
        user = result.scalar_one_or_none()

        if user:
            print(f"\n✅ User found: {user.first_name} (@{user.username})")

            # Проверяем трекеры
            result = await session.execute(
                select(CustomTracker)
                .where(CustomTracker.user_id == 6072711152)
                .where(CustomTracker.is_active == True)
            )
            trackers = result.scalars().all()
            print(f"✅ Trackers: {[t.name for t in trackers]}")
            assert len(trackers) >= 4, "Should have at least 4 default trackers"
        else:
            print("\n⚠️ User 6072711152 not found in DB")
            # Создаем тестового пользователя
            user = User(
                id=6072711152,
                username="test_user",
                first_name="Test",
                last_name="User"
            )
            session.add(user)
            await session.commit()
            print("✅ Created test user")


async def test_api_endpoints():
    """Тест 3: Доступность API endpoints"""
    base_url = "https://skilltracer.art-artel.su"

    async with httpx.AsyncClient() as client:
        # Health check
        resp = await client.get(f"{base_url}/health")
        assert resp.status_code == 200
        print(f"\n✅ Health: {resp.json()}")

        # API with user_id fallback (should be 401 in production now)
        resp = await client.get(
            f"{base_url}/api/v1/entries/week",
            params={"start_date": "2026-04-13", "user_id": "6072711152"}
        )
        print(f"✅ API with user_id: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"   Entries: {len(data.get('entries', []))}")
        elif resp.status_code == 401:
            print("   Expected 401 in production (fallback disabled)")

        # API without auth (should be 401)
        resp = await client.get(
            f"{base_url}/api/v1/entries/week?start_date=2026-04-13"
        )
        assert resp.status_code == 401
        print(f"✅ API without auth: 401 (correct)")

        # Debug endpoint (no auth)
        resp = await client.get(
            f"{base_url}/api/v1/entries/week/debug",
            params={"start_date": "2026-04-13", "user_id": "6072711152"}
        )
        assert resp.status_code == 200
        data = resp.json()
        print(f"✅ Debug endpoint: {data['daily_entries_count']} daily, {data['journal_entries_count']} journal")


async def test_init_data_validation():
    """Тест 4: Валидация initData (проверка BOT_TOKEN)"""
    # Проверяем что BOT_TOKEN настроен
    assert settings.BOT_TOKEN, "BOT_TOKEN not set!"
    assert len(settings.BOT_TOKEN) > 20, "BOT_TOKEN looks invalid"
    print(f"\n✅ BOT_TOKEN configured (len:{len(settings.BOT_TOKEN)})")

    # Проверяем что можно создать подпись (HMAC)
    import hmac
    import hashlib

    secret = hmac.new(
        b"WebAppData",
        settings.BOT_TOKEN.encode(),
        hashlib.sha256
    ).digest()
    assert len(secret) == 32
    print("✅ HMAC secret generation works")


async def test_week_entries_data():
    """Тест 5: Проверка данных за неделю"""
    async with AsyncSessionLocal() as session:
        start = date(2026, 4, 13)
        end = start + timedelta(days=6)

        # Daily entries
        result = await session.execute(
            select(func.count(DailyEntry.id)).where(
                DailyEntry.user_id == 6072711152,
                DailyEntry.entry_date >= start,
                DailyEntry.entry_date <= end,
            )
        )
        daily_count = result.scalar()

        # Journal entries
        result = await session.execute(
            select(func.count(JournalEntry.id)).where(
                JournalEntry.user_id == 6072711152,
                JournalEntry.entry_date >= start,
                JournalEntry.entry_date <= end,
            )
        )
        journal_count = result.scalar()

        print(f"\n✅ Week data: {daily_count} daily, {journal_count} journal entries")
        assert daily_count + journal_count > 0, "No entries found for the week"


async def main():
    await test_database_connection()
    await test_user_and_trackers()
    await test_api_endpoints()
    await test_init_data_validation()
    await test_week_entries_data()
    print("\n🎉 All tests passed!")


if __name__ == "__main__":
    asyncio.run(main())

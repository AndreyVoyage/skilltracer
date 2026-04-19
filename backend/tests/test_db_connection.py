"""
Integration tests for PostgreSQL database connection.
Run with: cd backend && python tests/test_db_connection.py
"""

import asyncio
from datetime import date, timedelta
from sqlalchemy import text, select
from app.database import AsyncSessionLocal
from app.models import User, CustomTracker, JournalEntry


async def test_database_connection():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1
        print("✅ test_database_connection passed")


async def test_user_exists():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        assert len(users) > 0
        print(f"✅ test_user_exists passed ({len(users)} users)")


async def test_trackers_exist_for_user():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(CustomTracker).where(CustomTracker.user_id == 6072711152)
        )
        trackers = result.scalars().all()
        assert len(trackers) == 4
        names = [t.name for t in trackers]
        assert "Здоровье" in names
        assert "Спорт" in names
        assert "Учёба" in names
        assert "Отдых" in names
        print(f"✅ test_trackers_exist_for_user passed ({names})")


async def test_journal_entries_exist():
    start = date(2026, 4, 13)
    end = start + timedelta(days=6)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(JournalEntry).where(
                JournalEntry.user_id == 6072711152,
                JournalEntry.entry_date >= start,
                JournalEntry.entry_date <= end,
            )
        )
        entries = result.scalars().all()
        assert len(entries) > 0
        print(f"✅ test_journal_entries_exist passed ({len(entries)} entries)")


async def main():
    await test_database_connection()
    await test_user_exists()
    await test_trackers_exist_for_user()
    await test_journal_entries_exist()
    print("\n🎉 All DB tests passed!")


if __name__ == "__main__":
    asyncio.run(main())

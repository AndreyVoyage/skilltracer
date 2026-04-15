"""
Полная проверка системы Skill Tracer (Phase 2).

Проверяет:
  1. Токен бота и webhook
  2. Подключение к БД (async)
  3. Генерацию PNG
  4. Валидацию initData
  5. Основные API endpoints

Запуск:
    cd backend
    python scripts/verify_system.py
"""

import asyncio
import hmac
import hashlib
import json
import os
import sys
import time
import urllib.parse
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.database import init_db, AsyncSessionLocal
from app.api.deps import validate_telegram_init_data
from app.services.report_generator import generate_week_poster
from app.models import User, DailyEntry, CustomTracker


async def check_bot() -> dict:
    """Проверка бота и webhook."""
    from aiogram import Bot
    
    print("🤖 Проверка бота...")
    result = {"ok": False, "error": None}
    try:
        bot = Bot(token=settings.BOT_TOKEN)
        me = await bot.get_me()
        print(f"   Бот: @{me.username} (ID: {me.id})")
        
        wh = await bot.get_webhook_info()
        expected_url = f"{settings.WEBAPP_URL}/webhook"
        if wh.url != expected_url:
            print(f"   ⚠️ Webhook не настроен: {wh.url} != {expected_url}")
            result["webhook_mismatch"] = True
        else:
            print(f"   ✅ Webhook: {wh.url}")
        
        await bot.session.close()
        result["ok"] = True
    except Exception as e:
        result["error"] = str(e)
        print(f"   ❌ Ошибка: {e}")
    return result


async def check_database() -> dict:
    """Проверка БД."""
    print("🗄️  Проверка базы данных...")
    result = {"ok": False, "error": None}
    try:
        await init_db(retries=3, delay=2)
        async with AsyncSessionLocal() as db:
            from sqlalchemy import text
            from app.models import Base
            from app.database import async_engine
            async with async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            r = await db.execute(text("SELECT 1"))
            assert r.scalar() == 1
            
            # Проверяем основные таблицы
            tables = ["users", "daily_entries", "custom_trackers", "week_reports", "telegram_queue"]
            for t in tables:
                r = await db.execute(text(f"SELECT COUNT(*) FROM {t}"))
                count = r.scalar()
                print(f"   {t}: {count} rows")
        
        print("   ✅ БД доступна")
        result["ok"] = True
    except Exception as e:
        result["error"] = str(e)
        print(f"   ❌ Ошибка: {e}")
    return result


async def check_png_generation() -> dict:
    """Проверка генерации PNG."""
    print("🖼️  Проверка генерации отчета...")
    result = {"ok": False, "error": None}
    
    async with AsyncSessionLocal() as db:
        user_id = 888888888
        from sqlalchemy import delete, select
        from app.models import EntryMetric
        # Удаляем метрики перед записями (для совместимости без FK)
        entry_ids = select(DailyEntry.id).where(DailyEntry.user_id == user_id)
        await db.execute(delete(EntryMetric).where(EntryMetric.entry_id.in_(entry_ids)))
        await db.execute(delete(DailyEntry).where(DailyEntry.user_id == user_id))
        await db.execute(delete(CustomTracker).where(CustomTracker.user_id == user_id))
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()
        
        user = User(id=user_id, username="verify", first_name="Verify")
        db.add(user)
        await db.flush()
        
        tracker = CustomTracker(user_id=user_id, name="Тест", icon="🧪")
        db.add(tracker)
        await db.flush()
        
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        for i in range(3):
            entry = DailyEntry(
                user_id=user_id,
                entry_date=monday + timedelta(days=i),
                mood=4,
                text=f"День {i+1}",
            )
            db.add(entry)
            await db.flush()
            from app.models import EntryMetric
            db.add(EntryMetric(entry_id=entry.id, tracker_id=tracker.id, value=4))
        await db.commit()
        
        try:
            buf = await generate_week_poster(user_id, monday, db, bot=None)
            size = buf.getbuffer().nbytes
            from PIL import Image
            buf.seek(0)
            img = Image.open(buf)
            
            assert img.size == (800, 1200), f"Неверный размер: {img.size}"
            assert size > 1000, "Файл слишком мал"
            
            print(f"   ✅ Размер: {img.size}, файл: {size} bytes")
            result["ok"] = True
        except Exception as e:
            result["error"] = str(e)
            print(f"   ❌ Ошибка: {e}")
        finally:
            from sqlalchemy import select
            from app.models import EntryMetric
            entry_ids = select(DailyEntry.id).where(DailyEntry.user_id == user_id)
            await db.execute(delete(EntryMetric).where(EntryMetric.entry_id.in_(entry_ids)))
            await db.execute(delete(DailyEntry).where(DailyEntry.user_id == user_id))
            await db.execute(delete(CustomTracker).where(CustomTracker.user_id == user_id))
            await db.execute(delete(User).where(User.id == user_id))
            await db.commit()
    
    return result


def check_init_data() -> dict:
    """Проверка валидации initData."""
    print("🔐 Проверка валидации initData...")
    result = {"ok": False, "error": None}
    
    try:
        # Генерируем валидные данные
        user = json.dumps({"id": 123456, "username": "test", "first_name": "Test"})
        data = {
            "user": user,
            "auth_date": str(int(time.time())),
            "query_id": "verify_query",
        }
        data_check_string = '\n'.join(f"{k}={v}" for k, v in sorted(data.items()))
        secret_key = hmac.new(b"WebAppData", settings.BOT_TOKEN.encode(), hashlib.sha256).digest()
        hash_value = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        data["hash"] = hash_value
        init_data = urllib.parse.urlencode(data)
        
        validated = validate_telegram_init_data(init_data)
        assert validated["id"] == 123456
        print("   ✅ Валидные initData прошли проверку")
        
        # Невалидные данные
        try:
            validate_telegram_init_data("fake=123&hash=wrong")
            print("   ❌ Невалидные initData должны были упасть")
            result["error"] = "Invalid initData accepted"
            return result
        except Exception:
            print("   ✅ Невалидные initData отклонены")
        
        result["ok"] = True
    except Exception as e:
        result["error"] = str(e)
        print(f"   ❌ Ошибка: {e}")
    return result


async def check_api() -> dict:
    """Быстрая проверка API endpoints."""
    print("🌐 Проверка API endpoints...")
    result = {"ok": False, "error": None}
    try:
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        
        # Health
        r = client.get("/health")
        assert r.status_code == 200, f"Health failed: {r.status_code}"
        print("   ✅ /health")
        
        # Root
        r = client.get("/")
        assert r.status_code == 200
        print("   ✅ /")
        
        result["ok"] = True
    except Exception as e:
        result["error"] = str(e)
        print(f"   ❌ Ошибка: {e}")
    return result


async def main():
    sys.stdout.reconfigure(encoding='utf-8')
    print("=" * 60)
    print("Skill Tracer Phase 2 - System Verification")
    print("=" * 60)
    print()
    
    checks = {
        "bot": await check_bot(),
        "database": await check_database(),
        "png": await check_png_generation(),
        "init_data": check_init_data(),
        "api": await check_api(),
    }
    
    print()
    print("=" * 60)
    print("Результаты:")
    print("=" * 60)
    
    all_ok = all(c["ok"] for c in checks.values())
    for name, res in checks.items():
        status = "✅" if res["ok"] else "❌"
        print(f"{status} {name:12s} {'OK' if res['ok'] else res.get('error', 'FAILED')}")
    
    print()
    if all_ok:
        print("🎉 Все проверки пройдены! Система готова к Phase 2.")
        sys.exit(0)
    else:
        print("⚠️  Некоторые проверки не пройдены. См. выше.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

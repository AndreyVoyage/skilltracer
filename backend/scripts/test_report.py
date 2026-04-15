"""
Быстрый тест генерации PNG отчета.

Запуск:
    cd backend
    python scripts/test_report.py

Требования:
    - Установлены зависимости из requirements.txt
    - Доступна БД (DATABASE_URL в .env)
"""

import asyncio
import io
import os
import sys
import tracemalloc
from datetime import date, timedelta

# Добавляем backend в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, init_db, async_engine
from app.models import User, DailyEntry, CustomTracker
from app.models.base import Base
from app.services.report_generator import generate_week_poster


async def create_test_data(db: AsyncSession) -> tuple[int, date]:
    """Создает тестового пользователя и записи за текущую неделю."""
    user_id = 999999999
    
    # Очищаем старые тестовые данные
    from sqlalchemy import delete
    await db.execute(delete(DailyEntry).where(DailyEntry.user_id == user_id))
    await db.execute(delete(CustomTracker).where(CustomTracker.user_id == user_id))
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()
    
    user = User(
        id=user_id,
        username="testreport",
        first_name="Test",
        last_name="Report",
    )
    db.add(user)
    await db.flush()
    
    tracker1 = CustomTracker(user_id=user_id, name="Спорт", icon="🏋️")
    tracker2 = CustomTracker(user_id=user_id, name="Чтение", icon="📚")
    db.add_all([tracker1, tracker2])
    await db.flush()
    
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    
    for i in range(5):
        entry = DailyEntry(
            user_id=user_id,
            entry_date=monday + timedelta(days=i),
            mood=3 + (i % 3),
            text=f"Тестовая запись дня {i+1}",
        )
        db.add(entry)
        await db.flush()
        
        from app.models import EntryMetric
        db.add_all([
            EntryMetric(entry_id=entry.id, tracker_id=tracker1.id, value=3 + (i % 2)),
            EntryMetric(entry_id=entry.id, tracker_id=tracker2.id, value=4),
        ])
    
    await db.commit()
    return user_id, monday


async def main():
    print("🚀 Запуск теста генерации отчета...")
    
    # Инициализация БД
    try:
        await init_db(retries=3, delay=2)
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        sys.exit(1)
    
    async with AsyncSessionLocal() as db:
        user_id, week_start = await create_test_data(db)
        print(f"✅ Тестовые данные созданы: user_id={user_id}, week={week_start}")
        
        # Замер памяти
        tracemalloc.start()
        
        start = asyncio.get_event_loop().time()
        try:
            # Генерируем без бота (фото не скачаются, но структура проверится)
            buf = await generate_week_poster(user_id, week_start, db, bot=None)
        except Exception as e:
            print(f"❌ Ошибка генерации: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        elapsed = asyncio.get_event_loop().time() - start
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        size = buf.getbuffer().nbytes
        print(f"✅ Отчет сгенерирован за {elapsed:.2f} сек")
        print(f"   Размер файла: {size} bytes ({size/1024:.1f} KB)")
        print(f"   RAM текущая: {current / 1024 / 1024:.2f} MB")
        print(f"   RAM пиковая: {peak / 1024 / 1024:.2f} MB")
        
        # Проверяем что это валидное изображение
        from PIL import Image
        buf.seek(0)
        img = Image.open(buf)
        print(f"   Размеры изображения: {img.size}")
        
        assert img.size[0] == 800, "Ширина должна быть 800"
        assert img.size[1] == 1200, "Высота должна быть 1200"
        assert size > 1000, "Файл не должен быть пустым"
        
        # Сохраняем для визуальной проверки
        out_path = "/tmp/test_report.jpg" if os.name != "nt" else "test_report.jpg"
        with open(out_path, "wb") as f:
            f.write(buf.getvalue())
        print(f"💾 Сохранено в: {out_path}")
        
        # Очистка
        from sqlalchemy import delete
        await db.execute(delete(DailyEntry).where(DailyEntry.user_id == user_id))
        await db.execute(delete(CustomTracker).where(CustomTracker.user_id == user_id))
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()
    
    print("\n🎉 Тест пройден успешно!")
    print(f"   Пик RAM: {peak / 1024 / 1024:.2f} MB (< 100MB: {'✅' if peak < 100*1024*1024 else '❌'})")


if __name__ == "__main__":
    asyncio.run(main())

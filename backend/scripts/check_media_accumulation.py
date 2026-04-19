#!/usr/bin/env python3
"""
Диагностика проблемы с медиа: проверяем что происходит в БД
"""
import asyncio
import sys
from datetime import date

sys.path.insert(0, '/var/www/www-root/data/www/skilltracer.art-artel.su/backend')

from app.database import AsyncSessionLocal
from app.models import DailyEntry, User
from sqlalchemy import select, inspect


async def check_today_entries():
    user_id = 6072711152
    today = date.today()

    print(f"🔍 Проверка записей за {today} для user {user_id}")
    print("=" * 50)

    async with AsyncSessionLocal() as session:
        # 1. Ищем ВСЕ записи за сегодня (вдруг их несколько?)
        result = await session.execute(
            select(DailyEntry)
            .where(DailyEntry.user_id == user_id)
            .where(DailyEntry.entry_date == today)
        )
        entries = result.scalars().all()

        print(f"📊 Найдено записей за сегодня: {len(entries)}")

        if len(entries) > 1:
            print("⚠️ ВНИМАНИЕ: Создано несколько записей на один день! Это баг.")
            for i, entry in enumerate(entries):
                print(f"  Запись #{i+1} ID={entry.id}")
                print(f"    Создана: {entry.created_at}")
                print(f"    Медиа: {len(entry.media_files or [])}")

        if not entries:
            print("❌ Записей нет")
            return

        # Берем первую
        entry = entries[0]
        print(f"\n📋 Детали записи ID={entry.id}:")
        print(f"  Создана: {entry.created_at}")
        print(f"  Обновлена: {entry.updated_at}")
        print(f"  Has media (флаг): {entry.has_media}")
        print(f"")

        # 2. Проверяем структуру media_files
        print("🔍 Поле media_files:")
        if entry.media_files is None:
            print("  ❌ NULL (None)")
        elif len(entry.media_files) == 0:
            print("  ⚠️ Пустой массив []")
        else:
            print(f"  ✅ Количество файлов: {len(entry.media_files)}")
            for i, media in enumerate(entry.media_files):
                print(f"    [{i}] ID: {media.get('id', 'NO_ID')}")
                print(f"         Type: {media.get('type', 'NO_TYPE')}")
                print(f"         FileID: {media.get('file_id', 'NO_FILEID')[:30]}...")
                print(f"         Created: {media.get('created_at', 'NO_DATE')}")

        # 3. Проверяем deprecated поля
        print(f"\n🔍 Deprecated поля (старая схема):")
        deprecated_found = False

        mapper = inspect(DailyEntry)
        columns = [c.name for c in mapper.columns]

        if 'photo_file_id' in columns:
            val = entry.photo_file_id
            print(f"  photo_file_id: {val if val else 'NULL'}")
            if val:
                deprecated_found = True

        if 'video_file_id' in columns:
            val = entry.video_file_id
            print(f"  video_file_id: {val if val else 'NULL'}")
            if val:
                deprecated_found = True

        if 'voice_file_id' in columns:
            val = entry.voice_file_id
            print(f"  voice_file_id: {val if val else 'NULL'}")
            if val:
                deprecated_found = True

        if not deprecated_found:
            print("  (все NULL)")

        # 4. Проверяем историю обновлений
        if entry.updated_at and entry.created_at:
            if entry.updated_at != entry.created_at:
                diff = (entry.updated_at - entry.created_at).total_seconds()
                print(f"\n⏱ Запись обновлялась: {diff:.1f} сек после создания")
                print("   (Это нормально - значит append работает)")
            else:
                print(f"\n⏱ Запись не обновлялась (created_at == updated_at)")

        # 5. Рекомендация
        print(f"\n{'=' * 50}")
        if len(entries) > 1:
            print("🚨 ПРОБЛЕМА: Создается новая запись вместо обновления старой!")
            print("   Исправь: _get_or_create_entry должен возвращать существующую")
        elif entry.media_files and len(entry.media_files) > 0:
            print("✅ В БД медиа сохранены корректно")
            print(f"   Всего файлов: {len(entry.media_files)}")
            print("   Если в приложении видно меньше - проблема в Frontend")
        else:
            print("⚠️ В БД нет медиа - бот не сохраняет при получении фото")


if __name__ == "__main__":
    asyncio.run(check_today_entries())

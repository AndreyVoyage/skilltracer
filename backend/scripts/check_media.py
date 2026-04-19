#!/usr/bin/env python3
"""
Скрипт проверки: сколько медиа должно быть vs сколько в БД
"""
import asyncio
from datetime import date
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import DailyEntry

async def diagnose():
    async with AsyncSessionLocal() as session:
        # Проверяем записи за сегодня для user 6072711152
        user_id = 6072711152
        today = date.today()
        
        result = await session.execute(
            select(DailyEntry)
            .where(DailyEntry.user_id == user_id)
            .where(DailyEntry.entry_date == today)
        )
        entry = result.scalar_one_or_none()
        
        if not entry:
            print("❌ Запись за сегодня не найдена!")
            return
        
        print(f"✅ Найдена запись ID: {entry.id}")
        print(f"📅 Дата: {entry.entry_date}")
        print(f"")
        
        # Проверяем структуру данных
        print("🔍 Проверка полей медиа:")
        print(f"   has_media: {entry.has_media}")
        
        # Проверяем устаревшие поля (если есть)
        if hasattr(entry, 'photo_file_id'):
            print(f"   photo_file_id (deprecated): {entry.photo_file_id}")
        if hasattr(entry, 'video_file_id'):
            print(f"   video_file_id (deprecated): {entry.video_file_id}")
        if hasattr(entry, 'voice_file_id'):
            print(f"   voice_file_id (deprecated): {entry.voice_file_id}")
            
        # Проверяем новое поле массива
        print(f"")
        print("🔍 Проверка media_files (JSON):")
        if entry.media_files:
            print(f"   Количество файлов: {len(entry.media_files)}")
            for i, media in enumerate(entry.media_files):
                print(f"   [{i}] ID: {media.get('id', 'N/A')}, Type: {media.get('type', 'N/A')}, FileID: {media.get('file_id', 'N/A')[:20]}...")
        else:
            print("   ❌ media_files пустой или NULL!")
            
        print(f"")
        print("📊 Итог:")
        if entry.media_files and len(entry.media_files) > 0:
            print(f"   ✅ В БД сохранено {len(entry.media_files)} медиафайлов")
            print(f"   ⚠️ Если в приложении видно меньше - проблема в Frontend (неправильно отображает массив)")
        else:
            print(f"   ❌ В БД нет медиа - проблема в Backend (бот не сохраняет/перезаписывает)")

if __name__ == "__main__":
    asyncio.run(diagnose())

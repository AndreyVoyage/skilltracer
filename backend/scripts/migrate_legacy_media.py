#!/usr/bin/env python3
"""
Миграция: переносит старые photo_file_id/voice_file_id/video_file_id
в новый media_files JSON-массив
"""
import asyncio
import sys
import uuid
from datetime import datetime

sys.path.insert(0, '/var/www/www-root/data/www/skilltracer.art-artel.su/backend')

from app.database import AsyncSessionLocal
from app.models import DailyEntry
from sqlalchemy import select


async def migrate():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(DailyEntry))
        entries = result.scalars().all()

        migrated = 0
        for entry in entries:
            # Если уже есть media_files — пропускаем
            if entry.media_files and len(entry.media_files) > 0:
                continue

            # Переносим из старых полей в новый массив
            media_list = []
            created = entry.created_at.isoformat() if entry.created_at else datetime.now().isoformat()

            if entry.photo_file_id:
                media_list.append({
                    "id": str(uuid.uuid4()),
                    "type": "photo",
                    "file_id": entry.photo_file_id,
                    "created_at": created
                })

            if entry.video_file_id:
                media_list.append({
                    "id": str(uuid.uuid4()),
                    "type": "video",
                    "file_id": entry.video_file_id,
                    "created_at": created
                })

            if entry.voice_file_id:
                media_list.append({
                    "id": str(uuid.uuid4()),
                    "type": "voice",
                    "file_id": entry.voice_file_id,
                    "created_at": created
                })

            if media_list:
                entry.media_files = media_list
                entry.has_media = True
                migrated += 1
                print(f"  Migrated entry ID={entry.id}: {len(media_list)} media items")

        await session.commit()
        print(f"\n✅ Мигрировано записей: {migrated}")


if __name__ == "__main__":
    asyncio.run(migrate())

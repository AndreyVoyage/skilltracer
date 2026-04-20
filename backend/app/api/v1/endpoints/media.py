"""
Media Proxy API

Проксирование медиафайлов из Telegram для WebApp.
Управление медиа в записях (добавление/удаление).
"""

import logging
import uuid
from datetime import date, datetime
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from app.api.deps import get_current_user_or_query, get_db
from app.bot import bot
from app.config import settings
from app.models import DailyEntry, User

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================

class MediaItemOut(BaseModel):
    id: str
    type: str
    file_id: str
    caption: Optional[str] = None
    created_at: str


class FileUrlOut(BaseModel):
    file_id: str
    url: str
    size: Optional[int] = None
    expires_in: int = 3600


# =============================================================================
# File URL / Proxy
# =============================================================================

@router.get("/file-url/{file_id}", response_model=FileUrlOut)
async def get_file_url(file_id: str):
    """
    Получает свежий URL для файла (обновляется каждый раз!).
    Telegram URLs действительны ~1 час.
    """
    try:
        file = await bot.get_file(file_id)

        if not file.file_path:
            raise HTTPException(status_code=404, detail="File path not available")

        download_url = f"https://api.telegram.org/file/bot{settings.BOT_TOKEN}/{file.file_path}"

        return {
            "file_id": file_id,
            "url": download_url,
            "size": file.file_size,
            "expires_in": 3600,
        }
    except Exception as e:
        logger.error(f"Error getting file {file_id}: {e}")
        raise HTTPException(status_code=404, detail=f"File not found or expired: {str(e)}")


@router.get("/{file_id}")
async def get_media(file_id: str):
    """
    Скачивание файла из Telegram по file_id.
    Возвращает потоковый ответ (фото/видео/голосовое).
    """
    try:
        file = await bot.get_file(file_id)
        bio = BytesIO()
        await bot.download_file(file.file_path, destination=bio)
        bio.seek(0)

        # Определяем content-type по расширению
        path = file.file_path or ""
        if path.endswith(".jpg") or path.endswith(".jpeg"):
            media_type = "image/jpeg"
        elif path.endswith(".png"):
            media_type = "image/png"
        elif path.endswith(".mp4"):
            media_type = "video/mp4"
        elif path.endswith(".ogg") or path.endswith(".oga"):
            media_type = "audio/ogg"
        elif path.endswith(".webp"):
            media_type = "image/webp"
        elif path.endswith(".webm"):
            media_type = "video/webm"
        else:
            media_type = "application/octet-stream"

        return StreamingResponse(
            bio,
            media_type=media_type,
            headers={"Cache-Control": "max-age=3600"},
        )
    except Exception as e:
        logger.error(f"Failed to fetch media {file_id}: {e}")
        raise HTTPException(status_code=404, detail="Media not found")


# =============================================================================
# Entry Media Management
# =============================================================================

@router.post("/entries/{entry_id}/media", response_model=MediaItemOut)
async def add_media(
    entry_id: int,
    media_type: str,
    file_id: str,
    caption: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_or_query),
):
    """Добавляет медиа к записи (append, не replace)."""
    result = await db.execute(
        select(DailyEntry).where(DailyEntry.id == entry_id)
    )
    entry = result.scalar_one_or_none()

    if not entry or entry.user_id != user.id:
        raise HTTPException(status_code=404, detail="Entry not found")

    if not entry.media_files:
        entry.media_files = []

    media_item = {
        "id": str(uuid.uuid4()),
        "type": media_type,
        "file_id": file_id,
        "caption": caption,
        "created_at": datetime.now().isoformat(),
    }

    current = entry.media_files or []
    entry.media_files = current + [media_item]
    entry.has_media = True

    await db.commit()
    return MediaItemOut(**media_item)


@router.delete("/entries/{entry_date}/media/{media_id}")
async def delete_media(
    entry_date: date,
    media_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_or_query),
):
    """Удаляет конкретное медиа по ID. Поддерживает legacy поля (photo/video/voice_file_id)."""
    result = await db.execute(
        select(DailyEntry).where(
            DailyEntry.user_id == user.id,
            DailyEntry.entry_date == entry_date,
        )
    )
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    # Legacy support: если ID начинается с legacy- — очищаем deprecated поле
    if media_id.startswith("legacy-"):
        legacy_type = media_id.replace("legacy-", "")
        cleared = False
        if legacy_type == "photo" and entry.photo_file_id:
            entry.photo_file_id = None
            cleared = True
        elif legacy_type == "video" and entry.video_file_id:
            entry.video_file_id = None
            cleared = True
        elif legacy_type == "voice" and entry.voice_file_id:
            entry.voice_file_id = None
            cleared = True

        if cleared:
            # Обновляем has_media если больше нет медиа
            has_any = bool(
                (entry.media_files and len(entry.media_files) > 0)
                or entry.photo_file_id
                or entry.video_file_id
                or entry.voice_file_id
            )
            entry.has_media = has_any
            await db.commit()
            return {"deleted": media_id, "remaining": len(entry.media_files or []), "legacy": True}
        else:
            raise HTTPException(status_code=404, detail="Legacy media not found")

    # Standard JSON array delete
    if not entry.media_files:
        raise HTTPException(status_code=404, detail="No media found")

    original_len = len(entry.media_files)
    entry.media_files = [m for m in entry.media_files if m.get("id") != media_id]

    if len(entry.media_files) == original_len:
        raise HTTPException(status_code=404, detail="Media item not found")

    if len(entry.media_files) == 0:
        entry.has_media = bool(entry.photo_file_id or entry.video_file_id or entry.voice_file_id)

    await db.commit()
    return {"deleted": media_id, "remaining": len(entry.media_files)}

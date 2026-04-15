"""
Media Proxy API

Проксирование медиафайлов из Telegram для WebApp.
"""

import logging
from io import BytesIO

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.bot import bot

logger = logging.getLogger(__name__)
router = APIRouter()


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

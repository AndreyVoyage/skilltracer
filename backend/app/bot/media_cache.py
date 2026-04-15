"""
Media Cache Module

Временное хранилище file_id для медиа, отправленного боту.
"""

import logging
import time
from typing import Optional

from app.bot.config import BotConfig

logger = logging.getLogger(__name__)

# Формат: {user_id: {"photo": file_id, "video": file_id, "expires": timestamp}}
media_cache: dict[int, dict] = {}


def get_cached_media(user_id: int, media_type: str = "photo") -> Optional[str]:
    """
    Получает file_id из кэша.
    
    Args:
        user_id: ID пользователя
        media_type: тип медиа (photo, video, voice)
        
    Returns:
        file_id или None если нет в кэше или истек срок
    """
    if user_id not in media_cache:
        return None
    
    cache_entry = media_cache[user_id]
    
    # Проверяем срок годности
    if time.time() > cache_entry.get("expires", 0):
        del media_cache[user_id]
        return None
    
    return cache_entry.get(media_type)


def cache_media(user_id: int, media_type: str, file_id: str) -> None:
    """
    Сохраняет file_id в кэш.
    
    Args:
        user_id: ID пользователя
        media_type: тип медиа (photo, video, voice)
        file_id: Telegram file_id
    """
    if user_id not in media_cache:
        media_cache[user_id] = {}
    
    media_cache[user_id][media_type] = file_id
    media_cache[user_id]["expires"] = time.time() + BotConfig.MEDIA_CACHE_TTL
    
    logger.debug(f"Cached {media_type} for user {user_id}: {file_id[:20]}...")


def clear_media_cache(user_id: int) -> None:
    """Очищает кэш медиа для пользователя."""
    if user_id in media_cache:
        del media_cache[user_id]
        logger.debug(f"Cleared media cache for user {user_id}")

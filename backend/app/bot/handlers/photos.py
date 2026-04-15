"""
Media Handlers

Обработка фото, видео, голосовых сообщений.
Сохраняет file_id во временный кэш для последующего использования в WebApp.
"""

import logging

from aiogram import Router, F
from aiogram.types import Message
from aiogram.utils.markdown import hide_link

from app.bot.config import BotMessages
from app.bot.keyboards import get_main_menu_keyboard
from app.bot.media_cache import cache_media

logger = logging.getLogger(__name__)

router = Router(name="photos")


# =============================================================================
# Photo Handler
# =============================================================================

@router.message(F.photo)
async def handle_photo(message: Message) -> None:
    """
    Обработчик фото.
    
    Получает самое большое фото (последнее в массиве),
    сохраняет file_id в кэш и предлагает открыть приложение.
    """
    if not message.photo:
        return
    
    # Берем самое большое фото (последнее в массиве)
    photo = message.photo[-1]
    file_id = photo.file_id
    file_size = photo.file_size or 0
    
    user_id = message.from_user.id
    
    logger.info(
        f"Received photo from {user_id}: "
        f"file_id={file_id[:20]}..., size={file_size} bytes"
    )
    
    # Сохраняем в кэш
    cache_media(user_id, "photo", file_id)
    
    # Отвечаем пользователю
    await message.answer(
        BotMessages.PHOTO_RECEIVED,
        reply_markup=get_main_menu_keyboard(),
    )


# =============================================================================
# Video Handler
# =============================================================================

@router.message(F.video)
async def handle_video(message: Message) -> None:
    """
    Обработчик видео.
    
    Сохраняет video file_id в кэш.
    """
    if not message.video:
        return
    
    video = message.video
    file_id = video.file_id
    file_size = video.file_size or 0
    duration = video.duration
    
    user_id = message.from_user.id
    
    logger.info(
        f"Received video from {user_id}: "
        f"file_id={file_id[:20]}..., size={file_size}, duration={duration}s"
    )
    
    # Сохраняем в кэш
    cache_media(user_id, "video", file_id)
    
    # Отвечаем пользователю
    await message.answer(
        BotMessages.VIDEO_RECEIVED,
        reply_markup=get_main_menu_keyboard(),
    )


# =============================================================================
# Voice Handler
# =============================================================================

@router.message(F.voice)
async def handle_voice(message: Message) -> None:
    """
    Обработчик голосовых сообщений.
    
    Сохраняет voice file_id в кэш.
    В будущем здесь может быть расшифровка (STT).
    """
    if not message.voice:
        return
    
    voice = message.voice
    file_id = voice.file_id
    duration = voice.duration
    
    user_id = message.from_user.id
    
    logger.info(
        f"Received voice from {user_id}: "
        f"file_id={file_id[:20]}..., duration={duration}s"
    )
    
    # Сохраняем в кэш
    cache_media(user_id, "voice", file_id)
    
    # Отвечаем пользователю
    await message.answer(
        BotMessages.VOICE_RECEIVED,
        reply_markup=get_main_menu_keyboard(),
    )


# =============================================================================
# Video Note Handler (кружочки)
# =============================================================================

@router.message(F.video_note)
async def handle_video_note(message: Message) -> None:
    """
    Обработчик видео-кружочков.
    
    Сохраняет video_note file_id в кэш как видео.
    """
    if not message.video_note:
        return
    
    video_note = message.video_note
    file_id = video_note.file_id
    duration = video_note.duration
    
    user_id = message.from_user.id
    
    logger.info(
        f"Received video note from {user_id}: "
        f"file_id={file_id[:20]}..., duration={duration}s"
    )
    
    # Сохраняем как видео
    cache_media(user_id, "video", file_id)
    
    await message.answer(
        "🎥 Видео-кружок получен! Добавь его в дневник через приложение.",
        reply_markup=get_main_menu_keyboard(),
    )


# =============================================================================
# Document Handler (файлы)
# =============================================================================

@router.message(F.document)
async def handle_document(message: Message) -> None:
    """
    Обработчик документов/файлов.
    
    Сохраняет document file_id если это изображение.
    """
    if not message.document:
        return
    
    document = message.document
    file_id = document.file_id
    mime_type = document.mime_type or ""
    file_name = document.file_name or "unknown"
    
    user_id = message.from_user.id
    
    logger.info(
        f"Received document from {user_id}: "
        f"file_id={file_id[:20]}..., mime={mime_type}, name={file_name}"
    )
    
    # Если это изображение, сохраняем как фото
    if mime_type.startswith("image/"):
        cache_media(user_id, "photo", file_id)
        
        await message.answer(
            f"📸 Изображение <b>{file_name}</b> получено!\n\n"
            f"Открой Skill Tracer, чтобы добавить его к записи.",
            reply_markup=get_main_menu_keyboard(),
        )
    else:
        # Другие типы файлов пока не поддерживаем
        await message.answer(
            "📎 Получен файл. Пока что поддерживаются только изображения, видео и голосовые.",
            reply_markup=get_main_menu_keyboard(),
        )


# =============================================================================
# Media Group Handler (альбомы)
# =============================================================================

@router.message(F.media_group_id)
async def handle_media_group(message: Message) -> None:
    """
    Обработчик групп медиа (альбомы).
    
    Пока что берем только первое фото из альбома.
    В будущем можно сделать множественную загрузку.
    """
    if message.photo:
        # Обрабатываем как обычное фото
        await handle_photo(message)
    elif message.video:
        await handle_video(message)

"""
Collection Handlers

Обработчики сбора контента от пользователя:
фото, видео, голосовые, аудио, текст.
"""

import logging
import uuid
from datetime import date, datetime

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from app.models import DailyEntry
from app.bot.config import BotButtons

logger = logging.getLogger(__name__)
router = Router(name="collection")

EXCLUDED_BUTTONS = {
    BotButtons.MY_WEEK,
    BotButtons.SETTINGS,
    BotButtons.HELP,
    BotButtons.BACK_TO_MENU,
    BotButtons.BACK_TO_DAYS,
    BotButtons.OPEN_APP,
}


# =============================================================================
# Helpers
# =============================================================================

async def _get_or_create_entry(user_id: int, entry_date: date, db) -> DailyEntry:
    result = await db.execute(
        select(DailyEntry).where(
            DailyEntry.user_id == user_id,
            DailyEntry.entry_date == entry_date,
        )
    )
    entry = result.scalar_one_or_none()
    
    if entry is None:
        logger.info(f"[MEDIA_DEBUG] Creating new DailyEntry for user={user_id}, date={entry_date}")
        entry = DailyEntry(user_id=user_id, entry_date=entry_date)
        db.add(entry)
        await db.flush()
    else:
        logger.info(f"[MEDIA_DEBUG] Found existing DailyEntry id={entry.id} for user={user_id}, date={entry_date}, media_count={len(entry.media_files or [])}")
    
    return entry


def _make_media_item(media_type: str, file_id: str, caption: str = None) -> dict:
    """Создает стандартный объект медиа."""
    return {
        "id": str(uuid.uuid4()),
        "type": media_type,
        "file_id": file_id,
        "caption": caption,
        "created_at": datetime.now().isoformat(),
    }


def _get_post_save_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏃 Оценить трекеры", callback_data="rate_today")],
        [InlineKeyboardButton(text="📊 Моя неделя", callback_data="my_week")],
        [InlineKeyboardButton(text="Готово ✅", callback_data="main_menu")],
    ])


# =============================================================================
# Photo Handler
# =============================================================================

@router.message(F.photo)
async def handle_photo(message: Message, db) -> None:
    """Сохранение фото дня (append, не replace)."""
    photo = message.photo[-1]
    file_id = photo.file_id
    
    user_id = message.from_user.id
    today = date.today()
    
    entry = await _get_or_create_entry(user_id, today, db)
    
    # Legacy field (backward compat)
    entry.photo_file_id = file_id
    
    # New unified array
    if not entry.media_files:
        entry.media_files = []
    old_count = len(entry.media_files)
    entry.media_files.append(_make_media_item("photo", file_id, message.caption))
    flag_modified(entry, "media_files")
    entry.has_media = True
    
    await db.commit()
    
    new_count = len(entry.media_files)
    logger.info(f"[MEDIA_DEBUG] Photo saved: user={user_id}, entry_id={entry.id}, media_before={old_count}, media_after={new_count}")
    
    await message.reply(
        f"📷 Фото добавлено! (всего: {new_count})\n"
        "Открой Skill Tracer, чтобы увидеть все файлы.",
        reply_markup=_get_post_save_keyboard(),
    )


# =============================================================================
# Video Handler
# =============================================================================

@router.message(F.video)
async def handle_video(message: Message, db) -> None:
    """Сохранение видео (append, не replace)."""
    video = message.video
    file_id = video.file_id
    
    user_id = message.from_user.id
    today = date.today()
    
    entry = await _get_or_create_entry(user_id, today, db)
    
    # Legacy field
    entry.video_file_id = file_id
    
    # New unified array
    if not entry.media_files:
        entry.media_files = []
    old_count = len(entry.media_files)
    entry.media_files.append(_make_media_item("video", file_id, message.caption))
    flag_modified(entry, "media_files")
    entry.has_media = True
    
    await db.commit()
    
    new_count = len(entry.media_files)
    logger.info(f"[MEDIA_DEBUG] Video saved: user={user_id}, entry_id={entry.id}, media_before={old_count}, media_after={new_count}")
    
    await message.reply(
        f"🎥 Видео добавлено! (всего: {new_count}, длительность: {video.duration} сек)\n"
        "Открой Skill Tracer, чтобы просмотреть его в журнале.",
        reply_markup=_get_post_save_keyboard(),
    )


# =============================================================================
# Video Note Handler (круглые видео)
# =============================================================================

@router.message(F.video_note)
async def handle_video_note(message: Message, db) -> None:
    """Сохранение круглого видео (video_note)."""
    video_note = message.video_note
    file_id = video_note.file_id
    
    user_id = message.from_user.id
    today = date.today()
    
    entry = await _get_or_create_entry(user_id, today, db)
    
    if not entry.media_files:
        entry.media_files = []
    entry.media_files.append(_make_media_item("video_note", file_id))
    flag_modified(entry, "media_files")
    entry.has_media = True
    
    await db.commit()
    
    count = len(entry.media_files)
    await message.reply(
        f"🎥 Круглое видео добавлено! (всего: {count})\n"
        "Открой Skill Tracer для просмотра.",
        reply_markup=_get_post_save_keyboard(),
    )


# =============================================================================
# Voice / Audio Handler
# =============================================================================

@router.message(F.voice)
async def handle_voice(message: Message, db) -> None:
    """Сохранение голосового сообщения (append, не replace)."""
    voice = message.voice
    file_id = voice.file_id
    
    user_id = message.from_user.id
    today = date.today()
    
    entry = await _get_or_create_entry(user_id, today, db)
    
    # Legacy field
    entry.voice_file_id = file_id
    
    # New unified array
    if not entry.media_files:
        entry.media_files = []
    old_count = len(entry.media_files)
    entry.media_files.append(_make_media_item("voice", file_id))
    flag_modified(entry, "media_files")
    entry.has_media = True
    
    await db.commit()
    
    new_count = len(entry.media_files)
    logger.info(f"[MEDIA_DEBUG] Voice saved: user={user_id}, entry_id={entry.id}, media_before={old_count}, media_after={new_count}")
    
    await message.reply(
        f"🎤 Голосовое добавлено! (всего: {new_count})\n"
        "Открой приложение, чтобы прослушать в журнале.",
        reply_markup=_get_post_save_keyboard(),
    )


@router.message(F.audio)
async def handle_audio(message: Message, db) -> None:
    """Сохранение аудио файла (музыка) (append, не replace)."""
    audio = message.audio
    file_id = audio.file_id
    
    user_id = message.from_user.id
    today = date.today()
    
    entry = await _get_or_create_entry(user_id, today, db)
    
    # Legacy field
    entry.voice_file_id = file_id
    
    # New unified array
    if not entry.media_files:
        entry.media_files = []
    old_count = len(entry.media_files)
    title = audio.title or audio.performer or None
    entry.media_files.append(_make_media_item("audio", file_id, title))
    flag_modified(entry, "media_files")
    entry.has_media = True
    
    await db.commit()
    
    new_count = len(entry.media_files)
    logger.info(f"[MEDIA_DEBUG] Audio saved: user={user_id}, entry_id={entry.id}, media_before={old_count}, media_after={new_count}")
    
    display_title = title or "Без названия"
    await message.reply(
        f"🎵 Аудио добавлено: {display_title}! (всего: {new_count})\n"
        "Открой Skill Tracer для прослушивания.",
        reply_markup=_get_post_save_keyboard(),
    )


# =============================================================================
# Document Handler (файлы)
# =============================================================================

@router.message(F.document)
async def handle_document(message: Message, db) -> None:
    """Сохранение документов/файлов как фото если это изображение."""
    document = message.document
    if not document:
        return
    
    mime_type = document.mime_type or ""
    file_name = document.file_name or "unknown"
    file_id = document.file_id
    
    user_id = message.from_user.id
    today = date.today()
    
    entry = await _get_or_create_entry(user_id, today, db)
    
    if mime_type.startswith("image/"):
        if not entry.media_files:
            entry.media_files = []
        old_count = len(entry.media_files)
        entry.media_files.append(_make_media_item("photo", file_id, file_name))
        flag_modified(entry, "media_files")
        entry.has_media = True
        await db.commit()
        
        new_count = len(entry.media_files)
        logger.info(f"[MEDIA_DEBUG] Document(image) saved: user={user_id}, entry_id={entry.id}, media_before={old_count}, media_after={new_count}")
        
        await message.reply(
            f"📸 Изображение <b>{file_name}</b> добавлено! (всего: {new_count})",
            reply_markup=_get_post_save_keyboard(),
        )
    else:
        await message.reply(
            "📎 Получен файл. Пока поддерживаются только изображения, видео и голосовые.",
            reply_markup=_get_post_save_keyboard(),
        )


# =============================================================================
# Text Handler
# =============================================================================

@router.message(F.text, ~F.text.in_(EXCLUDED_BUTTONS))
async def handle_text(message: Message, db) -> None:
    """Сохранение текстовой заметки — ДОБАВЛЕНИЕ к существующему тексту."""
    if message.text and message.text.startswith("/"):
        return  # Команды обрабатываются в другом роутере
    
    logger.info(f"COLLECTION: Получен текст '{message.text[:50]}...' от {message.from_user.id}")
    
    user_id = message.from_user.id
    today = date.today()
    
    entry = await _get_or_create_entry(user_id, today, db)
    
    # APPEND к тексту, не REPLACE!
    if entry.text:
        entry.text = f"{entry.text}\n\n{message.text}"
    else:
        entry.text = message.text
    
    await db.commit()
    
    await message.reply(
        "✅ Заметка добавлена!\n"
        f"Текущий текст ({len(entry.text)} симв.):\n{entry.text[:100]}...",
        reply_markup=_get_post_save_keyboard(),
    )

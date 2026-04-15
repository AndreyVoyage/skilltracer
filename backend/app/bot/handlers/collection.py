"""
Collection Handlers

Обработчики сбора контента от пользователя:
фото, текст, голосовые сообщения.
"""

from datetime import date

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select

from app.models import DailyEntry

router = Router(name="collection")


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
        entry = DailyEntry(user_id=user_id, entry_date=entry_date)
        db.add(entry)
        await db.flush()
    
    return entry


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
    """Сохранение фото дня."""
    photo = message.photo[-1]
    file_id = photo.file_id
    
    user_id = message.from_user.id
    today = date.today()
    
    entry = await _get_or_create_entry(user_id, today, db)
    entry.photo_file_id = file_id
    await db.commit()
    
    await message.reply(
        "✅ Фото сохранено!\n"
        "Хотите добавить описание или оценить трекеры?",
        reply_markup=_get_post_save_keyboard(),
    )


# =============================================================================
# Voice / Audio Handler
# =============================================================================

@router.message(F.voice | F.audio)
async def handle_voice(message: Message, db) -> None:
    """Сохранение голосового/аудио."""
    if message.voice:
        file_id = message.voice.file_id
    elif message.audio:
        file_id = message.audio.file_id
    else:
        return
    
    user_id = message.from_user.id
    today = date.today()
    
    entry = await _get_or_create_entry(user_id, today, db)
    # Используем photo_file_id как универсальное поле для медиа (или text для voice metadata)
    # TODO: добавить отдельное поле voice_file_id в модель
    entry.text = f"[voice:{file_id}]" if not entry.text else f"{entry.text}\n[voice:{file_id}]"
    await db.commit()
    
    await message.reply(
        "✅ Аудио сохранено! 🎤\n"
        "Что еще добавим сегодня?",
        reply_markup=_get_post_save_keyboard(),
    )


# =============================================================================
# Text Handler
# =============================================================================

@router.message(F.text)
async def handle_text(message: Message, db) -> None:
    """Сохранение текстовой заметки."""
    if message.text and message.text.startswith("/"):
        return  # Команды обрабатываются в другом роутере
    
    user_id = message.from_user.id
    today = date.today()
    
    entry = await _get_or_create_entry(user_id, today, db)
    entry.text = message.text
    await db.commit()
    
    await message.reply(
        "✅ Заметка сохранена!\n"
        "Что еще добавим сегодня?",
        reply_markup=_get_post_save_keyboard(),
    )

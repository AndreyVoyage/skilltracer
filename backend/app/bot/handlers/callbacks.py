"""
Callback Handlers

Обработчики inline-кнопок бота.
"""

from datetime import date, timedelta

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, func

from app.models import DailyEntry, CustomTracker
from app.bot.config import BotMessages

router = Router(name="callbacks")


# =============================================================================
# Main Menu
# =============================================================================

@router.callback_query(F.data == "main_menu")
async def show_main_menu(callback: CallbackQuery) -> None:
    """Главное меню с кнопками."""
    await callback.answer()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Моя неделя", callback_data="my_week")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")],
        [InlineKeyboardButton(text="📝 Заполнить сегодня", callback_data="fill_today")],
    ])
    
    await callback.message.edit_text(
        "👋 Привет! Что будем делать?",
        reply_markup=keyboard,
    )


# =============================================================================
# My Week
# =============================================================================

@router.callback_query(F.data == "my_week")
async def show_week(callback: CallbackQuery, db, user) -> None:
    """Показать текущую неделю."""
    await callback.answer("Загружаю статистику...")
    
    user_id = callback.from_user.id
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    result = await db.execute(
        select(
            func.count(DailyEntry.id).label("filled_days"),
            func.avg(DailyEntry.mood).label("avg_mood"),
        ).where(
            DailyEntry.user_id == user_id,
            DailyEntry.entry_date >= start_of_week,
            DailyEntry.entry_date <= today,
        )
    )
    stats = result.first()
    
    text = f"📊 Неделя {start_of_week.strftime('%d.%m')} – {end_of_week.strftime('%d.%m')}\n\n"
    text += f"Заполнено дней: {stats.filled_days or 0}/7\n"
    text += f"Среднее настроение: {round(stats.avg_mood, 1) if stats.avg_mood else '—'}/5\n\n"
    text += "Выберите день:"
    
    # Кнопки дней недели
    keyboard = []
    days_short = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    for i in range(7):
        day = start_of_week + timedelta(days=i)
        has = await _has_entry(user_id, day, db)
        emoji = "✅" if has else "◻️"
        keyboard.append([InlineKeyboardButton(
            text=f"{emoji} {days_short[i]} {day.strftime('%d')}",
            callback_data=f"date_{day.isoformat()}",
        )])
    
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))


# =============================================================================
# Settings
# =============================================================================

@router.callback_query(F.data == "settings")
async def show_settings(callback: CallbackQuery, user) -> None:
    """Настройки пользователя."""
    await callback.answer()
    
    settings = user.settings or {}
    theme = settings.get("theme", "cozy")
    reminder = settings.get("reminder_time", "20:00")
    timezone = user.timezone or "Europe/Moscow"
    
    theme_name = "🏠 Уютный дом" if theme == "cozy" else "💎 Неоновая ночь"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎨 Сменить тему", callback_data="change_theme")],
        [InlineKeyboardButton(text=f"⏰ Напоминания ({reminder})", callback_data="settings:reminder")],
        [InlineKeyboardButton(text="🏃 Управление трекерами", callback_data="manage_trackers")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
    ])
    
    text = (
        f"⚙️ Настройки:\n"
        f"• Тема: {theme_name}\n"
        f"• Напоминания: {reminder}\n"
        f"• Часовой пояс: {timezone}"
    )
    
    await callback.message.edit_text(text, reply_markup=keyboard)


# =============================================================================
# Help
# =============================================================================

@router.callback_query(F.data == "help")
async def show_help(callback: CallbackQuery) -> None:
    """Помощь."""
    await callback.answer()
    
    text = (
        "❓ Как пользоваться Skill Tracer:\n\n"
        "1️⃣ Отправляйте фото, текст или голосовые — это ваш дневник\n"
        "2️⃣ Оценивайте трекеры (спорт, языки) по шкале 0–5\n"
        "3️⃣ В конце недели публикуйте отчет для друзей\n"
        "4️⃣ Создавайте группы до 3 человек\n\n"
        "📝 Команды:\n"
        "/start — главное меню\n"
        "/week — текущая неделя\n"
        "/settings — настройки"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)


# =============================================================================
# Day Selection
# =============================================================================

@router.callback_query(F.data.startswith("date_"))
async def select_date(callback: CallbackQuery, db, user) -> None:
    """Выбор конкретного дня для просмотра/редактирования."""
    selected_date = callback.data.split("_", 1)[1]
    
    result = await db.execute(
        select(DailyEntry).where(
            DailyEntry.user_id == user.id,
            DailyEntry.entry_date == selected_date,
        )
    )
    entry = result.scalar_one_or_none()
    
    text = f"📅 {selected_date}\n\n"
    if entry:
        text += f"📝 Заметка: {entry.text or '—'}\n"
        text += f"😊 Настроение: {entry.mood or '—'}/5\n"
    else:
        text += "Пока нет записей на этот день.\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Добавить запись", callback_data=f"add_entry_{selected_date}")],
        [InlineKeyboardButton(text="🏃 Оценить трекеры", callback_data=f"rate_{selected_date}")],
        [InlineKeyboardButton(text="⬅️ Назад к неделе", callback_data="my_week")],
    ])
    
    await callback.answer()
    await callback.message.edit_text(text, reply_markup=keyboard)


# =============================================================================
# Fill Today / Theme / Trackers
# =============================================================================

@router.callback_query(F.data == "fill_today")
async def fill_today(callback: CallbackQuery) -> None:
    """Подсказка по заполнению на сегодня."""
    await callback.answer("Отправьте фото, текст или голосовое сообщение!")
    await callback.message.edit_text(
        "📝 Чтобы заполнить день, просто отправьте боту:\n"
        "• Фото дня\n"
        "• Текстовую заметку\n"
        "• Голосовое сообщение\n\n"
        "Всё сохранится автоматически!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
        ]),
    )


@router.callback_query(F.data == "change_theme")
async def change_theme(callback: CallbackQuery, db, user) -> None:
    """Переключение темы."""
    settings = user.settings or {}
    current = settings.get("theme", "cozy")
    new_theme = "neon" if current == "cozy" else "cozy"
    settings["theme"] = new_theme
    user.settings = settings
    await db.commit()
    
    theme_name = "💎 Неоновая ночь" if new_theme == "neon" else "🏠 Уютный дом"
    await callback.answer(f"Тема изменена: {theme_name}")
    await show_settings(callback, user)


@router.callback_query(F.data == "manage_trackers")
async def manage_trackers(callback: CallbackQuery, db, user) -> None:
    """Управление трекерами."""
    result = await db.execute(
        select(CustomTracker).where(
            CustomTracker.user_id == user.id,
            CustomTracker.is_active == True,
        )
    )
    trackers = result.scalars().all()
    
    text = "🏃 Ваши трекеры:\n\n"
    if trackers:
        for t in trackers:
            text += f"{t.icon} {t.name}\n"
    else:
        text += "Пока нет трекеров.\n"
    
    text += "\nОтправьте /addtracker чтобы добавить новый."
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="settings")],
    ])
    
    await callback.answer()
    await callback.message.edit_text(text, reply_markup=keyboard)


# =============================================================================
# Fallback
# =============================================================================

@router.callback_query()
async def cb_fallback(callback: CallbackQuery) -> None:
    """Обработчик неизвестных inline кнопок."""
    await callback.answer("🛠️ Эта функция в разработке")


# =============================================================================
# Helpers
# =============================================================================

async def _has_entry(user_id: int, entry_date: date, db) -> bool:
    result = await db.execute(
        select(DailyEntry).where(
            DailyEntry.user_id == user_id,
            DailyEntry.entry_date == entry_date,
        )
    )
    return result.scalar_one_or_none() is not None

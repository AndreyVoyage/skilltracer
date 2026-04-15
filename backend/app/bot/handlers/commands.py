"""
Command Handlers

Обработчики команд бота: /start, /help, /week, /settings
"""

import logging
from datetime import date, timedelta

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, DailyEntry, CustomTracker
from app.bot.config import BotMessages, BotConfig
from app.bot.keyboards import (
    get_main_menu_keyboard,
    get_week_status_keyboard,
    get_settings_keyboard,
    build_progress_bar,
)

logger = logging.getLogger(__name__)

router = Router(name="commands")


# =============================================================================
# /start Command
# =============================================================================

@router.message(Command("start"))
async def cmd_start(message: Message, db: AsyncSession, user: User) -> None:
    """
    Обработчик команды /start.
    
    Приветствует пользователя и показывает главное меню.
    Автоматически создает пользователя через middleware.
    """
    first_name = user.first_name or message.from_user.first_name or "Друг"
    
    await message.answer(
        BotMessages.START.format(first_name=first_name),
        reply_markup=get_main_menu_keyboard(),
    )
    
    logger.info(f"User {user.id} started the bot")


# =============================================================================
# /help Command
# =============================================================================

@router.message(Command("help"))
async def cmd_help(message: Message, user: User) -> None:
    """Обработчик команды /help."""
    await message.answer(BotMessages.HELP)


# =============================================================================
# /week Command
# =============================================================================

@router.message(Command("week"))
async def cmd_week(message: Message, db: AsyncSession, user: User) -> None:
    """
    Обработчик команды /week.
    
    Показывает статус текущей недели: сколько дней заполнено,
    среднее настроение, прогресс-бар.
    """
    # Определяем даты текущей недели
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    
    # Считаем заполненные дни
    result = await db.execute(
        select(
            func.count(DailyEntry.id).label("filled"),
            func.avg(DailyEntry.mood).label("avg_mood"),
        )
        .where(
            DailyEntry.user_id == user.id,
            DailyEntry.entry_date >= monday,
            DailyEntry.entry_date <= sunday,
        )
    )
    stats = result.one()
    filled_days = stats.filled or 0
    avg_mood = stats.avg_mood
    
    # Строим прогресс-бар
    progress_bar = build_progress_bar(filled_days)
    percent = int((filled_days / BotConfig.DAYS_IN_WEEK) * 100)
    
    # Выбираем статусный текст
    if filled_days == 0:
        status_text = BotMessages.WEEK_EMPTY
    elif filled_days == BotConfig.DAYS_IN_WEEK:
        status_text = BotMessages.WEEK_EXCELLENT
    elif filled_days >= 5:
        status_text = BotMessages.WEEK_GOOD
    else:
        status_text = "Хорошее начало! Продолжай заполнять дневник 💪"
    
    # Формируем текст настроения
    mood_text = ""
    if avg_mood:
        mood_emojis = {1: "😭", 2: "😟", 3: "😐", 4: "🙂", 5: "😄"}
        mood_emoji = mood_emojis.get(round(avg_mood), "📊")
        mood_text = f"\n📈 Среднее настроение: {mood_emoji} {avg_mood:.1f}/5"
    
    text = BotMessages.WEEK_STATUS.format(
        filled=filled_days,
        total=BotConfig.DAYS_IN_WEEK,
        percent=percent,
        progress_bar=progress_bar,
        status_text=status_text,
    ) + mood_text
    
    await message.answer(
        text,
        reply_markup=get_week_status_keyboard(filled_days),
    )


# =============================================================================
# /settings Command
# =============================================================================

@router.message(Command("settings"))
async def cmd_settings(message: Message, db: AsyncSession, user: User) -> None:
    """
    Обработчик команды /settings.
    
    Показывает текущие настройки пользователя.
    """
    # Считаем количество трекеров
    result = await db.execute(
        select(func.count(CustomTracker.id))
        .where(
            CustomTracker.user_id == user.id,
            CustomTracker.is_active == True,
        )
    )
    trackers_count = result.scalar() or 0
    
    # Получаем настройки
    settings = user.settings or {}
    reminder_time = settings.get("reminder_time", "21:00")
    
    text = BotMessages.SETTINGS.format(
        timezone=user.timezone,
        reminder_time=reminder_time,
        trackers_count=trackers_count,
    )
    
    await message.answer(
        text,
        reply_markup=get_settings_keyboard(),
    )


# =============================================================================
# Text Button Handlers
# =============================================================================

@router.message(F.text == BotMessages.HELP)
async def btn_help(message: Message, user: User) -> None:
    """Обработчик кнопки Помощь."""
    await cmd_help(message, user)


@router.message(F.text == BotMessages.WEEK_STATUS)
async def btn_week(message: Message, db: AsyncSession, user: User) -> None:
    """Обработчик кнопки Моя неделя."""
    await cmd_week(message, db, user)


@router.message(F.text == BotMessages.SETTINGS)
async def btn_settings(message: Message, db: AsyncSession, user: User) -> None:
    """Обработчик кнопки Настройки."""
    await cmd_settings(message, db, user)


# =============================================================================
# Callback Handlers
# =============================================================================

@router.callback_query(F.data == "view_stats")
async def cb_view_stats(callback: CallbackQuery, db: AsyncSession, user: User) -> None:
    """Обработчик кнопки 'Статистика'."""
    await callback.answer("📊 Статистика будет доступна скоро!")
    # TODO: Реализовать детальную статистику


@router.callback_query(F.data.startswith("settings:"))
async def cb_settings(callback: CallbackQuery) -> None:
    """Обработчик кнопок настроек."""
    action = callback.data.split(":")[1]
    
    if action == "timezone":
        from app.bot.keyboards import get_timezones_keyboard
        await callback.message.edit_text(
            "🌍 Выберите ваш часовой пояс:",
            reply_markup=get_timezones_keyboard(),
        )
        await callback.answer()
    elif action == "reminder":
        from app.bot.keyboards import get_reminder_times_keyboard
        await callback.message.edit_text(
            "🔔 Выберите время напоминания:",
            reply_markup=get_reminder_times_keyboard(),
        )
        await callback.answer()
    elif action == "trackers":
        await callback.answer("📊 Управление трекерами будет в приложении!")
    else:
        await callback.answer("⚙️ Настройка в разработке")


@router.callback_query(F.data.startswith("timezone:"))
async def cb_set_timezone(callback: CallbackQuery, db: AsyncSession, user: User) -> None:
    """Обработчик выбора часового пояса."""
    timezone = callback.data.split(":", 1)[1]
    
    user.timezone = timezone
    await db.commit()
    
    await callback.answer(f"✅ Часовой пояс изменен на {timezone}")
    await callback.message.edit_text(
        f"🌍 Часовой пояс установлен: {timezone}\n\n"
        f"Вернитесь к настройкам: /settings"
    )


@router.callback_query(F.data.startswith("reminder:"))
async def cb_set_reminder(callback: CallbackQuery, db: AsyncSession, user: User) -> None:
    """Обработчик выбора времени напоминания."""
    time_str = callback.data.split(":", 1)[1]
    
    settings = user.settings or {}
    
    if time_str == "Отключить":
        settings["reminder_time"] = None
        msg = "🔔 Напоминания отключены"
    else:
        settings["reminder_time"] = time_str
        msg = f"🔔 Напоминания установлены на {time_str}"
    
    user.settings = settings
    await db.commit()
    
    await callback.answer(msg)
    await callback.message.edit_text(
        f"{msg}\n\nВернитесь к настройкам: /settings"
    )


# =============================================================================
# Error Handler
# =============================================================================

@router.callback_query()
async def cb_fallback(callback: CallbackQuery) -> None:
    """Обработчик неизвестных inline кнопок."""
    logger.info(f"Unhandled callback: {callback.data}")
    await callback.answer("🛠️ Эта функция в разработке")


@router.errors()
async def handle_errors(event, db: AsyncSession = None) -> None:
    """Обработчик ошибок в хендлерах команд."""
    logger.error(f"Error in command handler: {event.exception}")
    
    # Если есть message, отвечаем пользователю
    if hasattr(event, 'update') and event.update.message:
        await event.update.message.answer(BotMessages.ERROR_GENERIC)

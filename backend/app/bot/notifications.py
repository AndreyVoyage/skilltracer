"""
Bot Notifications

Функции для отправки уведомлений пользователям.
"""

import logging
from datetime import date, timedelta
from typing import List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, Group, GroupMember, WeekReport
from app.bot import bot
from app.bot.config import BotMessages

logger = logging.getLogger(__name__)


# =============================================================================
# Daily Reminders
# =============================================================================

async def send_daily_reminder(user_id: int) -> bool:
    """
    Отправляет ежедневное напоминание о заполнении дневника.
    
    Args:
        user_id: ID пользователя Telegram
        
    Returns:
        True если сообщение отправлено успешно
    """
    try:
        await bot.send_message(
            chat_id=user_id,
            text=BotMessages.REMINDER_DAILY,
        )
        logger.info(f"Daily reminder sent to {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send reminder to {user_id}: {e}")
        return False


async def send_daily_reminders_to_all(db: AsyncSession) -> int:
    """
    Отправляет напоминания всем пользователям у которых время совпадает.
    
    Args:
        db: Сессия базы данных
        
    Returns:
        Количество отправленных напоминаний
    """
    from datetime import datetime
    
    current_hour = datetime.utcnow().hour
    current_minute = datetime.utcnow().minute
    current_time = f"{current_hour:02d}:{current_minute:02d}"
    
    # Находим пользователей с напоминанием на текущее время
    result = await db.execute(
        select(User).where(
            User.settings["reminder_time"].as_string() == current_time
        )
    )
    users = result.scalars().all()
    
    sent_count = 0
    for user in users:
        if await send_daily_reminder(user.id):
            sent_count += 1
    
    logger.info(f"Sent {sent_count} daily reminders")
    return sent_count


# =============================================================================
# Weekly Summary
# =============================================================================

async def send_weekly_summary(user_id: int, db: AsyncSession) -> bool:
    """
    Отправляет напоминание о подведении итогов недели.
    
    Args:
        user_id: ID пользователя
        db: Сессия базы данных
        
    Returns:
        True если отправлено успешно
    """
    # Проверяем есть ли опубликованный отчет на этой неделе
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    
    result = await db.execute(
        select(WeekReport).where(
            WeekReport.user_id == user_id,
            WeekReport.week_start_date == monday,
        )
    )
    report = result.scalar_one_or_none()
    
    # Если уже опубликован, не напоминаем
    if report and report.status.value == "published":
        logger.debug(f"User {user_id} already published report, skipping")
        return False
    
    # Считаем заполненные дни
    result = await db.execute(
        select(func.count(DailyEntry.id))
        .where(
            DailyEntry.user_id == user_id,
            DailyEntry.entry_date >= monday,
            DailyEntry.entry_date <= today,
        )
    )
    filled_days = result.scalar() or 0
    
    # Формируем текст с учетом прогресса
    if filled_days >= 5:
        text = (
            f"{BotMessages.REMINDER_WEEKLY}\n\n"
            f"📊 У тебя {filled_days} заполненных дня! "
            f"Отличный результат, поделись с друзьями! 🌟"
        )
    elif filled_days > 0:
        text = (
            f"{BotMessages.REMINDER_WEEKLY}\n\n"
            f"📊 Заполнено {filled_days} дней. "
            f"Опубликуй отчет, чтобы получить поддержку друзей! 💪"
        )
    else:
        text = BotMessages.REMINDER_WEEKLY
    
    try:
        from app.bot.keyboards import get_week_status_keyboard
        
        await bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=get_week_status_keyboard(filled_days),
        )
        logger.info(f"Weekly summary sent to {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send weekly summary to {user_id}: {e}")
        return False


# =============================================================================
# Group Notifications
# =============================================================================

async def send_published_notification(
    group_id: int,
    publisher_user_id: int,
    publisher_name: str,
    db: AsyncSession,
) -> int:
    """
    Отправляет уведомление группе о публикации отчета.
    
    Args:
        group_id: ID группы
        publisher_user_id: ID пользователя, опубликовавшего отчет
        publisher_name: Имя публикующего пользователя
        db: Сессия базы данных
        
    Returns:
        Количество отправленных уведомлений
    """
    # Получаем членов группы
    result = await db.execute(
        select(GroupMember).where(GroupMember.group_id == group_id)
    )
    members = result.scalars().all()
    
    text = BotMessages.PUBLISHED_NOTIFICATION.format(
        user_name=publisher_name,
    )
    
    sent_count = 0
    for member in members:
        # Не отправляем самому публикующему
        if member.user_id == publisher_user_id:
            continue
        
        try:
            await bot.send_message(
                chat_id=member.user_id,
                text=text,
            )
            sent_count += 1
            logger.info(f"Published notification sent to {member.user_id}")
        except Exception as e:
            logger.error(f"Failed to notify {member.user_id}: {e}")
    
    return sent_count


async def send_new_member_notification(
    group_id: int,
    new_member_id: int,
    db: AsyncSession,
) -> None:
    """
    Отправляет уведомление группе о новом участнике.
    
    Args:
        group_id: ID группы
        new_member_id: ID нового участника
        db: Сессия базы данных
    """
    # Получаем информацию о новом участнике
    result = await db.execute(
        select(User).where(User.id == new_member_id)
    )
    new_user = result.scalar_one_or_none()
    
    if not new_user:
        return
    
    # Получаем других членов группы
    result = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id != new_member_id,
        )
    )
    members = result.scalars().all()
    
    text = (
        f"👋 <b>Новый участник!</b>\n\n"
        f"{new_user.get_full_name()} присоединился к группе!\n"
        f"Теперь вас {len(members) + 1} человек.\n\n"
        f"Поддерживайте друг друга в достижении целей! 💪"
    )
    
    for member in members:
        try:
            await bot.send_message(
                chat_id=member.user_id,
                text=text,
            )
        except Exception as e:
            logger.error(f"Failed to notify about new member: {e}")


# =============================================================================
# Comment Notifications
# =============================================================================

async def send_comment_notification(
    report_owner_id: int,
    comment_author_name: str,
    comment_text: str,
    db: AsyncSession,
) -> bool:
    """
    Отправляет уведомление о новом комментарии.
    
    Args:
        report_owner_id: ID владельца отчета
        comment_author_name: Имя автора комментария
        comment_text: Текст комментария
        db: Сессия базы данных
        
    Returns:
        True если отправлено успешно
    """
    # Обрезаем длинный текст
    text_preview = comment_text[:100] + "..." if len(comment_text) > 100 else comment_text
    
    text = (
        f"💬 <b>Новый комментарий!</b>\n\n"
        f"<b>{comment_author_name}</b> прокомментировал(а) ваш отчет:\n"
        f"<i>{text_preview}</i>"
    )
    
    try:
        await bot.send_message(
            chat_id=report_owner_id,
            text=text,
        )
        logger.info(f"Comment notification sent to {report_owner_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send comment notification: {e}")
        return False


# =============================================================================
# Helper Functions
# =============================================================================

async def is_user_active(user_id: int) -> bool:
    """
    Проверяет, может ли бот отправлять сообщения пользователю.
    
    Args:
        user_id: ID пользователя
        
    Returns:
        True если можно отправить сообщение
    """
    try:
        # Пробуем получить информацию о чате
        chat = await bot.get_chat(user_id)
        return True
    except Exception as e:
        logger.warning(f"User {user_id} is not accessible: {e}")
        return False


async def send_safe_message(
    user_id: int,
    text: str,
    **kwargs,
) -> bool:
    """
    Безопасная отправка сообщения с обработкой ошибок.
    
    Args:
        user_id: ID пользователя
        text: Текст сообщения
        **kwargs: Дополнительные аргументы для send_message
        
    Returns:
        True если отправлено успешно
    """
    try:
        await bot.send_message(
            chat_id=user_id,
            text=text,
            **kwargs,
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send message to {user_id}: {e}")
        return False

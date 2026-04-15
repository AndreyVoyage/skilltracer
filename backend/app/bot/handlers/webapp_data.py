"""
WebApp Data Handler

Обработка данных, отправленных из WebApp через window.Telegram.WebApp.sendData().
Используется как fallback или для быстрых действий без backend API.
"""

import json
import logging

from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.services.report_generator import send_report_to_chat
from datetime import date, timedelta

logger = logging.getLogger(__name__)

router = Router(name="webapp_data")


@router.message(F.web_app_data)
async def handle_web_app_data(message: Message, db: AsyncSession, user: User) -> None:
    """
    Обрабатывает данные от WebApp.
    
    Ожидаемый JSON:
    {
        "action": "share_report",
        "week_start": "2024-04-08"
    }
    """
    if not message.web_app_data:
        return
    
    try:
        data = json.loads(message.web_app_data.data)
    except json.JSONDecodeError:
        await message.answer("❌ Неверный формат данных от приложения.")
        return
    
    action = data.get("action")
    logger.info(f"WebApp data from user {user.id}: action={action}")
    
    if action == "share_report":
        week_start_str = data.get("week_start")
        if week_start_str:
            week_start = date.fromisoformat(week_start_str)
        else:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())
        
        from app.bot import bot
        await message.answer("🎨 Генерирую отчет...")
        try:
            await send_report_to_chat(user.id, week_start, db, bot)
        except Exception as e:
            logger.error(f"Failed to send report from web_app_data: {e}")
            await message.answer("❌ Не удалось отправить отчет. Попробуй позже.")
    else:
        await message.answer("✅ Данные получены!")

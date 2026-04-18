"""
Skill Tracer Telegram Bot

Инициализация бота и диспетчера Aiogram 3.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from app.config import settings
from app.bot.config import BotCommands
from app.bot.middlewares import DatabaseMiddleware, UserMiddleware
from app.bot.handlers import commands, journal, settings_menu, callbacks, photos, skills, webapp_data, collection

logger = logging.getLogger(__name__)

# =============================================================================
# Bot & Dispatcher Initialization
# =============================================================================

# Чтение прокси из переменных окружения
TELEGRAM_PROXY = os.getenv("TELEGRAM_PROXY")

# Таймаут для HTTP-сессии бота (30 секунд)
if TELEGRAM_PROXY:
    bot_session = AiohttpSession(timeout=30.0, proxy=TELEGRAM_PROXY)
    # Логируем прокси без credentials
    proxy_display = TELEGRAM_PROXY.split("@")[-1] if "@" in TELEGRAM_PROXY else TELEGRAM_PROXY
    logger.info(f"✅ Bot will use proxy: {proxy_display}")
else:
    bot_session = AiohttpSession(timeout=30.0)
    logger.info("⚠️ Bot will work without proxy")

# Инициализация бота с дефолтными свойствами
default_properties = DefaultBotProperties(
    parse_mode=ParseMode.HTML,
    link_preview_is_disabled=True,
)

bot = Bot(
    token=settings.BOT_TOKEN,
    session=bot_session,
    default=default_properties,
)

# Хранилище состояний в памяти (достаточно для 3 пользователей)
storage = MemoryStorage()

# Диспетчер
dp = Dispatcher(storage=storage)

# =============================================================================
# Setup Functions
# =============================================================================

def setup_handlers() -> None:
    """Регистрация всех хендлеров."""
    # Команды и Reply-кнопки
    dp.include_router(commands.router)
    
    # Журнал (Моя неделя + FSM)
    dp.include_router(journal.router)
    
    # Настройки (inline)
    dp.include_router(settings_menu.router)
    
    # Callback кнопки (legacy + новые inline)
    dp.include_router(callbacks.router)
    
    # Сбор контента (фото, текст, голос) — должен быть ПОСЛЕ FSM-роутеров
    dp.include_router(collection.router)
    
    # Фото и медиа
    dp.include_router(photos.router)
    
    # Conversation для трекеров
    dp.include_router(skills.router)
    
    # WebApp data
    dp.include_router(webapp_data.router)
    
    logger.info("Handlers registered")


def setup_middlewares() -> None:
    """Регистрация middleware."""
    # Внешние (outer) middleware - выполняются первыми
    # DatabaseMiddleware должен быть первым, чтобы UserMiddleware могла использовать db
    dp.message.outer_middleware(DatabaseMiddleware())
    dp.callback_query.outer_middleware(DatabaseMiddleware())
    
    dp.message.outer_middleware(UserMiddleware())
    dp.callback_query.outer_middleware(UserMiddleware())
    
    logger.info("Middlewares registered")


async def set_bot_commands() -> None:
    """Устанавливает команды меню бота."""
    from aiogram.types import BotCommand
    
    commands_list = [
        BotCommand(command=cmd, description=desc)
        for cmd, desc in BotCommands.get_commands()
    ]
    
    await bot.set_my_commands(commands_list)
    logger.info("Bot commands set")


# =============================================================================
# Lifecycle Management
# =============================================================================

async def start_polling() -> None:
    """Запуск бота в режиме polling."""
    logger.info("Starting bot polling...")
    
    # Удаляем вебхук если был
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запускаем polling
    await dp.start_polling(bot)


async def setup_webhook(webhook_url: str) -> None:
    """Настройка вебхука для production."""
    logger.info(f"Setting up webhook: {webhook_url}")
    
    await bot.set_webhook(
        url=webhook_url,
        allowed_updates=["message", "callback_query", "inline_query"],
    )
    logger.info("Webhook set")


async def shutdown_bot() -> None:
    """Graceful shutdown бота."""
    logger.info("Shutting down bot...")
    
    # Закрываем сессию
    await bot.session.close()
    
    # Очищаем кэш
    from app.bot.media_cache import media_cache
    media_cache.clear()
    
    logger.info("Bot shutdown complete")


# =============================================================================
# Initialization
# =============================================================================

def init_bot() -> None:
    """Инициализация бота (вызывается при старте приложения)."""
    setup_middlewares()
    setup_handlers()
    logger.info("Bot initialized")


# Автоматическая инициализация при импорте
init_bot()

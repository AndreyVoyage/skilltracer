"""
Bot Middlewares

Middleware для обработки сообщений перед хендлерами.
"""

import logging
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import User as UserModel

logger = logging.getLogger(__name__)


# =============================================================================
# Database Middleware
# =============================================================================

class DatabaseMiddleware(BaseMiddleware):
    """
    Middleware для предоставления сессии БД в хендлеры.
    
    Добавляет объект db (AsyncSession) в data хендлера.
    
    Usage:
        async def handler(message: Message, db: AsyncSession):
            user = await db.get(User, message.from_user.id)
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Создает сессию БД и передает в хендлер."""
        async with AsyncSessionLocal() as session:
            data["db"] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception as e:
                await session.rollback()
                logger.error(f"Database error in handler: {e}")
                raise
            finally:
                await session.close()


# =============================================================================
# User Middleware
# =============================================================================

class UserMiddleware(BaseMiddleware):
    """
    Middleware для автоматического создания/обновления пользователя.
    
    При каждом сообщении:
    1. Получает или создает пользователя в БД
    2. Обновляет профильные данные (username, first_name, etc)
    3. Добавляет объект user в data хендлера
    
    Работает с сессией из DatabaseMiddleware через data["db"].
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Обрабатывает пользователя перед хендлером."""
        from_user = None
        
        # Получаем пользователя из разных типов событий
        if isinstance(event, Message):
            from_user = event.from_user
        elif isinstance(event, CallbackQuery):
            from_user = event.from_user
        
        if from_user is None:
            return await handler(event, data)
        
        # Получаем сессию БД из data (если есть)
        db: AsyncSession | None = data.get("db")
        
        if db is None:
            # Если нет сессии (внешний middleware), пропускаем
            logger.warning("No database session in data, skipping user update")
            data["user"] = None
            return await handler(event, data)
        
        try:
            # Ищем пользователя
            from sqlalchemy import select
            
            result = await db.execute(
                select(UserModel).where(UserModel.id == from_user.id)
            )
            user = result.scalar_one_or_none()
            
            if user is None:
                # Создаем нового пользователя
                user = UserModel(
                    id=from_user.id,
                    username=from_user.username,
                    first_name=from_user.first_name,
                    last_name=from_user.last_name,
                    photo_url=None,  # Нужно получать отдельно через API
                )
                db.add(user)
                await db.flush()
                logger.info(f"Created new user: {from_user.id} (@{from_user.username})")
                
                # Создаем 4 дефолтных трекера
                from app.models import CustomTracker
                defaults = [
                    ("Здоровье", "❤️", 1),
                    ("Спорт", "🏃", 2),
                    ("Учёба", "📚", 3),
                    ("Отдых", "🧘", 4),
                ]
                for name, icon, sort_order in defaults:
                    db.add(CustomTracker(
                        user_id=user.id,
                        name=name,
                        icon=icon,
                        sort_order=sort_order,
                        is_default=True,
                    ))
                await db.flush()
                logger.info(f"Created default trackers for user: {from_user.id}")
            else:
                # Обновляем данные пользователя
                updated = False
                
                if user.username != from_user.username:
                    user.username = from_user.username
                    updated = True
                
                if user.first_name != from_user.first_name:
                    user.first_name = from_user.first_name
                    updated = True
                
                if user.last_name != from_user.last_name:
                    user.last_name = from_user.last_name
                    updated = True
                
                if updated:
                    logger.debug(f"Updated user profile: {from_user.id}")
            
            # Добавляем пользователя в data
            data["user"] = user
            
        except Exception as e:
            logger.error(f"Error in UserMiddleware: {e}")
            data["user"] = None
        
        return await handler(event, data)


# =============================================================================
# Logging Middleware
# =============================================================================

class LoggingMiddleware(BaseMiddleware):
    """
    Middleware для логирования входящих сообщений.
    
    Логирует: user_id, chat_id, тип сообщения, текст/данные.
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Логирует сообщение и передает дальше."""
        if isinstance(event, Message):
            logger.info(
                f"Message from {event.from_user.id if event.from_user else 'unknown'}: "
                f"{event.text or '[no text]'} ({event.content_type})"
            )
        elif isinstance(event, CallbackQuery):
            logger.info(
                f"Callback from {event.from_user.id}: {event.data}"
            )
        
        return await handler(event, data)

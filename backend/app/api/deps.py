"""
API Dependencies

Зависимости для FastAPI endpoints: авторизация, БД, текущий пользователь.
"""

import hmac
import hashlib
import urllib.parse
import time
import logging
from typing import Optional

from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import User, Group, GroupMember, CustomTracker
from app.config import settings

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)


# =============================================================================
# Database Dependency
# =============================================================================

async def get_db() -> AsyncSession:
    """Dependency для получения сессии БД."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# =============================================================================
# Telegram Init Data Validation
# =============================================================================

def validate_telegram_init_data(init_data: str) -> dict:
    """
    Валидация initData от Telegram Mini App.
    
    Проверяет HMAC-SHA256 подпись и время (не старше 5 минут).
    
    Args:
        init_data: Query string от Telegram.WebApp.initData
        
    Returns:
        dict с данными пользователя
        
    Raises:
        HTTPException: если подпись невалидна или данные устарели
    """
    try:
        # Парсим query string
        parsed = urllib.parse.parse_qs(init_data)
        data_dict = {k: v[0] for k, v in parsed.items()}
        
        received_hash = data_dict.pop('hash', None)
        if not received_hash:
            raise ValueError("Missing hash")
        
        # Проверяем auth_date (не старше 5 минут)
        auth_date = int(data_dict.get('auth_date', 0))
        if time.time() - auth_date > 300:  # 5 минут
            raise ValueError("Data expired")
        
        # Формируем data_check_string
        data_check_string = '\n'.join(
            f"{k}={v}" for k, v in sorted(data_dict.items())
        )
        
        # Вычисляем HMAC-SHA256
        secret_key = hmac.new(
            b"WebAppData",
            settings.BOT_TOKEN.encode(),
            hashlib.sha256
        ).digest()
        
        computed_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if computed_hash != received_hash:
            raise ValueError("Invalid hash")
        
        # Парсим user из JSON
        import json
        user_data = json.loads(data_dict.get('user', '{}'))
        
        return user_data
        
    except Exception as e:
        logger.warning(f"Init data validation failed: {e}. Init data length: {len(init_data) if init_data else 0}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired init data",
        )


# =============================================================================
# Current User Dependency
# =============================================================================

async def get_current_user(
    init_data: Optional[str] = Header(None, alias="X-Init-Data"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Получает текущего пользователя из initData.
    Создает пользователя если не существует.
    """
    logger.info(f"get_current_user called. init_data present: {bool(init_data)}, length: {len(init_data) if init_data else 0}")
    
    if not init_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing init data",
        )
    
    tg_user = validate_telegram_init_data(init_data)
    
    # Ищем пользователя
    result = await db.execute(
        select(User).where(User.id == tg_user['id'])
    )
    user = result.scalar_one_or_none()
    
    if not user:
        # Создаем нового
        user = User(
            id=tg_user['id'],
            username=tg_user.get('username'),
            first_name=tg_user.get('first_name'),
            last_name=tg_user.get('last_name'),
            photo_url=tg_user.get('photo_url'),
        )
        db.add(user)
        await db.flush()
        
        # Создаем 4 базовых трекера
        default_trackers = [
            {"name": "Здоровье", "icon": "❤️", "sort_order": 1},
            {"name": "Спорт", "icon": "🏃", "sort_order": 2},
            {"name": "Учёба", "icon": "📚", "sort_order": 3},
            {"name": "Отдых", "icon": "🧘", "sort_order": 4},
        ]
        for tracker_data in default_trackers:
            tracker = CustomTracker(
                user_id=user.id,
                is_default=True,
                **tracker_data
            )
            db.add(tracker)
        await db.flush()
        
        logger.info(f"Created user from Mini App with default trackers: {user.id}")
    else:
        # Обновляем данные
        if user.username != tg_user.get('username'):
            user.username = tg_user.get('username')
        if user.first_name != tg_user.get('first_name'):
            user.first_name = tg_user.get('first_name')
        if user.last_name != tg_user.get('last_name'):
            user.last_name = tg_user.get('last_name')
        if user.photo_url != tg_user.get('photo_url'):
            user.photo_url = tg_user.get('photo_url')
    
    return user


# =============================================================================
# Current Group Dependency
# =============================================================================

async def get_current_group(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Optional[Group]:
    """Возвращает группу текущего пользователя или None."""
    result = await db.execute(
        select(GroupMember).where(GroupMember.user_id == user.id)
    )
    membership = result.scalar_one_or_none()
    
    if not membership:
        return None
    
    result = await db.execute(
        select(Group).where(Group.id == membership.group_id)
    )
    return result.scalar_one_or_none()


# =============================================================================
# Optional Auth (для некоторых endpoints)
# =============================================================================

async def get_current_user_or_query(
    request: Request,
    init_data: Optional[str] = Header(None, alias="X-Init-Data"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Получает пользователя из initData или fallback на user_id в query params.
    Временное решение для WebApp до исправления initData.
    """
    if init_data:
        try:
            return await get_current_user(init_data, db)
        except HTTPException:
            logger.warning("InitData auth failed, trying query fallback")
    
    # Fallback: user_id из query params
    user_id_str = request.query_params.get("user_id")
    if user_id_str:
        try:
            user_id = int(user_id_str)
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                logger.info(f"Auth fallback: user {user_id} from query params")
                return user
        except (ValueError, Exception) as e:
            logger.warning(f"Query fallback failed: {e}")
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized: invalid initData or missing user_id",
    )


async def get_optional_user(
    init_data: Optional[str] = Header(None, alias="X-Init-Data"),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Опциональная авторизация (возвращает None если нет init_data)."""
    if not init_data:
        return None
    try:
        return await get_current_user(init_data, db)
    except HTTPException:
        return None

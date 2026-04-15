"""
Users API

Управление текущим пользователем.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from app.api.deps import get_current_user, get_db
from app.models import User, DailyEntry, WeekReport

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================

class SettingsUpdate(BaseModel):
    settings: dict


class UserOut(BaseModel):
    id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    photo_url: Optional[str]
    timezone: str
    settings: dict
    
    class Config:
        from_attributes = True


class UserStats(BaseModel):
    current_streak: int
    total_entries: int
    avg_mood: Optional[float]
    published_weeks: int


# =============================================================================
# Endpoints
# =============================================================================

@router.get("", response_model=UserOut)
async def get_me(
    user: User = Depends(get_current_user),
):
    """Текущий пользователь."""
    return UserOut(
        id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        photo_url=user.photo_url,
        timezone=user.timezone,
        settings=user.settings or {},
    )


@router.put("/settings")
async def update_settings(
    data: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Обновление настроек (merge)."""
    current_settings = user.settings or {}
    current_settings.update(data.settings)
    user.settings = current_settings
    
    await db.commit()
    return {"settings": user.settings}


class ThemeUpdate(BaseModel):
    theme: str


@router.post("/theme")
async def update_theme(
    data: ThemeUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Обновление темы WebApp."""
    current_settings = user.settings or {}
    current_settings["theme"] = data.theme
    user.settings = current_settings
    await db.commit()
    return {"theme": data.theme}


@router.get("/stats", response_model=UserStats)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Общая статистика пользователя."""
    from datetime import date, timedelta
    
    # Всего записей
    result = await db.execute(
        select(func.count(DailyEntry.id)).where(DailyEntry.user_id == user.id)
    )
    total_entries = result.scalar() or 0
    
    # Среднее настроение
    result = await db.execute(
        select(func.avg(DailyEntry.mood)).where(
            DailyEntry.user_id == user.id,
            DailyEntry.mood.isnot(None),
        )
    )
    avg_mood = result.scalar()
    
    # Опубликованных недель
    result = await db.execute(
        select(func.count(WeekReport.id)).where(WeekReport.user_id == user.id)
    )
    published_weeks = result.scalar() or 0
    
    # Текущая серия (streak)
    result = await db.execute(
        select(DailyEntry.entry_date)
        .where(DailyEntry.user_id == user.id)
        .order_by(DailyEntry.entry_date.desc())
    )
    dates = [row[0] for row in result.all()]
    
    streak = 0
    today = date.today()
    for i, d in enumerate(dates):
        expected = today - timedelta(days=i)
        if d == expected or (i == 0 and d == today - timedelta(days=1)):
            streak += 1
        else:
            break
    
    return UserStats(
        current_streak=streak,
        total_entries=total_entries,
        avg_mood=round(avg_mood, 2) if avg_mood else None,
        published_weeks=published_weeks,
    )

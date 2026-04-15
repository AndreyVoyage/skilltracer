"""
Entries API

CRUD для DailyEntry (приватных записей).
"""

import logging
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel, Field

from app.api.deps import get_current_user, get_db
from app.models import User, DailyEntry, EntryMetric, CustomTracker

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================

class MetricCreate(BaseModel):
    tracker_id: int
    value: int = Field(..., ge=0, le=5)


class EntryCreate(BaseModel):
    entry_date: date
    mood: Optional[int] = Field(None, ge=1, le=5)
    text: Optional[str] = None
    metrics: List[MetricCreate] = []
    photo_file_id: Optional[str] = None


class EntryOut(BaseModel):
    id: int
    entry_date: date
    mood: Optional[int]
    text: Optional[str]
    photo_file_id: Optional[str]
    voice_file_id: Optional[str]
    video_file_id: Optional[str]
    has_media: bool
    metrics: List[dict] = []
    
    class Config:
        from_attributes = True


class WeekOut(BaseModel):
    start_date: date
    end_date: date
    entries: List[EntryOut]
    trackers: List[dict]
    stats: dict


# =============================================================================
# Endpoints
# =============================================================================

@router.post("", response_model=EntryOut)
async def create_entry(
    data: EntryCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Создание или обновление записи дня (upsert)."""
    # Проверка: можно редактировать только последние 10 дней
    days_diff = (date.today() - data.entry_date).days
    if days_diff > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only edit entries from last 10 days",
        )
    
    # Ищем существующую запись
    result = await db.execute(
        select(DailyEntry).where(
            DailyEntry.user_id == user.id,
            DailyEntry.entry_date == data.entry_date,
        )
    )
    entry = result.scalar_one_or_none()
    
    if entry:
        # Обновляем
        entry.mood = data.mood
        entry.text = data.text
        if data.photo_file_id:
            entry.photo_file_id = data.photo_file_id
        
        # Удаляем старые метрики
        await db.execute(
            delete(EntryMetric).where(EntryMetric.entry_id == entry.id)
        )
    else:
        # Создаем новую
        entry = DailyEntry(
            user_id=user.id,
            entry_date=data.entry_date,
            mood=data.mood,
            text=data.text,
            photo_file_id=data.photo_file_id,
        )
        db.add(entry)
        await db.flush()
    
    # Добавляем метрики
    for m in data.metrics:
        metric = EntryMetric(
            entry_id=entry.id,
            tracker_id=m.tracker_id,
            value=m.value,
        )
        db.add(metric)
    
    await db.commit()
    await db.refresh(entry)
    
    # Формируем response
    return EntryOut(
        id=entry.id,
        entry_date=entry.entry_date,
        mood=entry.mood,
        text=entry.text,
        photo_file_id=entry.photo_file_id,
        metrics=[{"tracker_id": m.tracker_id, "value": m.value} for m in entry.metrics],
    )


@router.get("", response_model=List[EntryOut])
async def get_entries(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Получение записей за период (по умолчанию последние 30 дней)."""
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    result = await db.execute(
        select(DailyEntry)
        .where(
            DailyEntry.user_id == user.id,
            DailyEntry.entry_date >= start_date,
            DailyEntry.entry_date <= end_date,
        )
        .order_by(DailyEntry.entry_date.desc())
    )
    entries = result.scalars().all()
    
    return [
        EntryOut(
            id=e.id,
            entry_date=e.entry_date,
            mood=e.mood,
            text=e.text,
            photo_file_id=e.photo_file_id,
            metrics=[{"tracker_id": m.tracker_id, "value": m.value} for m in e.metrics],
        )
        for e in entries
    ]


@router.get("/{entry_date}", response_model=EntryOut)
async def get_entry(
    entry_date: date,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Получение конкретной записи по дате."""
    result = await db.execute(
        select(DailyEntry).where(
            DailyEntry.user_id == user.id,
            DailyEntry.entry_date == entry_date,
        )
    )
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    return EntryOut(
        id=entry.id,
        entry_date=entry.entry_date,
        mood=entry.mood,
        text=entry.text,
        photo_file_id=entry.photo_file_id,
        metrics=[{"tracker_id": m.tracker_id, "value": m.value} for m in entry.metrics],
    )


@router.get("/week", response_model=WeekOut)
async def get_week_entries(
    start_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Получение записей за неделю с трекерами."""
    if not start_date:
        start_date = date.today() - timedelta(days=date.today().weekday())
    end_date = start_date + timedelta(days=6)
    
    result = await db.execute(
        select(DailyEntry)
        .where(
            DailyEntry.user_id == user.id,
            DailyEntry.entry_date >= start_date,
            DailyEntry.entry_date <= end_date,
        )
        .order_by(DailyEntry.entry_date)
    )
    entries = result.scalars().all()
    
    result = await db.execute(
        select(CustomTracker)
        .where(
            CustomTracker.user_id == user.id,
            CustomTracker.is_active == True,
        )
        .order_by(CustomTracker.sort_order)
    )
    trackers = result.scalars().all()
    
    moods = [e.mood for e in entries if e.mood is not None]
    stats = {
        "filled_days": len(entries),
        "avg_mood": round(sum(moods) / len(moods), 2) if moods else None,
    }
    
    return WeekOut(
        start_date=start_date,
        end_date=end_date,
        entries=[
            EntryOut(
                id=e.id,
                entry_date=e.entry_date,
                mood=e.mood,
                text=e.text,
                photo_file_id=e.photo_file_id,
                voice_file_id=e.voice_file_id,
                video_file_id=e.video_file_id,
                has_media=e.has_media,
                metrics=[{"tracker_id": m.tracker_id, "value": m.value} for m in e.metrics],
            )
            for e in entries
        ],
        trackers=[
            {"id": t.id, "name": t.name, "icon": t.icon, "target_value": t.target_value, "is_default": t.is_default}
            for t in trackers
        ],
        stats=stats,
    )


@router.delete("/{entry_date}")
async def delete_entry(
    entry_date: date,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Удаление записи (только в пределах 10 дней)."""
    days_diff = (date.today() - entry_date).days
    if days_diff > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only delete entries from last 10 days",
        )
    
    result = await db.execute(
        delete(DailyEntry).where(
            DailyEntry.user_id == user.id,
            DailyEntry.entry_date == entry_date,
        )
    )
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    await db.commit()
    return {"status": "deleted"}

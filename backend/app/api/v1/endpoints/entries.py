"""
Entries API

CRUD для DailyEntry (приватных записей).
"""

import logging
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel, Field

from app.api.deps import get_current_user_or_query, get_db
from app.models import User, DailyEntry, EntryMetric, CustomTracker, JournalEntry

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
    mood: Optional[int] = None
    text: Optional[str] = None
    photo_file_id: Optional[str] = None
    voice_file_id: Optional[str] = None
    video_file_id: Optional[str] = None
    has_media: bool = False
    metrics: List[dict] = []
    
    # Поля из бота (JournalEntry)
    health_score: Optional[int] = None
    sport_score: Optional[int] = None
    study_score: Optional[int] = None
    rest_score: Optional[int] = None
    comment: Optional[str] = None
    media_urls: List[str] = []
    
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
    user: User = Depends(get_current_user_or_query),
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
    user: User = Depends(get_current_user_or_query),
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


@router.get("/week", response_model=WeekOut)
async def get_week_entries(
    start_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_or_query),
):
    """Получение записей за неделю с трекерами (DailyEntry + JournalEntry)."""
    if not start_date:
        start_date = date.today() - timedelta(days=date.today().weekday())
    end_date = start_date + timedelta(days=6)
    
    # Запрашиваем DailyEntry (WebApp)
    result = await db.execute(
        select(DailyEntry)
        .where(
            DailyEntry.user_id == user.id,
            DailyEntry.entry_date >= start_date,
            DailyEntry.entry_date <= end_date,
        )
        .order_by(DailyEntry.entry_date)
    )
    daily_entries = {e.entry_date: e for e in result.scalars().all()}
    
    # Запрашиваем JournalEntry (бот)
    result = await db.execute(
        select(JournalEntry)
        .where(
            JournalEntry.user_id == user.id,
            JournalEntry.entry_date >= start_date,
            JournalEntry.entry_date <= end_date,
        )
        .order_by(JournalEntry.entry_date)
    )
    journal_entries = {e.entry_date: e for e in result.scalars().all()}
    
    result = await db.execute(
        select(CustomTracker)
        .where(
            CustomTracker.user_id == user.id,
            CustomTracker.is_active == True,
        )
        .order_by(CustomTracker.sort_order)
    )
    trackers = result.scalars().all()
    
    # Собираем все даты
    all_dates = set(daily_entries.keys()) | set(journal_entries.keys())
    moods = [e.mood for e in daily_entries.values() if e.mood is not None]
    stats = {
        "filled_days": len(all_dates),
        "avg_mood": round(sum(moods) / len(moods), 2) if moods else None,
    }
    
    merged_entries = []
    for i in range(7):
        d = start_date + timedelta(days=i)
        de = daily_entries.get(d)
        je = journal_entries.get(d)
        
        entry = EntryOut(
            id=de.id if de else (je.id if je else 0),
            entry_date=d,
            mood=de.mood if de else None,
            text=de.text if de else None,
            photo_file_id=de.photo_file_id if de else None,
            voice_file_id=de.voice_file_id if de else None,
            video_file_id=de.video_file_id if de else None,
            has_media=de.has_media if de else False,
            metrics=[{"tracker_id": m.tracker_id, "value": m.value} for m in de.metrics] if de else [],
            health_score=je.health_score if je else None,
            sport_score=je.sport_score if je else None,
            study_score=je.study_score if je else None,
            rest_score=je.rest_score if je else None,
            comment=je.comment if je else None,
            media_urls=je.media_urls if je else [],
        )
        merged_entries.append(entry)
    
    return WeekOut(
        start_date=start_date,
        end_date=end_date,
        entries=merged_entries,
        trackers=[
            {"id": t.id, "name": t.name, "icon": t.icon, "target_value": t.target_value, "is_default": t.is_default}
            for t in trackers
        ],
        stats=stats,
    )


@router.get("/week/debug")
async def get_week_debug(
    start_date: str = Query(..., description="YYYY-MM-DD"),
    user_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Временный debug endpoint без авторизации. Проверяет данные в БД."""
    try:
        week_start = date.fromisoformat(start_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format, expected YYYY-MM-DD")
    
    week_end = week_start + timedelta(days=6)
    
    # Проверяем DailyEntry
    result = await db.execute(
        select(DailyEntry).where(
            DailyEntry.user_id == user_id,
            DailyEntry.entry_date >= week_start,
            DailyEntry.entry_date <= week_end,
        )
    )
    daily = result.scalars().all()
    
    # Проверяем JournalEntry (бот)
    result = await db.execute(
        select(JournalEntry).where(
            JournalEntry.user_id == user_id,
            JournalEntry.entry_date >= week_start,
            JournalEntry.entry_date <= week_end,
        )
    )
    journal = result.scalars().all()
    
    # Проверяем пользователя
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    return {
        "status": "ok",
        "debug": True,
        "user_id": user_id,
        "user_exists": user is not None,
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "daily_entries_count": len(daily),
        "journal_entries_count": len(journal),
        "daily_entries": [
            {"date": e.entry_date.isoformat(), "mood": e.mood, "text": e.text}
            for e in daily
        ],
        "journal_entries": [
            {
                "date": e.entry_date.isoformat(),
                "health": e.health_score,
                "sport": e.sport_score,
                "study": e.study_score,
                "rest": e.rest_score,
                "comment": e.comment,
            }
            for e in journal
        ],
    }


@router.get("/{entry_date}", response_model=EntryOut)
async def get_entry(
    entry_date: date,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_or_query),
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


@router.delete("/{entry_date}")
async def delete_entry(
    entry_date: date,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_or_query),
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

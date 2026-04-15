"""
Reports API

Управление WeekReport (публикация недельных отчетов).
"""

import json
import logging
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from app.api.deps import get_current_user, get_db
from app.models import User, DailyEntry, WeekReport, ReportStatus, CustomTracker, TelegramQueue, ReportLink
from app.services.report_generator import generate_week_poster, send_report_to_chat
import secrets

logger = logging.getLogger(__name__)
router = APIRouter()

# =============================================================================
# Schemas
# =============================================================================

class WeekOut(BaseModel):
    week_start: date
    week_end: date
    status: str
    filled_days: int
    avg_mood: Optional[float]
    metrics_summary: dict
    published_at: Optional[date]
    
    class Config:
        from_attributes = True


class AnalyticsOut(BaseModel):
    mood_by_day: List[dict]
    tracker_averages: List[dict]
    stats: dict


class WeekDataOut(BaseModel):
    week_start: date
    week_end: date
    entries: List[dict]
    trackers: List[dict]
    file_ids: List[str]


class RenderOut(BaseModel):
    status: str
    message: str


class ShareOut(BaseModel):
    status: str
    queue_id: int
    message: str


# =============================================================================
# Helpers
# =============================================================================

def get_week_dates(week_start: date) -> tuple[date, date]:
    """Возвращает (monday, sunday) для недели."""
    return week_start, week_start + timedelta(days=6)


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/current", response_model=WeekOut)
async def get_current_week(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Получение статуса текущей недели."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    
    # Ищем существующий отчет
    result = await db.execute(
        select(WeekReport).where(
            WeekReport.user_id == user.id,
            WeekReport.week_start_date == monday,
        )
    )
    report = result.scalar_one_or_none()
    
    # Считаем заполненные дни
    result = await db.execute(
        select(func.count(DailyEntry.id), func.avg(DailyEntry.mood))
        .where(
            DailyEntry.user_id == user.id,
            DailyEntry.entry_date >= monday,
            DailyEntry.entry_date <= sunday,
        )
    )
    filled_count, avg_mood = result.one()
    
    if report:
        return WeekOut(
            week_start=report.week_start_date,
            week_end=report.week_end_date,
            status=report.status.value,
            filled_days=report.filled_days,
            avg_mood=report.avg_mood,
            metrics_summary=report.metrics_summary,
            published_at=report.published_at.date() if report.published_at else None,
        )
    else:
        return WeekOut(
            week_start=monday,
            week_end=sunday,
            status="draft",
            filled_days=filled_count or 0,
            avg_mood=round(avg_mood, 2) if avg_mood else None,
            metrics_summary={},
            published_at=None,
        )


@router.get("/{week_start}/data", response_model=WeekDataOut)
async def get_week_data(
    week_start: date,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Агрегированные данные недели для визуализации (JSON)."""
    monday = week_start
    sunday = monday + timedelta(days=6)
    
    result = await db.execute(
        select(DailyEntry)
        .where(
            DailyEntry.user_id == user.id,
            DailyEntry.entry_date >= monday,
            DailyEntry.entry_date <= sunday,
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
    
    file_ids = [e.photo_file_id for e in entries if e.photo_file_id]
    
    return WeekDataOut(
        week_start=monday,
        week_end=sunday,
        entries=[
            {
                "date": e.entry_date.isoformat(),
                "mood": e.mood,
                "text": e.text,
                "photo_file_id": e.photo_file_id,
                "metrics": [{"tracker_id": m.tracker_id, "value": m.value} for m in e.metrics],
            }
            for e in entries
        ],
        trackers=[
            {"id": t.id, "name": t.name, "icon": t.icon, "target_value": t.target_value}
            for t in trackers
        ],
        file_ids=file_ids,
    )


@router.post("/{week_start}/render")
async def render_week_report(
    week_start: date,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Генерация PNG/JPEG отчета за неделю.
    Возвращает 202 Accepted и ставит задачу в фон.
    Для получения файла используйте /render/download с теми же параметрами.
    """
    # Простая валидация: минимум 1 день
    monday = week_start
    sunday = monday + timedelta(days=6)
    
    result = await db.execute(
        select(func.count(DailyEntry.id))
        .where(
            DailyEntry.user_id == user.id,
            DailyEntry.entry_date >= monday,
            DailyEntry.entry_date <= sunday,
        )
    )
    count = result.scalar() or 0
    if count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No entries for this week",
        )
    
    return RenderOut(
        status="accepted",
        message="Report generation accepted. Use /render/download to fetch.",
    )


@router.get("/{week_start}/render/download")
async def download_rendered_report(
    week_start: date,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Скачивание сгенерированного отчета за неделю (JPEG)."""
    from app.bot import bot
    
    monday = week_start
    try:
        buf = await generate_week_poster(user.id, monday, db, bot=bot)
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {e}",
        )
    
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="image/jpeg",
        headers={
            "Content-Disposition": f"inline; filename=week_report_{monday.isoformat()}.jpg"
        },
    )


@router.post("/{week_start}/share", response_model=ShareOut)
async def share_week_report(
    week_start: date,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Поделиться отчетом в чат с ботом.
    Ставит задачу в очередь telegram_queue и возвращает 202.
    """
    monday = week_start
    sunday = monday + timedelta(days=6)
    
    # Проверяем записи
    result = await db.execute(
        select(func.count(DailyEntry.id))
        .where(
            DailyEntry.user_id == user.id,
            DailyEntry.entry_date >= monday,
            DailyEntry.entry_date <= sunday,
        )
    )
    count = result.scalar() or 0
    if count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No entries for this week",
        )
    
    # Создаем задачу в очереди
    queue_item = TelegramQueue(
        user_id=user.id,
        action="send_report",
        payload=json.dumps({
            "week_start": monday.isoformat(),
            "caption": f"Ваша неделя {monday.day}-{sunday.day} {monday.strftime('%b')}! 🎉",
        }),
        status="pending",
    )
    db.add(queue_item)
    await db.commit()
    await db.refresh(queue_item)
    
    return ShareOut(
        status="accepted",
        queue_id=queue_item.id,
        message="Report queued for delivery to your chat.",
    )


@router.post("/{week_start}/publish", response_model=WeekOut)
async def publish_week(
    week_start: date,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Публикация недельного отчета."""
    monday = week_start
    sunday = monday + timedelta(days=6)
    
    # Получаем записи недели
    result = await db.execute(
        select(DailyEntry)
        .where(
            DailyEntry.user_id == user.id,
            DailyEntry.entry_date >= monday,
            DailyEntry.entry_date <= sunday,
        )
    )
    entries = result.scalars().all()
    
    # Проверка: минимум 3 дня
    if len(entries) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Need at least 3 days to publish",
        )
    
    # Считаем статистику
    moods = [e.mood for e in entries if e.mood]
    avg_mood = sum(moods) / len(moods) if moods else None
    
    # Считаем средние по трекерам
    tracker_sums = {}
    tracker_counts = {}
    
    for entry in entries:
        for metric in entry.metrics:
            tracker_name = metric.tracker.name if metric.tracker else f"t{metric.tracker_id}"
            tracker_sums[tracker_name] = tracker_sums.get(tracker_name, 0) + metric.value
            tracker_counts[tracker_name] = tracker_counts.get(tracker_name, 0) + 1
    
    metrics_summary = {
        name: round(tracker_sums[name] / tracker_counts[name], 2)
        for name in tracker_sums
    }
    
    # Ищем или создаем отчет
    result = await db.execute(
        select(WeekReport).where(
            WeekReport.user_id == user.id,
            WeekReport.week_start_date == monday,
        )
    )
    report = result.scalar_one_or_none()
    
    if report:
        report.status = ReportStatus.PUBLISHED
        report.published_at = func.now()
        report.filled_days = len(entries)
        report.avg_mood = avg_mood
        report.metrics_summary = metrics_summary
    else:
        report = WeekReport(
            user_id=user.id,
            week_start_date=monday,
            week_end_date=sunday,
            status=ReportStatus.PUBLISHED,
            filled_days=len(entries),
            avg_mood=avg_mood,
            metrics_summary=metrics_summary,
        )
        db.add(report)
    
    await db.commit()
    await db.refresh(report)
    
    return WeekOut(
        week_start=report.week_start_date,
        week_end=report.week_end_date,
        status=report.status.value,
        filled_days=report.filled_days,
        avg_mood=report.avg_mood,
        metrics_summary=report.metrics_summary,
        published_at=report.published_at.date() if report.published_at else None,
    )


@router.get("/{week_start}/analytics", response_model=AnalyticsOut)
async def get_week_analytics(
    week_start: date,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Получение данных для графиков (analytics)."""
    monday = week_start
    sunday = monday + timedelta(days=6)
    
    # Получаем записи
    result = await db.execute(
        select(DailyEntry)
        .where(
            DailyEntry.user_id == user.id,
            DailyEntry.entry_date >= monday,
            DailyEntry.entry_date <= sunday,
        )
        .order_by(DailyEntry.entry_date)
    )
    entries = result.scalars().all()
    
    # Mood by day
    mood_by_day = []
    for i in range(7):
        d = monday + timedelta(days=i)
        entry = next((e for e in entries if e.entry_date == d), None)
        mood_by_day.append({
            "date": d.isoformat(),
            "mood": entry.mood if entry else None,
        })
    
    # Tracker averages
    tracker_data = {}
    for entry in entries:
        for m in entry.metrics:
            name = m.tracker.name if m.tracker else f"t{m.tracker_id}"
            if name not in tracker_data:
                tracker_data[name] = {"sum": 0, "count": 0, "icon": m.tracker.icon if m.tracker else "📊"}
            tracker_data[name]["sum"] += m.value
            tracker_data[name]["count"] += 1
    
    tracker_averages = [
        {
            "name": name,
            "avg": round(data["sum"] / data["count"], 2),
            "icon": data["icon"],
        }
        for name, data in tracker_data.items()
    ]
    
    # Stats
    moods = [e.mood for e in entries if e.mood]
    stats = {
        "avg_mood": round(sum(moods) / len(moods), 2) if moods else None,
        "total_days": len(entries),
        "best_day": max(moods) if moods else None,
    }
    
    return AnalyticsOut(
        mood_by_day=mood_by_day,
        tracker_averages=tracker_averages,
        stats=stats,
    )


# =============================================================================
# Public Report Link Endpoints
# =============================================================================

class LinkOut(BaseModel):
    token: str
    url: str
    week_start: date
    expires_at: Optional[date]


@router.post("/{week_start}/generate-link", response_model=LinkOut)
async def generate_public_link(
    week_start: date,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Создание публичной ссылки на отчет недели."""
    from datetime import datetime, timedelta
    
    monday = week_start
    
    # Проверяем записи
    result = await db.execute(
        select(func.count(DailyEntry.id))
        .where(
            DailyEntry.user_id == user.id,
            DailyEntry.entry_date >= monday,
            DailyEntry.entry_date <= monday + timedelta(days=6),
        )
    )
    count = result.scalar() or 0
    if count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No entries for this week",
        )
    
    # Ищем существующую активную ссылку
    result = await db.execute(
        select(ReportLink).where(
            ReportLink.user_id == user.id,
            ReportLink.week_start == monday,
            ReportLink.is_active == True,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return LinkOut(
            token=existing.token,
            url=f"https://skilltracer.art-artel.su/report/{existing.token}",
            week_start=existing.week_start,
            expires_at=existing.expires_at.date() if existing.expires_at else None,
        )
    
    # Создаем новую ссылку
    token = secrets.token_urlsafe(12)[:16]
    link = ReportLink(
        token=token,
        user_id=user.id,
        week_start=monday,
        expires_at=datetime.utcnow() + timedelta(days=30),
        is_active=True,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    
    return LinkOut(
        token=link.token,
        url=f"https://skilltracer.art-artel.su/report/{link.token}",
        week_start=link.week_start,
        expires_at=link.expires_at.date() if link.expires_at else None,
    )

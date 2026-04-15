"""
Trackers API

Управление пользовательскими трекерами.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from pydantic import BaseModel, Field

from app.api.deps import get_current_user, get_db
from app.models import User, CustomTracker

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================

class TrackerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    icon: str = Field(default="📊", max_length=10)
    target_value: int = Field(None, ge=1, le=31)


class TrackerOut(BaseModel):
    id: int
    name: str
    icon: str
    target_value: int
    is_active: bool
    sort_order: int
    
    class Config:
        from_attributes = True


class TrackerReorder(BaseModel):
    tracker_ids: List[int]


# =============================================================================
# Endpoints
# =============================================================================

@router.get("", response_model=List[TrackerOut])
async def get_trackers(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Мои трекеры (только активные)."""
    result = await db.execute(
        select(CustomTracker)
        .where(
            CustomTracker.user_id == user.id,
            CustomTracker.is_active == True,
        )
        .order_by(CustomTracker.sort_order)
    )
    trackers = result.scalars().all()
    
    return [
        TrackerOut(
            id=t.id,
            name=t.name,
            icon=t.icon,
            target_value=t.target_value,
            is_active=t.is_active,
            sort_order=t.sort_order,
        )
        for t in trackers
    ]


@router.post("", response_model=TrackerOut)
async def create_tracker(
    data: TrackerCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Создание трекера."""
    # Получаем максимальный sort_order
    result = await db.execute(
        select(func.max(CustomTracker.sort_order))
        .where(CustomTracker.user_id == user.id)
    )
    max_order = result.scalar() or 0
    
    tracker = CustomTracker(
        user_id=user.id,
        name=data.name,
        icon=data.icon,
        target_value=data.target_value,
        sort_order=max_order + 1,
    )
    db.add(tracker)
    await db.commit()
    await db.refresh(tracker)
    
    return TrackerOut(
        id=tracker.id,
        name=tracker.name,
        icon=tracker.icon,
        target_value=tracker.target_value,
        is_active=tracker.is_active,
        sort_order=tracker.sort_order,
    )


@router.put("/{tracker_id}", response_model=TrackerOut)
async def update_tracker(
    tracker_id: int,
    data: TrackerCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Обновление трекера."""
    result = await db.execute(
        select(CustomTracker).where(
            CustomTracker.id == tracker_id,
            CustomTracker.user_id == user.id,
        )
    )
    tracker = result.scalar_one_or_none()
    
    if not tracker:
        raise HTTPException(status_code=404, detail="Tracker not found")
    
    tracker.name = data.name
    tracker.icon = data.icon
    tracker.target_value = data.target_value
    
    await db.commit()
    await db.refresh(tracker)
    
    return TrackerOut(
        id=tracker.id,
        name=tracker.name,
        icon=tracker.icon,
        target_value=tracker.target_value,
        is_active=tracker.is_active,
        sort_order=tracker.sort_order,
    )


@router.delete("/{tracker_id}")
async def delete_tracker(
    tracker_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Удаление трекера (soft delete)."""
    result = await db.execute(
        select(CustomTracker).where(
            CustomTracker.id == tracker_id,
            CustomTracker.user_id == user.id,
        )
    )
    tracker = result.scalar_one_or_none()
    
    if not tracker:
        raise HTTPException(status_code=404, detail="Tracker not found")
    
    tracker.is_active = False
    await db.commit()
    
    return {"status": "deleted"}


@router.post("/reorder")
async def reorder_trackers(
    data: TrackerReorder,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Изменение порядка трекеров."""
    for idx, tracker_id in enumerate(data.tracker_ids):
        await db.execute(
            update(CustomTracker)
            .where(
                CustomTracker.id == tracker_id,
                CustomTracker.user_id == user.id,
            )
            .values(sort_order=idx)
        )
    
    await db.commit()
    return {"status": "reordered"}

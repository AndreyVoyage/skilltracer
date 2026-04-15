"""
Groups API

Управление группами и групповой лентой.
"""

import logging
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, Field

from app.api.deps import get_current_user, get_db
from app.models import User, Group, GroupMember, WeekReport, ReportStatus, GroupRole

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================

class GroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class JoinGroup(BaseModel):
    invite_code: str = Field(..., min_length=6, max_length=32)


class GroupOut(BaseModel):
    id: int
    name: str
    invite_code: str
    description: Optional[str]
    member_count: int
    
    class Config:
        from_attributes = True


class GroupMemberOut(BaseModel):
    user_id: int
    first_name: str
    photo_url: Optional[str]
    role: str


class FeedItemOut(BaseModel):
    id: int
    user: dict
    week_start: date
    week_end: date
    avg_mood: Optional[float]
    filled_days: int
    metrics_summary: dict
    published_at: date
    
    class Config:
        from_attributes = True


# =============================================================================
# Endpoints
# =============================================================================

@router.post("", response_model=GroupOut)
async def create_group(
    data: GroupCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Создание группы."""
    # Проверяем что пользователь не в группе
    result = await db.execute(
        select(GroupMember).where(GroupMember.user_id == user.id)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already in a group",
        )
    
    # Создаем группу
    group = Group(
        name=data.name,
        invite_code=Group.generate_invite_code(),
        owner_id=user.id,
        description=data.description,
    )
    db.add(group)
    await db.flush()
    
    # Добавляем создателя как owner
    member = GroupMember(
        group_id=group.id,
        user_id=user.id,
        role=GroupRole.OWNER,
    )
    db.add(member)
    await db.commit()
    await db.refresh(group)
    
    return GroupOut(
        id=group.id,
        name=group.name,
        invite_code=group.invite_code,
        description=group.description,
        member_count=1,
    )


@router.post("/join")
async def join_group(
    data: JoinGroup,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Присоединение к группе по коду."""
    # Проверяем что пользователь не в группе
    result = await db.execute(
        select(GroupMember).where(GroupMember.user_id == user.id)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already in a group",
        )
    
    # Ищем группу
    result = await db.execute(
        select(Group).where(Group.invite_code == data.invite_code.upper())
    )
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # Проверяем лимит (3 человека)
    result = await db.execute(
        select(func.count(GroupMember.user_id)).where(GroupMember.group_id == group.id)
    )
    member_count = result.scalar()
    
    if member_count >= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group is full (max 3 members)",
        )
    
    # Добавляем
    member = GroupMember(
        group_id=group.id,
        user_id=user.id,
        role=GroupRole.MEMBER,
    )
    db.add(member)
    await db.commit()
    
    return {"status": "joined", "group_id": group.id}


@router.get("/my", response_model=GroupOut)
async def get_my_group(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Моя группа."""
    result = await db.execute(
        select(GroupMember).where(GroupMember.user_id == user.id)
    )
    membership = result.scalar_one_or_none()
    
    if not membership:
        raise HTTPException(status_code=404, detail="Not in a group")
    
    result = await db.execute(
        select(Group).where(Group.id == membership.group_id)
    )
    group = result.scalar_one()
    
    # Считаем участников
    result = await db.execute(
        select(func.count(GroupMember.user_id)).where(GroupMember.group_id == group.id)
    )
    member_count = result.scalar()
    
    return GroupOut(
        id=group.id,
        name=group.name,
        invite_code=group.invite_code,
        description=group.description,
        member_count=member_count,
    )


@router.get("/members", response_model=List[GroupMemberOut])
async def get_group_members(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Участники моей группы."""
    # Находим группу пользователя
    result = await db.execute(
        select(GroupMember).where(GroupMember.user_id == user.id)
    )
    membership = result.scalar_one_or_none()
    
    if not membership:
        raise HTTPException(status_code=404, detail="Not in a group")
    
    # Получаем участников
    result = await db.execute(
        select(GroupMember, User)
        .join(User, GroupMember.user_id == User.id)
        .where(GroupMember.group_id == membership.group_id)
    )
    members = result.all()
    
    return [
        GroupMemberOut(
            user_id=u.id,
            first_name=u.first_name or "User",
            photo_url=u.photo_url,
            role=m.role.value,
        )
        for m, u in members
    ]


@router.get("/feed", response_model=List[FeedItemOut])
async def get_group_feed(
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Групповая лента (только published отчеты).
    Ключевая фича - видны только опубликованные отчеты!
    """
    # Находим группу
    result = await db.execute(
        select(GroupMember).where(GroupMember.user_id == user.id)
    )
    membership = result.scalar_one_or_none()
    
    if not membership:
        raise HTTPException(status_code=404, detail="Not in a group")
    
    # Получаем ID участников группы
    result = await db.execute(
        select(GroupMember.user_id).where(
            GroupMember.group_id == membership.group_id,
            GroupMember.user_id != user.id,  # Не показываем свои отчеты в ленте
        )
    )
    member_ids = [row[0] for row in result.all()]
    
    if not member_ids:
        return []
    
    # Получаем published отчеты
    result = await db.execute(
        select(WeekReport, User)
        .join(User, WeekReport.user_id == User.id)
        .where(
            WeekReport.user_id.in_(member_ids),
            WeekReport.status == ReportStatus.PUBLISHED,
        )
        .order_by(WeekReport.published_at.desc())
        .limit(limit)
        .offset(offset)
    )
    reports = result.all()
    
    return [
        FeedItemOut(
            id=r.id,
            user={
                "id": u.id,
                "first_name": u.first_name,
                "photo_url": u.photo_url,
            },
            week_start=r.week_start_date,
            week_end=r.week_end_date,
            avg_mood=r.avg_mood,
            filled_days=r.filled_days,
            metrics_summary=r.metrics_summary,
            published_at=r.published_at.date() if r.published_at else r.week_start_date,
        )
        for r, u in reports
    ]

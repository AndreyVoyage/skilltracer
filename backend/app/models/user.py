"""
User Model

Модель пользователя Telegram с настройками и связями.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import BigInteger, JSON, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.entry import DailyEntry
    from app.models.tracker import CustomTracker
    from app.models.report import WeekReport
    from app.models.group import Group, GroupMember


class User(Base, TimestampMixin):
    """
    Пользователь Telegram.
    
    Primary key - telegram user_id (BigInteger).
    Хранит настройки в JSON поле.
    """
    
    __tablename__ = "users"
    
    # Primary Key - Telegram user_id
    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=False,  # Telegram ID приходит извне
        comment="Telegram user ID",
    )
    
    # Profile info
    username: Mapped[Optional[str]] = mapped_column(
        String(255),
        index=True,
        nullable=True,
        comment="Telegram username без @",
    )
    
    first_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Имя в Telegram",
    )
    
    last_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Фамилия в Telegram",
    )
    
    photo_url: Mapped[Optional[str]] = mapped_column(
        String(2048),
        nullable=True,
        comment="URL аватара из Telegram",
    )
    
    timezone: Mapped[str] = mapped_column(
        String(50),
        default="Europe/Moscow",
        server_default=text("'Europe/Moscow'"),
        nullable=False,
        comment="Часовой пояс пользователя (IANA format)",
    )
    
    settings: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        server_default=text("'{}'::jsonb"),
        nullable=False,
        comment='Настройки пользователя: {"reminder_time": "21:00", "theme": "dark"}',
    )
    
    # Relationships
    entries: Mapped[List["DailyEntry"]] = relationship(
        "DailyEntry",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    trackers: Mapped[List["CustomTracker"]] = relationship(
        "CustomTracker",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="CustomTracker.sort_order",
    )
    
    week_reports: Mapped[List["WeekReport"]] = relationship(
        "WeekReport",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="WeekReport.week_start_date.desc()",
    )
    
    owned_groups: Mapped[List["Group"]] = relationship(
        "Group",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    memberships: Mapped[List["GroupMember"]] = relationship(
        "GroupMember",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username!r})>"
    
    def get_full_name(self) -> str:
        """Полное имя пользователя."""
        parts = [self.first_name or "", self.last_name or ""]
        return " ".join(p for p in parts if p).strip() or f"User{self.id}"
    
    def get_current_week_dates(self) -> tuple[datetime, datetime]:
        """
        Возвращает (monday, sunday) для текущей недели с учетом timezone.
        
        Returns:
            tuple: (monday 00:00:00, sunday 23:59:59)
        """
        # Для MVP используем UTC, в проде нужно учитывать timezone
        today = datetime.utcnow().date()
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        return (
            datetime.combine(monday, datetime.min.time()),
            datetime.combine(sunday, datetime.max.time()),
        )
    
    def has_group(self) -> bool:
        """Проверяет, состоит ли пользователь в какой-либо группе."""
        return len(self.memberships) > 0
    
    def get_active_trackers(self) -> List["CustomTracker"]:
        """Возвращает только активные трекеры пользователя."""
        return [t for t in self.trackers if t.is_active]
    
    def get_group_ids(self) -> List[int]:
        """Возвращает список ID групп, в которых состоит пользователь."""
        return [m.group_id for m in self.memberships]

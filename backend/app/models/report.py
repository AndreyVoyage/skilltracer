"""
Report Models

WeekReport - публикуемый недельный отчет.
Comment - комментарий к опубликованному отчету.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class ReportStatus(str, PyEnum):
    """Статус недельного отчета."""
    
    DRAFT = "draft"
    PUBLISHED = "published"


class WeekReport(Base, TimestampMixin):
    """
    Недельный отчет (ПУБЛИЧНЫЙ после публикации).
    
    Ключевая логика приватности:
    - DRAFT: виден только владельцу (черновик)
    - PUBLISHED: виден группе (опубликован)
    
    Содержит агрегированные данные из DailyEntry за неделю,
    но не сами приватные DailyEntry.
    """
    
    __tablename__ = "week_reports"
    
    __table_args__ = (
        # Одна неделя = один отчет на пользователя
        UniqueConstraint("user_id", "week_start_date", name="uix_user_week"),
    )
    
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Уникальный ID отчета",
    )
    
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        comment="ID автора отчета",
    )
    
    week_start_date: Mapped[date] = mapped_column(
        Date,
        index=True,
        nullable=False,
        comment="Понедельник недели отчета",
    )
    
    week_end_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Воскресенье недели отчета",
    )
    
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, name="report_status", native_enum=False),
        default=ReportStatus.DRAFT,
        server_default=text("'draft'"),
        index=True,
        nullable=False,
        comment="draft или published",
    )
    
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Когда отчет был опубликован",
    )
    
    avg_mood: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Среднее настроение за неделю (1-5)",
    )
    
    filled_days: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
        comment="Сколько дней заполнено (0-7)",
    )
    
    metrics_summary: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        server_default=text("'{}'::jsonb"),
        nullable=False,
        comment='Средние значения трекеров: {"sport_avg": 4.2, ...}',
    )
    
    highlights: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Текстовое summary от AI или пользователя",
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="week_reports",
    )
    
    comments: Mapped[List["Comment"]] = relationship(
        "Comment",
        back_populates="week_report",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Comment.created_at",
    )
    
    def __repr__(self) -> str:
        return (
            f"<WeekReport(id={self.id}, user_id={self.user_id}, "
            f"week={self.week_start_date}, status={self.status.value})>"
        )
    
    def publish(self) -> None:
        """
        Публикует отчет.
        
        - Меняет статус на 'published'
        - Устанавливает published_at
        - Вызывает calculate_summary() если нужно
        """
        self.status = ReportStatus.PUBLISHED
        self.published_at = datetime.utcnow()
    
    def unpublish(self) -> None:
        """Возвращает отчет в черновики (draft)."""
        self.status = ReportStatus.DRAFT
        self.published_at = None
    
    def calculate_summary(self, entries: List) -> None:
        """
        Вычисляет summary отчета из списка DailyEntry.
        
        Args:
            entries: Список DailyEntry за неделю
        """
        if not entries:
            self.avg_mood = None
            self.filled_days = 0
            self.metrics_summary = {}
            return
        
        # Считаем среднее настроение
        moods = [e.mood for e in entries if e.mood is not None]
        self.avg_mood = sum(moods) / len(moods) if moods else None
        self.filled_days = len(entries)
        
        # Считаем средние по трекерам
        tracker_sums: dict = {}
        tracker_counts: dict = {}
        
        for entry in entries:
            for metric in entry.metrics:
                tracker_id = metric.tracker_id
                tracker_name = metric.tracker.name if metric.tracker else f"tracker_{tracker_id}"
                
                if tracker_name not in tracker_sums:
                    tracker_sums[tracker_name] = 0
                    tracker_counts[tracker_name] = 0
                
                tracker_sums[tracker_name] += metric.value
                tracker_counts[tracker_name] += 1
        
        # Формируем summary
        self.metrics_summary = {
            name: round(tracker_sums[name] / tracker_counts[name], 2)
            for name in tracker_sums
            if tracker_counts[name] > 0
        }
    
    def is_visible_to(self, user_id: int, group_member_ids: List[int]) -> bool:
        """
        Проверяет, может ли пользователь видеть этот отчет.
        
        Args:
            user_id: ID запрашивающего пользователя
            group_member_ids: ID членов группы автора
            
        Returns:
            True если пользователь может видеть отчет
        """
        # Свой отчет всегда виден
        if user_id == self.user_id:
            return True
        
        # Чужие draft не видны
        if self.status == ReportStatus.DRAFT:
            return False
        
        # Published виден членам группы
        return user_id in group_member_ids
    
    def format_week_label(self) -> str:
        """Форматирует метку недели: '15-21 Jan'."""
        start = self.week_start_date
        end = self.week_end_date
        
        if start.month == end.month:
            return f"{start.day}-{end.day} {start.strftime('%b')}"
        else:
            return f"{start.strftime('%d %b')} - {end.strftime('%d %b')}"
    
    def format_status_icon(self) -> str:
        """Иконка статуса: 📝 (draft) или ✅ (published)."""
        return "📝" if self.status == ReportStatus.DRAFT else "✅"


class Comment(Base, TimestampMixin):
    """
    Комментарий к опубликованному WeekReport.
    
    Только для отчетов со статусом 'published'.
    """
    
    __tablename__ = "comments"
    
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Уникальный ID комментария",
    )
    
    week_report_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("week_reports.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        comment="ID отчета",
    )
    
    author_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID автора комментария",
    )
    
    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Текст комментария",
    )
    
    # Relationships
    week_report: Mapped["WeekReport"] = relationship(
        "WeekReport",
        back_populates="comments",
    )
    
    author: Mapped["User"] = relationship(
        "User",
        foreign_keys=[author_id],
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        text_preview = self.text[:30] + "..." if len(self.text) > 30 else self.text
        return f"<Comment(id={self.id}, author={self.author_id}, text={text_preview!r})>"

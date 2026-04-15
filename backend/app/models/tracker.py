"""
CustomTracker Model

Пользовательские трекеры для отслеживания активностей.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.entry import EntryMetric


class CustomTracker(Base, TimestampMixin):
    """
    Пользовательский трекер (Спорт, Языки, Здоровье и т.д.).
    
    Каждый пользователь может создать свои трекеры
    и отслеживать их в DailyEntry через EntryMetric.
    """
    
    __tablename__ = "custom_trackers"
    
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Уникальный ID трекера",
    )
    
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        comment="ID владельца трекера",
    )
    
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Название трекера (например, 'Спорт', 'Английский')",
    )
    
    icon: Mapped[str] = mapped_column(
        String(10),
        default="📊",
        server_default=text("'📊'"),
        nullable=False,
        comment="Эмодзи иконка для трекера",
    )
    
    target_value: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Целевое значение (например, 5 раз в неделю). Null = без цели",
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("TRUE"),
        nullable=False,
        comment="Активен ли трекер (можно архивировать)",
    )
    
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        comment="Системный трекер (Здоровье, Спорт, Учёба, Отдых)",
    )
    
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
        comment="Порядок отображения в списке",
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="trackers",
    )
    
    metrics: Mapped[List["EntryMetric"]] = relationship(
        "EntryMetric",
        back_populates="tracker",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<CustomTracker(id={self.id}, name={self.name!r}, user_id={self.user_id})>"
    
    def format_display(self) -> str:
        """Форматирует отображение трекера: 📊 Спорт."""
        return f"{self.icon} {self.name}"
    
    def calculate_week_average(self, start_date: datetime, end_date: datetime) -> float:
        """
        Вычисляет среднее значение трекера за период.
        
        Args:
            start_date: Начало периода
            end_date: Конец периода
            
        Returns:
            Среднее значение (0.0 если нет данных)
        """
        from app.models.entry import DailyEntry
        
        relevant_metrics = [
            m for m in self.metrics
            if start_date.date() <= m.entry.entry_date <= end_date.date()
        ]
        
        if not relevant_metrics:
            return 0.0
        
        return sum(m.value for m in relevant_metrics) / len(relevant_metrics)

"""
Entry Models

DailyEntry - ежедневная приватная запись.
EntryMetric - значение трекера для конкретного дня.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.tracker import CustomTracker


class DailyEntry(Base, TimestampMixin):
    """
    Ежедневная запись (ПРИВАТНАЯ).
    
    Пользователь создает одну запись на день со своим настроением,
    заметками и значениями трекеров (EntryMetric).
    
    Видна только владельцу, группа не видит DailyEntry,
    только опубликованные WeekReport.
    """
    
    __tablename__ = "daily_entries"
    
    __table_args__ = (
        # Один день = одна запись на пользователя
        UniqueConstraint("user_id", "entry_date", name="uix_user_date"),
        # Настроение от 1 до 5
        CheckConstraint("mood BETWEEN 1 AND 5", name="ck_mood_range"),
    )
    
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Уникальный ID записи",
    )
    
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        comment="ID владельца записи",
    )
    
    entry_date: Mapped[date] = mapped_column(
        Date,
        index=True,
        nullable=False,
        comment="Дата записи (не created_at!)",
    )
    
    mood: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Настроение от 1 (ужасно) до 5 (отлично)",
    )
    
    text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Заметки/текст дня (приватный!)",
    )
    
    photo_file_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Telegram file_id фото дня (приватное!)",
    )
    
    voice_file_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Telegram file_id голосового/аудио сообщения",
    )
    
    video_file_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Telegram file_id видео сообщения",
    )
    
    has_media: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        comment="Есть ли медиа в записи (фото/голос/видео)",
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="entries",
    )
    
    metrics: Mapped[List["EntryMetric"]] = relationship(
        "EntryMetric",
        back_populates="entry",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<DailyEntry(id={self.id}, user_id={self.user_id}, date={self.entry_date})>"
    
    def get_metric_value(self, tracker_id: int) -> Optional[int]:
        """
        Получает значение конкретного трекера для этого дня.
        
        Args:
            tracker_id: ID трекера
            
        Returns:
            Значение или None если трекер не заполнен
        """
        for metric in self.metrics:
            if metric.tracker_id == tracker_id:
                return metric.value
        return None
    
    def set_metric_value(self, tracker: "CustomTracker", value: int) -> "EntryMetric":
        """
        Устанавливает значение трекера для этого дня.
        Создает новый EntryMetric или обновляет существующий.
        
        Args:
            tracker: Трекер
            value: Значение (0-5)
            
        Returns:
            EntryMetric объект
        """
        # Ищем существующий метрик
        for metric in self.metrics:
            if metric.tracker_id == tracker.id:
                metric.value = value
                return metric
        
        # Создаем новый
        from app.models.entry import EntryMetric
        metric = EntryMetric(
            entry=self,
            tracker=tracker,
            value=value,
        )
        self.metrics.append(metric)
        return metric
    
    def format_short(self) -> str:
        """Краткое форматирование записи: '2024-01-15 😊' (если mood есть)."""
        mood_emojis = {1: "😭", 2: "😟", 3: "😐", 4: "🙂", 5: "😄"}
        mood_str = mood_emojis.get(self.mood, "❓") if self.mood else "❓"
        return f"{self.entry_date} {mood_str}"


class EntryMetric(Base):
    """
    Значение трекера для конкретного дня.
    
    Связующая таблица между DailyEntry и CustomTracker
    с дополнительным полем value.
    """
    
    __tablename__ = "entry_metrics"
    
    __table_args__ = (
        # Один трекер = одно значение в день
        UniqueConstraint("entry_id", "tracker_id", name="uix_entry_tracker"),
        # Значение от 0 до 5
        CheckConstraint("value BETWEEN 0 AND 5", name="ck_value_range"),
    )
    
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Уникальный ID",
    )
    
    entry_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("daily_entries.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        comment="ID записи дня",
    )
    
    tracker_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("custom_trackers.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID трекера",
    )
    
    value: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Значение от 0 (нет активности) до 5 (максимум)",
    )
    
    # Relationships
    entry: Mapped["DailyEntry"] = relationship(
        "DailyEntry",
        back_populates="metrics",
    )
    
    tracker: Mapped["CustomTracker"] = relationship(
        "CustomTracker",
        back_populates="metrics",
    )
    
    def __repr__(self) -> str:
        return f"<EntryMetric(id={self.id}, tracker={self.tracker_id}, value={self.value})>"
    
    def format_display(self) -> str:
        """Форматирует отображение: 📊 Спорт: 4/5."""
        tracker_name = self.tracker.name if self.tracker else "Unknown"
        tracker_icon = self.tracker.icon if self.tracker else "📊"
        return f"{tracker_icon} {tracker_name}: {self.value}/5"

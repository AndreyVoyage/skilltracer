"""
Journal Entry Model

Модель для записей, создаваемых через бот (кнопочный интерфейс).
Соответствует ТЗ таблице entries.
"""

from datetime import date
from typing import Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    Integer,
    JSON,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class JournalEntry(Base, TimestampMixin):
    """
    Запись дневника, созданная через бот.
    """
    
    __tablename__ = "entries"
    
    __table_args__ = (
        UniqueConstraint("user_id", "entry_date", name="uix_user_date_entry"),
        CheckConstraint("health_score BETWEEN 1 AND 5", name="ck_health_range"),
        CheckConstraint("sport_score BETWEEN 1 AND 5", name="ck_sport_range"),
        CheckConstraint("study_score BETWEEN 1 AND 5", name="ck_study_range"),
        CheckConstraint("rest_score BETWEEN 1 AND 5", name="ck_rest_range"),
    )
    
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
    )
    
    entry_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    
    health_score: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    
    sport_score: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    
    study_score: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    
    rest_score: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    
    comment: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    media_urls: Mapped[list] = mapped_column(
        JSON,
        default=list,
        server_default="[]",
        nullable=False,
    )

"""
Report Link Model

Публичные ссылки для просмотра отчетов без авторизации.
"""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, Date, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ReportLink(Base):
    """
    Публичная ссылка на недельный отчет.
    
    Используется для шеринга отчетов вне Telegram.
    """
    
    __tablename__ = "report_links"
    
    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        comment="Уникальный ID ссылки",
    )
    
    token: Mapped[str] = mapped_column(
        String(16),
        unique=True,
        index=True,
        nullable=False,
        comment="Уникальный токен для URL",
    )
    
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="ID автора отчета",
    )
    
    week_start: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Начало недели отчета",
    )
    
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Дата истечения ссылки",
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Активна ли ссылка",
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        comment="Дата создания ссылки",
    )

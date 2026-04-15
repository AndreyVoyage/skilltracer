"""
Telegram Queue Model

Простая очередь для отправки отчетов через бота.
Используется для надежной доставки PNG отчетов из WebApp.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

if TYPE_CHECKING:
    pass


class TelegramQueue(Base):
    """
    Очередь задач на отправку сообщений через Telegram бота.
    
    Backend ставит задачу при запросе "Поделиться отчетом".
    Бот (или отдельная корутина) периодически проверяет и отправляет.
    """
    
    __tablename__ = "telegram_queue"
    
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Уникальный ID задачи",
    )
    
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
        comment="ID получателя (Telegram user_id)",
    )
    
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="send_report",
        comment="Тип действия: send_report, send_message",
    )
    
    payload: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment='JSON с данными для отправки',
    )
    
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
        index=True,
        comment="pending, processing, done, failed",
    )
    
    error_message: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        comment="Ошибка при отправке",
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Когда создана задача",
    )
    
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Когда обработана",
    )
    
    def __repr__(self) -> str:
        return f"<TelegramQueue(id={self.id}, user_id={self.user_id}, status={self.status})>"

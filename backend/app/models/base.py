"""
Base Model for SQLAlchemy 2.0

Содержит базовый класс и миксины для всех моделей.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Базовый класс для всех моделей SQLAlchemy 2.0.
    """
    
    # Автоматическое именование таблиц в snake_case
    # Можно переопределить через __tablename__
    pass


class TimestampMixin:
    """
    Миксин для автоматического добавления created_at и updated_at.
    
    Usage:
        class MyModel(Base, TimestampMixin):
            __tablename__ = "my_table"
            ...
    """
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Дата создания записи",
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Дата последнего обновления",
    )


class BigIntPrimaryKeyMixin:
    """
    Миксин для моделей с автоинкрементным BIGINT primary key.
    
    Usage:
        class MyModel(Base, BigIntPrimaryKeyMixin):
            __tablename__ = "my_table"
            ...
    """
    
    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="Уникальный идентификатор",
    )

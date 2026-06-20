from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import engine
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.entry import Entry
    from app.models.streak import Streak
    from app.models.user_settings import UserSettings
    from app.models.weekly_report import WeeklyReport


def _utc_now() -> datetime:
    """Return the current UTC time as a timezone-naive datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    """Telegram user stored in the application database."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
    )
    username: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    first_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    last_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    language: Mapped[str] = mapped_column(
        String(10),
        default="ru",
        nullable=False,
    )
    timezone: Mapped[str] = mapped_column(
        String(50),
        default="Europe/Moscow",
        nullable=False,
    )
    avatar_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        default=_utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=_utc_now,
        onupdate=_utc_now,
        nullable=False,
    )

    categories: Mapped[list["Category"]] = relationship(
        "Category",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    entries: Mapped[list["Entry"]] = relationship(
        "Entry",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    user_settings: Mapped["UserSettings"] = relationship(
        "UserSettings",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    streak: Mapped["Streak"] = relationship(
        "Streak",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    weekly_reports: Mapped[list["WeeklyReport"]] = relationship(
        "WeeklyReport",
        back_populates="user",
        cascade="all, delete-orphan",
    )


async def create_tables() -> None:
    """Create all tables defined by the ORM metadata."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

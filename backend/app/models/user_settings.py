from __future__ import annotations

from datetime import datetime, time, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


def _utc_now() -> datetime:
    """Return the current UTC time as a timezone-naive datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class UserSettings(Base):
    """User-specific application settings."""

    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
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
    reminder_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    reminder_time: Mapped[time] = mapped_column(
        Time,
        nullable=True,
    )
    reminder_days: Mapped[str] = mapped_column(
        String(20),
        default="1,2,3,4,5",  # mon-fri as CSV
        nullable=False,
    )
    report_template: Mapped[str] = mapped_column(
        String(50),
        default="default",
        nullable=False,
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

    user: Mapped["User"] = relationship("User", back_populates="user_settings")

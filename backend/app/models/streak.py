from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


def _utc_now() -> datetime:
    """Return the current UTC time as a timezone-naive datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Streak(Base):
    """User streak tracking for consecutive daily entries."""

    __tablename__ = "streaks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    current_streak: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    best_streak: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    last_entry_date: Mapped[datetime | None] = mapped_column(
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

    __table_args__ = (
        CheckConstraint("current_streak <= best_streak", name="ck_streak_current_le_best"),
        CheckConstraint("current_streak >= 0", name="ck_streak_current_ge_0"),
    )

    user: Mapped["User"] = relationship("User", back_populates="streak")

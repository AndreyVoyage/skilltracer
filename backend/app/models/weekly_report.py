from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


def _utc_now() -> datetime:
    """Return the current UTC time as a timezone-naive datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class WeeklyReport(Base):
    """Generated weekly report (PNG or video) for a user."""

    __tablename__ = "weekly_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    week_start: Mapped[datetime] = mapped_column(
        Date,
        nullable=False,
    )
    week_end: Mapped[datetime] = mapped_column(
        Date,
        nullable=False,
    )
    report_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,  # png, video
    )
    template: Mapped[str] = mapped_column(
        String(50),
        default="default",
        nullable=False,
    )
    file_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,  # pending, generating, ready, failed
    )
    error_message: Mapped[str | None] = mapped_column(
        String(1000),
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
        CheckConstraint("week_end = week_start + 6", name="ck_weekly_report_week_duration"),
        CheckConstraint(
            "status IN ('pending', 'generating', 'ready', 'failed')",
            name="ck_weekly_report_status",
        ),
    )

    user: Mapped["User"] = relationship("User", back_populates="weekly_reports")

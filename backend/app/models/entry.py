from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.media_attachment import MediaAttachment
    from app.models.rating import Rating
    from app.models.user import User


def _utc_now() -> datetime:
    """Return the current UTC time as a timezone-naive datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Entry(Base):
    """A daily journal entry with optional comment and media attachments."""

    __tablename__ = "entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    entry_date: Mapped[datetime] = mapped_column(
        Date,
        nullable=False,
    )
    comment: Mapped[str | None] = mapped_column(
        String(2000),
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
        UniqueConstraint("user_id", "entry_date", name="uq_entry_user_date"),
        Index("ix_entries_user_id_entry_date", "user_id", "entry_date"),
    )

    user: Mapped["User"] = relationship("User", back_populates="entries")
    ratings: Mapped[list["Rating"]] = relationship(
        "Rating",
        back_populates="entry",
        cascade="all, delete-orphan",
    )
    media_attachments: Mapped[list["MediaAttachment"]] = relationship(
        "MediaAttachment",
        back_populates="entry",
        cascade="all, delete-orphan",
    )

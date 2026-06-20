from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.entry import Entry


def _utc_now() -> datetime:
    """Return the current UTC time as a timezone-naive datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class MediaAttachment(Base):
    """Media file attached to an entry (photo, voice, audio)."""

    __tablename__ = "media_attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("entries.id", ondelete="CASCADE"),
        nullable=False,
    )
    telegram_file_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    local_file_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    media_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,  # photo, voice, audio
    )
    file_size: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
    mime_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        default=_utc_now,
        nullable=False,
    )

    entry: Mapped["Entry"] = relationship("Entry", back_populates="media_attachments")

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.entry import Entry


def _utc_now() -> datetime:
    """Return the current UTC time as a timezone-naive datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Rating(Base):
    """A rating score (1-5) for a specific category within an entry."""

    __tablename__ = "ratings"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("entries.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
    )
    score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        default=_utc_now,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("entry_id", "category_id", name="uq_rating_entry_category"),
        CheckConstraint("score IN (1, 2, 3, 4, 5)", name="ck_rating_score_range"),
    )

    entry: Mapped["Entry"] = relationship("Entry", back_populates="ratings")
    category: Mapped["Category"] = relationship("Category", back_populates="ratings")

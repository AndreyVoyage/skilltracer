from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.entry import Entry
from app.models.rating import Rating
from app.models.schemas import EntryCreate, EntryUpdate, RatingCreate
from app.models.streak import Streak
from app.models.user import User

if TYPE_CHECKING:
    from app.models.user import User


class EntryServiceError(Exception):
    """Base exception for entry service errors."""

    pass


class EntryAlreadyExistsError(EntryServiceError):
    """Raised when user tries to create a second entry for the same date."""

    pass


class EntryNotFoundError(EntryServiceError):
    """Raised when entry is not found or doesn't belong to the user."""

    pass


class EntryService:
    """Service for managing daily journal entries with atomic transactions."""

    @staticmethod
    async def create_entry(
        db: AsyncSession,
        user: User,
        data: EntryCreate,
    ) -> Entry:
        """Create a new daily entry with ratings (atomic transaction).

        Raises:
            EntryAlreadyExistsError: If entry for this date already exists.
        """
        # Check for existing entry on the same date
        existing = await db.execute(
            select(Entry).where(
                Entry.user_id == user.id,
                Entry.entry_date == data.entry_date,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise EntryAlreadyExistsError(
                f"Entry for {data.entry_date} already exists. Use update instead."
            )

        # Create entry
        entry = Entry(
            user_id=user.id,
            entry_date=data.entry_date,
            comment=data.comment,
        )
        db.add(entry)
        await db.flush()  # Get entry.id for ratings

        # Create ratings
        for rating_data in data.ratings:
            rating = Rating(
                entry_id=entry.id,
                category_id=rating_data.category_id,
                score=rating_data.score,
            )
            db.add(rating)

        # Update streak
        await EntryService._update_streak(db, user, data.entry_date)

        await db.commit()
        # Eagerly load relationships for response serialization
        result = await db.execute(
            select(Entry)
            .options(selectinload(Entry.ratings))
            .options(selectinload(Entry.media_attachments))
            .where(Entry.id == entry.id)
        )
        return result.scalar_one()

    @staticmethod
    async def update_entry(
        db: AsyncSession,
        user: User,
        entry_id: int,
        data: EntryUpdate,
    ) -> Entry:
        """Update an existing entry (comment and/or ratings).

        Raises:
            EntryNotFoundError: If entry doesn't exist or doesn't belong to user.
        """
        entry = await EntryService.get_entry(db, user, entry_id)

        if data.comment is not None:
            entry.comment = data.comment

        if data.ratings is not None:
            # Delete old ratings and clear collection
            for old_rating in entry.ratings:
                await db.delete(old_rating)
            entry.ratings.clear()
            await db.flush()

            for rating_data in data.ratings:
                rating = Rating(
                    category_id=rating_data.category_id,
                    score=rating_data.score,
                )
                entry.ratings.append(rating)

        await db.commit()
        return entry

    @staticmethod
    async def delete_entry(
        db: AsyncSession,
        user: User,
        entry_id: int,
    ) -> None:
        """Delete an entry and all related ratings/media (cascade).

        Raises:
            EntryNotFoundError: If entry doesn't exist or doesn't belong to user.
        """
        entry = await EntryService.get_entry(db, user, entry_id)
        await db.delete(entry)
        await db.commit()

    @staticmethod
    async def get_entry(
        db: AsyncSession,
        user: User,
        entry_id: int,
    ) -> Entry:
        """Get entry by ID with ownership check.

        Raises:
            EntryNotFoundError: If entry doesn't exist or doesn't belong to user.
        """
        result = await db.execute(
            select(Entry)
            .options(selectinload(Entry.ratings))
            .options(selectinload(Entry.media_attachments))
            .where(Entry.id == entry_id, Entry.user_id == user.id)
        )
        entry = result.scalar_one_or_none()
        if entry is None:
            raise EntryNotFoundError(f"Entry {entry_id} not found")
        return entry

    @staticmethod
    async def list_entries(
        db: AsyncSession,
        user: User,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Entry]:
        """List entries for user, ordered by date descending."""
        result = await db.execute(
            select(Entry)
            .options(selectinload(Entry.ratings))
            .options(selectinload(Entry.media_attachments))
            .where(Entry.user_id == user.id)
            .order_by(Entry.entry_date.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_entry_by_date(
        db: AsyncSession,
        user: User,
        entry_date: date,
    ) -> Entry | None:
        """Get entry for a specific date."""
        result = await db.execute(
            select(Entry)
            .options(selectinload(Entry.ratings))
            .options(selectinload(Entry.media_attachments))
            .where(Entry.user_id == user.id, Entry.entry_date == entry_date)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def _update_streak(
        db: AsyncSession,
        user: User,
        entry_date: date,
    ) -> None:
        """Update user's streak after creating an entry."""
        result = await db.execute(
            select(Streak).where(Streak.user_id == user.id)
        )
        streak = result.scalar_one_or_none()

        if streak is None:
            streak = Streak(user_id=user.id, current_streak=1, best_streak=1)
            db.add(streak)
            return

        # Check if entry is consecutive
        if streak.last_entry_date is not None:
            delta = entry_date - streak.last_entry_date
            if delta.days == 1:
                # Consecutive day
                streak.current_streak += 1
                if streak.current_streak > streak.best_streak:
                    streak.best_streak = streak.current_streak
            elif delta.days == 0:
                # Same day, don't update streak
                pass
            else:
                # Streak broken
                streak.current_streak = 1

        streak.last_entry_date = entry_date

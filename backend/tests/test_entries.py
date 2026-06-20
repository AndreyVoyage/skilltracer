from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.entry import Entry
from app.models.schemas import CategoryCreate, EntryCreate, EntryUpdate, RatingCreate, UserCreate
from app.models.user import User
from app.services.auth import create_access_token, get_or_create_user
from app.services.category import create_category
from app.services.entry_service import (
    EntryAlreadyExistsError,
    EntryNotFoundError,
    EntryService,
)


def _auth_headers(user: User) -> dict[str, str]:
    """Return an Authorization header with a valid JWT for the user."""
    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


async def _other_user(db_session: AsyncSession) -> User:
    """Create and return a second user for ownership tests."""
    return await get_or_create_user(
        db_session,
        UserCreate(
            telegram_id=999888777,
            username="otheruser",
            first_name="Other",
            last_name="User",
        ),
    )


async def _create_category(db_session: AsyncSession, user: User, name: str) -> None:
    """Helper to create a category for rating tests."""
    await create_category(db_session, user.id, CategoryCreate(name=name))


class TestEntryService:
    """Tests for entry service-level CRUD operations."""

    async def test_create_entry(self, db_session: AsyncSession) -> None:
        """Creating an entry should persist it with ratings."""
        user = await get_or_create_user(
            db_session,
            UserCreate(telegram_id=111222333, username="entryuser"),
        )
        await _create_category(db_session, user, "Health")
        await _create_category(db_session, user, "Work")

        # Get category IDs
        from app.models.category import Category
        result = await db_session.execute(
            select(Category).where(Category.user_id == user.id)
        )
        categories = list(result.scalars().all())
        assert len(categories) == 2

        entry = await EntryService.create_entry(
            db_session,
            user,
            EntryCreate(
                entry_date=date(2026, 6, 20),
                comment="Great day!",
                ratings=[
                    RatingCreate(category_id=categories[0].id, score=5),
                    RatingCreate(category_id=categories[1].id, score=4),
                ],
            ),
        )

        assert entry.id is not None
        assert entry.user_id == user.id
        assert entry.entry_date == date(2026, 6, 20)
        assert entry.comment == "Great day!"
        assert len(entry.ratings) == 2
        assert entry.ratings[0].score == 5
        assert entry.ratings[1].score == 4

    async def test_create_entry_duplicate_date(self, db_session: AsyncSession) -> None:
        """Creating a second entry for the same date should raise."""
        user = await get_or_create_user(
            db_session,
            UserCreate(telegram_id=111222334, username="dupuser"),
        )
        await _create_category(db_session, user, "Health")

        result = await db_session.execute(
            select(Entry).where(Entry.user_id == user.id)
        )
        # Actually get category
        from app.models.category import Category
        cat_result = await db_session.execute(
            select(Category).where(Category.user_id == user.id)
        )
        category = cat_result.scalar_one()

        await EntryService.create_entry(
            db_session,
            user,
            EntryCreate(
                entry_date=date(2026, 6, 20),
                ratings=[RatingCreate(category_id=category.id, score=3)],
            ),
        )

        try:
            await EntryService.create_entry(
                db_session,
                user,
                EntryCreate(
                    entry_date=date(2026, 6, 20),
                    ratings=[RatingCreate(category_id=category.id, score=4)],
                ),
            )
            assert False, "Expected EntryAlreadyExistsError"
        except EntryAlreadyExistsError:
            pass

    async def test_get_entry(self, db_session: AsyncSession) -> None:
        """Getting an entry should return it with ratings."""
        user = await get_or_create_user(
            db_session,
            UserCreate(telegram_id=111222335, username="getuser"),
        )
        await _create_category(db_session, user, "Health")

        from app.models.category import Category
        cat_result = await db_session.execute(
            select(Category).where(Category.user_id == user.id)
        )
        category = cat_result.scalar_one()

        entry = await EntryService.create_entry(
            db_session,
            user,
            EntryCreate(
                entry_date=date(2026, 6, 21),
                ratings=[RatingCreate(category_id=category.id, score=3)],
            ),
        )

        retrieved = await EntryService.get_entry(db_session, user, entry.id)
        assert retrieved.id == entry.id
        assert len(retrieved.ratings) == 1

    async def test_get_entry_ownership(self, db_session: AsyncSession) -> None:
        """A user should not retrieve another user's entry."""
        user = await get_or_create_user(
            db_session,
            UserCreate(telegram_id=111222336, username="ownuser"),
        )
        other = await _other_user(db_session)
        await _create_category(db_session, other, "Health")

        from app.models.category import Category
        cat_result = await db_session.execute(
            select(Category).where(Category.user_id == other.id)
        )
        category = cat_result.scalar_one()

        entry = await EntryService.create_entry(
            db_session,
            other,
            EntryCreate(
                entry_date=date(2026, 6, 22),
                ratings=[RatingCreate(category_id=category.id, score=5)],
            ),
        )

        try:
            await EntryService.get_entry(db_session, user, entry.id)
            assert False, "Expected EntryNotFoundError"
        except EntryNotFoundError:
            pass

    async def test_list_entries(self, db_session: AsyncSession) -> None:
        """Listing entries should return only the user's entries, ordered by date."""
        user = await get_or_create_user(
            db_session,
            UserCreate(telegram_id=111222337, username="listuser"),
        )
        await _create_category(db_session, user, "Health")

        from app.models.category import Category
        cat_result = await db_session.execute(
            select(Category).where(Category.user_id == user.id)
        )
        category = cat_result.scalar_one()

        await EntryService.create_entry(
            db_session,
            user,
            EntryCreate(
                entry_date=date(2026, 6, 18),
                ratings=[RatingCreate(category_id=category.id, score=3)],
            ),
        )
        await EntryService.create_entry(
            db_session,
            user,
            EntryCreate(
                entry_date=date(2026, 6, 19),
                ratings=[RatingCreate(category_id=category.id, score=4)],
            ),
        )

        entries = await EntryService.list_entries(db_session, user)

        assert len(entries) == 2
        # Ordered by date descending
        assert entries[0].entry_date == date(2026, 6, 19)
        assert entries[1].entry_date == date(2026, 6, 18)

    async def test_update_entry(self, db_session: AsyncSession) -> None:
        """Updating an entry should change comment and ratings."""
        user = await get_or_create_user(
            db_session,
            UserCreate(telegram_id=111222338, username="upduser"),
        )
        await _create_category(db_session, user, "Health")
        await _create_category(db_session, user, "Work")

        from app.models.category import Category
        cat_result = await db_session.execute(
            select(Category).where(Category.user_id == user.id)
        )
        categories = list(cat_result.scalars().all())

        entry = await EntryService.create_entry(
            db_session,
            user,
            EntryCreate(
                entry_date=date(2026, 6, 23),
                comment="Old comment",
                ratings=[
                    RatingCreate(category_id=categories[0].id, score=2),
                ],
            ),
        )

        updated = await EntryService.update_entry(
            db_session,
            user,
            entry.id,
            EntryUpdate(
                comment="New comment",
                ratings=[
                    RatingCreate(category_id=categories[0].id, score=5),
                    RatingCreate(category_id=categories[1].id, score=4),
                ],
            ),
        )

        assert updated.comment == "New comment"
        assert len(updated.ratings) == 2
        assert updated.ratings[0].score == 5
        assert updated.ratings[1].score == 4

    async def test_delete_entry(self, db_session: AsyncSession) -> None:
        """Deleting an entry should remove it and cascade ratings."""
        user = await get_or_create_user(
            db_session,
            UserCreate(telegram_id=111222339, username="deluser"),
        )
        await _create_category(db_session, user, "Health")

        from app.models.category import Category
        cat_result = await db_session.execute(
            select(Category).where(Category.user_id == user.id)
        )
        category = cat_result.scalar_one()

        entry = await EntryService.create_entry(
            db_session,
            user,
            EntryCreate(
                entry_date=date(2026, 6, 24),
                ratings=[RatingCreate(category_id=category.id, score=3)],
            ),
        )

        await EntryService.delete_entry(db_session, user, entry.id)

        try:
            await EntryService.get_entry(db_session, user, entry.id)
            assert False, "Expected EntryNotFoundError"
        except EntryNotFoundError:
            pass

    async def test_entry_with_user(self, db_session: AsyncSession) -> None:
        """An entry should be accessible through the user relationship."""
        user = await get_or_create_user(
            db_session,
            UserCreate(telegram_id=111222340, username="reluser"),
        )
        await _create_category(db_session, user, "Health")

        from app.models.category import Category
        cat_result = await db_session.execute(
            select(Category).where(Category.user_id == user.id)
        )
        category = cat_result.scalar_one()

        entry = await EntryService.create_entry(
            db_session,
            user,
            EntryCreate(
                entry_date=date(2026, 6, 25),
                ratings=[RatingCreate(category_id=category.id, score=4)],
            ),
        )

        result = await db_session.execute(
            select(User)
            .options(selectinload(User.entries))
            .where(User.id == user.id),
        )
        user_with_entries = result.scalar_one()

        assert len(user_with_entries.entries) == 1
        assert user_with_entries.entries[0].id == entry.id


class TestEntryEndpoints:
    """Tests for the entries API endpoints."""

    async def test_create_entry(self, client: TestClient, sample_user: User, db_session: AsyncSession) -> None:
        """An authenticated user can create an entry with ratings."""
        await create_category(db_session, sample_user.id, CategoryCreate(name="Health"))

        # Get category ID
        from app.models.category import Category
        cat_result = await db_session.execute(
            select(Category).where(Category.user_id == sample_user.id)
        )
        category = cat_result.scalar_one()

        response = client.post(
            "/api/v1/entries",
            json={
                "entry_date": "2026-06-20",
                "comment": "Great day!",
                "ratings": [
                    {"category_id": category.id, "score": 5},
                ],
            },
            headers=_auth_headers(sample_user),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["entry_date"] == "2026-06-20"
        assert data["comment"] == "Great day!"
        assert len(data["ratings"]) == 1
        assert data["ratings"][0]["score"] == 5

    async def test_create_entry_duplicate(self, client: TestClient, sample_user: User, db_session: AsyncSession) -> None:
        """Creating a duplicate entry for the same date returns 409."""
        await create_category(db_session, sample_user.id, CategoryCreate(name="Health"))

        from app.models.category import Category
        cat_result = await db_session.execute(
            select(Category).where(Category.user_id == sample_user.id)
        )
        category = cat_result.scalar_one()

        # First entry
        client.post(
            "/api/v1/entries",
            json={
                "entry_date": "2026-06-21",
                "ratings": [{"category_id": category.id, "score": 3}],
            },
            headers=_auth_headers(sample_user),
        )

        # Duplicate
        response = client.post(
            "/api/v1/entries",
            json={
                "entry_date": "2026-06-21",
                "ratings": [{"category_id": category.id, "score": 4}],
            },
            headers=_auth_headers(sample_user),
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    async def test_list_entries(self, client: TestClient, sample_user: User, db_session: AsyncSession) -> None:
        """An authenticated user can list their entries."""
        await create_category(db_session, sample_user.id, CategoryCreate(name="Health"))

        from app.models.category import Category
        cat_result = await db_session.execute(
            select(Category).where(Category.user_id == sample_user.id)
        )
        category = cat_result.scalar_one()

        await EntryService.create_entry(
            db_session,
            sample_user,
            EntryCreate(
                entry_date=date(2026, 6, 15),
                ratings=[RatingCreate(category_id=category.id, score=3)],
            ),
        )

        response = client.get(
            "/api/v1/entries",
            headers=_auth_headers(sample_user),
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["entry_date"] == "2026-06-15"

    async def test_get_entry(self, client: TestClient, sample_user: User, db_session: AsyncSession) -> None:
        """An authenticated user can retrieve their entry."""
        await create_category(db_session, sample_user.id, CategoryCreate(name="Health"))

        from app.models.category import Category
        cat_result = await db_session.execute(
            select(Category).where(Category.user_id == sample_user.id)
        )
        category = cat_result.scalar_one()

        entry = await EntryService.create_entry(
            db_session,
            sample_user,
            EntryCreate(
                entry_date=date(2026, 6, 16),
                ratings=[RatingCreate(category_id=category.id, score=4)],
            ),
        )

        response = client.get(
            f"/api/v1/entries/{entry.id}",
            headers=_auth_headers(sample_user),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == entry.id
        assert data["ratings"][0]["score"] == 4

    async def test_update_entry(self, client: TestClient, sample_user: User, db_session: AsyncSession) -> None:
        """An authenticated user can update their entry."""
        await create_category(db_session, sample_user.id, CategoryCreate(name="Health"))

        from app.models.category import Category
        cat_result = await db_session.execute(
            select(Category).where(Category.user_id == sample_user.id)
        )
        category = cat_result.scalar_one()

        entry = await EntryService.create_entry(
            db_session,
            sample_user,
            EntryCreate(
                entry_date=date(2026, 6, 17),
                comment="Old",
                ratings=[RatingCreate(category_id=category.id, score=2)],
            ),
        )

        response = client.patch(
            f"/api/v1/entries/{entry.id}",
            json={
                "comment": "Updated",
                "ratings": [{"category_id": category.id, "score": 5}],
            },
            headers=_auth_headers(sample_user),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["comment"] == "Updated"
        assert data["ratings"][0]["score"] == 5

    async def test_delete_entry(self, client: TestClient, sample_user: User, db_session: AsyncSession) -> None:
        """An authenticated user can delete their entry."""
        await create_category(db_session, sample_user.id, CategoryCreate(name="Health"))

        from app.models.category import Category
        cat_result = await db_session.execute(
            select(Category).where(Category.user_id == sample_user.id)
        )
        category = cat_result.scalar_one()

        entry = await EntryService.create_entry(
            db_session,
            sample_user,
            EntryCreate(
                entry_date=date(2026, 6, 18),
                ratings=[RatingCreate(category_id=category.id, score=3)],
            ),
        )

        response = client.delete(
            f"/api/v1/entries/{entry.id}",
            headers=_auth_headers(sample_user),
        )

        assert response.status_code == 200
        assert response.json() == {"message": "Entry deleted"}

    async def test_entry_ownership(self, client: TestClient, sample_user: User, db_session: AsyncSession) -> None:
        """A user cannot access another user's entry."""
        other = await _other_user(db_session)
        await create_category(db_session, other.id, CategoryCreate(name="Health"))

        from app.models.category import Category
        cat_result = await db_session.execute(
            select(Category).where(Category.user_id == other.id)
        )
        category = cat_result.scalar_one()

        entry = await EntryService.create_entry(
            db_session,
            other,
            EntryCreate(
                entry_date=date(2026, 6, 19),
                ratings=[RatingCreate(category_id=category.id, score=5)],
            ),
        )

        response = client.get(
            f"/api/v1/entries/{entry.id}",
            headers=_auth_headers(sample_user),
        )

        assert response.status_code == 404

    def test_unauthorized_entry_list(self, client: TestClient) -> None:
        """Requesting entries without authentication should return 401."""
        response = client.get("/api/v1/entries")

        assert response.status_code == 401

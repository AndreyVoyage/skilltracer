from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.services.auth import create_access_token, get_or_create_user
from app.models.schemas import CategoryCreate, CategoryUpdate, UserCreate
from app.services.category import (
    create_category,
    delete_category,
    get_category,
    list_categories,
    update_category,
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


class TestCategoryService:
    """Tests for category service-level CRUD operations."""

    async def test_create_category(self, db_session: AsyncSession) -> None:
        """Creating a category should persist it with the given fields."""
        user = await get_or_create_user(
            db_session,
            UserCreate(telegram_id=111222333, username="catuser"),
        )

        category = await create_category(
            db_session,
            user.id,
            CategoryCreate(name="Health", icon="💪", color="#FF0000"),
        )

        assert category.id is not None
        assert category.user_id == user.id
        assert category.name == "Health"
        assert category.icon == "💪"
        assert category.color == "#FF0000"

    async def test_list_categories(self, db_session: AsyncSession) -> None:
        """Listing categories should return only the user's categories."""
        user = await get_or_create_user(
            db_session,
            UserCreate(telegram_id=111222334, username="listuser"),
        )
        other = await _other_user(db_session)

        await create_category(
            db_session,
            user.id,
            CategoryCreate(name="Work"),
        )
        await create_category(
            db_session,
            other.id,
            CategoryCreate(name="Personal"),
        )

        categories = await list_categories(db_session, user.id)

        assert len(categories) == 1
        assert categories[0].name == "Work"

    async def test_get_category_ownership(
        self,
        db_session: AsyncSession,
    ) -> None:
        """A user should not retrieve another user's category."""
        user = await get_or_create_user(
            db_session,
            UserCreate(telegram_id=111222335, username="ownuser"),
        )
        other = await _other_user(db_session)
        category = await create_category(
            db_session,
            other.id,
            CategoryCreate(name="Secret"),
        )

        result = await get_category(db_session, category.id, user.id)

        assert result is None

    async def test_update_category(self, db_session: AsyncSession) -> None:
        """Updating a category should change only the provided fields."""
        user = await get_or_create_user(
            db_session,
            UserCreate(telegram_id=111222336, username="upduser"),
        )
        category = await create_category(
            db_session,
            user.id,
            CategoryCreate(name="Old", icon="📁"),
        )

        updated = await update_category(
            db_session,
            category,
            CategoryUpdate(name="New"),
        )

        assert updated.name == "New"
        assert updated.icon == "📁"

    async def test_delete_category(self, db_session: AsyncSession) -> None:
        """Deleting a category should remove it from the database."""
        user = await get_or_create_user(
            db_session,
            UserCreate(telegram_id=111222337, username="deluser"),
        )
        category = await create_category(
            db_session,
            user.id,
            CategoryCreate(name="Temp"),
        )

        await delete_category(db_session, category)
        result = await get_category(db_session, category.id, user.id)

        assert result is None

    async def test_category_with_user(self, db_session: AsyncSession) -> None:
        """A category should be accessible through the user relationship."""
        user = await get_or_create_user(
            db_session,
            UserCreate(telegram_id=111222338, username="reluser"),
        )
        category = await create_category(
            db_session,
            user.id,
            CategoryCreate(name="Rel"),
        )

        result = await db_session.execute(
            select(User)
            .options(selectinload(User.categories))
            .where(User.id == user.id),
        )
        user_with_categories = result.scalar_one()

        assert len(user_with_categories.categories) == 1
        assert user_with_categories.categories[0].id == category.id


class TestCategoryEndpoints:
    """Tests for the categories API endpoints."""

    async def test_create_category(
        self,
        client: TestClient,
        sample_user: User,
    ) -> None:
        """An authenticated user can create a category."""
        response = client.post(
            "/api/v1/categories",
            json={"name": "Finance", "icon": "💰", "color": "#00FF00"},
            headers=_auth_headers(sample_user),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Finance"
        assert data["icon"] == "💰"
        assert data["color"] == "#00FF00"
        assert data["id"] is not None

    async def test_list_categories(
        self,
        client: TestClient,
        sample_user: User,
        db_session: AsyncSession,
    ) -> None:
        """An authenticated user can list their categories."""
        await create_category(
            db_session,
            sample_user.id,
            CategoryCreate(name="Books"),
        )

        response = client.get(
            "/api/v1/categories",
            headers=_auth_headers(sample_user),
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Books"

    async def test_get_category(
        self,
        client: TestClient,
        sample_user: User,
        db_session: AsyncSession,
    ) -> None:
        """An authenticated user can retrieve one of their categories."""
        category = await create_category(
            db_session,
            sample_user.id,
            CategoryCreate(name="Sport"),
        )

        response = client.get(
            f"/api/v1/categories/{category.id}",
            headers=_auth_headers(sample_user),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == category.id
        assert data["name"] == "Sport"

    async def test_update_category(
        self,
        client: TestClient,
        sample_user: User,
        db_session: AsyncSession,
    ) -> None:
        """An authenticated user can update their category."""
        category = await create_category(
            db_session,
            sample_user.id,
            CategoryCreate(name="Old Name"),
        )

        response = client.patch(
            f"/api/v1/categories/{category.id}",
            json={"name": "New Name", "icon": "🌟"},
            headers=_auth_headers(sample_user),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["icon"] == "🌟"

    async def test_delete_category(
        self,
        client: TestClient,
        sample_user: User,
        db_session: AsyncSession,
    ) -> None:
        """An authenticated user can delete their category."""
        category = await create_category(
            db_session,
            sample_user.id,
            CategoryCreate(name="To Delete"),
        )

        response = client.delete(
            f"/api/v1/categories/{category.id}",
            headers=_auth_headers(sample_user),
        )

        assert response.status_code == 200
        assert response.json() == {"message": "Category deleted"}

    async def test_category_ownership(
        self,
        client: TestClient,
        sample_user: User,
        db_session: AsyncSession,
    ) -> None:
        """A user cannot access another user's category."""
        other = await _other_user(db_session)
        category = await create_category(
            db_session,
            other.id,
            CategoryCreate(name="Private"),
        )

        response = client.get(
            f"/api/v1/categories/{category.id}",
            headers=_auth_headers(sample_user),
        )

        assert response.status_code == 404

    def test_unauthorized_category_list(self, client: TestClient) -> None:
        """Requesting categories without authentication should return 401."""
        response = client.get("/api/v1/categories")

        assert response.status_code == 401

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.schemas import CategoryCreate, CategoryUpdate


async def create_category(
    db: AsyncSession,
    user_id: int,
    data: CategoryCreate,
) -> Category:
    """Create a new category owned by the given user."""
    category = Category(
        user_id=user_id,
        name=data.name,
        icon=data.icon,
        color=data.color,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


async def list_categories(
    db: AsyncSession,
    user_id: int,
) -> list[Category]:
    """Return all categories belonging to the given user."""
    result = await db.execute(
        select(Category).where(Category.user_id == user_id),
    )
    return list(result.scalars().all())


async def get_category(
    db: AsyncSession,
    category_id: int,
    user_id: int,
) -> Category | None:
    """Return a category by ID only if it belongs to the given user."""
    result = await db.execute(
        select(Category).where(
            Category.id == category_id,
            Category.user_id == user_id,
        ),
    )
    return result.scalar_one_or_none()


async def update_category(
    db: AsyncSession,
    category: Category,
    data: CategoryUpdate,
) -> Category:
    """Apply non-null update fields and persist the category."""
    if data.name is not None:
        category.name = data.name
    if data.icon is not None:
        category.icon = data.icon
    if data.color is not None:
        category.color = data.color

    await db.commit()
    await db.refresh(category)
    return category


async def delete_category(
    db: AsyncSession,
    category: Category,
) -> None:
    """Delete the given category."""
    await db.delete(category)
    await db.commit()

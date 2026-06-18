from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.schemas import CategoryCreate, CategoryResponse, CategoryUpdate
from app.models.user import User
from app.services import category as category_service

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post("", response_model=CategoryResponse)
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CategoryResponse:
    """Create a new category for the current user."""
    category = await category_service.create_category(
        db,
        current_user.id,
        data,
    )
    return CategoryResponse.model_validate(category)


@router.get("", response_model=list[CategoryResponse])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CategoryResponse]:
    """List all categories owned by the current user."""
    categories = await category_service.list_categories(db, current_user.id)
    return [CategoryResponse.model_validate(c) for c in categories]


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CategoryResponse:
    """Get a single category by ID if it belongs to the current user."""
    category = await category_service.get_category(
        db,
        category_id,
        current_user.id,
    )
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    return CategoryResponse.model_validate(category)


@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CategoryResponse:
    """Update a category if it belongs to the current user."""
    category = await category_service.get_category(
        db,
        category_id,
        current_user.id,
    )
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    updated = await category_service.update_category(db, category, data)
    return CategoryResponse.model_validate(updated)


@router.delete("/{category_id}")
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Delete a category if it belongs to the current user."""
    category = await category_service.get_category(
        db,
        category_id,
        current_user.id,
    )
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    await category_service.delete_category(db, category)
    return {"message": "Category deleted"}

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.schemas import TelegramAuthData, Token, UserCreate, UserResponse
from app.models.user import User
from app.services.auth import create_access_token, get_or_create_user, verify_telegram_auth

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/telegram", response_model=Token)
async def telegram_auth(
    data: TelegramAuthData,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """Authenticate a Telegram user and return a JWT access token."""
    if not verify_telegram_auth(data):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram authentication data",
        )

    user_data = UserCreate(
        telegram_id=data.id,
        username=data.username,
        first_name=data.first_name,
        last_name=data.last_name,
    )
    user = await get_or_create_user(db, user_data)
    access_token = create_access_token(user.id)

    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    """Return the currently authenticated user."""
    return current_user

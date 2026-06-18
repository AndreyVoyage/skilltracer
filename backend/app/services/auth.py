from __future__ import annotations

import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone
from typing import Any, cast

from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.schemas import TelegramAuthData, UserCreate
from app.models.user import User


def create_access_token(user_id: int) -> str:
    """Encode a JWT access token for the given user ID."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    payload = {"sub": str(user_id), "exp": expire}
    return cast(
        str,
        jwt.encode(
            payload,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        ),
    )


def decode_access_token(token: str) -> int | None:
    """Decode a JWT access token and return the user ID, or None if invalid."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return int(user_id)
    except (JWTError, ValueError):
        return None


def _build_data_check_string(data: dict[str, Any]) -> str:
    """Build the Telegram data check string used for HMAC verification."""
    items = sorted(
        (key, str(value))
        for key, value in data.items()
        if value is not None and key != "hash"
    )
    return "\n".join(f"{key}={value}" for key, value in items)


def verify_telegram_auth(data: TelegramAuthData, max_age_seconds: int = 86400) -> bool:
    """Verify Telegram Login Widget payload using HMAC-SHA256."""
    payload = data.model_dump(exclude={"hash"}, exclude_none=True)

    auth_date = payload.get("auth_date")
    if not isinstance(auth_date, int):
        return False

    if time.time() - auth_date > max_age_seconds:
        return False

    data_check_string = _build_data_check_string(payload)
    secret_key = hashlib.sha256(settings.TELEGRAM_BOT_TOKEN.encode()).digest()
    computed_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(computed_hash, data.hash)


async def get_or_create_user(
    db: AsyncSession,
    user_data: UserCreate,
) -> User:
    """Find a user by Telegram ID or create a new one."""
    result = await db.execute(
        select(User).where(User.telegram_id == user_data.telegram_id),
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            telegram_id=user_data.telegram_id,
            username=user_data.username,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    updated = False
    if user_data.username is not None and user.username != user_data.username:
        user.username = user_data.username
        updated = True
    if user_data.first_name is not None and user.first_name != user_data.first_name:
        user.first_name = user_data.first_name
        updated = True
    if user_data.last_name is not None and user.last_name != user_data.last_name:
        user.last_name = user_data.last_name
        updated = True

    if updated:
        await db.commit()
        await db.refresh(user)

    return user

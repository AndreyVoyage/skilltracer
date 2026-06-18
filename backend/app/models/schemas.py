from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    """Payload for creating or resolving a Telegram user."""

    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None


class UserResponse(BaseModel):
    """Public user representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_id: int
    username: str | None
    first_name: str | None
    created_at: datetime


class Token(BaseModel):
    """JWT access token returned after successful authentication."""

    access_token: str
    token_type: str = "bearer"


class TelegramAuthData(BaseModel):
    """Data sent by Telegram Login Widget during OAuth callback."""

    id: int
    auth_date: int
    hash: str
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None


class CategoryCreate(BaseModel):
    """Payload for creating a new category."""

    name: str
    icon: str | None = None
    color: str | None = None


class CategoryUpdate(BaseModel):
    """Payload for updating an existing category."""

    name: str | None = None
    icon: str | None = None
    color: str | None = None


class CategoryResponse(BaseModel):
    """Public category representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    icon: str | None
    color: str | None
    created_at: datetime

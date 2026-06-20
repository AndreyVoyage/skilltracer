from __future__ import annotations

from datetime import date, datetime, time

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
    language: str
    timezone: str
    avatar_url: str | None
    created_at: datetime


class UserSettingsResponse(BaseModel):
    """User settings representation."""

    model_config = ConfigDict(from_attributes=True)

    language: str
    timezone: str
    reminder_enabled: bool
    reminder_time: time | None
    reminder_days: str
    report_template: str


class UserSettingsUpdate(BaseModel):
    """Payload for updating user settings."""

    language: str | None = None
    timezone: str | None = None
    reminder_enabled: bool | None = None
    reminder_time: time | None = None
    reminder_days: str | None = None
    report_template: str | None = None


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
    sort_order: int | None = None
    is_active: bool | None = None


class CategoryResponse(BaseModel):
    """Public category representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    icon: str | None
    color: str | None
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class RatingCreate(BaseModel):
    """Payload for creating a rating."""

    category_id: int
    score: int


class RatingResponse(BaseModel):
    """Public rating representation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
    score: int


class MediaAttachmentResponse(BaseModel):
    """Public media attachment representation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_file_id: str
    local_file_path: str | None
    media_type: str
    file_size: int | None
    mime_type: str | None


class EntryCreate(BaseModel):
    """Payload for creating a new daily entry."""

    entry_date: date
    comment: str | None = None
    ratings: list[RatingCreate]


class EntryUpdate(BaseModel):
    """Payload for updating an existing entry."""

    comment: str | None = None
    ratings: list[RatingCreate] | None = None


class EntryResponse(BaseModel):
    """Public entry representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    entry_date: date
    comment: str | None
    ratings: list[RatingResponse]
    media_attachments: list[MediaAttachmentResponse]
    created_at: datetime
    updated_at: datetime


class WeeklyReportRequest(BaseModel):
    """Payload for requesting a weekly report."""

    week_start: date
    report_type: str = "png"  # png, video
    template: str = "default"


class WeeklyReportResponse(BaseModel):
    """Public weekly report representation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    week_start: date
    week_end: date
    report_type: str
    template: str
    file_url: str | None
    status: str
    created_at: datetime


class StreakResponse(BaseModel):
    """Public streak representation."""

    model_config = ConfigDict(from_attributes=True)

    current_streak: int
    best_streak: int
    last_entry_date: date | None

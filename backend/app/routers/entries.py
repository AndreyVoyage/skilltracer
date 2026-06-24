from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models.media_attachment import MediaAttachment
from app.models.schemas import EntryCreate, EntryResponse, EntryUpdate
from app.models.user import User
from app.services.entry_service import (
    EntryAlreadyExistsError,
    EntryNotFoundError,
    EntryService,
)

router = APIRouter(prefix="/entries", tags=["entries"])


@router.post("", response_model=EntryResponse, status_code=status.HTTP_201_CREATED)
async def create_entry(
    data: EntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EntryResponse:
    """Create a new daily entry with ratings (atomic transaction).

    Raises 409 if entry for this date already exists.
    """
    try:
        entry = await EntryService.create_entry(db, current_user, data)
        return EntryResponse.model_validate(entry)
    except EntryAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )


@router.get("", response_model=list[EntryResponse])
async def list_entries(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[EntryResponse]:
    """List entries for the current user, ordered by date descending."""
    entries = await EntryService.list_entries(db, current_user, limit, offset)
    return [EntryResponse.model_validate(e) for e in entries]


@router.get("/{entry_id}", response_model=EntryResponse)
async def get_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EntryResponse:
    """Get a single entry by ID with ownership check."""
    try:
        entry = await EntryService.get_entry(db, current_user, entry_id)
        return EntryResponse.model_validate(entry)
    except EntryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.get("/by-date/{entry_date}", response_model=EntryResponse)
async def get_entry_by_date(
    entry_date: date,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EntryResponse:
    """Get entry for a specific date (YYYY-MM-DD)."""
    entry = await EntryService.get_entry_by_date(db, current_user, entry_date)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No entry found for {entry_date}",
        )
    return EntryResponse.model_validate(entry)


@router.patch("/{entry_id}", response_model=EntryResponse)
async def update_entry(
    entry_id: int,
    data: EntryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EntryResponse:
    """Update an entry (comment and/or ratings)."""
    try:
        entry = await EntryService.update_entry(db, current_user, entry_id, data)
        return EntryResponse.model_validate(entry)
    except EntryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.delete("/{entry_id}")
async def delete_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Delete an entry and all related ratings/media (cascade)."""
    try:
        await EntryService.delete_entry(db, current_user, entry_id)
        return {"message": "Entry deleted"}
    except EntryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.post("/{entry_id}/media", status_code=status.HTTP_201_CREATED)
async def upload_media(
    entry_id: int,
    file: UploadFile = File(...),
    caption: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, int | str]:
    """Upload a media attachment to an entry.

    Returns media attachment id and file path.
    """
    # Verify entry ownership
    entry = await EntryService.get_entry(db, current_user, entry_id)

    import os
    import uuid

    # Ensure upload directory exists
    upload_dir = os.path.join(settings.MEDIA_UPLOAD_DIR, str(current_user.id), str(entry_id))
    os.makedirs(upload_dir, exist_ok=True)

    # Generate unique filename
    ext = os.path.splitext(file.filename or "")[1] or ".bin"
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(upload_dir, unique_name)

    # Save file
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Determine media type from content type
    media_type = "photo"
    if file.content_type:
        if file.content_type.startswith("image/"):
            media_type = "photo"
        elif file.content_type.startswith("audio/"):
            media_type = "audio"
        elif file.content_type.startswith("video/"):
            media_type = "video"
        else:
            media_type = "document"

    # Create database record
    media = MediaAttachment(
        entry_id=entry_id,
        telegram_file_id=unique_name,  # Using local filename as reference
        local_file_path=file_path,
        media_type=media_type,
        file_size=len(content),
        mime_type=file.content_type,
    )
    db.add(media)
    await db.commit()
    await db.refresh(media)

    return {
        "id": media.id,
        "file_path": file_path,
        "media_type": media_type,
    }

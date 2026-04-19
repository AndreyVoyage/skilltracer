"""add_media_files_to_daily_entries

Revision ID: 9c540ec3bd5c
Revises: 785b0a35c76c
Create Date: 2026-04-18 20:21:54.340379

"""
from typing import Sequence, Union
from datetime import datetime
import uuid

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9c540ec3bd5c'
down_revision: Union[str, None] = '785b0a35c76c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add media_files column
    op.add_column(
        'daily_entries',
        sa.Column(
            'media_files',
            sa.JSON(),
            server_default='[]',
            nullable=False,
            comment='Массив медиа [{id, type, file_id, caption, created_at}]',
        ),
    )

    # 2. Migrate legacy media fields into media_files array
    connection = op.get_bind()
    result = connection.execute(
        sa.text("""
            SELECT id, photo_file_id, voice_file_id, video_file_id
            FROM daily_entries
            WHERE photo_file_id IS NOT NULL
               OR voice_file_id IS NOT NULL
               OR video_file_id IS NOT NULL
        """)
    )

    for row in result:
        entry_id = row[0]
        media_items = []
        created_at = datetime.now().isoformat()

        if row[1]:  # photo_file_id
            media_items.append({
                "id": str(uuid.uuid4()),
                "type": "photo",
                "file_id": row[1],
                "caption": None,
                "created_at": created_at,
            })
        if row[2]:  # voice_file_id
            media_items.append({
                "id": str(uuid.uuid4()),
                "type": "voice",
                "file_id": row[2],
                "caption": None,
                "created_at": created_at,
            })
        if row[3]:  # video_file_id
            media_items.append({
                "id": str(uuid.uuid4()),
                "type": "video",
                "file_id": row[3],
                "caption": None,
                "created_at": created_at,
            })

        if media_items:
            import json
            connection.execute(
                sa.text("UPDATE daily_entries SET media_files = :media WHERE id = :id"),
                {"media": json.dumps(media_items), "id": entry_id},
            )

    # 3. Update video_file_id comment
    op.alter_column(
        'daily_entries',
        'video_file_id',
        existing_type=sa.VARCHAR(length=255),
        comment='Telegram file_id видео сообщения (DEPRECATED: use media_files)',
        existing_comment='Telegram file_id видео сообщения',
        existing_nullable=True,
    )


def downgrade() -> None:
    # Revert video_file_id comment
    op.alter_column(
        'daily_entries',
        'video_file_id',
        existing_type=sa.VARCHAR(length=255),
        comment='Telegram file_id видео сообщения',
        existing_comment='Telegram file_id видео сообщения (DEPRECATED: use media_files)',
        existing_nullable=True,
    )

    # Drop media_files column
    op.drop_column('daily_entries', 'media_files')

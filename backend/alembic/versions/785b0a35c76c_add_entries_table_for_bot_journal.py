"""add entries table for bot journal

Revision ID: 785b0a35c76c
Revises: b6178ccac1e2
Create Date: 2026-04-16 16:23:54.035873

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '785b0a35c76c'
down_revision: Union[str, None] = 'b6178ccac1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'entries',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False, index=True),
        sa.Column('entry_date', sa.Date(), nullable=False, index=True),
        sa.Column('health_score', sa.Integer(), nullable=True),
        sa.Column('sport_score', sa.Integer(), nullable=True),
        sa.Column('study_score', sa.Integer(), nullable=True),
        sa.Column('rest_score', sa.Integer(), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('media_urls', sa.JSON(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'entry_date', name='uix_user_date_entry'),
        sa.CheckConstraint('health_score BETWEEN 1 AND 5', name='ck_health_range'),
        sa.CheckConstraint('sport_score BETWEEN 1 AND 5', name='ck_sport_range'),
        sa.CheckConstraint('study_score BETWEEN 1 AND 5', name='ck_study_range'),
        sa.CheckConstraint('rest_score BETWEEN 1 AND 5', name='ck_rest_range'),
    )


def downgrade() -> None:
    op.drop_table('entries')

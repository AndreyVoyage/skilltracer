from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "64adc25a394e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add columns to users
    op.add_column("users", sa.Column("language", sa.String(length=10), server_default="ru", nullable=False))
    op.add_column("users", sa.Column("timezone", sa.String(length=50), server_default="Europe/Moscow", nullable=False))
    op.add_column("users", sa.Column("avatar_url", sa.String(length=500), nullable=True))

    # Add columns to categories
    op.add_column("categories", sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False))
    op.add_column("categories", sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False))
    op.add_column("categories", sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))

    # Create user_settings
    op.create_table(
        "user_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(length=10), server_default="ru", nullable=False),
        sa.Column("timezone", sa.String(length=50), server_default="Europe/Moscow", nullable=False),
        sa.Column("reminder_enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("reminder_time", sa.Time(), nullable=True),
        sa.Column("reminder_days", sa.String(length=20), server_default="1,2,3,4,5", nullable=False),
        sa.Column("report_template", sa.String(length=50), server_default="default", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    # Create streaks
    op.create_table(
        "streaks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("current_streak", sa.Integer(), server_default="0", nullable=False),
        sa.Column("best_streak", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_entry_date", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
        sa.CheckConstraint("current_streak <= best_streak", name="ck_streak_current_le_best"),
        sa.CheckConstraint("current_streak >= 0", name="ck_streak_current_ge_0"),
    )

    # Create entries
    op.create_table(
        "entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("comment", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "entry_date", name="uq_entry_user_date"),
    )
    op.create_index("ix_entries_user_id_entry_date", "entries", ["user_id", "entry_date"], unique=False)

    # Create ratings
    op.create_table(
        "ratings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["entry_id"], ["entries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entry_id", "category_id", name="uq_rating_entry_category"),
        sa.CheckConstraint("score IN (1, 2, 3, 4, 5)", name="ck_rating_score_range"),
    )

    # Create media_attachments
    op.create_table(
        "media_attachments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("telegram_file_id", sa.String(length=255), nullable=False),
        sa.Column("local_file_path", sa.String(length=500), nullable=True),
        sa.Column("media_type", sa.String(length=20), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["entry_id"], ["entries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create weekly_reports
    op.create_table(
        "weekly_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("week_end", sa.Date(), nullable=False),
        sa.Column("report_type", sa.String(length=20), nullable=False),
        sa.Column("template", sa.String(length=50), server_default="default", nullable=False),
        sa.Column("file_url", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("week_end = week_start + 6", name="ck_weekly_report_week_duration"),
        sa.CheckConstraint("status IN ('pending', 'generating', 'ready', 'failed')", name="ck_weekly_report_status"),
    )


def downgrade() -> None:
    op.drop_table("weekly_reports")
    op.drop_table("media_attachments")
    op.drop_table("ratings")
    op.drop_table("entries")
    op.drop_table("streaks")
    op.drop_table("user_settings")
    op.drop_column("categories", "updated_at")
    op.drop_column("categories", "is_active")
    op.drop_column("categories", "sort_order")
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "timezone")
    op.drop_column("users", "language")

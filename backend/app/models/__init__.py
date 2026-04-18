"""
Skill Tracer SQLAlchemy Models

Все модели для работы с базой данных.
"""

# Base
from app.models.base import Base, TimestampMixin, BigIntPrimaryKeyMixin

# Models
from app.models.user import User
from app.models.tracker import CustomTracker
from app.models.entry import DailyEntry, EntryMetric
from app.models.report import WeekReport, Comment, ReportStatus
from app.models.report_link import ReportLink
from app.models.group import Group, GroupMember, GroupRole
from app.models.telegram_queue import TelegramQueue
from app.models.journal_entry import JournalEntry

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    "BigIntPrimaryKeyMixin",
    # Models
    "User",
    "CustomTracker",
    "DailyEntry",
    "EntryMetric",
    "WeekReport",
    "Comment",
    "Group",
    "GroupMember",
    "TelegramQueue",
    "ReportLink",
    "JournalEntry",
    # Enums
    "ReportStatus",
    "GroupRole",
]

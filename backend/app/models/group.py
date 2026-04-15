"""
Group Models

Group - группа друзей для обмена отчетами.
GroupMember - связь пользователь-группа.
"""

from __future__ import annotations

import secrets
import string
from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    BigInteger,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class GroupRole(str, PyEnum):
    """Роль в группе."""
    
    MEMBER = "member"
    MODERATOR = "moderator"
    OWNER = "owner"


class Group(Base, TimestampMixin):
    """
    Группа друзей для обмена опубликованными WeekReport.
    
    Особенности:
    - У группы есть owner (создатель)
    - invite_code для приглашения (8 символов, uppercase)
    - Максимум 3 человека в группе (логика на уровне приложения)
    """
    
    __tablename__ = "groups"
    
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Уникальный ID группы",
    )
    
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Название группы",
    )
    
    invite_code: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        index=True,
        nullable=False,
        comment="Код приглашения (8 символов)",
    )
    
    owner_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID владельца группы",
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Описание группы",
    )
    
    # Relationships
    owner: Mapped["User"] = relationship(
        "User",
        foreign_keys=[owner_id],
        back_populates="owned_groups",
    )
    
    members: Mapped[List["GroupMember"]] = relationship(
        "GroupMember",
        back_populates="group",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="GroupMember.joined_at",
    )
    
    def __repr__(self) -> str:
        return f"<Group(id={self.id}, name={self.name!r}, invite_code={self.invite_code})>"
    
    @staticmethod
    def generate_invite_code(length: int = 8) -> str:
        """
        Генерирует случайный код приглашения.
        
        Args:
            length: Длина кода (default 8)
            
        Returns:
            Код из uppercase букв и цифр (без похожих символов)
        """
        # Исключаем похожие символы: 0, O, 1, I, L
        alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
        return "".join(secrets.choice(alphabet) for _ in range(length))
    
    def get_member_ids(self) -> List[int]:
        """Возвращает список ID всех членов группы."""
        return [m.user_id for m in self.members]
    
    def get_member_count(self) -> int:
        """Возвращает количество членов группы."""
        return len(self.members)
    
    def is_full(self, max_members: int = 3) -> bool:
        """Проверяет, заполнена ли группа (по умолчанию 3 человека)."""
        return self.get_member_count() >= max_members
    
    def is_member(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь членом группы."""
        return any(m.user_id == user_id for m in self.members)
    
    def get_member(self, user_id: int) -> Optional["GroupMember"]:
        """Возвращает GroupMember по user_id или None."""
        for member in self.members:
            if member.user_id == user_id:
                return member
        return None
    
    def can_user_join(self, user_id: int, max_members: int = 3) -> tuple[bool, str]:
        """
        Проверяет, может ли пользователь присоединиться к группе.
        
        Returns:
            tuple: (может_присоединиться, причина_отказа)
        """
        if self.is_member(user_id):
            return False, "Вы уже состоите в этой группе"
        
        if self.is_full(max_members):
            return False, f"Группа заполнена (максимум {max_members} участников)"
        
        return True, ""
    
    def format_members_list(self) -> str:
        """Форматирует список членов для отображения."""
        lines = []
        for member in self.members:
            role_icon = "👑" if member.role == GroupRole.OWNER else "👤"
            user = member.user
            name = user.get_full_name() if user else f"User{member.user_id}"
            lines.append(f"{role_icon} {name}")
        return "\n".join(lines)


class GroupMember(Base):
    """
    Связь пользователь-группа.
    
    Составной primary key: (group_id, user_id)
    """
    
    __tablename__ = "group_members"
    
    __table_args__ = (
        # Один пользователь = одно членство в группе
        # (но может быть в нескольких группах - это допустимо)
        UniqueConstraint("group_id", "user_id", name="uix_group_user"),
    )
    
    group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("groups.id", ondelete="CASCADE"),
        primary_key=True,
        comment="ID группы",
    )
    
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        comment="ID пользователя",
    )
    
    role: Mapped[GroupRole] = mapped_column(
        String(20),
        default=GroupRole.MEMBER,
        nullable=False,
        comment="member, moderator или owner",
    )
    
    joined_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
        comment="Когда присоединился к группе",
    )
    
    # Relationships
    group: Mapped["Group"] = relationship(
        "Group",
        back_populates="members",
    )
    
    user: Mapped["User"] = relationship(
        "User",
        back_populates="memberships",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<GroupMember(group_id={self.group_id}, user_id={self.user_id}, role={self.role})>"
    
    def is_owner(self) -> bool:
        """Проверяет, является ли член владельцем."""
        return self.role == GroupRole.OWNER
    
    def is_moderator(self) -> bool:
        """Проверяет, является ли член модератором или выше."""
        return self.role in (GroupRole.MODERATOR, GroupRole.OWNER)

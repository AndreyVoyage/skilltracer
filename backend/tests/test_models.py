"""
Skill Tracer Models Tests

Тесты для всех SQLAlchemy моделей.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta, date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select, insert
from sqlalchemy.exc import IntegrityError

from app.models import (
    User,
    CustomTracker,
    DailyEntry,
    EntryMetric,
    WeekReport,
    Comment,
    Group,
    GroupMember,
    ReportStatus,
    GroupRole,
    Base,
)
from app.models.base import Base


# =============================================================================
# Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def db_session(async_engine) -> AsyncSession:
    """Создает тестовую сессию БД."""
    async_session = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Создает тестового пользователя."""
    user = User(
        id=123456789,
        username="testuser",
        first_name="Test",
        last_name="User",
        timezone="Europe/Moscow",
        settings={"reminder_time": "21:00"},
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_tracker(db_session: AsyncSession, test_user: User) -> CustomTracker:
    """Создает тестовый трекер."""
    tracker = CustomTracker(
        user_id=test_user.id,
        name="Спорт",
        icon="💪",
        target_value=5,
        sort_order=1,
    )
    db_session.add(tracker)
    await db_session.commit()
    await db_session.refresh(tracker)
    return tracker


@pytest_asyncio.fixture
async def test_entry(db_session: AsyncSession, test_user: User) -> DailyEntry:
    """Создает тестовую запись дня."""
    entry = DailyEntry(
        user_id=test_user.id,
        entry_date=date.today(),
        mood=4,
        text="Отличный день!",
    )
    db_session.add(entry)
    await db_session.commit()
    await db_session.refresh(entry)
    return entry


@pytest_asyncio.fixture
async def test_group(db_session: AsyncSession, test_user: User) -> Group:
    """Создает тестовую группу."""
    group = Group(
        name="Test Group",
        invite_code=Group.generate_invite_code(),
        owner_id=test_user.id,
        description="Test description",
    )
    db_session.add(group)
    await db_session.commit()
    await db_session.refresh(group)
    
    # Добавляем owner как члена группы
    member = GroupMember(
        group_id=group.id,
        user_id=test_user.id,
        role=GroupRole.OWNER,
    )
    db_session.add(member)
    await db_session.commit()
    
    return group


# =============================================================================
# User Tests
# =============================================================================

@pytest.mark.asyncio
async def test_create_user(db_session: AsyncSession):
    """Тест создания пользователя с заполненным created_at."""
    user = User(
        id=111111,
        username="newuser",
        first_name="New",
        last_name="User",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    assert user.id == 111111
    assert user.username == "newuser"
    assert user.created_at is not None
    assert user.timezone == "Europe/Moscow"  # default
    assert user.settings == {}  # default


@pytest.mark.asyncio
async def test_user_get_full_name(db_session: AsyncSession):
    """Тест метода get_full_name()."""
    user = User(
        id=222222,
        first_name="John",
        last_name="Doe",
    )
    db_session.add(user)
    await db_session.commit()
    
    assert user.get_full_name() == "John Doe"


@pytest.mark.asyncio
async def test_user_get_current_week_dates(db_session: AsyncSession):
    """Тест метода get_current_week_dates()."""
    user = User(id=333333)
    db_session.add(user)
    await db_session.commit()
    
    monday, sunday = user.get_current_week_dates()
    
    assert monday.weekday() == 0  # Monday
    assert sunday.weekday() == 6  # Sunday
    assert (sunday - monday).days == 6


@pytest.mark.asyncio
async def test_user_has_group(db_session: AsyncSession, test_user: User, test_group: Group):
    """Тест метода has_group()."""
    # После фикстуры test_group пользователь должен быть в группе
    await db_session.refresh(test_user, ['memberships'])
    assert test_user.has_group() is True
    
    # Новый пользователь не в группе
    new_user = User(id=444444)
    db_session.add(new_user)
    await db_session.commit()
    await db_session.refresh(new_user, ["memberships"])
    assert new_user.has_group() is False


# =============================================================================
# CustomTracker Tests
# =============================================================================

@pytest.mark.asyncio
async def test_create_tracker(db_session: AsyncSession, test_user: User):
    """Тест создания трекера."""
    tracker = CustomTracker(
        user_id=test_user.id,
        name="Английский",
        icon="📚",
        target_value=7,
    )
    db_session.add(tracker)
    await db_session.commit()
    await db_session.refresh(tracker)
    
    assert tracker.id is not None
    assert tracker.name == "Английский"
    assert tracker.icon == "📚"
    assert tracker.is_active is True


@pytest.mark.asyncio
async def test_tracker_format_display(db_session: AsyncSession, test_user: User):
    """Тест форматирования отображения трекера."""
    tracker = CustomTracker(
        user_id=test_user.id,
        name="Медитация",
        icon="🧘",
    )
    db_session.add(tracker)
    await db_session.commit()
    
    assert tracker.format_display() == "🧘 Медитация"


# =============================================================================
# DailyEntry & EntryMetric Tests
# =============================================================================

@pytest.mark.asyncio
async def test_create_daily_entry(db_session: AsyncSession, test_user: User):
    """Тест создания DailyEntry."""
    entry = DailyEntry(
        user_id=test_user.id,
        entry_date=date.today(),
        mood=5,
        text="Супер день!",
    )
    db_session.add(entry)
    await db_session.commit()
    await db_session.refresh(entry)
    
    assert entry.id is not None
    assert entry.mood == 5
    assert entry.text == "Супер день!"
    assert entry.created_at is not None


@pytest.mark.asyncio
async def test_daily_entry_unique_constraint(db_session: AsyncSession, test_user: User):
    """Тест unique constraint (user_id, entry_date)."""
    today = date.today()
    
    # Первая запись - OK
    entry1 = DailyEntry(
        user_id=test_user.id,
        entry_date=today,
        mood=4,
    )
    db_session.add(entry1)
    await db_session.commit()
    
    # Вторая запись на тот же день - должна быть ошибка
    entry2 = DailyEntry(
        user_id=test_user.id,
        entry_date=today,
        mood=3,
    )
    db_session.add(entry2)
    
    with pytest.raises(IntegrityError):
        await db_session.commit()
    
    await db_session.rollback()


@pytest.mark.asyncio
async def test_create_entry_metric(db_session: AsyncSession, test_entry: DailyEntry, test_tracker: CustomTracker):
    """Тест создания EntryMetric и связи с DailyEntry."""
    metric = EntryMetric(
        entry_id=test_entry.id,
        tracker_id=test_tracker.id,
        value=5,
    )
    db_session.add(metric)
    await db_session.commit()
    await db_session.refresh(metric)
    
    assert metric.id is not None
    assert metric.value == 5
    assert metric.entry_id == test_entry.id
    assert metric.tracker_id == test_tracker.id


@pytest.mark.asyncio
async def test_entry_metrics_relationship(db_session: AsyncSession, test_entry: DailyEntry, test_tracker: CustomTracker):
    """Тест отношения entry.metrics."""
    metric = EntryMetric(
        entry_id=test_entry.id,
        tracker_id=test_tracker.id,
        value=4,
    )
    db_session.add(metric)
    await db_session.commit()
    
    # Перезагружаем entry с метриками
    entry = await db_session.get(DailyEntry, test_entry.id)
    await db_session.refresh(entry, ["metrics"])
    for m in entry.metrics:
        await db_session.refresh(m, ["tracker"])

    assert len(entry.metrics) == 1
    assert entry.metrics[0].value == 4
    assert entry.metrics[0].tracker.name == "Спорт"


@pytest.mark.asyncio
async def test_entry_metric_unique_constraint(db_session: AsyncSession, test_entry: DailyEntry, test_tracker: CustomTracker):
    """Тест unique constraint (entry_id, tracker_id)."""
    metric1 = EntryMetric(
        entry_id=test_entry.id,
        tracker_id=test_tracker.id,
        value=3,
    )
    db_session.add(metric1)
    await db_session.commit()
    
    # Второй метрик для того же entry и tracker - ошибка
    metric2 = EntryMetric(
        entry_id=test_entry.id,
        tracker_id=test_tracker.id,
        value=4,
    )
    db_session.add(metric2)
    
    with pytest.raises(IntegrityError):
        await db_session.commit()
    
    await db_session.rollback()


@pytest.mark.asyncio
async def test_daily_entry_set_metric_value(db_session: AsyncSession, test_entry: DailyEntry, test_tracker: CustomTracker):
    """Тест метода set_metric_value()."""
    # Устанавливаем значение
    metric = test_entry.set_metric_value(test_tracker, 5)
    db_session.add(metric)
    await db_session.commit()
    
    assert test_entry.get_metric_value(test_tracker.id) == 5
    
    # Обновляем значение
    metric2 = test_entry.set_metric_value(test_tracker, 3)
    await db_session.commit()
    
    # Должно быть то же количество метрик, но другое значение
    assert test_entry.get_metric_value(test_tracker.id) == 3


@pytest.mark.asyncio
async def test_mood_check_constraint(db_session: AsyncSession, test_user: User):
    """Тест CHECK constraint для mood (1-5)."""
    # mood = 6 (вне диапазона) - должна быть ошибка
    entry = DailyEntry(
        user_id=test_user.id,
        entry_date=date.today(),
        mood=6,
    )
    db_session.add(entry)
    
    with pytest.raises(IntegrityError):
        await db_session.commit()
    
    await db_session.rollback()


# =============================================================================
# WeekReport Tests
# =============================================================================

@pytest.mark.asyncio
async def test_create_week_report(db_session: AsyncSession, test_user: User):
    """Тест создания WeekReport."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    
    report = WeekReport(
        user_id=test_user.id,
        week_start_date=monday,
        week_end_date=sunday,
        status=ReportStatus.DRAFT,
    )
    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)
    
    assert report.id is not None
    assert report.status == ReportStatus.DRAFT
    assert report.published_at is None
    assert report.avg_mood is None


@pytest.mark.asyncio
async def test_week_report_publish(db_session: AsyncSession, test_user: User):
    """Тест метода publish()."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    
    report = WeekReport(
        user_id=test_user.id,
        week_start_date=monday,
        week_end_date=sunday,
    )
    db_session.add(report)
    await db_session.commit()
    
    # Публикуем
    report.publish()
    await db_session.commit()
    await db_session.refresh(report)
    
    assert report.status == ReportStatus.PUBLISHED
    assert report.published_at is not None


@pytest.mark.asyncio
async def test_week_report_calculate_summary(db_session: AsyncSession, test_user: User, test_tracker: CustomTracker):
    """Тест метода calculate_summary()."""
    # Создаем записи за неделю
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    
    entries = []
    for i in range(3):  # 3 дня с данными
        entry = DailyEntry(
            user_id=test_user.id,
            entry_date=monday + timedelta(days=i),
            mood=4,
        )
        db_session.add(entry)
        await db_session.flush()
        
        metric = EntryMetric(
            entry_id=entry.id,
            tracker_id=test_tracker.id,
            value=i + 2,  # 2, 3, 4
        )
        db_session.add(metric)
        entries.append(entry)
    
    await db_session.commit()
    
    # Создаем отчет
    sunday = monday + timedelta(days=6)
    report = WeekReport(
        user_id=test_user.id,
        week_start_date=monday,
        week_end_date=sunday,
    )
    db_session.add(report)
    await db_session.commit()
    
    # Перезагружаем entries с метриками
    for entry in entries:
        await db_session.refresh(entry)
    
    # Считаем summary
    report.calculate_summary(entries)
    await db_session.commit()
    
    assert report.filled_days == 3
    assert report.avg_mood == 4.0
    assert "Спорт" in report.metrics_summary
    assert report.metrics_summary["Спорт"] == 3.0  # (2+3+4)/3


@pytest.mark.asyncio
async def test_week_report_visibility(db_session: AsyncSession, test_user: User):
    """Тест логики видимости is_visible_to()."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    
    # Создаем отчет-черновик
    draft_report = WeekReport(
        user_id=test_user.id,
        week_start_date=monday,
        week_end_date=sunday,
        status=ReportStatus.DRAFT,
    )
    db_session.add(draft_report)
    
    # Создаем опубликованный отчет
    published_report = WeekReport(
        user_id=test_user.id,
        week_start_date=monday - timedelta(days=7),
        week_end_date=sunday - timedelta(days=7),
        status=ReportStatus.PUBLISHED,
    )
    db_session.add(published_report)
    await db_session.commit()
    
    # Чужой пользователь
    other_user_id = 999999
    group_members = [test_user.id, other_user_id]
    
    # Свой черновик виден
    assert draft_report.is_visible_to(test_user.id, group_members) is True
    
    # Чужой черновик не виден
    assert draft_report.is_visible_to(other_user_id, group_members) is False
    
    # Опубликованный виден членам группы
    assert published_report.is_visible_to(other_user_id, group_members) is True
    
    # Опубликованный не виден не-членам
    assert published_report.is_visible_to(888888, []) is False


# =============================================================================
# Group Tests
# =============================================================================

@pytest.mark.asyncio
async def test_create_group(db_session: AsyncSession, test_user: User):
    """Тест создания группы."""
    group = Group(
        name="Fitness Group",
        invite_code=Group.generate_invite_code(),
        owner_id=test_user.id,
    )
    db_session.add(group)
    await db_session.commit()
    await db_session.refresh(group)
    
    assert group.id is not None
    assert len(group.invite_code) == 8
    assert group.invite_code.isupper()


@pytest.mark.asyncio
async def test_group_generate_invite_code():
    """Тест генерации invite_code."""
    code = Group.generate_invite_code()
    assert len(code) == 8
    assert code.isalnum()
    assert code.isupper()
    
    # Другой код
    code2 = Group.generate_invite_code()
    assert code != code2


@pytest.mark.asyncio
async def test_group_add_members(db_session: AsyncSession, test_group: Group, test_user: User):
    """Тест добавления членов в группу."""
    # Создаем еще 2 пользователей
    user2 = User(id=222222, username="user2")
    user3 = User(id=333333, username="user3")
    db_session.add_all([user2, user3])
    await db_session.commit()
    
    # Добавляем в группу
    member2 = GroupMember(
        group_id=test_group.id,
        user_id=user2.id,
        role=GroupRole.MEMBER,
    )
    member3 = GroupMember(
        group_id=test_group.id,
        user_id=user3.id,
        role=GroupRole.MEMBER,
    )
    db_session.add_all([member2, member3])
    await db_session.commit()
    
    # Перезагружаем группу
    group = await db_session.get(Group, test_group.id)
    await db_session.refresh(group, ["members"])

    assert group.get_member_count() == 3
    assert user2.id in group.get_member_ids()
    assert user3.id in group.get_member_ids()


@pytest.mark.asyncio
async def test_group_is_full(db_session: AsyncSession, test_group: Group):
    """Тест проверки заполненности группы."""
    # Добавляем 2 членов (всего 3 с owner)
    for i in range(2):
        user = User(id=100000 + i, username=f"user{i}")
        db_session.add(user)
        await db_session.flush()
        
        member = GroupMember(
            group_id=test_group.id,
            user_id=user.id,
            role=GroupRole.MEMBER,
        )
        db_session.add(member)
    
    await db_session.commit()
    
    # Перезагружаем
    group = await db_session.get(Group, test_group.id)
    await db_session.refresh(group, ["members"])

    assert group.get_member_count() == 3
    assert group.is_full(max_members=3) is True
    assert group.is_full(max_members=5) is False


@pytest.mark.asyncio
async def test_group_can_user_join(db_session: AsyncSession, test_group: Group, test_user: User):
    """Тест проверки возможности присоединиться."""
    await db_session.refresh(test_group, ["members"])
    # Существующий член не может
    can_join, reason = test_group.can_user_join(test_user.id, max_members=3)
    assert can_join is False
    assert "уже состоите" in reason
    
    # Новый пользователь может
    can_join, reason = test_group.can_user_join(999999, max_members=3)
    assert can_join is True
    assert reason == ""


@pytest.mark.asyncio
async def test_group_member_is_owner(db_session: AsyncSession, test_group: Group, test_user: User):
    """Тест проверки роли в группе."""
    result = await db_session.execute(
        select(GroupMember).where(
            GroupMember.group_id == test_group.id,
            GroupMember.user_id == test_user.id,
        )
    )
    member = result.scalar_one()
    
    assert member.is_owner() is True
    assert member.is_moderator() is True


# =============================================================================
# Comment Tests
# =============================================================================

@pytest.mark.asyncio
async def test_create_comment(db_session: AsyncSession, test_user: User):
    """Тест создания комментария."""
    # Создаем опубликованный отчет
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    
    report = WeekReport(
        user_id=test_user.id,
        week_start_date=monday,
        week_end_date=sunday,
        status=ReportStatus.PUBLISHED,
    )
    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)
    
    # Создаем комментарий
    author = User(id=888888, username="commenter")
    db_session.add(author)
    await db_session.commit()
    
    comment = Comment(
        week_report_id=report.id,
        author_id=author.id,
        text="Отличная неделя! Молодец!",
    )
    db_session.add(comment)
    await db_session.commit()
    await db_session.refresh(comment)
    
    assert comment.id is not None
    assert comment.text == "Отличная неделя! Молодец!"
    assert comment.author_id == 888888


# =============================================================================
# Privacy Tests
# =============================================================================

@pytest.mark.asyncio
async def test_draft_report_not_visible_to_group(db_session: AsyncSession, test_user: User):
    """
    Тест ключевой логики приватности:
    WeekReport со status='draft' не должен быть виден группе.
    """
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    
    # Создаем черновик
    draft = WeekReport(
        user_id=test_user.id,
        week_start_date=monday,
        week_end_date=sunday,
        status=ReportStatus.DRAFT,
        highlights="Мои приватные мысли",
    )
    db_session.add(draft)
    await db_session.commit()
    
    # Создаем другого пользователя
    other_user = User(id=777777, username="other")
    db_session.add(other_user)
    await db_session.commit()
    
    # Проверяем - черновик не виден другому пользователю
    assert draft.is_visible_to(other_user.id, [test_user.id, other_user.id]) is False
    
    # Но виден владельцу
    assert draft.is_visible_to(test_user.id, [test_user.id, other_user.id]) is True

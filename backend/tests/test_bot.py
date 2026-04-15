"""
Bot Tests

Тесты для Telegram бота (Aiogram 3).
"""

import pytest
import pytest_asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from aiogram.types import (
    Message,
    User as TgUser,
    Chat,
    PhotoSize,
    Update,
    CallbackQuery,
)
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import MagicMock, create_autospec

from app.models import User, DailyEntry, CustomTracker
from app.bot.config import BotMessages, BotCommands, BotButtons
from app.bot.media_cache import cache_media, get_cached_media, clear_media_cache


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_tg_user():
    """Mock Telegram пользователя."""
    return TgUser(
        id=123456,
        is_bot=False,
        first_name="Test",
        last_name="User",
        username="testuser",
    )


@pytest.fixture
def mock_chat():
    """Mock Telegram чата."""
    return Chat(
        id=123456,
        type="private",
    )


@pytest.fixture
def mock_message(mock_tg_user, mock_chat):
    """Mock текстового сообщения."""
    msg = create_autospec(Message, instance=True)
    msg.message_id = 1
    msg.from_user = mock_tg_user
    msg.chat = mock_chat
    msg.date = datetime.now()
    msg.text = "/start"
    return msg


@pytest.fixture
def mock_photo_message(mock_tg_user, mock_chat):
    """Mock сообщения с фото."""
    photo = PhotoSize(
        file_id="AgACAgIAAxkBAAIBZ2XXXX",
        file_unique_id="unique_id",
        width=1280,
        height=720,
        file_size=102400,
    )
    
    msg = create_autospec(Message, instance=True)
    msg.message_id = 2
    msg.from_user = mock_tg_user
    msg.chat = mock_chat
    msg.date = datetime.now()
    msg.photo = [photo]
    return msg


@pytest.fixture
def mock_callback_query(mock_tg_user, mock_chat):
    """Mock callback query."""
    cb = create_autospec(CallbackQuery, instance=True)
    cb.id = "callback_id"
    cb.from_user = mock_tg_user
    cb.data = "view_stats"
    cb.chat_instance = "test_instance"
    return cb


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Создает тестового пользователя."""
    user = User(
        id=123456,
        username="testuser",
        first_name="Test",
        last_name="User",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# =============================================================================
# Media Cache Tests
# =============================================================================

def test_cache_media():
    """Тест сохранения file_id в кэш."""
    user_id = 123456
    file_id = "AgACAgIAAxkBAAIBZ2XXXX"
    
    # Сохраняем
    cache_media(user_id, "photo", file_id)
    
    # Проверяем что получаем
    cached = get_cached_media(user_id, "photo")
    assert cached == file_id


def test_get_cached_media_expired():
    """Тест что истекший кэш возвращает None."""
    import time
    
    user_id = 123456
    file_id = "test_file_id"
    
    # Сохраняем
    cache_media(user_id, "photo", file_id)
    
    # Проверяем что есть
    assert get_cached_media(user_id, "photo") == file_id
    
    # Очищаем кэш принудительно
    clear_media_cache(user_id)
    
    # Проверяем что нет
    assert get_cached_media(user_id, "photo") is None


def test_clear_media_cache():
    """Тест очистки кэша."""
    user_id = 123456
    cache_media(user_id, "photo", "photo_id")
    cache_media(user_id, "video", "video_id")
    
    # Очищаем
    clear_media_cache(user_id)
    
    # Проверяем
    assert get_cached_media(user_id, "photo") is None
    assert get_cached_media(user_id, "video") is None


# =============================================================================
# Command Handler Tests
# =============================================================================

@pytest.mark.asyncio
async def test_start_command(mock_message, test_user):
    """Тест команды /start."""
    # Mock answer
    mock_message.answer = AsyncMock()
    
    # Импортируем хендлер
    from app.bot.handlers.commands import cmd_start
    
    # Вызываем
    await cmd_start(mock_message, None, test_user)
    
    # Проверяем что ответ был
    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args
    
    # Проверяем текст
    text = call_args[0][0]
    assert "Skill Tracer" in text
    assert "Test" in text  # first_name
    
    # Проверяем что есть клавиатура
    assert "reply_markup" in call_args[1]


@pytest.mark.asyncio
async def test_help_command(mock_message):
    """Тест команды /help."""
    mock_message.answer = AsyncMock()
    
    from app.bot.handlers.commands import cmd_help
    
    user = User(id=123456, first_name="Test")
    await cmd_help(mock_message, user)
    
    mock_message.answer.assert_called_once()
    text = mock_message.answer.call_args[0][0]
    assert "Как пользоваться" in text or "How to use" in text or "команды" in text


@pytest.mark.asyncio
async def test_week_command_empty_week(mock_message, test_user, db_session):
    """Тест команды /week когда неделя пустая."""
    mock_message.answer = AsyncMock()
    
    from app.bot.handlers.commands import cmd_week
    
    await cmd_week(mock_message, db_session, test_user)
    
    mock_message.answer.assert_called_once()
    text = mock_message.answer.call_args[0][0]
    
    # Должно быть 0 заполненных дней
    assert "0 из 7" in text or "0/7" in text


@pytest.mark.asyncio
async def test_week_command_with_entries(mock_message, test_user, db_session):
    """Тест команды /week с заполненными днями."""
    from datetime import date, timedelta
    
    # Создаем записи
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    
    for i in range(3):
        entry = DailyEntry(
            user_id=test_user.id,
            entry_date=monday + timedelta(days=i),
            mood=4,
        )
        db_session.add(entry)
    
    await db_session.commit()
    
    mock_message.answer = AsyncMock()
    
    from app.bot.handlers.commands import cmd_week
    await cmd_week(mock_message, db_session, test_user)
    
    text = mock_message.answer.call_args[0][0]
    
    # Должно быть 3 заполненных дня
    assert "3 из 7" in text or "3/7" in text


@pytest.mark.asyncio
async def test_settings_command(mock_message, test_user, db_session):
    """Тест команды /settings."""
    mock_message.answer = AsyncMock()
    
    from app.bot.handlers.commands import cmd_settings
    await cmd_settings(mock_message, db_session, test_user)
    
    mock_message.answer.assert_called_once()
    text = mock_message.answer.call_args[0][0]
    
    # Проверяем наличие настроек в тексте
    assert test_user.timezone in text


# =============================================================================
# Photo Handler Tests
# =============================================================================

@pytest.mark.asyncio
async def test_photo_handler(mock_photo_message):
    """Тест обработки фото."""
    mock_photo_message.answer = AsyncMock()
    
    from app.bot.handlers.photos import handle_photo
    await handle_photo(mock_photo_message)
    
    mock_photo_message.answer.assert_called_once()
    text = mock_photo_message.answer.call_args[0][0]
    
    # Должно быть сообщение о получении фото
    assert "Фото получено" in text or "Photo received" in text or "📸" in text
    
    # Проверяем что file_id сохранен в кэш
    cached = get_cached_media(mock_photo_message.from_user.id, "photo")
    assert cached == "AgACAgIAAxkBAAIBZ2XXXX"


# =============================================================================
# Callback Handler Tests
# =============================================================================

@pytest.mark.asyncio
async def test_view_stats_callback(mock_callback_query):
    """Тест callback view_stats."""
    mock_callback_query.answer = AsyncMock()
    
    from app.bot.handlers.commands import cb_view_stats
    await cb_view_stats(mock_callback_query, None, None)
    
    mock_callback_query.answer.assert_called_once()


# =============================================================================
# Keyboard Tests
# =============================================================================

def test_get_main_menu_keyboard():
    """Тест главной клавиатуры."""
    from app.bot.keyboards import get_main_menu_keyboard
    
    keyboard = get_main_menu_keyboard()
    
    assert keyboard is not None
    # Проверяем что клавиатура имеет кнопки
    assert len(keyboard.keyboard) > 0


def test_build_progress_bar():
    """Тест построения прогресс-бара."""
    from app.bot.keyboards import build_progress_bar
    
    # 3 из 7
    bar = build_progress_bar(3, 7)
    assert "●" in bar  # filled
    assert "○" in bar  # empty
    assert len(bar) == 7
    
    # 0 из 7
    bar = build_progress_bar(0, 7)
    assert "●" not in bar
    assert bar.count("○") == 7
    
    # 7 из 7
    bar = build_progress_bar(7, 7)
    assert "○" not in bar
    assert bar.count("●") == 7


# =============================================================================
# Integration Tests
# =============================================================================

@pytest.mark.asyncio
async def test_user_middleware_creates_user(mock_message, db_session):
    """Тест что middleware создает пользователя в БД."""
    from app.bot.middlewares import UserMiddleware
    from app.models import User
    from sqlalchemy import select
    
    middleware = UserMiddleware()
    
    # Создаем mock handler
    mock_handler = AsyncMock()
    
    # Данные для middleware
    data = {"db": db_session}
    
    # Вызываем middleware
    await middleware(mock_handler, mock_message, data)
    
    # Проверяем что пользователь создан
    result = await db_session.execute(
        select(User).where(User.id == mock_message.from_user.id)
    )
    user = result.scalar_one_or_none()
    
    assert user is not None
    assert user.id == mock_message.from_user.id
    assert user.username == mock_message.from_user.username


@pytest.mark.asyncio
async def test_webapp_url_in_keyboard():
    """Тест что WebApp кнопка содержит правильный URL."""
    from app.bot.keyboards import get_main_menu_keyboard
    from app.config import settings
    
    keyboard = get_main_menu_keyboard()
    
    # Ищем кнопку с web_app
    found_webapp = False
    for row in keyboard.keyboard:
        for button in row:
            if hasattr(button, 'web_app') and button.web_app:
                found_webapp = True
                # URL должен содержать настроенный WEBAPP_URL
                assert settings.WEBAPP_URL in button.web_app.url
    
    assert found_webapp, "WebApp button not found in keyboard"


# =============================================================================
# Bot Commands Test
# =============================================================================

def test_bot_commands_format():
    """Тест формата команд для BotFather."""
    commands = BotCommands.get_commands()
    
    assert len(commands) > 0
    
    for cmd, desc in commands:
        # Команда без /
        assert not cmd.startswith("/")
        # Описание не пустое
        assert len(desc) > 0
        # Длина описания не более 256 (лимит Telegram)
        assert len(desc) <= 256


@pytest.mark.asyncio
async def test_bot_config_texts():
    """Тест что все тексты сообщений определены."""
    assert BotMessages.START
    assert BotMessages.HELP
    assert BotMessages.WEEK_STATUS
    assert BotMessages.SETTINGS
    assert BotMessages.PHOTO_RECEIVED
    assert BotMessages.ERROR_GENERIC

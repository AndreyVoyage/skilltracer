"""
Bot Keyboards

Все клавиатуры для бота: Reply и Inline.
"""

from datetime import date, timedelta

from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

from app.config import settings
from app.bot.config import BotButtons, BotConfig


# =============================================================================
# Reply Keyboards (основные меню)
# =============================================================================

def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Главное меню бота с WebApp кнопкой.
    
    Returns:
        ReplyKeyboardMarkup с кнопкой открытия приложения
    """
    builder = ReplyKeyboardBuilder()
    
    # Первый ряд
    builder.row(
        KeyboardButton(text=BotButtons.MY_WEEK),
        KeyboardButton(text=BotButtons.SETTINGS),
    )
    
    # Второй ряд
    builder.row(
        KeyboardButton(
            text=BotButtons.OPEN_APP,
            web_app=WebAppInfo(url=settings.WEBAPP_URL),
        ),
        KeyboardButton(text=BotButtons.HELP),
    )
    
    return builder.as_markup(
        resize_keyboard=True,
        one_time_keyboard=False,
        is_persistent=True,
    )


def get_back_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с одной кнопкой 'Назад'."""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=BotButtons.BACK))
    
    return builder.as_markup(
        resize_keyboard=True,
        one_time_keyboard=True,
    )


DAYS_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MONTHS_SHORT = {
    1: "янв", 2: "фев", 3: "мар", 4: "апр", 5: "май", 6: "июн",
    7: "июл", 8: "авг", 9: "сен", 10: "окт", 11: "ноя", 12: "дек",
}


def generate_day_labels() -> dict[str, date]:
    """Генерирует метки дней для Reply-клавиатуры."""
    today = date.today()
    labels = {}
    for i in range(9, -1, -1):
        d = today - timedelta(days=i)
        label = f"{DAYS_SHORT[d.weekday()]}, {d.day} {MONTHS_SHORT[d.month]}"
        labels[label] = d
    return labels


def get_days_keyboard(filled_dates: set | None = None) -> ReplyKeyboardMarkup:
    """
    Reply-клавиатура с 10 последними датами + Назад.
    Формат: 'Пн, 14 апр' или '✅ Пн, 14 апр' если заполнено.
    """
    if filled_dates is None:
        filled_dates = set()
    
    builder = ReplyKeyboardBuilder()
    
    for label, d in generate_day_labels().items():
        display = f"✅ {label}" if d in filled_dates else label
        builder.row(KeyboardButton(text=display))
    
    builder.row(KeyboardButton(text=BotButtons.BACK_TO_MENU))
    
    return builder.as_markup(
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def get_help_back_keyboard() -> ReplyKeyboardMarkup:
    """Reply-клавиатура для справки с кнопкой назад."""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=BotButtons.BACK_TO_MENU))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


# =============================================================================
# Inline Keyboards (кнопки под сообщениями)
# =============================================================================

def get_entry_rating_keyboard(scores: dict | None = None) -> InlineKeyboardMarkup:
    """
    Inline-клавиатура для оценки 4 категорий.
    
    Args:
        scores: dict вида {'health': 4, 'sport': 3, ...}
    """
    if scores is None:
        scores = {}
    
    builder = InlineKeyboardBuilder()
    categories = [
        ("Здоровье", "health"),
        ("Спорт", "sport"),
        ("Учёба", "study"),
        ("Отдых", "rest"),
    ]
    
    for name, key in categories:
        row = []
        current = scores.get(key)
        for val in range(1, 6):
            text_btn = f"{val}" if current != val else f"[{val}]"
            row.append(
                InlineKeyboardButton(
                    text=text_btn,
                    callback_data=f"rate_{key}_{val}",
                )
            )
        # Первая кнопка — название категории (без callback, просто текст)
        row.insert(0, InlineKeyboardButton(text=name, callback_data="noop"))
        builder.row(*row)
    
    builder.row(
        InlineKeyboardButton(text="📝 Текст", callback_data="entry:text"),
        InlineKeyboardButton(text="📎 Медиа", callback_data="entry:media"),
    )
    builder.row(
        InlineKeyboardButton(text=BotButtons.SAVE_ENTRY, callback_data="save_entry"),
    )
    builder.row(
        InlineKeyboardButton(text=BotButtons.BACK_TO_DAYS, callback_data="back_to_days"),
    )
    
    return builder.as_markup()


def get_week_status_keyboard(filled_days: int = 0) -> InlineKeyboardMarkup:
    """
    Клавиатура статуса недели.
    
    Args:
        filled_days: Сколько дней заполнено
        
    Returns:
        InlineKeyboardMarkup с кнопками действий
    """
    builder = InlineKeyboardBuilder()
    
    # Кнопка заполнить сегодня (WebApp)
    builder.row(
        InlineKeyboardButton(
            text=BotButtons.FILL_TODAY,
            web_app=WebAppInfo(url=f"{settings.WEBAPP_URL}?date=today"),
        )
    )
    
    # Дополнительные кнопки
    builder.row(
        InlineKeyboardButton(
            text=BotButtons.VIEW_STATS,
            callback_data="view_stats",
        ),
    )
    
    return builder.as_markup()


def get_back_to_scores_keyboard(scores: dict | None = None) -> InlineKeyboardMarkup:
    """Inline-клавиатура с кнопкой возврата к оценкам."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад к оценкам", callback_data="entry:back_to_scores"),
    )
    return builder.as_markup()


def get_settings_inline_keyboard() -> InlineKeyboardMarkup:
    """Inline-клавиатура настроек бота."""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="👤 Изменить имя", callback_data="settings:change_name"),
        InlineKeyboardButton(text="📧 Изменить email", callback_data="settings:change_email"),
    )
    builder.row(
        InlineKeyboardButton(text="🔔 Уведомления: Вкл/Выкл", callback_data="settings:toggle_notifications"),
    )
    builder.row(
        InlineKeyboardButton(text=BotButtons.BACK_TO_MENU, callback_data="settings:back_to_menu"),
    )
    
    return builder.as_markup()


def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура настроек (legacy)."""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=BotButtons.CHANGE_TIMEZONE,
            callback_data="settings:timezone",
        ),
    )
    
    builder.row(
        InlineKeyboardButton(
            text=BotButtons.CHANGE_REMINDER,
            callback_data="settings:reminder",
        ),
    )
    
    builder.row(
        InlineKeyboardButton(
            text=BotButtons.MANAGE_TRACKERS,
            callback_data="settings:trackers",
        ),
    )
    
    return builder.as_markup()


def get_report_actions_keyboard(report_id: int, is_owner: bool = False) -> InlineKeyboardMarkup:
    """
    Клавиатура действий с отчетом.
    
    Args:
        report_id: ID отчета
        is_owner: Владелец ли смотрит отчет
        
    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()
    
    if is_owner:
        # Для владельца - кнопка публикации (если draft)
        builder.row(
            InlineKeyboardButton(
                text=BotButtons.PUBLISH_REPORT,
                callback_data=f"report:publish:{report_id}",
            ),
        )
    else:
        # Для других - кнопка комментария
        builder.row(
            InlineKeyboardButton(
                text=BotButtons.ADD_COMMENT,
                callback_data=f"report:comment:{report_id}",
            ),
        )
    
    return builder.as_markup()


def get_confirmation_keyboard(action: str, item_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура подтверждения действия.
    
    Args:
        action: Действие (delete, publish, etc)
        item_id: ID элемента
        
    Returns:
        InlineKeyboardMarkup с Да/Нет
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="✅ Да",
            callback_data=f"confirm:{action}:{item_id}:yes",
        ),
        InlineKeyboardButton(
            text="❌ Нет",
            callback_data=f"confirm:{action}:{item_id}:no",
        ),
    )
    
    return builder.as_markup()


# =============================================================================
# Helper Functions
# =============================================================================

def build_progress_bar(filled: int, total: int = BotConfig.DAYS_IN_WEEK) -> str:
    """
    Строит текстовый прогресс-бар.
    
    Args:
        filled: Сколько заполнено
        total: Всего (по умолчанию 7)
        
    Returns:
        Строка с прогресс-баром
    """
    filled_symbols = BotConfig.PROGRESS_FILLED * filled
    empty_symbols = BotConfig.PROGRESS_EMPTY * (total - filled)
    return filled_symbols + empty_symbols


def get_timezones_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора часового пояса."""
    builder = InlineKeyboardBuilder()
    
    timezones = [
        ("Москва (UTC+3)", "Europe/Moscow"),
        ("Киев (UTC+2)", "Europe/Kiev"),
        ("Лондон (UTC+0/+1)", "Europe/London"),
        ("Нью-Йорк (UTC-5/-4)", "America/New_York"),
        ("Лос-Анджелес (UTC-8/-7)", "America/Los_Angeles"),
        ("Токио (UTC+9)", "Asia/Tokyo"),
    ]
    
    for name, tz in timezones:
        builder.row(
            InlineKeyboardButton(
                text=name,
                callback_data=f"timezone:{tz}",
            ),
        )
    
    return builder.as_markup()


def get_reminder_times_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора времени напоминания."""
    builder = InlineKeyboardBuilder()
    
    times = [
        "19:00", "20:00", "21:00", "22:00",
        "Отключить", "Настроить вручную",
    ]
    
    buttons = [
        InlineKeyboardButton(text=t, callback_data=f"reminder:{t}")
        for t in times
    ]
    
    # По 3 кнопки в ряд
    for i in range(0, len(buttons), 3):
        row_buttons = buttons[i:i+3]
        builder.row(*row_buttons)
    
    return builder.as_markup()

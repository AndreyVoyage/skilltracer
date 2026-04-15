"""
Bot Configuration & Texts

Константы и тексты для бота.
Все тексты вынесены сюда для легкого редактирования.
"""

from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class BotCommands:
    """Команды бота для BotFather."""
    
    START = "start"
    HELP = "help"
    WEEK = "week"
    SETTINGS = "settings"
    
    @classmethod
    def get_commands(cls) -> List[Tuple[str, str]]:
        """Возвращает список команд для BotFather."""
        return [
            (cls.START, "Начать работу с ботом"),
            (cls.HELP, "Помощь и инструкция"),
            (cls.WEEK, "Статус текущей недели"),
            (cls.SETTINGS, "Настройки"),
        ]


@dataclass(frozen=True)
class BotMessages:
    """Тексты сообщений бота."""
    
    # /start
    START = """Привет, {first_name}! 👋

Добро пожаловать в <b>Skill Tracer</b> — твой личный дневник прогресса.

📊 <b>Отслеживай:</b>
• Настроение и эмоции
• Спорт, языки, здоровье
• Фото дня

👥 <b>Делись успехами с друзьями</b> (группа до 3 человек)

Нажми кнопку ниже, чтобы открыть приложение! 🚀"""
    
    # /help
    HELP = """📖 <b>Как пользоваться Skill Tracer</b>

<b>Ежедневно:</b>
• Открывай приложение и отмечай свой прогресс
• Добавляй фото дня (отправь фото боту)
• Оцени настроение от 1 до 5

<b>Раз в неделю:</b>
• Просматривай свой прогресс
• Публикуй отчет для друзей (черновик → публикация)
• Смотри отчеты друзей и комментируй

<b>Команды:</b>
/week — сколько дней заполнено
/settings — изменить настройки

<b>Совет:</b> Включи уведомления, чтобы не забывать заполнять дневник!"""
    
    # /week
    WEEK_STATUS = """📅 <b>Статус недели</b>

Заполнено дней: <b>{filled}/{total}</b> ({percent}%)

{progress_bar}

{status_text}"""
    
    WEEK_EMPTY = "Пока нет записей на этой неделе. Начни сегодня! 💪"
    WEEK_GOOD = "Отличный прогресс! Продолжай в том же духе! 🌟"
    WEEK_EXCELLENT = "Потрясающе! Неделя полностью заполнена! 🎉"
    
    # /settings
    SETTINGS = """⚙️ <b>Настройки</b>

🌍 <b>Часовой пояс:</b> {timezone}
🔔 <b>Напоминания:</b> {reminder_time}
📊 <b>Трекеры:</b> {trackers_count}

Выбери, что хочешь изменить:"""
    
    # Фото получено
    PHOTO_RECEIVED = """📸 <b>Фото получено!</b>

Открой Skill Tracer, чтобы добавить его к сегодняшней записи.

<i>Фото хранится 10 минут, успей!</i>"""
    
    # Видео получено
    VIDEO_RECEIVED = """🎥 <b>Видео получено!</b>

Открой Skill Tracer, чтобы добавить его к сегодняшней записи."""
    
    # Голосовое получено
    VOICE_RECEIVED = """🎤 <b>Голосовое сообщение получено!</b>

В будущем здесь будет расшифровка текста.
Пока что можно прослушать в приложении."""
    
    # Ошибки
    ERROR_GENERIC = "😔 Произошла ошибка. Попробуйте позже или напишите /start"
    ERROR_DATABASE = "⚠️ Не удалось сохранить данные. Попробуйте еще раз."
    
    # Уведомления
    REMINDER_DAILY = "🌙 Как прошел день? Не забудь отметить прогресс в Skill Tracer!"
    REMINDER_WEEKLY = "📊 Подведи итоги недели! Опубликуй отчет для друзей."
    PUBLISHED_NOTIFICATION = "🎉 <b>{user_name}</b> опубликовал отчет за неделю!\n\nПосмотри и поддержи друга 💪"


@dataclass(frozen=True)
class BotButtons:
    """Тексты кнопок."""
    
    # Main menu
    OPEN_APP = "🚀 Открыть Skill Tracer"
    WEEK_STATUS = "📅 Моя неделя"
    SETTINGS = "⚙️ Настройки"
    HELP = "❓ Помощь"
    
    # Week keyboard
    FILL_TODAY = "✍️ Заполнить сегодня"
    VIEW_STATS = "📊 Статистика"
    BACK = "◀️ Назад"
    
    # Settings
    CHANGE_TIMEZONE = "🌍 Изменить часовой пояс"
    CHANGE_REMINDER = "🔔 Настроить напоминания"
    MANAGE_TRACKERS = "📊 Управление трекерами"
    
    # Inline
    PUBLISH_REPORT = "📤 Опубликовать отчет"
    VIEW_REPORT = "👀 Посмотреть отчет"
    ADD_COMMENT = "💬 Комментировать"


@dataclass(frozen=True)
class BotConfig:
    """Конфигурация бота."""
    
    # Время хранения file_id в памяти (секунды)
    MEDIA_CACHE_TTL = 600  # 10 минут
    
    # Максимальный размер файла (20 MB для фото Telegram)
    MAX_FILE_SIZE = 20 * 1024 * 1024
    
    # Количество дней в неделе (для расчетов)
    DAYS_IN_WEEK = 7
    
    # Символы для прогресс-бара
    PROGRESS_FILLED = "●"
    PROGRESS_EMPTY = "○"

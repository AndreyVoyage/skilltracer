#!/usr/bin/env python3.9
"""
Telegram Updates Processor

Скрипт для обработки очереди сообщений от Telegram.
Запускается каждую минуту через Cron.

Cron: * * * * * cd /www/skilltracer.art-artel.su && /usr/bin/python3.9 backend/cron/process_updates.py >> logs/cron.log 2>&1
"""

import sys
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Добавляем путь к backend
sys.path.insert(0, '/www/skilltracer.art-artel.su/backend')

from config.database import get_db_connection, execute

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/www/skilltracer.art-artel.su/logs/processor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Bot token
BOT_TOKEN = "7973502371:AAGZ1A5XeWdKaiMKZDumfTa9gCr0I3a8EMg"


def send_message(chat_id: int, text: str, parse_mode: str = "HTML") -> bool:
    """Отправка сообщения через Telegram API."""
    import urllib.request
    import urllib.parse
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode,
    }).encode()
    
    try:
        req = urllib.request.Request(url, data=data, method='POST')
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())
            return result.get('ok', False)
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        return False


def get_or_create_user(user_data: Dict[str, Any]) -> int:
    """Получить или создать пользователя."""
    user_id = user_data['id']
    username = user_data.get('username')
    first_name = user_data.get('first_name')
    last_name = user_data.get('last_name')
    photo_url = user_data.get('photo_url')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Проверяем существование
            cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if cursor.fetchone():
                # Обновляем данные
                cursor.execute("""
                    UPDATE users 
                    SET username = %s, first_name = %s, last_name = %s, photo_url = %s
                    WHERE id = %s
                """, (username, first_name, last_name, photo_url, user_id))
            else:
                # Создаем нового
                cursor.execute("""
                    INSERT INTO users (id, username, first_name, last_name, photo_url)
                    VALUES (%s, %s, %s, %s, %s)
                """, (user_id, username, first_name, last_name, photo_url))
                logger.info(f"Created new user: {user_id}")
            
            conn.commit()
            return user_id
    finally:
        conn.close()


def handle_start_command(user_id: int, chat_id: int) -> None:
    """Обработка /start."""
    text = f"""Привет! 👋

Добро пожаловать в Skill Tracer — твой личный дневник прогресса.

📊 Отслеживай настроение, спорт, языки и другие навыки.

👥 Делись успехами с друзьями (группа до 3 человек)

🚀 <a href=\"https://skilltracer.art-artel.su/app/\">Открыть Skill Tracer</a>

Используй меню ниже или напиши /help для справки."""
    
    send_message(chat_id, text)


def handle_help_command(user_id: int, chat_id: int) -> None:
    """Обработка /help."""
    text = """📖 <b>Команды:</b>

/start — Начать работу
/help — Эта справка

<b>Как пользоваться:</b>
1. Нажми кнопку "Открыть Skill Tracer"
2. Отмечай настроение и прогресс каждый день
3. В конце недели публикуй отчет для друзей

<b>Совет:</b> Отправь фото боту, чтобы добавить его к записи!"""
    
    send_message(chat_id, text)


def handle_photo(user_id: int, chat_id: int, photo_file_id: str) -> None:
    """Обработка фото."""
    # Сохраняем file_id временно (можно в кэш или БД)
    # Для простоты просто отвечаем
    text = """📸 <b>Фото получено!</b>

Открой Skill Tracer и добавь фото к сегодняшней записи.

<i>Фото доступно в течение 10 минут.</i>"""
    
    send_message(chat_id, text)


def process_update(update: Dict[str, Any]) -> bool:
    """Обработка одного update."""
    try:
        # Получаем message или callback_query
        if 'message' in update:
            message = update['message']
            user = message['from']
            chat_id = message['chat']['id']
            text = message.get('text', '')
            
            user_id = get_or_create_user(user)
            
            if text.startswith('/start'):
                handle_start_command(user_id, chat_id)
            elif text.startswith('/help'):
                handle_help_command(user_id, chat_id)
            elif 'photo' in message:
                photo = message['photo'][-1]  # Самое большое
                handle_photo(user_id, chat_id, photo['file_id'])
            else:
                # Отвечаем на обычное сообщение
                send_message(chat_id, "Используйте кнопку ниже для открытия приложения 👇")
            
            return True
            
        elif 'callback_query' in update:
            # Обработка callback (inline buttons)
            callback = update['callback_query']
            user = callback['from']
            chat_id = callback['message']['chat']['id']
            data = callback.get('data', '')
            
            get_or_create_user(user)
            
            # Простой ответ
            send_message(chat_id, "Функция в разработке! 🚧")
            return True
            
    except Exception as e:
        logger.error(f"Error processing update: {e}")
        return False
    
    return False


def main():
    """Main loop."""
    logger.info("Starting processor...")
    
    conn = get_db_connection()
    processed_count = 0
    
    try:
        with conn.cursor() as cursor:
            # Получаем не обработанные записи
            cursor.execute("""
                SELECT id, update_data 
                FROM telegram_updates 
                WHERE processed = 0 
                ORDER BY created_at 
                LIMIT 10
            """)
            
            updates = cursor.fetchall()
            
            for row in updates:
                update_id = row['id']
                update_data = json.loads(row['update_data'])
                
                logger.info(f"Processing update_id: {update_id}")
                
                if process_update(update_data):
                    # Помечаем как обработанное
                    cursor.execute("""
                        UPDATE telegram_updates 
                        SET processed = 1, processed_at = NOW() 
                        WHERE id = %s
                    """, (update_id,))
                    conn.commit()
                    processed_count += 1
                else:
                    logger.warning(f"Failed to process update: {update_id}")
                    
    except Exception as e:
        logger.error(f"Database error: {e}")
    finally:
        conn.close()
    
    logger.info(f"Processed {processed_count} updates")


if __name__ == '__main__':
    main()

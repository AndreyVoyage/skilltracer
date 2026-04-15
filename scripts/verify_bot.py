#!/usr/bin/env python3
"""
Skill Tracer - Bot Token Verification Script

Проверяет валидность токена Telegram бота, выводит информацию о боте
и устанавливает webhook для production режима.

Usage:
    python scripts/verify_bot.py
    # или с кастомным .env файлом:
    ENV_FILE=/opt/skilltracer/.env python scripts/verify_bot.py
"""

import asyncio
import os
import sys
from pathlib import Path

import aiohttp
from dotenv import load_dotenv

# Handle Windows console encoding for emojis
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def load_env() -> None:
    """Загружает переменные окружения из .env файла."""
    env_file = os.environ.get("ENV_FILE", ".env")
    
    # Пробуем несколько путей
    candidates = [
        Path(env_file),
        Path(__file__).parent.parent / env_file,
        Path("/opt/skilltracer/.env"),
        Path("/opt/skilltracer/backend/.env"),
    ]
    
    for candidate in candidates:
        if candidate.exists():
            load_dotenv(candidate, override=True)
            print(f"[OK] Загружен .env: {candidate}")
            return
    
    print("[WARN] .env файл не найден, используются переменные окружения")


async def make_request(session: aiohttp.ClientSession, url: str) -> dict:
    """Делает GET запрос к Telegram Bot API."""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            data = await resp.json()
            return data
    except Exception as e:
        return {"ok": False, "description": str(e)}


async def verify_bot() -> int:
    """Основная логика проверки бота."""
    load_env()
    
    token = os.environ.get("BOT_TOKEN", "").strip()
    domain = os.environ.get("DOMAIN", "").strip()
    webapp_url = os.environ.get("WEBAPP_URL", "").strip()
    
    if not token:
        print("❌ Ошибка: BOT_TOKEN не найден в .env или переменных окружения")
        print("   Убедитесь что файл .env содержит строку:")
        print("   BOT_TOKEN=your_bot_token_here")
        return 1
    
    # Проверка формата токена
    if ":" not in token or len(token) < 20:
        print(f"[ERROR] BOT_TOKEN выглядит невалидным: '{token[:10]}...'")
        return 1
    
    base_url = f"https://api.telegram.org/bot{token}"
    
    async with aiohttp.ClientSession() as session:
        # 1. getMe
        print("\n🔍 Проверяем токен через getMe...")
        me_data = await make_request(session, f"{base_url}/getMe")
        
        if not me_data.get("ok"):
            error = me_data.get("description", "Unknown error")
            print(f"[ERROR] Токен НЕВАЛИДЕН: {error}")
            print("   Возможные причины:")
            print("   • Токен отозван в @BotFather")
            print("   • Опечатка в токене")
            print("   • Telegram API временно недоступен")
            return 1
        
        bot_info = me_data["result"]
        bot_id = bot_info.get("id")
        bot_first_name = bot_info.get("first_name", "Unknown")
        bot_username = bot_info.get("username", "Unknown")
        bot_can_join_groups = bot_info.get("can_join_groups", False)
        bot_supports_inline_queries = bot_info.get("supports_inline_queries", False)
        
        print("[OK] Токен валиден!")
        print(f"   Bot: {bot_first_name}")
        print(f"   Username: @{bot_username}")
        print(f"   ID: {bot_id}")
        print(f"   Can join groups: {bot_can_join_groups}")
        print(f"   Inline queries: {bot_supports_inline_queries}")
        
        # 2. getWebhookInfo
        print("\n🔍 Проверяем текущий webhook...")
        webhook_data = await make_request(session, f"{base_url}/getWebhookInfo")
        
        if webhook_data.get("ok"):
            webhook_info = webhook_data["result"]
            current_url = webhook_info.get("url", "")
            pending_updates = webhook_info.get("pending_update_count", 0)
            
            if current_url:
                print(f"   Current webhook: {current_url}")
                print(f"   📨 Pending updates: {pending_updates}")
            else:
                print("   Webhook не установлен (используется polling)")
        else:
            print("   [WARN] Не удалось получить webhook info")
        
        # 3. Установка webhook
        # Определяем webhook URL
        webhook_domain = domain or webapp_url.replace("https://", "").replace("http://", "").split("/")[0]
        
        if not webhook_domain or webhook_domain in ("localhost", "127.0.0.1"):
            print("\n[WARN] DOMAIN не задан или localhost — webhook НЕ устанавливаем")
            print("   Для production укажите в .env:")
            print("   DOMAIN=your-domain.ru")
            print("   WEBAPP_URL=https://your-domain.ru")
            return 0
        
        webhook_url = f"https://{webhook_domain}/webhook"
        
        print(f"\n[SETUP] Устанавливаем webhook: {webhook_url}")
        set_webhook_data = await make_request(
            session,
            f"{base_url}/setWebhook?url={webhook_url}&allowed_updates=%5B%22message%22%2C%22callback_query%22%2C%22inline_query%22%5D"
        )
        
        if set_webhook_data.get("ok"):
            print(f"[OK] Webhook успешно установлен: {webhook_url}")
            
            # Перепроверяем
            webhook_data = await make_request(session, f"{base_url}/getWebhookInfo")
            if webhook_data.get("ok"):
                wh_info = webhook_data["result"]
                print(f"   📡 Подтверждённый URL: {wh_info.get('url', 'N/A')}")
                print(f"   📨 Pending updates: {wh_info.get('pending_update_count', 0)}")
                if wh_info.get("has_custom_certificate"):
                    print("   Custom certificate: Yes")
        else:
            error = set_webhook_data.get("description", "Unknown error")
            print(f"[ERROR] Не удалось установить webhook: {error}")
            return 1
    
    print("\n[DONE] Все проверки пройдены успешно!")
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(verify_bot())
    except KeyboardInterrupt:
        print("\n[ABORT] Прервано пользователем")
        exit_code = 130
    
    sys.exit(exit_code)

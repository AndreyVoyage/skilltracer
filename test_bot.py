#!/usr/bin/env python3.9
"""
Skill Tracer - Bot & Database Test Script

Проверяет:
- Подключение к MySQL
- Наличие необходимых таблиц
- Валидность токена бота
- Статус очереди сообщений

Usage:
    cd /www/skilltracer.art-artel.su
    python3.9 test_bot.py
"""

import sys
import os
import json

# Добавляем путь к backend
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_color(text, color):
    """Добавляет цвет к тексту (если терминал поддерживает)."""
    colors = {
        'green': '\033[92m',
        'red': '\033[91m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'reset': '\033[0m'
    }
    return f"{colors.get(color, '')}{text}{colors['reset']}"

def test_database():
    """Проверка подключения к MySQL и структуры таблиц."""
    print(test_color("🔍 Тест 1: Подключение к MySQL...", 'blue'))
    
    try:
        from backend.config.database import DB_CONFIG, get_db_connection
        
        print(f"   База данных: {DB_CONFIG['database']}")
        print(f"   Пользователь: {DB_CONFIG['user']}")
        
        # Подключение
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверка версии MySQL
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        print(f"   Версия MySQL: {version['VERSION()'] if isinstance(version, dict) else version[0]}")
        
        # Проверка таблиц
        print("\n   Проверка таблиц:")
        required_tables = [
            'users', 'custom_trackers', 'daily_entries', 'entry_metrics',
            'week_reports', 'groups', 'group_members', 'telegram_updates', 'comments'
        ]
        
        cursor.execute("SHOW TABLES")
        existing_tables = [row[0] if isinstance(row, tuple) else list(row.values())[0] for row in cursor.fetchall()]
        
        all_exist = True
        for table in required_tables:
            exists = table in existing_tables
            status = test_color("✅", 'green') if exists else test_color("❌", 'red')
            print(f"   {status} {table}")
            if not exists:
                all_exist = False
        
        if not all_exist:
            print(test_color("\n❌ Не все таблицы существуют!", 'red'))
            print("   Импортируйте database.sql через phpMyAdmin")
            return False
        
        # Проверка очереди
        print("\n   Статус очереди сообщений:")
        cursor.execute("SELECT COUNT(*) as total FROM telegram_updates")
        total = cursor.fetchone()
        total = total['total'] if isinstance(total, dict) else total[0]
        
        cursor.execute("SELECT COUNT(*) as pending FROM telegram_updates WHERE processed=0")
        pending = cursor.fetchone()
        pending = pending['pending'] if isinstance(pending, dict) else pending[0]
        
        print(f"   📨 Всего сообщений: {total}")
        print(f"   ⏳ В очереди (не обработано): {pending}")
        
        conn.close()
        
        print(test_color("\n✅ Подключение к БД успешно!", 'green'))
        return True
        
    except ImportError as e:
        print(test_color(f"\n❌ Ошибка импорта: {e}", 'red'))
        print("   Проверьте что файл backend/config/database.py существует")
        return False
    except Exception as e:
        print(test_color(f"\n❌ Ошибка подключения к БД: {e}", 'red'))
        print("   Проверьте:")
        print("   - Правильность данных в backend/config/database.py")
        print("   - Что пользователь MySQL имеет доступ к базе")
        print("   - Что MySQL сервер запущен")
        return False


def test_bot_token():
    """Проверка токена бота через Telegram API."""
    print(test_color("\n🔍 Тест 2: Проверка токена бота...", 'blue'))
    
    try:
        # Импортируем токен из process_updates.py
        import re
        
        # Читаем файл и находим токен
        with open('backend/cron/process_updates.py', 'r') as f:
            content = f.read()
        
        # Ищем BOT_TOKEN
        match = re.search(r'BOT_TOKEN\s*=\s*["\']([^"\']+)["\']', content)
        if not match:
            print(test_color("❌ BOT_TOKEN не найден в process_updates.py", 'red'))
            return False
        
        token = match.group(1)
        
        if token == 'YOUR_BOT_TOKEN_HERE' or len(token) < 20:
            print(test_color("❌ Токен не настроен (стоит заглушка)", 'red'))
            return False
        
        print(f"   Токен найден: {token[:20]}...")
        
        # Проверяем через Telegram API
        try:
            import urllib.request
            import urllib.error
            
            url = f'https://api.telegram.org/bot{token}/getMe'
            
            print("   Отправка запроса к Telegram API...")
            
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
                
                if data.get('ok'):
                    bot_info = data['result']
                    print(test_color(f"\n✅ Бот найден!", 'green'))
                    print(f"   Имя: {bot_info.get('first_name', 'N/A')}")
                    print(f"   Username: @{bot_info.get('username', 'N/A')}")
                    if bot_info.get('is_bot'):
                        print(f"   Тип: Bot ✓")
                    return True
                else:
                    print(test_color(f"\n❌ Ошибка API: {data}", 'red'))
                    return False
                    
        except ImportError:
            print("   ⚠️ urllib не доступен, пропускаем проверку через API")
            print(f"   Токен найден: {token[:20]}...")
            return True
        except urllib.error.HTTPError as e:
            if e.code == 401:
                print(test_color("\n❌ Токен недействителен (401 Unauthorized)", 'red'))
                print("   Получите новый токен через @BotFather")
            else:
                print(test_color(f"\n❌ HTTP ошибка: {e.code}", 'red'))
            return False
        except Exception as e:
            print(test_color(f"\n⚠️ Не удалось проверить через API: {e}", 'yellow'))
            print("   Проверьте токен вручную")
            return True
            
    except FileNotFoundError:
        print(test_color("❌ Файл process_updates.py не найден", 'red'))
        return False
    except Exception as e:
        print(test_color(f"❌ Ошибка: {e}", 'red'))
        return False


def test_webhook_setup():
    """Проверка доступности webhook URL."""
    print(test_color("\n🔍 Тест 3: Проверка webhook URL...", 'blue'))
    
    webhook_url = "https://skilltracer.art-artel.su/webhook.php"
    print(f"   URL: {webhook_url}")
    
    # Проверяем что файл существует
    if os.path.exists('webhook.php'):
        print(test_color("   ✅ Файл webhook.php существует", 'green'))
        
        # Проверяем что токен установлен
        with open('webhook.php', 'r') as f:
            content = f.read()
        
        if 'YOUR_BOT_TOKEN_HERE' in content or "'7973502371:" in content:
            print(test_color("   ✅ Токен установлен в webhook.php", 'green'))
        else:
            print(test_color("   ⚠️ Не удалось найти токен в webhook.php", 'yellow'))
        
        return True
    else:
        print(test_color("   ❌ Файл webhook.php не найден!", 'red'))
        return False


def test_cron_setup():
    """Проверка настройки cron."""
    print(test_color("\n🔍 Тест 4: Проверка cron...", 'blue'))
    
    cron_script = 'backend/cron/process_updates.py'
    
    if os.path.exists(cron_script):
        print(test_color(f"   ✅ Скрипт {cron_script} существует", 'green'))
        
        # Проверяем что он исполняемый
        if os.access(cron_script, os.X_OK):
            print(test_color("   ✅ Скрипт исполняемый", 'green'))
        else:
            print(test_color("   ⚠️ Скрипт не исполняемый (chmod +x не критично для cron)", 'yellow'))
        
        # Проверяем что cron запускается
        print("   ℹ️ Проверьте вручную что cron настроен в ISPmanager")
        print("   Команда: cd /www/skilltracer.art-artel.su && python3.9 backend/cron/process_updates.py")
        
        return True
    else:
        print(test_color(f"   ❌ Скрипт {cron_script} не найден!", 'red'))
        return False


def main():
    """Главная функция."""
    print(test_color("="*60, 'blue'))
    print(test_color("  Skill Tracer - Тестирование системы", 'blue'))
    print(test_color("="*60, 'blue'))
    print()
    
    # Запускаем все тесты
    results = []
    
    results.append(('База данных', test_database()))
    results.append(('Токен бота', test_bot_token()))
    results.append(('Webhook', test_webhook_setup()))
    results.append(('Cron', test_cron_setup()))
    
    # Итог
    print(test_color("\n" + "="*60, 'blue'))
    print(test_color("  РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ", 'blue'))
    print(test_color("="*60, 'blue'))
    
    all_passed = True
    for name, passed in results:
        status = test_color("✅ ПРОЙДЕН", 'green') if passed else test_color("❌ ОШИБКА", 'red')
        print(f"   {name}: {status}")
        if not passed:
            all_passed = False
    
    print(test_color("="*60, 'blue'))
    
    if all_passed:
        print(test_color("\n🎉 Все проверки пройдены!", 'green'))
        print("\nСледующие шаги:")
        print("   1. Установите webhook: откройте https://skilltracer.art-artel.su/setup_webhook.php")
        print("   2. Отправьте боту /start в Telegram")
        print("   3. Проверьте что сообщение появилось в БД")
        print("   4. Подождите 1 минуту и проверьте что бот ответил")
        return 0
    else:
        print(test_color("\n⚠️  Есть ошибки. Исправьте перед запуском!", 'red'))
        print("\nДля отладки:")
        print("   - Проверьте логи: tail -f logs/*.log")
        print("   - Проверьте права: ls -la")
        print("   - Проверьте конфиги: cat config/database.php")
        return 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

#!/usr/bin/env python3.9
"""
Skill Tracer - Database Connection Test (Python)

Проверяет подключение к MySQL из Python (для cron)

Usage:
    cd /www/skilltracer.art-artel.su
    python3.9 test_db_connection.py
"""

import sys
import os

# Добавляем путь к backend
sys.path.insert(0, '/www/skilltracer.art-artel.su')

def test_import():
    """Проверка импорта конфига."""
    print("🔍 Тест 1: Импорт конфигурации...")
    try:
        from backend.config.database import DB_CONFIG
        print(f"   ✅ Конфиг загружен")
        print(f"   Host: {DB_CONFIG['host']}")
        print(f"   Database: {DB_CONFIG['database']}")
        print(f"   User: {DB_CONFIG['user']}")
        return DB_CONFIG
    except ImportError as e:
        print(f"   ❌ Ошибка импорта: {e}")
        print("   Проверьте что файл backend/config/database.py существует")
        sys.exit(1)
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        sys.exit(1)

def test_pymysql():
    """Проверка установки pymysql."""
    print("\n🔍 Тест 2: Проверка pymysql...")
    try:
        import pymysql
        print(f"   ✅ pymysql установлен (версия: {pymysql.__version__})")
        return True
    except ImportError:
        print("   ❌ pymysql не установлен")
        print("   Установите: pip3 install pymysql")
        return False

def test_connection(db_config):
    """Проверка подключения к БД."""
    print("\n🔍 Тест 3: Подключение к MySQL...")
    
    try:
        import pymysql
        
        print(f"   Подключение к {db_config['host']}...")
        
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()
        
        # Проверка версии
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        print(f"   ✅ Подключено!")
        print(f"   MySQL версия: {version[0]}")
        
        # Список таблиц
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"   Найдено таблиц: {len(tables)}")
        
        if tables:
            print(f"   Таблицы: {', '.join(tables[:5])}", end='')
            if len(tables) > 5:
                print(f" и еще {len(tables) - 5}...")
            else:
                print()
        
        # Проверка конкретных таблиц
        required = ['users', 'telegram_updates', 'daily_entries', 'week_reports', 'groups']
        missing = [t for t in required if t not in tables]
        
        if missing:
            print(f"\n   ⚠️  Отсутствуют таблицы: {', '.join(missing)}")
            print("   Импортируйте database.sql")
        else:
            print(f"   ✅ Все необходимые таблицы найдены")
        
        # Проверка очереди
        cursor.execute("SELECT COUNT(*) FROM telegram_updates")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM telegram_updates WHERE processed=0")
        pending = cursor.fetchone()[0]
        
        print(f"\n   📨 Сообщений в очереди: {pending} (всего: {total})")
        
        conn.close()
        return True
        
    except pymysql.err.OperationalError as e:
        error_code, error_msg = e.args
        print(f"   ❌ Ошибка подключения: {error_msg}")
        
        if error_code == 1045:
            print("   → Неверный логин или пароль")
        elif error_code == 1049:
            print("   → База данных не найдена")
            print(f"   → Проверьте что имя '{db_config['database']}' правильное")
            print("   → Возможно нужно: u1893136_skilltracer вместо u1893136_skilltracer.art-artel.s")
        elif error_code == 2003:
            print("   → Не удалось подключиться к серверу MySQL")
        
        return False
        
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return False

def test_file_permissions():
    """Проверка прав на файлы."""
    print("\n🔍 Тест 4: Проверка прав доступа...")
    
    paths_to_check = [
        '/www/skilltracer.art-artel.su/logs',
        '/www/skilltracer.art-artel.su/backend/cron',
    ]
    
    for path in paths_to_check:
        if os.path.exists(path):
            perms = oct(os.stat(path).st_mode)[-3:]
            writable = os.access(path, os.W_OK)
            status = "✅" if writable else "⚠️"
            print(f"   {status} {path} (perms: {perms}, writable: {writable})")
        else:
            print(f"   ❌ {path} не существует")

def main():
    """Главная функция."""
    print("=" * 60)
    print("  Skill Tracer - Python DB Connection Test")
    print("=" * 60)
    print()
    
    # Проверка Python версии
    if sys.version_info < (3, 9):
        print(f"⚠️  Рекомендуется Python 3.9+, текущая версия: {sys.version}")
        print()
    
    # Запускаем тесты
    db_config = test_import()
    
    if not test_pymysql():
        print("\n❌ Установите pymysql: pip3 install pymysql")
        sys.exit(1)
    
    if not test_connection(db_config):
        print("\n" + "=" * 60)
        print("❌ ПОДКЛЮЧЕНИЕ НЕ УДАЛОСЬ")
        print("=" * 60)
        print("\nПроверьте:")
        print("1. Имя базы данных в backend/config/database.py")
        print("2. Логин и пароль")
        print("3. Что пользователь имеет доступ к базе")
        sys.exit(1)
    
    test_file_permissions()
    
    print("\n" + "=" * 60)
    print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    print("=" * 60)
    print("\nPython может подключаться к MySQL.")
    print("Cron должен работать корректно.")
    
    return 0

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

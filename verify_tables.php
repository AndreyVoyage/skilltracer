<?php
/**
 * Skill Tracer - Table Verification Script
 * 
 * Проверяет что все необходимые таблицы созданы
 * URL: https://skilltracer.art-artel.su/verify_tables.php
 */

require_once 'config/database.php';

header('Content-Type: text/plain; charset=utf-8');

echo "=== Skill Tracer - Table Verification ===\n\n";

try {
    $pdo = new PDO("mysql:host=" . DB_HOST . ";dbname=" . DB_NAME, DB_USER, DB_PASS);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    
    echo "✅ Подключение к БД успешно\n";
    echo "   База: " . DB_NAME . "\n\n";
    
    // Получаем список таблиц
    $stmt = $pdo->query("SHOW TABLES");
    $tables = $stmt->fetchAll(PDO::FETCH_COLUMN);
    
    echo "Найдено таблиц: " . count($tables) . "\n";
    echo "Список: " . implode(', ', $tables) . "\n\n";
    
    // Проверяем необходимые таблицы
    $required = [
        'users' => 'Telegram пользователи',
        'custom_trackers' => 'Пользовательские трекеры',
        'daily_entries' => 'Ежедневные записи',
        'entry_metrics' => 'Метрики записей',
        'week_reports' => 'Недельные отчеты',
        'groups' => 'Группы',
        'group_members' => 'Члены групп',
        'telegram_updates' => 'Очередь Telegram',
        'comments' => 'Комментарии'
    ];
    
    echo "=== Проверка необходимых таблиц ===\n\n";
    
    $allOk = true;
    foreach ($required as $table => $description) {
        $exists = in_array($table, $tables);
        $status = $exists ? '✅' : '❌';
        echo "$status $table - $description\n";
        if (!$exists) {
            $allOk = false;
        }
    }
    
    echo "\n=== Результат ===\n\n";
    
    if ($allOk) {
        echo "✅ ВСЕ ТАБЛИЦЫ СОЗДАНЫ!\n";
        echo "Всего таблиц: " . count($tables) . "\n\n";
        echo "Следующий шаг:\n";
        echo "1. Откройте: https://skilltracer.art-artel.su/test_db.php\n";
        echo "2. Убедитесь что 'overall_status' = 'SUCCESS'\n";
        echo "3. Затем установите webhook\n";
    } else {
        echo "❌ НЕ ВСЕ ТАБЛИЦЫ НАЙДЕНЫ!\n\n";
        echo "Импортируйте database.sql через phpMyAdmin:\n";
        echo "1. ISPmanager → Базы данных\n";
        echo "2. Выберите базу '" . DB_NAME . "'\n";
        echo "3. Нажмите 'Web интерфейс БД' (phpMyAdmin)\n";
        echo "4. Вкладка 'Импорт' → Выберите database.sql\n";
        echo "5. Нажмите 'Вперед'\n";
    }
    
} catch (PDOException $e) {
    echo "❌ Ошибка подключения к БД:\n";
    echo "   " . $e->getMessage() . "\n\n";
    echo "Проверьте:\n";
    echo "1. Файл config/database.php\n";
    echo "2. Логин и пароль\n";
    echo "3. Имя базы данных\n";
}

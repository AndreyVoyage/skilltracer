<?php
/**
 * Skill Tracer - System Test Script
 * 
 * URL: https://skilltracer.art-artel.su/test.php
 * 
 * Проверяет:
 * - PHP версию
 * - Подключение к БД
 * - Права на logs
 * - Структуру таблиц
 * - SSL (HTTPS)
 */

header('Content-Type: application/json; charset=utf-8');

$tests = [];
$allPassed = true;

// Тест 1: Проверка PHP версии
$phpVersion = PHP_VERSION;
$tests['php_version'] = [
    'status' => version_compare($phpVersion, '8.0.0', '>=') ? 'OK' : 'FAIL',
    'value' => $phpVersion,
    'message' => version_compare($phpVersion, '8.0.0', '>=') 
        ? 'PHP версия поддерживается' 
        : 'Требуется PHP 8.0+'
];
if (version_compare($phpVersion, '8.0.0', '<')) {
    $allPassed = false;
}

// Тест 2: Проверка PDO MySQL
$tests['pdo_mysql'] = [
    'status' => extension_loaded('pdo_mysql') ? 'OK' : 'FAIL',
    'message' => extension_loaded('pdo_mysql') 
        ? 'PDO MySQL расширение загружено' 
        : 'Необходимо расширение pdo_mysql'
];
if (!extension_loaded('pdo_mysql')) {
    $allPassed = false;
}

// Тест 3: Проверка подключения к БД
try {
    if (file_exists('config/database.php')) {
        require_once 'config/database.php';
        $pdo = new PDO("mysql:host=" . DB_HOST . ";dbname=" . DB_NAME, DB_USER, DB_PASS);
        $pdo->query('SELECT 1');
        $tests['database'] = [
            'status' => 'OK',
            'message' => 'Подключение к БД успешно',
            'database' => DB_NAME,
            'user' => DB_USER
        ];
    } else {
        $tests['database'] = [
            'status' => 'FAIL',
            'message' => 'Файл config/database.php не найден'
        ];
        $allPassed = false;
    }
} catch (Exception $e) {
    $tests['database'] = [
        'status' => 'FAIL',
        'message' => 'Ошибка подключения: ' . $e->getMessage()
    ];
    $allPassed = false;
}

// Тест 4: Проверка прав на logs
$logsDir = 'logs/';
if (!is_dir($logsDir)) {
    @mkdir($logsDir, 0777, true);
}
$tests['logs_writable'] = [
    'status' => is_writable($logsDir) ? 'OK' : 'FAIL',
    'message' => is_writable($logsDir) 
        ? 'Папка logs доступна для записи' 
        : 'Нужны права 777 на logs/',
    'path' => realpath($logsDir)
];
if (!is_writable($logsDir)) {
    $allPassed = false;
}

// Тест 5: Проверка структуры таблиц (если БД подключена)
if (isset($pdo) && $pdo) {
    try {
        $requiredTables = ['users', 'telegram_updates', 'daily_entries', 'week_reports', 'groups'];
        $existingTables = [];
        $missingTables = [];
        
        foreach ($requiredTables as $table) {
            $stmt = $pdo->query("SHOW TABLES LIKE '$table'");
            if ($stmt->rowCount() > 0) {
                $existingTables[] = $table;
            } else {
                $missingTables[] = $table;
            }
        }
        
        $tests['table_structure'] = [
            'status' => count($missingTables) === 0 ? 'OK' : 'WARN',
            'message' => count($missingTables) === 0 
                ? 'Все необходимые таблицы существуют' 
                : 'Отсутствуют таблицы: ' . implode(', ', $missingTables),
            'existing' => $existingTables,
            'missing' => $missingTables
        ];
        
        if (count($missingTables) > 0) {
            $allPassed = false;
        }
        
        // Тест 6: Проверка очереди сообщений
        $stmt = $pdo->query("SELECT COUNT(*) as total, SUM(CASE WHEN processed=0 THEN 1 ELSE 0 END) as pending FROM telegram_updates");
        $queueStats = $stmt->fetch(PDO::FETCH_ASSOC);
        $tests['queue_status'] = [
            'status' => 'OK',
            'message' => "Всего сообщений: {$queueStats['total']}, в очереди: {$queueStats['pending']}",
            'total' => (int)$queueStats['total'],
            'pending' => (int)$queueStats['pending']
        ];
        
    } catch (Exception $e) {
        $tests['table_structure'] = [
            'status' => 'FAIL',
            'message' => 'Ошибка проверки таблиц: ' . $e->getMessage()
        ];
        $allPassed = false;
    }
}

// Тест 7: Проверка SSL (для Telegram)
$isHttps = isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] === 'on';
$tests['ssl'] = [
    'status' => $isHttps ? 'OK' : 'WARN',
    'message' => $isHttps 
        ? 'HTTPS включен (обязательно для Telegram)' 
        : 'HTTPS не обнаружен. Для работы бота нужен SSL!',
    'protocol' => $isHttps ? 'https' : 'http'
];

// Тест 8: Проверка конфигурации Python
try {
    if (file_exists('backend/config/database.py')) {
        $tests['python_config'] = [
            'status' => 'OK',
            'message' => 'Конфиг Python найден'
        ];
    } else {
        $tests['python_config'] = [
            'status' => 'WARN',
            'message' => 'Файл backend/config/database.py не найден'
        ];
    }
} catch (Exception $e) {
    $tests['python_config'] = [
        'status' => 'FAIL',
        'message' => $e->getMessage()
    ];
}

// Тест 9: Проверка доступности внешних URL
$tests['webhook_url'] = [
    'status' => 'INFO',
    'message' => 'Webhook URL должен быть: https://skilltracer.art-artel.su/webhook.php'
];

// Формируем ответ
$response = [
    'all_passed' => $allPassed,
    'system_ready' => $allPassed && $isHttps,
    'tests' => $tests,
    'server' => [
        'php_version' => $phpVersion,
        'server_software' => $_SERVER['SERVER_SOFTWARE'] ?? 'Unknown',
        'document_root' => $_SERVER['DOCUMENT_ROOT'] ?? 'Unknown',
        'https' => $isHttps,
    ],
    'timestamp' => date('Y-m-d H:i:s'),
    'next_steps' => $allPassed 
        ? 'Все проверки пройдены! Можно устанавливать webhook.' 
        : 'Исправьте ошибки перед продолжением.'
];

echo json_encode($response, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);

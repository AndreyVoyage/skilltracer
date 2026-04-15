<?php
/**
 * Skill Tracer - Database Diagnostic Tool
 * 
 * Подробный тест подключения к базе данных
 * URL: https://skilltracer.art-artel.su/test_db.php
 */

header('Content-Type: application/json; charset=utf-8');

$result = [
    'time' => date('Y-m-d H:i:s'),
    'server' => [
        'php_version' => PHP_VERSION,
        'document_root' => $_SERVER['DOCUMENT_ROOT'] ?? 'Unknown',
        'current_dir' => getcwd(),
    ],
    'tests' => []
];

// Тест 1: Конфиг существует
$configPath = 'config/database.php';
if (!file_exists($configPath)) {
    // Пробуем найти в других местах
    $possiblePaths = [
        'config/database.php',
        '../config/database.php',
        './config/database.php',
        __DIR__ . '/config/database.php'
    ];
    
    $found = false;
    foreach ($possiblePaths as $path) {
        if (file_exists($path)) {
            $configPath = $path;
            $found = true;
            break;
        }
    }
    
    if (!$found) {
        echo json_encode([
            'error' => 'Config file not found',
            'searched_paths' => $possiblePaths,
            'current_dir' => getcwd(),
            'files_in_current' => scandir('.')
        ], JSON_PRETTY_PRINT);
        exit;
    }
}

$result['tests']['config_file'] = [
    'status' => 'OK',
    'path' => realpath($configPath)
];

// Подключаем конфиг
try {
    require $configPath;
} catch (Exception $e) {
    echo json_encode([
        'error' => 'Failed to load config',
        'message' => $e->getMessage()
    ], JSON_PRETTY_PRINT);
    exit;
}

// Тест 2: Константы определены
$result['tests']['constants'] = [
    'DB_HOST' => defined('DB_HOST') ? DB_HOST : 'NOT DEFINED',
    'DB_NAME' => defined('DB_NAME') ? DB_NAME : 'NOT DEFINED',
    'DB_USER' => defined('DB_USER') ? DB_USER : 'NOT DEFINED',
    'DB_PASS' => defined('DB_PASS') ? (strlen(DB_PASS) > 0 ? '***hidden***' : 'EMPTY') : 'NOT DEFINED'
];

if (!defined('DB_HOST') || !defined('DB_NAME') || !defined('DB_USER') || !defined('DB_PASS')) {
    echo json_encode([
        'error' => 'Database constants not defined',
        'tests' => $result['tests']
    ], JSON_PRETTY_PRINT);
    exit;
}

// Тест 3: Подключение PDO
try {
    $dsn = "mysql:host=" . DB_HOST . ";dbname=" . DB_NAME . ";charset=utf8mb4";
    $start = microtime(true);
    
    $pdo = new PDO($dsn, DB_USER, DB_PASS, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_TIMEOUT => 5
    ]);
    
    $connectTime = round((microtime(true) - $start) * 1000, 2);
    
    $result['tests']['connection'] = [
        'status' => 'OK',
        'message' => 'Connected successfully',
        'time_ms' => $connectTime
    ];
    
    // Тест 4: Версия MySQL
    $stmt = $pdo->query("SELECT VERSION() as version");
    $version = $stmt->fetch();
    $result['tests']['mysql_version'] = [
        'status' => 'OK',
        'version' => $version['version']
    ];
    
    // Тест 5: Список таблиц
    $stmt = $pdo->query("SHOW TABLES");
    $tables = $stmt->fetchAll(PDO::FETCH_COLUMN);
    $result['tests']['tables'] = [
        'count' => count($tables),
        'list' => $tables
    ];
    
    // Тест 6: Проверка конкретных таблиц
    $requiredTables = ['users', 'telegram_updates', 'daily_entries', 'week_reports', 'groups', 'custom_trackers'];
    $missing = array_diff($requiredTables, $tables);
    $result['tests']['required_tables'] = [
        'status' => empty($missing) ? 'OK' : 'FAIL',
        'required' => $requiredTables,
        'found' => array_intersect($requiredTables, $tables),
        'missing' => array_values($missing)
    ];
    
    // Тест 7: Права на запись (logs)
    $logsPath = 'logs/';
    if (!is_dir($logsPath)) {
        @mkdir($logsPath, 0777, true);
    }
    
    $result['tests']['logs_writable'] = [
        'status' => is_writable($logsPath) ? 'OK' : 'FAIL',
        'path' => realpath($logsPath),
        'permissions' => is_dir($logsPath) ? substr(sprintf('%o', fileperms($logsPath)), -4) : 'N/A'
    ];
    
    // Тест 8: Проверка записи
    if (is_writable($logsPath)) {
        $testFile = $logsPath . 'db_test_' . time() . '.txt';
        $writeSuccess = @file_put_contents($testFile, 'test') !== false;
        if ($writeSuccess) {
            @unlink($testFile);
        }
        $result['tests']['logs_write_test'] = [
            'status' => $writeSuccess ? 'OK' : 'FAIL',
            'message' => $writeSuccess ? 'Can write to logs/' : 'Cannot write to logs/'
        ];
    }
    
    // Тест 9: Проверка очереди сообщений
    if (in_array('telegram_updates', $tables)) {
        $stmt = $pdo->query("SELECT COUNT(*) as total, SUM(CASE WHEN processed=0 THEN 1 ELSE 0 END) as pending FROM telegram_updates");
        $queueStats = $stmt->fetch();
        $result['tests']['queue_status'] = [
            'total_messages' => (int)$queueStats['total'],
            'pending' => (int)$queueStats['pending'],
            'processed' => (int)$queueStats['total'] - (int)$queueStats['pending']
        ];
    }
    
    // Итоговый статус
    $hasErrors = false;
    foreach ($result['tests'] as $test) {
        if (is_array($test) && isset($test['status']) && $test['status'] === 'FAIL') {
            $hasErrors = true;
            break;
        }
    }
    
    $result['overall_status'] = $hasErrors ? 'PARTIAL' : 'SUCCESS';
    $result['message'] = $hasErrors 
        ? 'Some tests failed. Check the details above.' 
        : 'All tests passed! System is ready.';
    
} catch (PDOException $e) {
    $errorCode = $e->getCode();
    $errorMsg = $e->getMessage();
    
    $result['tests']['connection'] = [
        'status' => 'FAIL',
        'error' => $errorMsg,
        'code' => $errorCode,
        'dsn' => str_replace(DB_PASS, '***', $dsn)
    ];
    
    // Расшифровка ошибок
    $errorHelp = '';
    if (strpos($errorMsg, 'Access denied') !== false) {
        $errorHelp = 'Неверный логин или пароль. Проверьте DB_USER и DB_PASS в config/database.php';
    } elseif (strpos($errorMsg, 'Unknown database') !== false) {
        $errorHelp = 'База данных не найдена. Проверьте DB_NAME в config/database.php. Возможно нужно: u1893136_skilltracer вместо u1893136_skilltracer.art-artel.s';
    } elseif (strpos($errorMsg, 'Connection refused') !== false) {
        $errorHelp = 'Не удалось подключиться к MySQL серверу. Обратитесь в поддержку хостинга.';
    } elseif (strpos($errorMsg, 'getaddrinfo failed') !== false) {
        $errorHelp = 'Не удалось разрешить имя хоста. Проверьте DB_HOST (обычно: localhost)';
    }
    
    if ($errorHelp) {
        $result['tests']['connection']['help'] = $errorHelp;
    }
    
    $result['overall_status'] = 'FAIL';
    $result['message'] = 'Database connection failed. Check the error details.';
}

// Добавляем рекомендации
$result['recommendations'] = [];

if ($result['overall_status'] === 'SUCCESS') {
    $result['recommendations'][] = '✅ Все тесты пройдены!';
    $result['recommendations'][] = 'Следующий шаг: откройте https://skilltracer.art-artel.su/setup_webhook.php';
} else {
    if (isset($result['tests']['connection']['status']) && $result['tests']['connection']['status'] === 'FAIL') {
        $result['recommendations'][] = '❌ Проблема с подключением к БД';
        $result['recommendations'][] = '1. Проверьте точное имя базы в панели ISPmanager';
        $result['recommendations'][] = '2. Убедитесь что пароль правильный';
        $result['recommendations'][] = '3. Проверьте что пользователь имеет доступ к базе';
    }
    
    if (isset($result['tests']['required_tables']['status']) && $result['tests']['required_tables']['status'] === 'FAIL') {
        $result['recommendations'][] = '';
        $result['recommendations'][] = '❌ Не все таблицы найдены';
        $result['recommendations'][] = 'Импортируйте database.sql через phpMyAdmin';
    }
    
    if (isset($result['tests']['logs_writable']['status']) && $result['tests']['logs_writable']['status'] === 'FAIL') {
        $result['recommendations'][] = '';
        $result['recommendations'][] = '❌ Папка logs/ недоступна для записи';
        $result['recommendations'][] = 'Выполните: chmod 777 logs/';
    }
}

echo json_encode($result, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);

<?php
/**
 * Skill Tracer - Full System Test
 * 
 * Комплексный тест всех компонентов перед запуском
 * URL: https://skilltracer.art-artel.su/test_full.php
 */

header('Content-Type: application/json; charset=utf-8');

$tests = [];
$allPassed = true;

// Тест 1: Конфигурация существует
try {
    require_once 'config/database.php';
    $tests['config'] = [
        'status' => 'OK',
        'message' => 'Config loaded successfully'
    ];
} catch (Exception $e) {
    $tests['config'] = [
        'status' => 'FAIL',
        'error' => $e->getMessage()
    ];
    $allPassed = false;
    
    echo json_encode([
        'timestamp' => date('Y-m-d H:i:s'),
        'overall_status' => 'CRITICAL_ERROR',
        'message' => 'Cannot load configuration',
        'tests' => $tests
    ], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
    exit;
}

// Тест 2: База данных
try {
    $pdo = new PDO("mysql:host=" . DB_HOST . ";dbname=" . DB_NAME, DB_USER, DB_PASS, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC
    ]);
    
    // Проверка версии MySQL
    $stmt = $pdo->query("SELECT VERSION() as version");
    $version = $stmt->fetch();
    
    $tests['database'] = [
        'status' => 'OK',
        'message' => 'Connected successfully',
        'mysql_version' => $version['version']
    ];
} catch (Exception $e) {
    $tests['database'] = [
        'status' => 'FAIL',
        'error' => $e->getMessage()
    ];
    $allPassed = false;
}

// Тест 3: Таблицы
if (isset($pdo)) {
    try {
        $required = ['users', 'telegram_updates', 'daily_entries', 'week_reports', 'groups', 'custom_trackers', 'entry_metrics', 'group_members'];
        $stmt = $pdo->query("SHOW TABLES");
        $tables = $stmt->fetchAll(PDO::FETCH_COLUMN);
        $missing = array_diff($required, $tables);
        
        $tests['tables'] = [
            'status' => empty($missing) ? 'OK' : 'FAIL',
            'found' => count($tables),
            'required' => count($required),
            'missing' => array_values($missing),
            'list' => $tables
        ];
        
        if (!empty($missing)) {
            $allPassed = false;
        }
    } catch (Exception $e) {
        $tests['tables'] = [
            'status' => 'FAIL',
            'error' => $e->getMessage()
        ];
        $allPassed = false;
    }
}

// Тест 4: Webhook endpoint доступен
try {
    $webhookPath = __DIR__ . '/webhook.php';
    if (file_exists($webhookPath)) {
        $tests['webhook_file'] = [
            'status' => 'OK',
            'message' => 'webhook.php exists'
        ];
        
        // Проверяем что URL доступен
        $context = stream_context_create([
            'http' => [
                'timeout' => 5,
                'ignore_errors' => true
            ],
            'ssl' => [
                'verify_peer' => false,
                'verify_peer_name' => false
            ]
        ]);
        
        $webhookUrl = 'https://skilltracer.art-artel.su/webhook.php';
        $response = @file_get_contents($webhookUrl, false, $context);
        
        if ($response !== false) {
            $tests['webhook_endpoint'] = [
                'status' => 'OK',
                'message' => 'Endpoint reachable',
                'url' => $webhookUrl
            ];
        } else {
            $tests['webhook_endpoint'] = [
                'status' => 'WARN',
                'message' => 'Cannot verify via HTTP (might be blocked)',
                'url' => $webhookUrl
            ];
        }
    } else {
        $tests['webhook_file'] = [
            'status' => 'FAIL',
            'error' => 'webhook.php not found'
        ];
        $allPassed = false;
    }
} catch (Exception $e) {
    $tests['webhook_endpoint'] = [
        'status' => 'WARN',
        'message' => 'Cannot test: ' . $e->getMessage()
    ];
}

// Тест 5: Права на запись
$permissions = [
    'logs/' => is_writable('logs/'),
    'config/' => is_readable('config/'),
    'backend/cron/' => is_readable('backend/cron/process_updates.py')
];

$permStatus = 'OK';
foreach ($permissions as $path => $writable) {
    if (!$writable) {
        $permStatus = 'FAIL';
        $allPassed = false;
    }
}

$tests['permissions'] = [
    'status' => $permStatus,
    'checks' => $permissions
];

// Тест 6: Python доступен
exec('which python3.9 2>/dev/null', $output, $returnCode);
if ($returnCode === 0) {
    $pythonPath = $output[0];
    
    // Проверяем версию
    exec('python3.9 --version 2>&1', $versionOutput, $versionCode);
    $pythonVersion = $versionCode === 0 ? $versionOutput[0] : 'unknown';
    
    $tests['python'] = [
        'status' => 'OK',
        'path' => $pythonPath,
        'version' => $pythonVersion
    ];
} else {
    // Пробуем python3
    exec('which python3 2>/dev/null', $output3, $returnCode3);
    if ($returnCode3 === 0) {
        $tests['python'] = [
            'status' => 'WARN',
            'path' => $output3[0],
            'message' => 'python3.9 not found, using python3 (may not work)'
        ];
    } else {
        $tests['python'] = [
            'status' => 'FAIL',
            'error' => 'Python not found. Install python3.9'
        ];
        $allPassed = false;
    }
}

// Тест 7: API endpoints
$endpoints = [
    'api/me.php' => file_exists(__DIR__ . '/api/me.php'),
    'api/entries.php' => file_exists(__DIR__ . '/api/entries.php'),
    'api/weeks.php' => file_exists(__DIR__ . '/api/weeks.php'),
    'api/groups.php' => file_exists(__DIR__ . '/api/groups.php')
];

$apiStatus = 'OK';
foreach ($endpoints as $endpoint => $exists) {
    if (!$exists) {
        $apiStatus = 'FAIL';
        $allPassed = false;
    }
}

$tests['api_endpoints'] = [
    'status' => $apiStatus,
    'endpoints' => $endpoints
];

// Тест 8: Bot Token валиден
$botToken = defined('BOT_TOKEN') ? BOT_TOKEN : null;
if ($botToken && strlen($botToken) > 20 && strpos($botToken, ':') !== false) {
    $tests['bot_token'] = [
        'status' => 'OK',
        'format' => 'Valid format',
        'length' => strlen($botToken)
    ];
} else {
    $tests['bot_token'] = [
        'status' => 'FAIL',
        'error' => 'Invalid or missing token'
    ];
    $allPassed = false;
}

// Тест 9: Проверка процессора (Python файл)
$processorPath = __DIR__ . '/backend/cron/process_updates.py';
if (file_exists($processorPath)) {
    $content = file_get_contents($processorPath);
    $hasBotToken = strpos($content, 'BOT_TOKEN') !== false;
    $hasDbConfig = strpos($content, 'DB_CONFIG') !== false;
    
    $tests['processor'] = [
        'status' => ($hasBotToken && $hasDbConfig) ? 'OK' : 'WARN',
        'file_exists' => true,
        'has_bot_token' => $hasBotToken,
        'has_db_config' => $hasDbConfig
    ];
} else {
    $tests['processor'] = [
        'status' => 'FAIL',
        'error' => 'Processor file not found'
    ];
    $allPassed = false;
}

// Тест 10: SSL/HTTPS
$isHttps = isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] === 'on';
$tests['ssl'] = [
    'status' => $isHttps ? 'OK' : 'WARN',
    'https_enabled' => $isHttps,
    'message' => $isHttps ? 'HTTPS is enabled' : 'HTTPS not detected (required for Telegram)'
];

if (!$isHttps) {
    // Это предупреждение, но не критическая ошибка для теста
}

// Формируем ответ
$response = [
    'timestamp' => date('Y-m-d H:i:s'),
    'domain' => 'skilltracer.art-artel.su',
    'overall_status' => $allPassed ? 'READY_FOR_LAUNCH' : 'NEEDS_FIX',
    'ready' => $allPassed,
    'tests' => $tests
];

if ($allPassed) {
    $response['next_steps'] = [
        '1. Установите webhook: https://skilltracer.art-artel.su/setup_webhook.php',
        '2. Проверьте webhook: https://skilltracer.art-artel.su/check_webhook.php',
        '3. Настройте Cron в ISPmanager (команда в INSTRUCTION_CRON.md)',
        '4. Отправьте боту /start для теста',
        '5. Проверьте logs/cron.log через 1 минуту'
    ];
    $response['message'] = '🎉 System is ready for launch!';
} else {
    $response['message'] = '❌ Please fix the errors above before launching';
    $response['recommendations'] = [];
    
    if ($tests['database']['status'] === 'FAIL') {
        $response['recommendations'][] = 'Check database credentials in config/database.php';
    }
    if ($tests['tables']['status'] === 'FAIL') {
        $response['recommendations'][] = 'Import database.sql via phpMyAdmin';
    }
    if ($tests['permissions']['status'] === 'FAIL') {
        $response['recommendations'][] = 'Fix permissions: chmod 777 logs/';
    }
    if ($tests['bot_token']['status'] === 'FAIL') {
        $response['recommendations'][] = 'Set BOT_TOKEN in config files';
    }
}

echo json_encode($response, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);

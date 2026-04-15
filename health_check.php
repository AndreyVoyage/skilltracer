<?php
/**
 * Skill Tracer - Health Check
 * 
 * Быстрая проверка здоровья системы (для мониторинга)
 * URL: https://skilltracer.art-artel.su/health_check.php
 */

header('Content-Type: application/json; charset=utf-8');

$checks = [
    'database' => false,
    'tables' => false,
    'webhook' => false,
    'cron_running' => false,
    'timestamp' => time()
];

try {
    require 'config/database.php';
    $pdo = new PDO("mysql:host=" . DB_HOST . ";dbname=" . DB_NAME, DB_USER, DB_PASS, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION
    ]);
    
    $checks['database'] = true;
    
    // Проверка таблиц
    $stmt = $pdo->query("SHOW TABLES LIKE 'users'");
    $checks['tables'] = $stmt->rowCount() > 0;
    
    // Проверка что cron работает (есть свежие записи за последние 10 минут)
    $stmt = $pdo->query("SELECT COUNT(*) FROM telegram_updates WHERE created_at > DATE_SUB(NOW(), INTERVAL 10 MINUTE)");
    $recent = $stmt->fetchColumn();
    $checks['recent_updates'] = (int)$recent;
    
    // Проверка очереди
    $stmt = $pdo->query("SELECT COUNT(*) FROM telegram_updates WHERE processed = 0");
    $pending = $stmt->fetchColumn();
    $checks['pending_updates'] = (int)$pending;
    
    // Cron считается работающим если были обновления за последние 10 минут или очередь пустая
    $checks['cron_running'] = $recent > 0 || $pending === 0;
    
} catch (Exception $e) {
    $checks['error'] = $e->getMessage();
}

// Проверка файлов
$checks['files'] = [
    'webhook' => file_exists(__DIR__ . '/webhook.php'),
    'processor' => file_exists(__DIR__ . '/backend/cron/process_updates.php'),
    'logs_writable' => is_writable(__DIR__ . '/logs/')
];

// Определяем статус
$isHealthy = $checks['database'] && 
             $checks['tables'] && 
             $checks['files']['webhook'] && 
             $checks['files']['logs_writable'];

// HTTP статус код
http_response_code($isHealthy ? 200 : 503);

echo json_encode([
    'status' => $isHealthy ? 'healthy' : 'unhealthy',
    'healthy' => $isHealthy,
    'checks' => $checks,
    'timestamp' => date('Y-m-d H:i:s')
], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);

<?php
/**
 * Telegram Bot Webhook Receiver
 * 
 * Принимает обновления от Telegram Bot API
 * Сохраняет в очередь (таблица telegram_updates)
 * Мгновенно отвечает OK (200) чтобы Telegram не повторял
 * 
 * URL: https://skilltracer.art-artel.su/webhook.php
 */

require_once __DIR__ . '/config/database.php';

// Настройки
$LOG_FILE = __DIR__ . '/logs/webhook.log';
$botToken = '7973502371:AAGZ1A5XeWdKaiMKZDumfTa9gCr0I3a8EMg';
$ALLOWED_IP_RANGES = [
    '149.154.160.0/20',
    '91.108.4.0/22',
];

/**
 * Проверка IP адреса
 */
function isAllowedIP(string $ip): bool {
    global $ALLOWED_IP_RANGES;
    
    foreach ($ALLOWED_IP_RANGES as $range) {
        if (ipInRange($ip, $range)) {
            return true;
        }
    }
    return false;
}

function ipInRange(string $ip, string $range): bool {
    list($subnet, $bits) = explode('/', $range);
    $ip = ip2long($ip);
    $subnet = ip2long($subnet);
    $mask = -1 << (32 - $bits);
    $subnet &= $mask;
    return ($ip & $mask) == $subnet;
}

/**
 * Логирование
 */
function logMessage(string $message): void {
    global $LOG_FILE;
    $timestamp = date('Y-m-d H:i:s');
    file_put_contents($LOG_FILE, "[$timestamp] $message\n", FILE_APPEND | LOCK_EX);
}

/**
 * Main
 */
header('Content-Type: application/json');

// Проверка IP
$clientIP = $_SERVER['REMOTE_ADDR'] ?? 'unknown';
if (!isAllowedIP($clientIP)) {
    http_response_code(403);
    logMessage("Forbidden IP: $clientIP");
    echo json_encode(['ok' => false, 'error' => 'Forbidden']);
    exit;
}

// Получаем raw POST data
$rawData = file_get_contents('php://input');
if (empty($rawData)) {
    http_response_code(400);
    logMessage("Empty request body");
    echo json_encode(['ok' => false, 'error' => 'Empty body']);
    exit;
}

// Парсим JSON
$update = json_decode($rawData, true);
if (!$update) {
    http_response_code(400);
    logMessage("Invalid JSON: " . json_last_error_msg());
    echo json_encode(['ok' => false, 'error' => 'Invalid JSON']);
    exit;
}

// Проверяем что это update от Telegram
if (!isset($update['update_id'])) {
    http_response_code(400);
    logMessage("Invalid update format");
    echo json_encode(['ok' => false, 'error' => 'Invalid format']);
    exit;
}

try {
    $db = getDB();
    
    // Сохраняем в очередь
    $stmt = $db->prepare("
        INSERT INTO telegram_updates (update_data, processed, created_at)
        VALUES (:update_data, 0, NOW())
    ");
    $stmt->execute([':update_data' => $rawData]);
    
    $updateId = $update['update_id'] ?? 'unknown';
    logMessage("Queued update_id: $updateId");
    
    // Мгновенно отвечаем OK (важно для Telegram!)
    http_response_code(200);
    echo json_encode(['ok' => true]);
    
} catch (Exception $e) {
    logMessage("Error: " . $e->getMessage());
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => 'Internal error']);
}

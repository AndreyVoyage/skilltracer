<?php
/**
 * Skill Tracer - Webhook Status Check
 * 
 * Проверяет статус webhook у Telegram
 * URL: https://skilltracer.art-artel.su/check_webhook.php
 */

require_once 'config/database.php';

header('Content-Type: application/json; charset=utf-8');

// Bot token из конфига
$botToken = defined('BOT_TOKEN') ? BOT_TOKEN : null;

if (!$botToken || $botToken === 'YOUR_BOT_TOKEN_HERE' || strlen($botToken) < 20) {
    echo json_encode([
        'status' => 'ERROR',
        'message' => 'Bot token not configured',
        'hint' => 'Check BOT_TOKEN in config files'
    ], JSON_PRETTY_PRINT);
    exit;
}

$apiUrl = "https://api.telegram.org/bot$botToken/getWebhookInfo";

// Используем cURL
$ch = curl_init($apiUrl);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_TIMEOUT, 10);
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, true);

$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$error = curl_error($ch);
curl_close($ch);

$result = [
    'timestamp' => date('Y-m-d H:i:s'),
    'domain' => 'skilltracer.art-artel.su',
    'http_code' => $httpCode,
    'webhook_installed' => false,
    'webhook_url' => null,
    'pending_updates' => 0,
    'max_connections' => 0,
    'last_error' => null,
    'last_error_date' => null,
    'allowed_updates' => null,
    'recommendations' => []
];

if ($error) {
    $result['curl_error'] = $error;
    $result['status'] = 'CONNECTION_ERROR';
    echo json_encode($result, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
    exit;
}

if ($httpCode !== 200) {
    $result['status'] = 'API_ERROR';
    $result['message'] = "Telegram API returned HTTP $httpCode";
    echo json_encode($result, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
    exit;
}

$data = json_decode($response, true);

if (!$data || !isset($data['ok'])) {
    $result['status'] = 'INVALID_RESPONSE';
    $result['raw_response'] = substr($response, 0, 500);
    echo json_encode($result, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
    exit;
}

if (!$data['ok']) {
    $result['status'] = 'TELEGRAM_ERROR';
    $result['error_code'] = $data['error_code'] ?? null;
    $result['description'] = $data['description'] ?? 'Unknown error';
    echo json_encode($result, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
    exit;
}

// Успешно получили информацию
$webhookInfo = $data['result'];

$result['webhook_installed'] = !empty($webhookInfo['url']);
$result['webhook_url'] = $webhookInfo['url'] ?? null;
$result['pending_updates'] = $webhookInfo['pending_update_count'] ?? 0;
$result['max_connections'] = $webhookInfo['max_connections'] ?? 40;
$result['last_error'] = $webhookInfo['last_error_message'] ?? null;
$result['last_error_date'] = $webhookInfo['last_error_date'] ?? null;
$result['allowed_updates'] = $webhookInfo['allowed_updates'] ?? ['message', 'callback_query'];

// Проверяем что URL совпадает с нашим доменом
if ($result['webhook_installed']) {
    if (strpos($result['webhook_url'], 'skilltracer.art-artel.su') !== false) {
        $result['status'] = 'OK';
        $result['url_match'] = true;
    } else {
        $result['status'] = 'WRONG_URL';
        $result['url_match'] = false;
        $result['recommendations'][] = 'Webhook points to different URL. Re-run setup_webhook.php';
    }
} else {
    $result['status'] = 'NOT_INSTALLED';
    $result['recommendations'][] = 'Webhook not installed. Open: https://skilltracer.art-artel.su/setup_webhook.php';
}

// Проверяем наличие ошибок
if ($result['last_error']) {
    $result['status'] = 'HAS_ERRORS';
    $result['recommendations'][] = 'Webhook has errors. Check last_error message.';
}

// Проверяем pending updates
if ($result['pending_updates'] > 10) {
    $result['recommendations'][] = "Many pending updates ({$result['pending_updates']}). Check cron is running.";
}

echo json_encode($result, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);

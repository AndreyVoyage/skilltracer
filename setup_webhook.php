<?php
/**
 * Setup Telegram Webhook
 * 
 * One-time script to set webhook URL.
 * Run once in browser: https://skilltracer.art-artel.su/setup_webhook.php
 */

header('Content-Type: application/json');

$botToken = '7973502371:AAGZ1A5XeWdKaiMKZDumfTa9gCr0I3a8EMg';
$webhookUrl = 'https://skilltracer.art-artel.su/webhook.php';

if ($botToken === 'YOUR_BOT_TOKEN_HERE') {
    http_response_code(500);
    echo json_encode([
        'ok' => false,
        'error' => 'Please set your BOT_TOKEN in this file first!'
    ]);
    exit;
}

// Telegram API endpoint
$apiUrl = "https://api.telegram.org/bot{$botToken}/setWebhook";

// Data
$data = [
    'url' => $webhookUrl,
    'allowed_updates' => json_encode(['message', 'callback_query', 'inline_query']),
    'max_connections' => 40,
];

// Send request
$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $apiUrl);
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, http_build_query($data));
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($response === false) {
    echo json_encode([
        'ok' => false,
        'error' => 'Failed to connect to Telegram API'
    ]);
    exit;
}

$result = json_decode($response, true);

echo json_encode([
    'ok' => $result['ok'] ?? false,
    'result' => $result['result'] ?? null,
    'description' => $result['description'] ?? null,
    'webhook_url' => $webhookUrl,
]);

// Log
$logFile = __DIR__ . '/logs/setup_webhook.log';
$timestamp = date('Y-m-d H:i:s');
file_put_contents($logFile, "[$timestamp] Webhook setup: $response\n", FILE_APPEND);

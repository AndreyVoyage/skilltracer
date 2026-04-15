<?php
/**
 * API: Current User
 * 
 * GET /api/me.php
 * Returns current user data, trackers, and current week status
 */

require_once __DIR__ . '/../config/database.php';

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: https://skilltracer.art-artel.su');
header('Access-Control-Allow-Headers: X-Init-Data, Content-Type');

/**
 * Validate Telegram initData
 */
function validateInitData(string $initData, string $botToken): ?array {
    // Parse query string
    parse_str($initData, $data);
    
    if (!isset($data['hash'])) {
        return null;
    }
    
    $receivedHash = $data['hash'];
    unset($data['hash']);
    
    // Check auth_date (not older than 5 minutes)
    if (!isset($data['auth_date'])) {
        return null;
    }
    
    $authDate = (int)$data['auth_date'];
    if (time() - $authDate > 300) { // 5 minutes
        return null;
    }
    
    // Build data_check_string
    $pairs = [];
    foreach ($data as $key => $value) {
        $pairs[] = "$key=$value";
    }
    sort($pairs);
    $dataCheckString = implode("\n", $pairs);
    
    // Calculate HMAC-SHA256
    $secretKey = hash_hmac('sha256', $botToken, 'WebAppData', true);
    $computedHash = hash_hmac('sha256', $dataCheckString, $secretKey);
    
    if (!hash_equals($computedHash, $receivedHash)) {
        return null;
    }
    
    // Parse user JSON
    if (!isset($data['user'])) {
        return null;
    }
    
    return json_decode($data['user'], true);
}

/**
 * Get or create user
 */
function getOrCreateUser(PDO $db, array $tgUser): array {
    $userId = $tgUser['id'];
    $username = $tgUser['username'] ?? null;
    $firstName = $tgUser['first_name'] ?? null;
    $lastName = $tgUser['last_name'] ?? null;
    $photoUrl = $tgUser['photo_url'] ?? null;
    
    // Check if exists
    $stmt = $db->prepare("SELECT * FROM users WHERE id = ?");
    $stmt->execute([$userId]);
    $user = $stmt->fetch();
    
    if ($user) {
        // Update
        $stmt = $db->prepare("
            UPDATE users 
            SET username = ?, first_name = ?, last_name = ?, photo_url = ?
            WHERE id = ?
        ");
        $stmt->execute([$username, $firstName, $lastName, $photoUrl, $userId]);
    } else {
        // Create
        $stmt = $db->prepare("
            INSERT INTO users (id, username, first_name, last_name, photo_url)
            VALUES (?, ?, ?, ?, ?)
        ");
        $stmt->execute([$userId, $username, $firstName, $lastName, $photoUrl]);
    }
    
    return [
        'id' => $userId,
        'username' => $username,
        'first_name' => $firstName,
        'last_name' => $lastName,
        'photo_url' => $photoUrl,
    ];
}

/**
 * Get user trackers
 */
function getUserTrackers(PDO $db, int $userId): array {
    $stmt = $db->prepare("
        SELECT id, name, icon, target_value, sort_order
        FROM custom_trackers
        WHERE user_id = ? AND is_active = 1
        ORDER BY sort_order
    ");
    $stmt->execute([$userId]);
    return $stmt->fetchAll();
}

/**
 * Get current week status
 */
function getCurrentWeek(PDO $db, int $userId): array {
    $today = date('Y-m-d');
    $monday = date('Y-m-d', strtotime('monday this week'));
    $sunday = date('Y-m-d', strtotime('sunday this week'));
    
    // Check existing report
    $stmt = $db->prepare("
        SELECT * FROM week_reports 
        WHERE user_id = ? AND week_start_date = ?
    ");
    $stmt->execute([$userId, $monday]);
    $report = $stmt->fetch();
    
    // Count filled days
    $stmt = $db->prepare("
        SELECT COUNT(*), AVG(mood)
        FROM daily_entries
        WHERE user_id = ? AND entry_date BETWEEN ? AND ?
    ");
    $stmt->execute([$userId, $monday, $sunday]);
    $stats = $stmt->fetch();
    
    if ($report) {
        return [
            'week_start' => $monday,
            'week_end' => $sunday,
            'status' => $report['status'],
            'filled_days' => (int)$report['filled_days'],
            'avg_mood' => $report['avg_mood'] ? (float)$report['avg_mood'] : null,
            'published_at' => $report['published_at'],
        ];
    } else {
        return [
            'week_start' => $monday,
            'week_end' => $sunday,
            'status' => 'draft',
            'filled_days' => (int)$stats['COUNT(*)'],
            'avg_mood' => $stats['AVG(mood)'] ? round((float)$stats['AVG(mood)'], 2) : null,
            'published_at' => null,
        ];
    }
}

// Main
$botToken = '7973502371:AAGZ1A5XeWdKaiMKZDumfTa9gCr0I3a8EMg';

$initData = $_SERVER['HTTP_X_INIT_DATA'] ?? '';

if (empty($initData)) {
    http_response_code(401);
    echo json_encode(['error' => 'Missing init data']);
    exit;
}

$userData = validateInitData($initData, $botToken);

if (!$userData) {
    http_response_code(401);
    echo json_encode(['error' => 'Invalid init data']);
    exit;
}

try {
    $db = getDB();
    
    $user = getOrCreateUser($db, $userData);
    $trackers = getUserTrackers($db, $user['id']);
    $week = getCurrentWeek($db, $user['id']);
    
    echo json_encode([
        'user' => $user,
        'trackers' => $trackers,
        'current_week' => $week,
    ]);
    
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['error' => 'Database error']);
}

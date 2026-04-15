<?php
/**
 * API: Week Reports
 * 
 * GET    /current - Current week status
 * POST   /publish?week_start=YYYY-MM-DD - Publish week
 * GET    /analytics?week_start=YYYY-MM-DD - Analytics data
 */

require_once __DIR__ . '/../config/database.php';

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: https://skilltracer.art-artel.su');
header('Access-Control-Allow-Headers: X-Init-Data, Content-Type');

$botToken = '7973502371:AAGZ1A5XeWdKaiMKZDumfTa9gCr0I3a8EMg';
$initData = $_SERVER['HTTP_X_INIT_DATA'] ?? '';

if (empty($initData)) {
    http_response_code(401);
    echo json_encode(['error' => 'Missing init data']);
    exit;
}

parse_str($initData, $data);
$userData = json_decode($data['user'] ?? '{}', true);
$userId = $userData['id'] ?? null;

if (!$userId) {
    http_response_code(401);
    echo json_encode(['error' => 'Invalid user']);
    exit;
}

// Ensure user exists
try {
    $db = getDB();
    $stmt = $db->prepare("SELECT id FROM users WHERE id = ?");
    $stmt->execute([$userId]);
    if (!$stmt->fetch()) {
        $stmt = $db->prepare("
            INSERT INTO users (id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        ");
        $stmt->execute([
            $userId,
            $userData['username'] ?? null,
            $userData['first_name'] ?? null,
            $userData['last_name'] ?? null,
        ]);
    }
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['error' => 'Database error']);
    exit;
}

$action = $_GET['action'] ?? '';
$method = $_SERVER['REQUEST_METHOD'];

try {
    $db = getDB();
    
    if ($method === 'GET' && $action === 'current') {
        // Get current week
        $monday = date('Y-m-d', strtotime('monday this week'));
        $sunday = date('Y-m-d', strtotime('sunday this week'));
        
        $stmt = $db->prepare("
            SELECT * FROM week_reports 
            WHERE user_id = ? AND week_start_date = ?
        ");
        $stmt->execute([$userId, $monday]);
        $report = $stmt->fetch();
        
        // Count filled days
        $stmt = $db->prepare("
            SELECT COUNT(*), AVG(mood) FROM daily_entries
            WHERE user_id = ? AND entry_date BETWEEN ? AND ?
        ");
        $stmt->execute([$userId, $monday, $sunday]);
        $stats = $stmt->fetch();
        
        echo json_encode([
            'week_start' => $monday,
            'week_end' => $sunday,
            'status' => $report['status'] ?? 'draft',
            'filled_days' => (int)($report['filled_days'] ?? $stats['COUNT(*)']),
            'avg_mood' => $report['avg_mood'] ?? ($stats['AVG(mood)'] ? round((float)$stats['AVG(mood)'], 2) : null),
            'published_at' => $report['published_at'] ?? null,
        ]);
        
    } elseif ($method === 'POST' && $action === 'publish') {
        // Publish week
        $weekStart = $_GET['week_start'] ?? date('Y-m-d', strtotime('monday this week'));
        $monday = $weekStart;
        $sunday = date('Y-m-d', strtotime($monday . ' +6 days'));
        
        // Check minimum 3 days
        $stmt = $db->prepare("
            SELECT COUNT(*) FROM daily_entries
            WHERE user_id = ? AND entry_date BETWEEN ? AND ?
        ");
        $stmt->execute([$userId, $monday, $sunday]);
        $count = $stmt->fetchColumn();
        
        if ($count < 3) {
            http_response_code(400);
            echo json_encode(['error' => 'Need at least 3 days to publish']);
            exit;
        }
        
        // Calculate stats
        $stmt = $db->prepare("
            SELECT AVG(mood) FROM daily_entries
            WHERE user_id = ? AND entry_date BETWEEN ? AND ? AND mood IS NOT NULL
        ");
        $stmt->execute([$userId, $monday, $sunday]);
        $avgMood = $stmt->fetchColumn();
        
        // Calculate tracker averages
        $stmt = $db->prepare("
            SELECT ct.name, AVG(em.value) as avg_value
            FROM entry_metrics em
            JOIN daily_entries de ON em.entry_id = de.id
            JOIN custom_trackers ct ON em.tracker_id = ct.id
            WHERE de.user_id = ? AND de.entry_date BETWEEN ? AND ?
            GROUP BY ct.name
        ");
        $stmt->execute([$userId, $monday, $sunday]);
        $trackers = $stmt->fetchAll();
        
        $metricsSummary = [];
        foreach ($trackers as $t) {
            $metricsSummary[$t['name']] = round((float)$t['avg_value'], 2);
        }
        
        // Insert or update report
        $stmt = $db->prepare("
            INSERT INTO week_reports (user_id, week_start_date, week_end_date, status, 
                avg_mood, filled_days, metrics_summary, published_at)
            VALUES (?, ?, ?, 'published', ?, ?, ?, NOW())
            ON DUPLICATE KEY UPDATE
                status = 'published',
                avg_mood = ?,
                filled_days = ?,
                metrics_summary = ?,
                published_at = NOW()
        ");
        $stmt->execute([
            $userId, $monday, $sunday,
            $avgMood ? round((float)$avgMood, 2) : null,
            $count,
            json_encode($metricsSummary),
            $avgMood ? round((float)$avgMood, 2) : null,
            $count,
            json_encode($metricsSummary),
        ]);
        
        echo json_encode([
            'status' => 'published',
            'week_start' => $monday,
            'week_end' => $sunday,
            'filled_days' => $count,
            'avg_mood' => $avgMood ? round((float)$avgMood, 2) : null,
            'metrics_summary' => $metricsSummary,
        ]);
        
    } elseif ($method === 'GET' && $action === 'analytics') {
        // Get analytics for charts
        $weekStart = $_GET['week_start'] ?? date('Y-m-d', strtotime('monday this week'));
        $monday = $weekStart;
        $sunday = date('Y-m-d', strtotime($monday . ' +6 days'));
        
        // Mood by day
        $moodByDay = [];
        for ($i = 0; $i < 7; $i++) {
            $date = date('Y-m-d', strtotime($monday . " +$i days"));
            $stmt = $db->prepare("SELECT mood FROM daily_entries WHERE user_id = ? AND entry_date = ?");
            $stmt->execute([$userId, $date]);
            $row = $stmt->fetch();
            $moodByDay[] = [
                'date' => $date,
                'mood' => $row ? (int)$row['mood'] : null,
            ];
        }
        
        // Tracker averages
        $stmt = $db->prepare("
            SELECT ct.name, ct.target_value, AVG(em.value) as avg_value
            FROM entry_metrics em
            JOIN daily_entries de ON em.entry_id = de.id
            JOIN custom_trackers ct ON em.tracker_id = ct.id
            WHERE de.user_id = ? AND de.entry_date BETWEEN ? AND ?
            GROUP BY ct.id
        ");
        $stmt->execute([$userId, $monday, $sunday]);
        $trackerAvgs = $stmt->fetchAll();
        
        $trackerAverages = [];
        foreach ($trackerAvgs as $t) {
            $trackerAverages[] = [
                'name' => $t['name'],
                'avg' => round((float)$t['avg_value'], 2),
                'target' => $t['target_value'] ? (int)$t['target_value'] : null,
            ];
        }
        
        // Stats
        $stmt = $db->prepare("
            SELECT AVG(mood), MAX(mood), COUNT(*)
            FROM daily_entries
            WHERE user_id = ? AND entry_date BETWEEN ? AND ?
        ");
        $stmt->execute([$userId, $monday, $sunday]);
        $stats = $stmt->fetch();
        
        echo json_encode([
            'mood_by_day' => $moodByDay,
            'tracker_averages' => $trackerAverages,
            'stats' => [
                'avg_mood' => $stats['AVG(mood)'] ? round((float)$stats['AVG(mood)'], 2) : null,
                'best_day' => $stats['MAX(mood)'],
                'total_days' => (int)$stats['COUNT(*)'],
            ],
        ]);
        
    } else {
        http_response_code(400);
        echo json_encode(['error' => 'Invalid action']);
    }
    
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['error' => 'Database error: ' . $e->getMessage()]);
}

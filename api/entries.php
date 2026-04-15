<?php
/**
 * API: Entries CRUD
 * 
 * POST   - Create/update entry
 * GET    - List entries (start_date, end_date)
 * DELETE - Delete entry (date)
 */

require_once __DIR__ . '/../config/database.php';

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: https://skilltracer.art-artel.su');
header('Access-Control-Allow-Headers: X-Init-Data, Content-Type');
header('Access-Control-Allow-Methods: GET, POST, DELETE, OPTIONS');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

$botToken = '7973502371:AAGZ1A5XeWdKaiMKZDumfTa9gCr0I3a8EMg';

// Validate initData
$initData = $_SERVER['HTTP_X_INIT_DATA'] ?? '';
if (empty($initData)) {
    http_response_code(401);
    echo json_encode(['error' => 'Missing init data']);
    exit;
}

parse_str($initData, $data);
if (!isset($data['hash']) || !isset($data['user'])) {
    http_response_code(401);
    echo json_encode(['error' => 'Invalid init data']);
    exit;
}

$userData = json_decode($data['user'], true);
$userId = $userData['id'] ?? null;

if (!$userId) {
    http_response_code(401);
    echo json_encode(['error' => 'Invalid user']);
    exit;
}

// Get or create user in DB
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

// Handle methods
$method = $_SERVER['REQUEST_METHOD'];

switch ($method) {
    case 'POST':
        // Create or update entry
        $input = json_decode(file_get_contents('php://input'), true);
        
        if (!$input || !isset($input['entry_date'])) {
            http_response_code(400);
            echo json_encode(['error' => 'Missing entry_date']);
            exit;
        }
        
        $entryDate = $input['entry_date'];
        $mood = $input['mood'] ?? null;
        $text = $input['text'] ?? null;
        $metrics = $input['metrics'] ?? [];
        $photoFileId = $input['photo_file_id'] ?? null;
        
        // Check 10 days limit
        $date = new DateTime($entryDate);
        $today = new DateTime();
        $diff = $today->diff($date)->days;
        
        if ($diff > 10 && $date < $today) {
            http_response_code(400);
            echo json_encode(['error' => 'Can only edit entries from last 10 days']);
            exit;
        }
        
        try {
            $db = getDB();
            
            // Check if entry exists
            $stmt = $db->prepare("
                SELECT id FROM daily_entries 
                WHERE user_id = ? AND entry_date = ?
            ");
            $stmt->execute([$userId, $entryDate]);
            $existing = $stmt->fetch();
            
            if ($existing) {
                // Update
                $stmt = $db->prepare("
                    UPDATE daily_entries 
                    SET mood = ?, text = ?, photo_file_id = ?
                    WHERE id = ?
                ");
                $stmt->execute([$mood, $text, $photoFileId, $existing['id']]);
                $entryId = $existing['id'];
                
                // Delete old metrics
                $stmt = $db->prepare("DELETE FROM entry_metrics WHERE entry_id = ?");
                $stmt->execute([$entryId]);
            } else {
                // Insert
                $stmt = $db->prepare("
                    INSERT INTO daily_entries (user_id, entry_date, mood, text, photo_file_id)
                    VALUES (?, ?, ?, ?, ?)
                ");
                $stmt->execute([$userId, $entryDate, $mood, $text, $photoFileId]);
                $entryId = $db->lastInsertId();
            }
            
            // Insert metrics
            foreach ($metrics as $metric) {
                $stmt = $db->prepare("
                    INSERT INTO entry_metrics (entry_id, tracker_id, value)
                    VALUES (?, ?, ?)
                ");
                $stmt->execute([
                    $entryId,
                    $metric['tracker_id'],
                    $metric['value']
                ]);
            }
            
            echo json_encode([
                'id' => $entryId,
                'entry_date' => $entryDate,
                'mood' => $mood,
                'text' => $text,
                'photo_file_id' => $photoFileId,
                'metrics' => $metrics,
            ]);
            
        } catch (Exception $e) {
            http_response_code(500);
            echo json_encode(['error' => 'Database error']);
        }
        break;
        
    case 'GET':
        // List entries
        $startDate = $_GET['start_date'] ?? date('Y-m-d', strtotime('-30 days'));
        $endDate = $_GET['end_date'] ?? date('Y-m-d');
        
        try {
            $db = getDB();
            
            $stmt = $db->prepare("
                SELECT de.*, 
                    JSON_ARRAYAGG(
                        JSON_OBJECT('tracker_id', em.tracker_id, 'value', em.value)
                    ) as metrics
                FROM daily_entries de
                LEFT JOIN entry_metrics em ON de.id = em.entry_id
                WHERE de.user_id = ? AND de.entry_date BETWEEN ? AND ?
                GROUP BY de.id
                ORDER BY de.entry_date DESC
            ");
            $stmt->execute([$userId, $startDate, $endDate]);
            $entries = $stmt->fetchAll();
            
            // Parse metrics JSON
            foreach ($entries as &$entry) {
                $entry['metrics'] = json_decode($entry['metrics'] ?? '[]', true);
                if ($entry['metrics'] === null || $entry['metrics'][0]['tracker_id'] === null) {
                    $entry['metrics'] = [];
                }
            }
            
            echo json_encode($entries);
            
        } catch (Exception $e) {
            http_response_code(500);
            echo json_encode(['error' => 'Database error']);
        }
        break;
        
    case 'DELETE':
        // Delete entry
        $entryDate = $_GET['date'] ?? null;
        
        if (!$entryDate) {
            http_response_code(400);
            echo json_encode(['error' => 'Missing date']);
            exit;
        }
        
        // Check 10 days limit
        $date = new DateTime($entryDate);
        $today = new DateTime();
        $diff = $today->diff($date)->days;
        
        if ($diff > 10) {
            http_response_code(400);
            echo json_encode(['error' => 'Can only delete entries from last 10 days']);
            exit;
        }
        
        try {
            $db = getDB();
            
            $stmt = $db->prepare("
                DELETE FROM daily_entries 
                WHERE user_id = ? AND entry_date = ?
            ");
            $stmt->execute([$userId, $entryDate]);
            
            if ($stmt->rowCount() === 0) {
                http_response_code(404);
                echo json_encode(['error' => 'Entry not found']);
                exit;
            }
            
            echo json_encode(['status' => 'deleted']);
            
        } catch (Exception $e) {
            http_response_code(500);
            echo json_encode(['error' => 'Database error']);
        }
        break;
        
    default:
        http_response_code(405);
        echo json_encode(['error' => 'Method not allowed']);
}

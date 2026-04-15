<?php
/**
 * API: Groups
 * 
 * POST /create - Create group
 * POST /join - Join by code
 * GET  /feed - Group feed (published reports only!)
 * GET  /my - My group info
 */

require_once __DIR__ . '/../config/database.php';

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: https://skilltracer.art-artel.su');
header('Access-Control-Allow-Headers: X-Init-Data, Content-Type');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

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

$method = $_SERVER['REQUEST_METHOD'];
$action = $_GET['action'] ?? '';

try {
    $db = getDB();
    
    // Ensure user exists
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
    
    if ($method === 'POST' && $action === 'create') {
        // Check if already in group
        $stmt = $db->prepare("SELECT group_id FROM group_members WHERE user_id = ?");
        $stmt->execute([$userId]);
        if ($stmt->fetch()) {
            http_response_code(400);
            echo json_encode(['error' => 'Already in a group']);
            exit;
        }
        
        $input = json_decode(file_get_contents('php://input'), true);
        $name = $input['name'] ?? 'My Group';
        $description = $input['description'] ?? null;
        
        // Generate invite code
        $code = strtoupper(substr(str_shuffle('ABCDEFGHJKMNPQRSTUVWXYZ23456789'), 0, 8));
        
        // Create group
        $stmt = $db->prepare("
            INSERT INTO groups (name, invite_code, owner_id, description)
            VALUES (?, ?, ?, ?)
        ");
        $stmt->execute([$name, $code, $userId, $description]);
        $groupId = $db->lastInsertId();
        
        // Add owner as member
        $stmt = $db->prepare("
            INSERT INTO group_members (group_id, user_id, role)
            VALUES (?, ?, 'owner')
        ");
        $stmt->execute([$groupId, $userId]);
        
        echo json_encode([
            'id' => $groupId,
            'name' => $name,
            'invite_code' => $code,
            'member_count' => 1,
        ]);
        
    } elseif ($method === 'POST' && $action === 'join') {
        $input = json_decode(file_get_contents('php://input'), true);
        $code = strtoupper($input['invite_code'] ?? '');
        
        // Check if already in group
        $stmt = $db->prepare("SELECT group_id FROM group_members WHERE user_id = ?");
        $stmt->execute([$userId]);
        if ($stmt->fetch()) {
            http_response_code(400);
            echo json_encode(['error' => 'Already in a group']);
            exit;
        }
        
        // Find group
        $stmt = $db->prepare("SELECT id FROM groups WHERE invite_code = ?");
        $stmt->execute([$code]);
        $group = $stmt->fetch();
        
        if (!$group) {
            http_response_code(404);
            echo json_encode(['error' => 'Group not found']);
            exit;
        }
        
        $groupId = $group['id'];
        
        // Check member limit (max 3)
        $stmt = $db->prepare("SELECT COUNT(*) FROM group_members WHERE group_id = ?");
        $stmt->execute([$groupId]);
        $count = $stmt->fetchColumn();
        
        if ($count >= 3) {
            http_response_code(400);
            echo json_encode(['error' => 'Group is full (max 3 members)']);
            exit;
        }
        
        // Add member
        $stmt = $db->prepare("
            INSERT INTO group_members (group_id, user_id, role)
            VALUES (?, ?, 'member')
        ");
        $stmt->execute([$groupId, $userId]);
        
        echo json_encode(['status' => 'joined', 'group_id' => $groupId]);
        
    } elseif ($method === 'GET' && $action === 'my') {
        // Get my group
        $stmt = $db->prepare("
            SELECT g.*, COUNT(gm.user_id) as member_count
            FROM groups g
            JOIN group_members gm ON g.id = gm.group_id
            WHERE g.id IN (SELECT group_id FROM group_members WHERE user_id = ?)
            GROUP BY g.id
        ");
        $stmt->execute([$userId]);
        $group = $stmt->fetch();
        
        if (!$group) {
            http_response_code(404);
            echo json_encode(['error' => 'Not in a group']);
            exit;
        }
        
        echo json_encode([
            'id' => $group['id'],
            'name' => $group['name'],
            'invite_code' => $group['invite_code'],
            'description' => $group['description'],
            'member_count' => (int)$group['member_count'],
        ]);
        
    } elseif ($method === 'GET' && $action === 'feed') {
        // Get feed (published reports only!)
        $limit = min((int)($_GET['limit'] ?? 10), 50);
        $offset = (int)($_GET['offset'] ?? 0);
        
        // Find user's group
        $stmt = $db->prepare("SELECT group_id FROM group_members WHERE user_id = ?");
        $stmt->execute([$userId]);
        $membership = $stmt->fetch();
        
        if (!$membership) {
            http_response_code(404);
            echo json_encode(['error' => 'Not in a group']);
            exit;
        }
        
        $groupId = $membership['group_id'];
        
        // Get group member IDs (exclude self)
        $stmt = $db->prepare("
            SELECT user_id FROM group_members 
            WHERE group_id = ? AND user_id != ?
        ");
        $stmt->execute([$groupId, $userId]);
        $memberIds = $stmt->fetchAll(PDO::FETCH_COLUMN);
        
        if (empty($memberIds)) {
            echo json_encode([]);
            exit;
        }
        
        // Get published reports from group members
        $placeholders = implode(',', array_fill(0, count($memberIds), '?'));
        $sql = "
            SELECT wr.*, u.id as user_id, u.first_name, u.photo_url
            FROM week_reports wr
            JOIN users u ON wr.user_id = u.id
            WHERE wr.user_id IN ($placeholders)
            AND wr.status = 'published'
            ORDER BY wr.published_at DESC
            LIMIT ? OFFSET ?
        ";
        
        $params = array_merge($memberIds, [$limit, $offset]);
        $stmt = $db->prepare($sql);
        $stmt->execute($params);
        $reports = $stmt->fetchAll();
        
        $result = [];
        foreach ($reports as $r) {
            $result[] = [
                'id' => $r['id'],
                'user' => [
                    'id' => $r['user_id'],
                    'first_name' => $r['first_name'],
                    'photo_url' => $r['photo_url'],
                ],
                'week_start' => $r['week_start_date'],
                'week_end' => $r['week_end_date'],
                'avg_mood' => $r['avg_mood'] ? (float)$r['avg_mood'] : null,
                'filled_days' => (int)$r['filled_days'],
                'metrics_summary' => json_decode($r['metrics_summary'] ?? '{}', true),
                'published_at' => $r['published_at'],
            ];
        }
        
        echo json_encode($result);
        
    } else {
        http_response_code(400);
        echo json_encode(['error' => 'Invalid action']);
    }
    
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['error' => 'Database error: ' . $e->getMessage()]);
}

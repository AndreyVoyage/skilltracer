<?php
/**
 * Database Configuration for PHP
 * 
 * Shared Hosting - Reg.ru
 * Database: 'u1893136_skilltracer.art-artel.s
 */

define('DB_HOST', 'localhost');
define('DB_NAME', 'u1893136_skilltracer.art-artel.s');
define('DB_USER', 'u1893136_admin');
define('DB_PASS', 'SkillTracer2024');
define('DB_CHARSET', 'utf8mb4');

/**
 * Get PDO connection
 * 
 * @return PDO
 * @throws Exception
 */
function getDB(): PDO {
    static $pdo = null;
    
    if ($pdo === null) {
        try {
            $dsn = "mysql:host=" . DB_HOST . ";dbname=" . DB_NAME . ";charset=" . DB_CHARSET;
            $options = [
                PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                PDO::ATTR_EMULATE_PREPARES => false,
            ];
            $pdo = new PDO($dsn, DB_USER, DB_PASS, $options);
        } catch (PDOException $e) {
            error_log("Database connection failed: " . $e->getMessage());
            throw new Exception("Database connection failed");
        }
    }
    
    return $pdo;
}

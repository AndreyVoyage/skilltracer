<?php
/**
 * Skill Tracer - Structure Fix Script
 * 
 * Исправляет расположение файлов (перемещает из hosting/ в корень)
 * URL: https://skilltracer.art-artel.su/fix_structure.php
 */

header('Content-Type: text/plain; charset=utf-8');

$log = [];
$log[] = "=== Skill Tracer Structure Fix ===";
$log[] = "Time: " . date('Y-m-d H:i:s');
$log[] = "Current directory: " . getcwd();
$log[] = "";

// Проверяем, находимся ли мы в корне или в hosting/
$currentDir = getcwd();
$isInHosting = strpos($currentDir, 'hosting') !== false || basename($currentDir) === 'hosting';

if ($isInHosting) {
    $log[] = "⚠️  Скрипт запущен из папки hosting/";
    $log[] = "📁 Корневая директория: " . dirname($currentDir);
    $rootDir = dirname($currentDir);
} else {
    $log[] = "✅ Скрипт уже в корневой директории";
    $rootDir = $currentDir;
}

$log[] = "";

// Список файлов и папок, которые должны быть в корне
$requiredFiles = [
    'webhook.php',
    'test.php',
    'test_db.php',
    'setup_webhook.php',
    'database.sql',
    '.env',
    '.gitignore',
];

$requiredDirs = [
    'api',
    'backend',
    'backend/cron',
    'backend/config',
    'backend/bot',
    'config',
    'logs',
];

// Функция для копирования файла
define('DS', DIRECTORY_SEPARATOR);

function copyFile($source, $dest, &$log) {
    if (!file_exists($source)) {
        $log[] = "❌ Source not found: $source";
        return false;
    }
    
    $destDir = dirname($dest);
    if (!is_dir($destDir)) {
        @mkdir($destDir, 0755, true);
    }
    
    if (copy($source, $dest)) {
        $log[] = "✅ Copied: " . basename($source) . " -> " . str_replace(getcwd() . DS, '', $dest);
        return true;
    } else {
        $log[] = "❌ Failed to copy: $source";
        return false;
    }
}

function copyDir($source, $dest, &$log) {
    if (!is_dir($source)) {
        $log[] = "❌ Source dir not found: $source";
        return false;
    }
    
    @mkdir($dest, 0755, true);
    
    $iterator = new RecursiveIteratorIterator(
        new RecursiveDirectoryIterator($source, RecursiveDirectoryIterator::SKIP_DOTS),
        RecursiveIteratorIterator::SELF_FIRST
    );
    
    $copied = 0;
    foreach ($iterator as $item) {
        $targetPath = $dest . DS . $iterator->getSubPathName();
        if ($item->isDir()) {
            if (!is_dir($targetPath)) {
                @mkdir($targetPath, 0755, true);
            }
        } else {
            if (copy($item->getPathname(), $targetPath)) {
                $copied++;
            }
        }
    }
    
    $log[] = "✅ Copied directory: " . basename($source) . " ($copied files) -> " . str_replace(getcwd() . DS, '', $dest);
    return true;
}

// Определяем пути
if ($isInHosting) {
    $sourceDir = $currentDir;
    $targetDir = $rootDir;
} else {
    $sourceDir = $currentDir . DS . 'hosting';
    $targetDir = $currentDir;
}

$log[] = "Source: $sourceDir";
$log[] = "Target: $targetDir";
$log[] = "";

// 1. Создаем необходимые папки
$log[] = "=== Creating directories ===";
foreach ($requiredDirs as $dir) {
    $fullPath = $targetDir . DS . $dir;
    if (!is_dir($fullPath)) {
        if (@mkdir($fullPath, 0755, true)) {
            $log[] = "✅ Created: $dir";
        } else {
            $log[] = "❌ Failed to create: $dir";
        }
    } else {
        $log[] = "ℹ️  Already exists: $dir";
    }
}

// 2. Устанавливаем права на logs
$logsPath = $targetDir . DS . 'logs';
if (is_dir($logsPath)) {
    @chmod($logsPath, 0777);
    $log[] = "";
    $log[] = "=== Setting permissions ===";
    $log[] = "✅ Set 777 on logs/";
}

// 3. Копируем файлы
$log[] = "";
$log[] = "=== Copying files ===";

foreach ($requiredFiles as $file) {
    $source = $sourceDir . DS . $file;
    $dest = $targetDir . DS . $file;
    
    if (file_exists($source)) {
        copyFile($source, $dest, $log);
    } else {
        $log[] = "⚠️  Not found in source: $file";
    }
}

// 4. Копируем директории
$log[] = "";
$log[] = "=== Copying directories ===";

$dirsToCopy = ['api', 'backend', 'config'];
foreach ($dirsToCopy as $dir) {
    $source = $sourceDir . DS . $dir;
    $dest = $targetDir . DS . $dir;
    
    if (is_dir($source)) {
        copyDir($source, $dest, $log);
    } else {
        $log[] = "⚠️  Directory not found: $dir";
    }
}

// 5. Проверка результата
$log[] = "";
$log[] = "=== Verification ===";

$allOk = true;
foreach ($requiredFiles as $file) {
    $path = $targetDir . DS . $file;
    if (file_exists($path)) {
        $log[] = "✅ $file exists in root";
    } else {
        $log[] = "❌ $file NOT FOUND in root";
        $allOk = false;
    }
}

// Проверка директорий
foreach (['api', 'backend', 'config', 'logs'] as $dir) {
    $path = $targetDir . DS . $dir;
    if (is_dir($path)) {
        $perms = substr(sprintf('%o', fileperms($path)), -4);
        $log[] = "✅ $dir/ exists (perms: $perms)";
    } else {
        $log[] = "❌ $dir/ NOT FOUND";
        $allOk = false;
    }
}

$log[] = "";
$log[] = "=== Summary ===";

if ($allOk) {
    $log[] = "✅ SUCCESS! All files are in place.";
    $log[] = "";
    $log[] = "Next steps:";
    $log[] = "1. Open https://skilltracer.art-artel.su/test_db.php";
    $log[] = "2. Check that 'overall_status' is 'SUCCESS'";
    $log[] = "3. If OK - run https://skilltracer.art-artel.su/setup_webhook.php";
} else {
    $log[] = "⚠️  PARTIAL SUCCESS. Some files are missing.";
    $log[] = "Check the log above for details.";
}

// Выводим лог
echo implode("\n", $log);

// Сохраняем лог
@file_put_contents($targetDir . DS . 'logs' . DS . 'structure_fix.log', implode("\n", $log));

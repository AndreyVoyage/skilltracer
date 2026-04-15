-- ============================================================================
-- Skill Tracer Database Schema
-- For Reg.ru Shared Hosting (MySQL 8.0)
-- Database: u1893136_skilltracer
-- ============================================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------------------------------------------------------
-- Table: users
-- Telegram пользователи
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
    `id` BIGINT UNSIGNED NOT NULL COMMENT 'Telegram user ID',
    `username` VARCHAR(255) DEFAULT NULL COMMENT 'Telegram username',
    `first_name` VARCHAR(255) DEFAULT NULL COMMENT 'First name',
    `last_name` VARCHAR(255) DEFAULT NULL COMMENT 'Last name',
    `photo_url` TEXT DEFAULT NULL COMMENT 'Avatar URL',
    `timezone` VARCHAR(50) NOT NULL DEFAULT 'Europe/Moscow' COMMENT 'User timezone',
    `settings` JSON DEFAULT NULL COMMENT 'User settings JSON',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Telegram users';

-- ----------------------------------------------------------------------------
-- Table: custom_trackers
-- Пользовательские трекеры
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS `custom_trackers`;
CREATE TABLE `custom_trackers` (
    `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `user_id` BIGINT UNSIGNED NOT NULL COMMENT 'Owner user ID',
    `name` VARCHAR(100) NOT NULL COMMENT 'Tracker name (e.g. Sport)',
    `icon` VARCHAR(10) NOT NULL DEFAULT '📊' COMMENT 'Emoji icon',
    `target_value` INT UNSIGNED DEFAULT NULL COMMENT 'Target (e.g. 5 per week)',
    `is_active` TINYINT(1) NOT NULL DEFAULT 1 COMMENT 'Active flag',
    `sort_order` INT NOT NULL DEFAULT 0 COMMENT 'Display order',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY `idx_user_active` (`user_id`, `is_active`),
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- Table: daily_entries
-- Ежедневные записи (приватные)
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS `daily_entries`;
CREATE TABLE `daily_entries` (
    `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `user_id` BIGINT UNSIGNED NOT NULL,
    `entry_date` DATE NOT NULL COMMENT 'Entry date',
    `mood` TINYINT UNSIGNED DEFAULT NULL COMMENT 'Mood 1-5',
    `text` TEXT DEFAULT NULL COMMENT 'Private notes',
    `photo_file_id` VARCHAR(255) DEFAULT NULL COMMENT 'Telegram file_id',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `uniq_user_date` (`user_id`, `entry_date`),
    KEY `idx_user_date` (`user_id`, `entry_date`),
    KEY `idx_entry_date` (`entry_date`),
    CONSTRAINT `chk_mood_range` CHECK (`mood` IS NULL OR (`mood` >= 1 AND `mood` <= 5)),
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- Table: entry_metrics
-- Значения трекеров для дня
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS `entry_metrics`;
CREATE TABLE `entry_metrics` (
    `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `entry_id` INT UNSIGNED NOT NULL,
    `tracker_id` INT UNSIGNED NOT NULL,
    `value` TINYINT UNSIGNED NOT NULL COMMENT 'Value 0-5',
    UNIQUE KEY `uniq_entry_tracker` (`entry_id`, `tracker_id`),
    KEY `idx_entry_id` (`entry_id`),
    CONSTRAINT `chk_value_range` CHECK (`value` >= 0 AND `value` <= 5),
    FOREIGN KEY (`entry_id`) REFERENCES `daily_entries`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`tracker_id`) REFERENCES `custom_trackers`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- Table: week_reports
-- Недельные отчеты (draft/published)
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS `week_reports`;
CREATE TABLE `week_reports` (
    `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `user_id` BIGINT UNSIGNED NOT NULL,
    `week_start_date` DATE NOT NULL COMMENT 'Monday of the week',
    `week_end_date` DATE NOT NULL COMMENT 'Sunday of the week',
    `status` ENUM('draft', 'published') NOT NULL DEFAULT 'draft',
    `published_at` TIMESTAMP NULL DEFAULT NULL,
    `avg_mood` DECIMAL(3,2) DEFAULT NULL COMMENT 'Average mood',
    `filled_days` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT 'Days filled 0-7',
    `metrics_summary` JSON DEFAULT NULL COMMENT 'Tracker averages JSON',
    `highlights` TEXT DEFAULT NULL COMMENT 'Week summary',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `uniq_user_week` (`user_id`, `week_start_date`),
    KEY `idx_user_status` (`user_id`, `status`),
    KEY `idx_status` (`status`),
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- Table: groups
-- Группы друзей
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS `groups`;
CREATE TABLE `groups` (
    `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(255) NOT NULL COMMENT 'Group name',
    `invite_code` VARCHAR(32) NOT NULL COMMENT 'Invite code',
    `owner_id` BIGINT UNSIGNED NOT NULL,
    `description` TEXT DEFAULT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `uniq_invite_code` (`invite_code`),
    KEY `idx_owner` (`owner_id`),
    FOREIGN KEY (`owner_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- Table: group_members
-- Члены групп
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS `group_members`;
CREATE TABLE `group_members` (
    `group_id` INT UNSIGNED NOT NULL,
    `user_id` BIGINT UNSIGNED NOT NULL,
    `role` ENUM('member', 'moderator', 'owner') NOT NULL DEFAULT 'member',
    `joined_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`group_id`, `user_id`),
    KEY `idx_user` (`user_id`),
    FOREIGN KEY (`group_id`) REFERENCES `groups`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- Table: telegram_updates
-- Очередь обновлений от Telegram (для cron)
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS `telegram_updates`;
CREATE TABLE `telegram_updates` (
    `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `update_data` JSON NOT NULL COMMENT 'Raw Telegram update',
    `processed` TINYINT(1) NOT NULL DEFAULT 0,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `processed_at` TIMESTAMP NULL DEFAULT NULL,
    KEY `idx_processed_created` (`processed`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Telegram webhook queue';

-- ----------------------------------------------------------------------------
-- Table: comments
-- Комментарии к отчетам (опционально)
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS `comments`;
CREATE TABLE `comments` (
    `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `week_report_id` INT UNSIGNED NOT NULL,
    `author_id` BIGINT UNSIGNED NOT NULL,
    `text` TEXT NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY `idx_report` (`week_report_id`),
    FOREIGN KEY (`week_report_id`) REFERENCES `week_reports`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`author_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

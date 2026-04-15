#!/bin/bash
# =============================================================================
# Skill Tracer - MySQL Setup Script (Native VPS)
# =============================================================================
# Создаёт базу данных skilltracer и пользователя skilluser@localhost
# с кодировкой utf8mb4_unicode_ci (поддержка эмодзи).
#
# Usage:
#   sudo ./scripts/setup_mysql.sh
#   # или с кастомным .env:
#   ENV_FILE=/opt/skilltracer/.env sudo ./scripts/setup_mysql.sh
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Определяем путь к .env
ENV_FILE="${ENV_FILE:-.env}"
if [ -f "$ENV_FILE" ]; then
    ENV_PATH="$ENV_FILE"
elif [ -f "$(dirname "$0")/../$ENV_FILE" ]; then
    ENV_PATH="$(dirname "$0")/../$ENV_FILE"
elif [ -f "/opt/skilltracer/.env" ]; then
    ENV_PATH="/opt/skilltracer/.env"
elif [ -f "/opt/skilltracer/backend/.env" ]; then
    ENV_PATH="/opt/skilltracer/backend/.env"
else
    log_error ".env файл не найден!"
    exit 1
fi

log_info "Используем .env: $ENV_PATH"

# Читаем переменные из .env
MYSQL_DATABASE=$(grep '^MYSQL_DATABASE=' "$ENV_PATH" | cut -d '=' -f2- | tr -d '"\' ')
MYSQL_USER=$(grep '^MYSQL_USER=' "$ENV_PATH" | cut -d '=' -f2- | tr -d '"\' ')
MYSQL_PASSWORD=$(grep '^MYSQL_PASSWORD=' "$ENV_PATH" | cut -d '=' -f2- | tr -d '"\' ')

# Fallback на старые имена переменных если не найдены
if [ -z "$MYSQL_DATABASE" ]; then
    MYSQL_DATABASE=$(grep '^DB_NAME=' "$ENV_PATH" | cut -d '=' -f2- | tr -d '"\' ')
fi
if [ -z "$MYSQL_USER" ]; then
    MYSQL_USER=$(grep '^DB_USER=' "$ENV_PATH" | cut -d '=' -f2- | tr -d '"\' ')
fi
if [ -z "$MYSQL_PASSWORD" ]; then
    MYSQL_PASSWORD=$(grep '^DB_PASSWORD=' "$ENV_PATH" | cut -d '=' -f2- | tr -d '"\' ')
fi

# Значения по умолчанию
MYSQL_DATABASE="${MYSQL_DATABASE:-skilltracer}"
MYSQL_USER="${MYSQL_USER:-skilluser}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-skillpass}"

log_info "База данных: $MYSQL_DATABASE"
log_info "Пользователь: $MYSQL_USER"

# Проверяем что mysql доступен
if ! command -v mysql &> /dev/null; then
    log_error "mysql клиент не найден. Установите: sudo apt-get install mysql-client"
    exit 1
fi

# Проверяем подключение как root
log_info "Проверяем подключение к MySQL..."
if mysql -u root -e "SELECT 1" &>/dev/null; then
    MYSQL_AUTH="mysql -u root"
elif mysql -u root -p -e "SELECT 1" &>/dev/null; then
    # Нужен пароль — спросим
    log_warn "Требуется пароль root для MySQL"
    read -rsp "Введите пароль root MySQL: " ROOT_PASSWORD
    echo
    MYSQL_AUTH="mysql -u root -p'$ROOT_PASSWORD'"
else
    log_error "Не удалось подключиться к MySQL как root"
    log_info "Возможно нужно использовать sudo mysql -u root"
    exit 1
fi

# Создаём БД и пользователя
log_info "Создаём базу данных (если не существует)..."
$MYSQL_AUTH -e "
CREATE DATABASE IF NOT EXISTS \`${MYSQL_DATABASE}\`
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
"

log_info "Создаём пользователя (если не существует)..."
$MYSQL_AUTH -e "
CREATE USER IF NOT EXISTS '${MYSQL_USER}'@'localhost'
    IDENTIFIED BY '${MYSQL_PASSWORD}';
"

log_info "Обновляем пароль пользователя..."
$MYSQL_AUTH -e "
ALTER USER '${MYSQL_USER}'@'localhost'
    IDENTIFIED BY '${MYSQL_PASSWORD}';
"

log_info "Выдаём права на базу..."
$MYSQL_AUTH -e "
GRANT ALL PRIVILEGES ON \`${MYSQL_DATABASE}\`.*
    TO '${MYSQL_USER}'@'localhost';
"

log_info "Применяем привилегии..."
$MYSQL_AUTH -e "FLUSH PRIVILEGES;"

# Проверяем подключение новым пользователем
log_info "Проверяем подключение пользователя $MYSQL_USER..."
if mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SHOW TABLES;" "$MYSQL_DATABASE" &>/dev/null; then
    log_info "✅ Пользователь $MYSQL_USER успешно подключился к $MYSQL_DATABASE"
else
    log_error "❌ Не удалось подключиться пользователем $MYSQL_USER"
    exit 1
fi

# Проверяем кодировку БД
log_info "Проверяем кодировку базы данных..."
CHARSET=$($MYSQL_AUTH -N -e "SELECT DEFAULT_CHARACTER_SET_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '${MYSQL_DATABASE}';")
COLLATION=$($MYSQL_AUTH -N -e "SELECT DEFAULT_COLLATION_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '${MYSQL_DATABASE}';")

log_info "Кодировка: $CHARSET | Сопоставление: $COLLATION"

if [ "$CHARSET" = "utf8mb4" ]; then
    log_info "✅ Кодировка utf8mb4 настроена корректно"
else
    log_warn "⚠️  Кодировка базы '$CHARSET'. Ожидалось utf8mb4"
fi

echo ""
echo "=========================================="
echo "MySQL настройка завершена!"
echo "=========================================="
echo "База:     $MYSQL_DATABASE"
echo "Пользователь: $MYSQL_USER@localhost"
echo "Кодировка:    $CHARSET / $COLLATION"
echo ""

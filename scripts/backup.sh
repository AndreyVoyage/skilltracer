#!/bin/bash
# =============================================================================
# Skill Tracer - MySQL Backup Script
# =============================================================================
# Создаёт дамп базы данных и ротирует старые бэкапы (храним 7 дней).
#
# Usage:
#   ./scripts/backup.sh
#   # или с кроном:
#   0 3 * * * /opt/skilltracer/scripts/backup.sh >> /var/log/skilltracer/backup.log 2>&1
# =============================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
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
    log_warn ".env не найден, используются переменные окружения"
    ENV_PATH=""
fi

# Читаем DATABASE_URL или отдельные переменные
if [ -n "$ENV_PATH" ] && [ -f "$ENV_PATH" ]; then
    DATABASE_URL=$(grep '^DATABASE_URL=' "$ENV_PATH" | cut -d '=' -f2- | tr -d '"\' ')
    MYSQL_DATABASE=$(grep '^MYSQL_DATABASE=' "$ENV_PATH" | cut -d '=' -f2- | tr -d '"\' ')
    MYSQL_USER=$(grep '^MYSQL_USER=' "$ENV_PATH" | cut -d '=' -f2- | tr -d '"\' ')
    MYSQL_PASSWORD=$(grep '^MYSQL_PASSWORD=' "$ENV_PATH" | cut -d '=' -f2- | tr -d '"\' ')
fi

# Fallback
if [ -z "$DATABASE_URL" ]; then
    DATABASE_URL="${DATABASE_URL:-mysql+aiomysql://skilluser:skillpass@localhost:3306/skilltracer}"
fi

# Парсим DATABASE_URL
# Формат: mysql+aiomysql://user:password@host:port/database
DB_NAME=$(echo "$DATABASE_URL" | sed -n 's/.*\/\(.*\)/\1/p')
DB_USER=$(echo "$DATABASE_URL" | sed -n 's/mysql+aiomysql:\/\/\([^:]*\):.*/\1/p')
DB_PASS=$(echo "$DATABASE_URL" | sed -n 's/mysql+aiomysql:\/\/[^:]*:\([^@]*\)@.*/\1/p')
DB_HOST=$(echo "$DATABASE_URL" | sed -n 's/mysql+aiomysql:\/\/[^@]*@\([^:]*\):.*/\1/p')

# Fallback на отдельные переменные
DB_NAME="${MYSQL_DATABASE:-$DB_NAME}"
DB_USER="${MYSQL_USER:-$DB_USER}"
DB_PASS="${MYSQL_PASSWORD:-$DB_PASS}"
DB_HOST="${DB_HOST:-localhost}"

BACKUP_DIR="${BACKUP_DIR:-/opt/skilltracer/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/skilltracer_${DATE}.sql"

if [ -z "$DB_NAME" ] || [ -z "$DB_USER" ]; then
    log_error "Не удалось определить имя базы или пользователя"
    exit 1
fi

# Создаём директорию для бэкапов
mkdir -p "$BACKUP_DIR"

log_info "Создаём бэкап базы $DB_NAME..."
log_info "Файл: $BACKUP_FILE"

# Делаем дамп
if mysqldump -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASS" \
    --single-transaction \
    --routines \
    --triggers \
    "$DB_NAME" > "$BACKUP_FILE"; then
    
    # Сжимаем
    gzip "$BACKUP_FILE"
    BACKUP_FILE="${BACKUP_FILE}.gz"
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    
    log_info "✅ Бэкап создан: $BACKUP_FILE ($SIZE)"
else
    log_error "❌ Ошибка создания бэкапа"
    exit 1
fi

# Ротация: удаляем бэкапы старше RETENTION_DAYS
log_info "Ротируем бэкапы старше $RETENTION_DAYS дней..."
DELETED=$(find "$BACKUP_DIR" -name "skilltracer_*.sql.gz" -mtime +$RETENTION_DAYS -print)
if [ -n "$DELETED" ]; then
    echo "$DELETED" | while read -r f; do
        log_info "Удаляем старый бэкап: $f"
    done
    find "$BACKUP_DIR" -name "skilltracer_*.sql.gz" -mtime +$RETENTION_DAYS -delete
else
    log_info "Старых бэкапов для удаления не найдено"
fi

# Выводим список актуальных бэкапов
BACKUP_COUNT=$(find "$BACKUP_DIR" -name "skilltracer_*.sql.gz" | wc -l)
log_info "Актуальных бэкапов: $BACKUP_COUNT"

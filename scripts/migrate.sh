#!/bin/bash
# =============================================================================
# Skill Tracer - Database Migration Script
# =============================================================================
# Запускает alembic upgrade head для применения миграций.
#
# Usage:
#   ./scripts/migrate.sh
# =============================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Определяем директорию проекта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_DIR/backend"

# Если есть /opt/skilltracer/backend — используем его
if [ -d "/opt/skilltracer/backend" ]; then
    BACKEND_DIR="/opt/skilltracer/backend"
fi

if [ ! -d "$BACKEND_DIR" ]; then
    log_error "Backend директория не найдена: $BACKEND_DIR"
    exit 1
fi

log_info "Backend директория: $BACKEND_DIR"
cd "$BACKEND_DIR"

# Ищем Python / venv
if [ -f "$BACKEND_DIR/../venv/bin/python" ]; then
    PYTHON="$BACKEND_DIR/../venv/bin/python"
    ALEMBIC="$BACKEND_DIR/../venv/bin/alembic"
elif [ -f "$BACKEND_DIR/venv/bin/python" ]; then
    PYTHON="$BACKEND_DIR/venv/bin/python"
    ALEMBIC="$BACKEND_DIR/venv/bin/alembic"
elif [ -f "/opt/skilltracer/venv/bin/python" ]; then
    PYTHON="/opt/skilltracer/venv/bin/python"
    ALEMBIC="/opt/skilltracer/venv/bin/alembic"
else
    PYTHON=$(command -v python3 || command -v python)
    ALEMBIC=$(command -v alembic)
fi

if [ -z "$PYTHON" ] || [ ! -x "$PYTHON" ]; then
    log_error "Python не найден"
    exit 1
fi

if [ -z "$ALEMBIC" ] || [ ! -x "$ALEMBIC" ]; then
    log_error "alembic не найден. Установите: pip install alembic"
    exit 1
fi

log_info "Python: $PYTHON"
log_info "Alembic: $ALEMBIC"

# Проверяем .env
ENV_FILE="${ENV_FILE:-$BACKEND_DIR/.env}"
if [ -f "$ENV_FILE" ]; then
    log_info "Найден .env: $ENV_FILE"
else
    log_warn ".env не найден по пути $ENV_FILE"
fi

# Запускаем миграции
log_info "Применяем миграции..."
$ALEMBIC upgrade head

if [ $? -eq 0 ]; then
    log_info "✅ Миграции успешно применены"
else
    log_error "❌ Ошибка применения миграций"
    exit 1
fi

# Проверяем таблицы (если есть mysql)
if command -v mysql &> /dev/null && [ -f "$ENV_FILE" ]; then
    DATABASE_URL=$(grep '^DATABASE_URL=' "$ENV_FILE" | cut -d '=' -f2- | tr -d '"\' ')
    # Парсим mysql+aiomysql://user:pass@host:port/db
    DB_NAME=$(echo "$DATABASE_URL" | sed -n 's/.*\/\(.*\)/\1/p')
    DB_USER=$(echo "$DATABASE_URL" | sed -n 's/mysql+aiomysql:\/\/\([^:]*\):.*/\1/p')
    DB_PASS=$(echo "$DATABASE_URL" | sed -n 's/mysql+aiomysql:\/\/[^:]*:\([^@]*\)@.*/\1/p')
    
    if [ -n "$DB_NAME" ] && [ -n "$DB_USER" ]; then
        log_info "Проверяем таблицы в базе $DB_NAME..."
        TABLES=$(mysql -u "$DB_USER" -p"$DB_PASS" -e "SHOW TABLES;" "$DB_NAME" 2>/dev/null | wc -l)
        TABLES=$((TABLES - 1))  # minus header
        log_info "✅ Найдено таблиц: $TABLES"
    fi
fi

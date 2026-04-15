#!/bin/bash
# =============================================================================
# Skill Tracer - Uninstall Script
# =============================================================================
# Останавливает и удаляет сервисы Skill Tracer.
# НЕ удаляет данные MySQL и .env без подтверждения.
#
# Usage:
#   sudo ./uninstall.sh
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

if [ "$EUID" -ne 0 ]; then
    log_error "Запустите скрипт с sudo или как root"
    exit 1
fi

APP_USER="${1:-skilltracer}"
APP_DIR="/opt/skilltracer"

echo "⚠️  ВНИМАНИЕ: Этот скрипт удалит сервисы Skill Tracer!"
echo ""
read -p "Продолжить удаление? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    log_info "Отменено"
    exit 0
fi

# 1. Остановка сервисов
log_info "Останавливаем сервисы..."
systemctl stop skilltracer 2>/dev/null || true
systemctl stop skilltracer-bot 2>/dev/null || true
systemctl disable skilltracer 2>/dev/null || true
systemctl disable skilltracer-bot 2>/dev/null || true

# 2. Удаление systemd units
log_info "Удаляем systemd units..."
rm -f /etc/systemd/system/skilltracer.service
rm -f /etc/systemd/system/skilltracer-bot.service
systemctl daemon-reload

# 3. Caddy
log_info "Восстанавливаем стандартный Caddyfile..."
if [ -f /etc/caddy/Caddyfile.bak ]; then
    cp /etc/caddy/Caddyfile.bak /etc/caddy/Caddyfile
    systemctl reload caddy 2>/dev/null || true
fi

# 4. Cron
log_info "Удаляем cron задачи..."
(crontab -u root -l 2>/dev/null | grep -v "$APP_DIR/scripts/backup.sh" || true) | crontab -u root -

# 5. Удаление директорий
read -p "Удалить директорию приложения $APP_DIR? (yes/no): " remove_app
if [ "$remove_app" = "yes" ]; then
    rm -rf "$APP_DIR"
    log_info "Директория $APP_DIR удалена"
fi

# 6. Удаление пользователя
read -p "Удалить системного пользователя $APP_USER? (yes/no): " remove_user
if [ "$remove_user" = "yes" ]; then
    userdel "$APP_USER" 2>/dev/null || true
    log_info "Пользователь $APP_USER удалён"
fi

log_info "Удаление завершено"

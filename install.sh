#!/bin/bash
# =============================================================================
# Skill Tracer - Native VPS Installation Script
# =============================================================================
# Устанавливает Skill Tracer на VPS без Docker.
# Оптимизировано для Reg.ru Host-0: 1GB RAM, 1 core, 13GB SSD.
#
# Usage:
#   sudo ./install.sh
#   # или с кастомным пользователем:
#   sudo ./install.sh skilltracer
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "\n${BLUE}==>${NC} $1"; }

# Конфигурация
APP_USER="${1:-skilltracer}"
APP_DIR="/opt/skilltracer"
LOG_DIR="/var/log/skilltracer"
BACKUP_DIR="/opt/skilltracer/backups"
PYTHON_BIN=""

log_step "Skill Tracer Native Installation"
log_info "App user: $APP_USER"
log_info "App dir:  $APP_DIR"

# =============================================================================
# 1. Проверка root
# =============================================================================
if [ "$EUID" -ne 0 ]; then
    log_error "Запустите скрипт с sudo или как root"
    exit 1
fi

# =============================================================================
# 2. Создание пользователя
# =============================================================================
log_step "Создаём системного пользователя $APP_USER..."
if id "$APP_USER" &>/dev/null; then
    log_info "Пользователь $APP_USER уже существует"
else
    useradd --system --no-create-home --shell /bin/false "$APP_USER"
    log_info "Пользователь $APP_USER создан"
fi

# =============================================================================
# 3. Создание директорий
# =============================================================================
log_step "Создаём директории..."
mkdir -p "$APP_DIR" "$APP_DIR/backend" "$APP_DIR/scripts" "$APP_DIR/systemd"
mkdir -p "$LOG_DIR" "$BACKUP_DIR"
chown -R "$APP_USER:$APP_USER" "$APP_DIR" "$BACKUP_DIR"
chmod 755 "$LOG_DIR"

# =============================================================================
# 4. Определяем Python
# =============================================================================
log_step "Ищем подходящий Python..."

find_python() {
    for cmd in python3.12 python3.11 python3.10 python3; do
        if command -v "$cmd" &>/dev/null; then
            version=$($cmd --version 2>&1 | awk '{print $2}')
            major=$(echo "$version" | cut -d. -f1)
            minor=$(echo "$version" | cut -d. -f2)
            if [ "$major" -eq 3 ] && [ "$minor" -ge 10 ]; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    return 1
}

PYTHON_BIN=$(find_python) || true

if [ -z "$PYTHON_BIN" ]; then
    log_warn "Python 3.10+ не найден. Пробуем установить..."
    
    if command -v apt-get &>/dev/null; then
        apt-get update -qq
        apt-get install -y -qq software-properties-common
        add-apt-repository -y ppa:deadsnakes/ppa 2>/dev/null || true
        apt-get update -qq
        apt-get install -y -qq python3.12 python3.12-venv python3.12-dev python3-pip
        PYTHON_BIN=$(find_python) || true
    elif command -v yum &>/dev/null; then
        yum install -y python3 python3-pip python3-virtualenv
        PYTHON_BIN=$(find_python) || true
    fi
fi

if [ -z "$PYTHON_BIN" ]; then
    log_error "Не удалось найти или установить Python 3.10+. Установите вручную."
    exit 1
fi

PYTHON_VERSION=$($PYTHON_BIN --version)
log_info "Найден Python: $PYTHON_VERSION ($PYTHON_BIN)"

# =============================================================================
# 5. Создание virtualenv
# =============================================================================
log_step "Создаём virtualenv..."
VENV_DIR="$APP_DIR/venv"

if [ -d "$VENV_DIR" ]; then
    log_info "Virtualenv уже существует: $VENV_DIR"
else
    $PYTHON_BIN -m venv "$VENV_DIR"
    log_info "Virtualenv создан"
fi

# Обновляем pip
"$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel -q

# =============================================================================
# 6. Установка зависимостей
# =============================================================================
log_step "Устанавливаем Python-зависимости..."

REQUIREMENTS="$APP_DIR/backend/requirements.txt"
if [ -f "$REQUIREMENTS" ]; then
    "$VENV_DIR/bin/pip" install -r "$REQUIREMENTS" -q
    log_info "Зависимости установлены из $REQUIREMENTS"
else
    log_warn "requirements.txt не найден по пути $REQUIREMENTS"
    log_info "Убедитесь что код проекта скопирован в $APP_DIR"
fi

# =============================================================================
# 7. Установка Caddy
# =============================================================================
log_step "Устанавливаем Caddy..."

if command -v caddy &>/dev/null; then
    log_info "Caddy уже установлен: $(caddy version)"
else
    if [ -f "$APP_DIR/caddy/install-caddy.sh" ]; then
        bash "$APP_DIR/caddy/install-caddy.sh"
    else
        log_warn "Скрипт install-caddy.sh не найден, пробуем официальный..."
        apt-get install -y -qq debian-keyring debian-archive-keyring apt-transport-https curl
        curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | \
            gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
        curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | \
            tee /etc/apt/sources.list.d/caddy-stable.list
        apt-get update -qq
        apt-get install -y -qq caddy
    fi
    systemctl enable caddy
    log_info "Caddy установлен: $(caddy version)"
fi

# =============================================================================
# 8. Копирование Caddyfile
# =============================================================================
log_step "Настраиваем Caddy..."

if [ -f "$APP_DIR/caddy/Caddyfile" ]; then
    cp "$APP_DIR/caddy/Caddyfile" /etc/caddy/Caddyfile
    
    # Валидация
    if caddy validate --config /etc/caddy/Caddyfile &>/dev/null; then
        log_info "Caddyfile валиден"
    else
        log_warn "Caddyfile имеет проблемы с валидацией, но скрипт продолжит"
    fi
    
    systemctl reload caddy || true
else
    log_warn "Caddyfile не найден в $APP_DIR/caddy/Caddyfile"
fi

# =============================================================================
# 9. Копирование systemd services
# =============================================================================
log_step "Настраиваем systemd сервисы..."

if [ -f "$APP_DIR/systemd/skilltracer.service" ]; then
    cp "$APP_DIR/systemd/skilltracer.service" /etc/systemd/system/skilltracer.service
    log_info "skilltracer.service установлен"
else
    log_warn "skilltracer.service не найден"
fi

if [ -f "$APP_DIR/systemd/skilltracer-bot.service" ]; then
    cp "$APP_DIR/systemd/skilltracer-bot.service" /etc/systemd/system/skilltracer-bot.service
    log_info "skilltracer-bot.service установлен"
fi

systemctl daemon-reload

# =============================================================================
# 10. Настройка прав на .env
# =============================================================================
log_step "Настраиваем права на .env..."

for env_file in "$APP_DIR/.env" "$APP_DIR/backend/.env"; do
    if [ -f "$env_file" ]; then
        chmod 600 "$env_file"
        chown "$APP_USER:$APP_USER" "$env_file"
        log_info "Права 600 установлены для $env_file"
    fi
done

# =============================================================================
# 11. Firewall (ufw / firewalld)
# =============================================================================
log_step "Настраиваем firewall..."

if command -v ufw &>/dev/null; then
    ufw allow 22/tcp comment 'SSH' || true
    ufw allow 80/tcp comment 'HTTP' || true
    ufw allow 443/tcp comment 'HTTPS' || true
    # Закрываем внутренние порты от внешки
    ufw deny 8000/tcp comment 'Backend internal' || true
    ufw deny 3306/tcp comment 'MySQL internal' || true
    ufw --force enable || true
    log_info "UFW настроен"
elif command -v firewall-cmd &>/dev/null; then
    firewall-cmd --permanent --add-service=http || true
    firewall-cmd --permanent --add-service=https || true
    firewall-cmd --permanent --remove-port=8000/tcp || true
    firewall-cmd --permanent --remove-port=3306/tcp || true
    firewall-cmd --reload || true
    log_info "Firewalld настроен"
else
    log_warn "Не найден ufw или firewalld — firewall не настроен"
fi

# =============================================================================
# 12. Cron для бэкапов
# =============================================================================
log_step "Настраиваем cron для бэкапов..."

BACKUP_SCRIPT="$APP_DIR/scripts/backup.sh"
if [ -f "$BACKUP_SCRIPT" ]; then
    chmod +x "$BACKUP_SCRIPT"
    CRON_JOB="0 3 * * * $BACKUP_SCRIPT >> $LOG_DIR/backup.log 2>&1"
    # Удаляем дубликаты
    (crontab -u root -l 2>/dev/null | grep -v "$BACKUP_SCRIPT" || true; echo "$CRON_JOB") | crontab -u root -
    log_info "Cron для бэкапов добавлен (3:00 AM)"
else
    log_warn "backup.sh не найден"
fi

# =============================================================================
# 13. Права на скрипты
# =============================================================================
log_step "Делаем скрипты исполняемыми..."

for script in "$APP_DIR/scripts/"*.sh "$APP_DIR/scripts/"*.py "$APP_DIR/caddy/install-caddy.sh"; do
    [ -f "$script" ] && chmod +x "$script"
done

# =============================================================================
# 14. Итог
# =============================================================================
log_step "Установка завершена!"

echo ""
echo "=========================================="
echo "       Skill Tracer установлен"
echo "=========================================="
echo ""
echo "Директория:     $APP_DIR"
echo "Python:         $PYTHON_VERSION"
echo "Virtualenv:     $VENV_DIR"
echo "Логи:           $LOG_DIR"
echo "Бэкапы:         $BACKUP_DIR"
echo ""
echo "Следующие шаги:"
echo "  1. Настройте $APP_DIR/.env (BOT_TOKEN, DOMAIN, DATABASE_URL)"
echo "  2. Проверьте токен:     sudo -u $APP_USER $VENV_DIR/bin/python $APP_DIR/scripts/verify_bot.py"
echo "  3. Настройте MySQL:     sudo $APP_DIR/scripts/setup_mysql.sh"
echo "  4. Примените миграции:  sudo $APP_DIR/scripts/migrate.sh"
echo "  5. Запустите сервис:    sudo systemctl start skilltracer"
echo "  6. Проверьте статус:    sudo systemctl status skilltracer"
echo "  7. Health check:        sudo $VENV_DIR/bin/python $APP_DIR/scripts/healthcheck.py"
echo ""
echo "Полезные команды:"
echo "  Логи приложения:  sudo journalctl -u skilltracer -f"
echo "  Перезапуск:       sudo systemctl restart skilltracer"
echo "  Остановка:        sudo systemctl stop skilltracer"
echo ""

#!/bin/bash
# =============================================================================
# Skill Tracer - Caddy Installation Script
# =============================================================================
# Устанавливает Caddy через официальный install.sh.
# Fallback на ручную установку для CentOS/Debian.
#
# Usage:
#   sudo ./caddy/install-caddy.sh
# =============================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

if [ "$EUID" -ne 0 ]; then
    log_error "Запустите с sudo"
    exit 1
fi

log_info "Устанавливаем Caddy..."

# Пробуем официальный скрипт
if command -v curl &>/dev/null; then
    log_info "Используем официальный install.sh..."
    curl -1sLf 'https://caddyserver.com/install.sh' | bash && {
        log_info "Caddy установлен через официальный скрипт"
        systemctl enable caddy
        exit 0
    }
fi

# Fallback для Debian/Ubuntu
if command -v apt-get &>/dev/null; then
    log_warn "Официальный скрипт не сработал, используем apt..."
    apt-get update -qq
    apt-get install -y -qq debian-keyring debian-archive-keyring apt-transport-https curl
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | \
        gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | \
        tee /etc/apt/sources.list.d/caddy-stable.list
    apt-get update -qq
    apt-get install -y -qq caddy

# Fallback для CentOS/RHEL/Fedora
elif command -v yum &>/dev/null; then
    log_warn "Официальный скрипт не сработал, используем yum..."
    yum install -y yum-plugin-copr
    yum copr -y enable @caddy/caddy
    yum install -y caddy
else
    log_error "Не удалось определить пакетный менеджер. Установите Caddy вручную."
    exit 1
fi

systemctl enable caddy
log_info "Caddy установлен: $(caddy version)"

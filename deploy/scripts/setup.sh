#!/bin/bash
# =============================================================================
# Skill Tracer - Setup Script for reg.ru Host-0
# =============================================================================
# 
# Run this script on your reg.ru VPS as root or with sudo:
#   chmod +x setup.sh
#   ./setup.sh
#
# This script will:
# - Install Python 3.12
# - Install Caddy web server
# - Install MySQL client libraries
# - Setup log directories
#
# =============================================================================

set -e  # Exit on error

echo "=========================================="
echo "Skill Tracer Setup for reg.ru Host-0"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    log_error "Please run as root or with sudo"
    exit 1
fi

# Get username (for reg.ru it's usually u1893136)
if [ -z "$1" ]; then
    USERNAME="u1893136"
    log_warn "No username provided, using default: $USERNAME"
    log_warn "Usage: ./setup.sh <username>"
else
    USERNAME="$1"
fi

USER_HOME="/home/$USERNAME"

echo ""
echo "Setup will use:"
echo "  Username: $USERNAME"
echo "  Home: $USER_HOME"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_info "Setup cancelled"
    exit 0
fi

# =============================================================================
# Update system
# =============================================================================
log_info "Updating package lists..."
apt-get update

# =============================================================================
# Install Python 3.12
# =============================================================================
log_info "Installing Python 3.12..."

# Add deadsnakes PPA
apt-get install -y software-properties-common
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update

# Install Python 3.12 and dependencies
apt-get install -y \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    python3.12-distutils \
    python3-pip

# Ensure pip is installed for Python 3.12
python3.12 -m ensurepip --upgrade || true

log_info "Python 3.12 installed: $(python3.12 --version)"

# =============================================================================
# Install MySQL client libraries
# =============================================================================
log_info "Installing MySQL client libraries..."
apt-get install -y \
    libmysqlclient-dev \
    pkg-config \
    default-libmysqlclient-dev

# =============================================================================
# Install Caddy
# =============================================================================
log_info "Installing Caddy web server..."

# Install dependencies
apt-get install -y \
    debian-keyring \
    debian-archive-keyring \
    apt-transport-https

# Add Caddy repository
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | \
    gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | \
    tee /etc/apt/sources.list.d/caddy-stable.list

# Install Caddy
apt-get update
apt-get install -y caddy

# Enable and start Caddy
systemctl enable caddy
systemctl start caddy

log_info "Caddy installed: $(caddy version)"

# =============================================================================
# Create directories
# =============================================================================
log_info "Creating directories..."

# App directory
mkdir -p "$USER_HOME/skilltracer"
chown "$USERNAME:$USERNAME" "$USER_HOME/skilltracer"

# Log directories
mkdir -p /var/log/caddy
mkdir -p "$USER_HOME/skilltracer/backend/logs"
chown -R "$USERNAME:$USERNAME" "$USER_HOME/skilltracer/backend/logs"

# =============================================================================
# Install useful tools
# =============================================================================
log_info "Installing useful tools..."

apt-get install -y \
    git \
    curl \
    wget \
    nano \
    htop \
    tree

# =============================================================================
# Setup firewall (optional but recommended)
# =============================================================================
log_info "Configuring firewall..."

if command -v ufw &> /dev/null; then
    ufw allow 22/tcp    # SSH
    ufw allow 80/tcp    # HTTP
    ufw allow 443/tcp   # HTTPS
    ufw --force enable
    log_info "UFW firewall enabled"
else
    log_warn "UFW not installed, skipping firewall setup"
fi

# =============================================================================
# Print summary
# =============================================================================
echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Copy your application code to: $USER_HOME/skilltracer"
echo "2. Create MySQL database via ISPmanager"
echo "3. Create .env file with your settings"
echo "4. Run: cd $USER_HOME/skilltracer/backend && python3.12 -m venv venv"
echo "5. Run: source venv/bin/activate && pip install -r requirements.txt"
echo "6. Run: alembic upgrade head"
echo "7. Copy Caddyfile: sudo cp deploy/caddy/Caddyfile /etc/caddy/Caddyfile"
echo "8. Copy systemd service: sudo cp deploy/systemd/skilltracer.service /etc/systemd/system/"
echo "9. Start: sudo systemctl daemon-reload && sudo systemctl start skilltracer"
echo ""
echo "Useful commands:"
echo "  Check status:  sudo systemctl status skilltracer"
echo "  View logs:     sudo journalctl -u skilltracer -f"
echo "  Caddy logs:    sudo tail -f /var/log/caddy/skilltracer.log"
echo "  Health check:  curl http://localhost:8000/health"
echo ""

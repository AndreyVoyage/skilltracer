#!/bin/bash
# SkillTracer Server Setup Script
# Run on Ubuntu 24.04 VDS as root
# IP: 157.22.187.38

set -e

echo "=== SkillTracer Server Setup ==="
echo "IP: 157.22.187.38"
echo "Domain: skilltracer.art-artel.su"
echo "OS: Ubuntu 24.04"
echo ""

# 1. Update system
echo "[1/10] Updating system..."
apt update && apt upgrade -y

# 2. Install essential tools
echo "[2/10] Installing essential tools..."
apt install -y curl wget git vim htop ufw fail2ban

# 3. Create user (optional but recommended)
echo "[3/10] Creating skilltracer user..."
useradd -m -s /bin/bash skilltracer || true
usermod -aG docker skilltracer || true

# 4. Install Docker
echo "[4/10] Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    usermod -aG docker root
    usermod -aG docker skilltracer
fi

# 5. Install Docker Compose
echo "[5/10] Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    apt install -y docker-compose-plugin
fi

# 6. Install Nginx
echo "[6/10] Installing Nginx..."
apt install -y nginx
systemctl enable nginx
systemctl start nginx

# 7. Install Certbot (Let's Encrypt)
echo "[7/10] Installing Certbot..."
apt install -y certbot python3-certbot-nginx

# 8. Configure firewall
echo "[8/10] Configuring firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 8000/tcp  # Backend API (dev)
ufw allow 3000/tcp  # Frontend (dev)
ufw --force enable

# 9. Setup timezone
echo "[9/10] Setting timezone..."
timedatectl set-timezone Europe/Moscow

# 10. Clone project
echo "[10/10] Cloning SkillTracer project..."
mkdir -p /opt
cd /opt
if [ -d "skilltracer" ]; then
    echo "Project already exists, pulling latest..."
    cd skilltracer
    git pull origin main
else
    git clone https://github.com/AndreyVoyage/skilltracer.git
    cd skilltracer
fi

echo ""
echo "=== Server setup complete! ==="
echo ""
echo "Next steps:"
echo "1. Copy .env.example to .env and fill in real values:"
echo "   cd /opt/skilltracer"
echo "   cp .env.example .env"
echo "   nano .env"
echo ""
echo "2. Generate secret key:"
echo "   openssl rand -hex 32"
echo ""
echo "3. Get Telegram bot token from @BotFather"
echo ""
echo "4. Start services:"
echo "   docker compose up -d"
echo ""
echo "5. Setup SSL:"
echo "   certbot --nginx -d skilltracer.art-artel.su"
echo ""
echo "6. Check status:"
echo "   docker compose ps"
echo "   docker compose logs -f backend"
echo ""
echo "Backend API: http://157.22.187.38:8000"
echo "Frontend: http://157.22.187.38:3000"

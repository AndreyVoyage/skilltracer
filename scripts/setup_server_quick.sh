#!/bin/bash
# SkillTracer Server Setup — Quick Run
# IP: 157.22.187.38
# SSH уже настроен по ключу (id_ed25519)

set -e

echo "=== SkillTracer Server Setup ==="
echo "IP: 157.22.187.38"
echo "Domain: skilltracer.art-artel.su"
echo ""

# 1. Update system
echo "[1/8] Updating system..."
apt update -y && apt upgrade -y

# 2. Install essential tools
echo "[2/8] Installing tools..."
apt install -y curl wget git vim htop ufw fail2ban

# 3. Install Docker
echo "[3/8] Installing Docker..."
curl -fsSL https://get.docker.com | sh
systemctl enable docker && systemctl start docker

# 4. Install Docker Compose
echo "[4/8] Installing Docker Compose..."
apt install -y docker-compose-plugin

# 5. Install Nginx + Certbot
echo "[5/8] Installing Nginx + Certbot..."
apt install -y nginx certbot python3-certbot-nginx
systemctl enable nginx && systemctl start nginx

# 6. Firewall
echo "[6/8] Firewall..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# 7. Clone repo
echo "[7/8] Cloning SkillTracer..."
cd /opt
if [ -d "skilltracer" ]; then
    cd skilltracer && git pull origin main
else
    git clone https://github.com/AndreyVoyage/skilltracer.git
    cd skilltracer
fi

# 8. Done
echo ""
echo "=== Setup Complete ==="
echo "Next: cd /opt/skilltracer && cp .env.example .env && nano .env"
echo "Then: docker compose up -d"
echo "Then: certbot --nginx -d skilltracer.art-artel.su"
echo ""
echo "Backend: http://157.22.187.38:8000"
echo "Frontend: http://157.22.187.38:3000"

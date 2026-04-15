# Skill Tracer — Native VPS Deployment Guide

Руководство по развёртыванию Skill Tracer на VPS **без Docker** (нативная установка). Оптимизировано для **Reg.ru Host-0** (~1GB RAM, 1 CPU core, 13GB SSD).

---

## 📋 Содержание

1. [Архитектура](#-архитектура)
2. [Требования](#-требования)
3. [Быстрый старт](#-быстрый-старт)
4. [Пошаговая установка](#-пошаговая-установка)
5. [Управление сервисами](#-управление-сервисами)
6. [Полезные команды](#-полезные-команды)
7. [Устранение неполадок](#-устранение-неполадок)
8. [Удаление](#-удаление)

---

## 🏗 Архитектура

```
Internet ──► Caddy (:80/:443) ──► Uvicorn @ 127.0.0.1:8000 ──► FastAPI + Aiogram
                                           │
                                           ▼
                                    MySQL @ localhost:3306
```

- **Caddy** — reverse proxy + автоматический HTTPS (Let's Encrypt)
- **Uvicorn** — 1 worker (критично для 1GB RAM)
- **FastAPI** — REST API + Telegram webhook endpoint `/webhook`
- **MySQL** — нативная установка на хосте, ограничен пул до 5 соединений

---

## 📦 Требования

- **OS**: Ubuntu 20.04+ / Debian 11+ / CentOS 8+
- **RAM**: 1GB минимум
- **CPU**: 1 core
- **Диск**: 2GB свободного места (без учёта ОС)
- **Домен**: желательно иметь (Caddy поднимет HTTPS автоматически)
- **MySQL**: 8.0+ или MariaDB 10.5+ на `localhost:3306`

---

## 🚀 Быстрый старт

```bash
# 1. Клонируйте проект (или скопируйте файлы)
cd /opt
sudo git clone https://github.com/AndreyVoyage/skilltracer.git
# или загрузите архив и распакуйте в /opt/skilltracer

# 2. Перейдите в директорию проекта
cd /opt/skilltracer

# 3. Создайте .env
sudo cp .env.example .env
sudo nano .env
#   Обязательно заполните:
#   - BOT_TOKEN
#   - DOMAIN (например: u1893136.isp.regruhosting.ru)
#   - WEBAPP_URL (https://ваш-домен)
#   - DATABASE_URL (mysql+aiomysql://skilluser:skillpass@localhost:3306/skilltracer)
#   - MYSQL_PASSWORD

# 4. Установите всё одной командой
sudo chmod +x install.sh
sudo ./install.sh

# 5. Проверьте токен бота
sudo /opt/skilltracer/venv/bin/python /opt/skilltracer/scripts/verify_bot.py

# 6. Настройте MySQL
sudo /opt/skilltracer/scripts/setup_mysql.sh

# 7. Примените миграции
sudo /opt/skilltracer/scripts/migrate.sh

# 8. Запустите сервис
sudo systemctl start skilltracer
sudo systemctl start caddy

# 9. Проверьте health
sudo /opt/skilltracer/venv/bin/python /opt/skilltracer/scripts/healthcheck.py
```

---

## 🔧 Пошаговая установка

### 1. Копирование кода

Рекомендуется размещать приложение в `/opt/skilltracer` ( systemd service настроен на этот путь ):

```bash
sudo mkdir -p /opt/skilltracer
sudo chown $USER:$USER /opt/skilltracer
git clone https://github.com/AndreyVoyage/skilltracer.git /opt/skilltracer
```

### 2. Настройка `.env`

```bash
cd /opt/skilltracer
sudo cp .env.example .env
sudo chmod 600 .env
sudo nano .env
```

**Обязательные поля:**

```ini
BOT_TOKEN=8685300793:AAGZ5djb-O7z9GZ_wn6kNCaz45brWMZyEEY
WEBAPP_URL=https://u1893136.isp.regruhosting.ru
DOMAIN=u1893136.isp.regruhosting.ru
DATABASE_URL=mysql+aiomysql://skilluser:skillpass@localhost:3306/skilltracer
MYSQL_DATABASE=skilltracer
MYSQL_USER=skilluser
MYSQL_PASSWORD=your_secure_password
SECRET_KEY=$(openssl rand -hex 32)
ENVIRONMENT=production
```

> ⚠️ **Важно**: `chmod 600 .env` — только владелец должен читать файл с паролями!

### 3. Запуск установочного скрипта

```bash
sudo chmod +x install.sh
sudo ./install.sh
```

Скрипт автоматически:
- Создаст пользователя `skilltracer`
- Установит Python 3.10+ (или 3.12 через deadsnakes)
- Создаст virtualenv в `/opt/skilltracer/venv`
- Установит зависимости
- Установит и запустит Caddy
- Скопирует systemd units
- Настроит firewall (UFW / firewalld)
- Добавит cron для ежедневных бэкапов

### 4. Проверка токена и установка webhook

```bash
sudo /opt/skilltracer/venv/bin/python /opt/skilltracer/scripts/verify_bot.py
```

Ожидаемый вывод:
```
✅ Токен валиден!
   🤖 Бот: Skill Tracer
   🔗 Username: @skilltracer_bot
   🆔 ID: 8685300793
🔧 Устанавливаем webhook: https://u1893136.isp.regruhosting.ru/webhook
✅ Webhook успешно установлен
```

### 5. Настройка MySQL

```bash
sudo /opt/skilltracer/scripts/setup_mysql.sh
```

Скрипт создаст базу `skilltracer` с кодировкой `utf8mb4_unicode_ci` и пользователя `skilluser@localhost`.

> Если MySQL ещё не установлен:
> ```bash
> sudo apt-get install mysql-server
> sudo mysql_secure_installation
> ```

### 6. Миграции базы данных

```bash
sudo /opt/skilltracer/scripts/migrate.sh
```

Должно создаться **8 таблиц**: `users`, `custom_trackers`, `daily_entries`, `entry_metrics`, `week_reports`, `groups`, `group_members`, `comments`.

Проверка:
```bash
mysql -u skilluser -p skilltracer -e "SHOW TABLES;"
```

### 7. Запуск сервисов

```bash
sudo systemctl daemon-reload
sudo systemctl enable skilltracer caddy
sudo systemctl start skilltracer caddy
```

---

## 🎮 Управление сервисами

### Skill Tracer backend

```bash
# Статус
sudo systemctl status skilltracer

# Логи в реальном времени
sudo journalctl -u skilltracer -f

# Перезапуск (после обновления кода)
sudo systemctl restart skilltracer

# Остановка
sudo systemctl stop skilltracer
```

### Caddy

```bash
# Статус
sudo systemctl status caddy

# Перезагрузка конфига
sudo systemctl reload caddy

# Проверка валидности Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile
```

### MySQL

```bash
sudo systemctl status mysql
sudo systemctl restart mysql
```

---

## 🛠 Полезные команды

### Health check

```bash
sudo /opt/skilltracer/venv/bin/python /opt/skilltracer/scripts/healthcheck.py
```

### Ручной бэкап

```bash
sudo /opt/skilltracer/scripts/backup.sh
```

Бэкапы сохраняются в `/opt/skilltracer/backups/`. Старые (>7 дней) удаляются автоматически.

### Проверка памяти

```bash
free -h
ps aux --sort=-%mem | head -10
```

### Проверка портов

```bash
sudo ss -tlnp | grep -E ':(80|443|8000|3306)'
```

### Обновление кода

```bash
cd /opt/skilltracer
sudo git pull origin master
sudo chown -R skilltracer:skilltracer /opt/skilltracer
sudo systemctl restart skilltracer
```

---

## 🔥 Устранение неполадок

### Сервис не стартует: `systemctl status skilltracer` показывает failed

```bash
# Смотрим детальные логи
sudo journalctl -u skilltracer -n 50 --no-pager

# Частые причины:
# 1. Нет .env файла
ls -la /opt/skilltracer/backend/.env

# 2. Неправильный DATABASE_URL
sudo -u skilltracer /opt/skilltracer/venv/bin/python -c \
  "from app.config import settings; print(settings.DATABASE_URL)"

# 3. MySQL недоступен
sudo systemctl status mysql
mysql -u skilluser -p -e "SELECT 1"
```

### Caddy не открывает HTTPS

```bash
# Проверьте что DOMAIN задан
sudo grep DOMAIN /opt/skilltracer/backend/.env

# Проверьте валидность Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile

# Проверьте открытость портов 80 и 443
sudo ss -tlnp | grep -E ':(80|443)'
```

### OOM (out of memory) — сервис падает

На Host-0 с 1GB RAM критично:
- Uvicorn запущен с `--workers 1` (проверьте `systemd/skilltracer.service`)
- SQLAlchemy pool `max_overflow=0` (уже настроено)
- MySQL настроен с `innodb_buffer_pool_size = 64M`

Добавьте в `/etc/mysql/mysql.conf.d/mysqld.cnf`:
```ini
[mysqld]
innodb_buffer_pool_size = 64M
key_buffer_size = 16M
max_connections = 20
```

### Бот не отвечает

```bash
# Проверьте webhook
sudo -u skilltracer /opt/skilltracer/venv/bin/python /opt/skilltracer/scripts/verify_bot.py

# Проверьте что FastAPI слушает 8000
sudo ss -tlnp | grep 8000
curl -s http://127.0.0.1:8000/health | python3 -m json.tool
```

---

## 🗑 Удаление

```bash
cd /opt/skilltracer
sudo ./uninstall.sh
```

Скрипт удалит:
- systemd сервисы
- cron задачи
- директорию приложения (опционально)
- системного пользователя (опционально)

> **MySQL данные и `.env` не удаляются автоматически.**

---

## ✅ Checklist Production Ready

- [ ] `.env` создан, `chmod 600` применён
- [ ] `BOT_TOKEN` валиден (`verify_bot.py` проходит)
- [ ] MySQL база создана (`setup_mysql.sh`)
- [ ] Alembic миграции применены (`migrate.sh`)
- [ ] `skilltracer.service` активен (`systemctl status skilltracer`)
- [ ] Caddy слушает 80/443 (`systemctl status caddy`)
- [ ] HTTPS работает (`curl -I https://$DOMAIN/health`)
- [ ] Webhook установлен (`verify_bot.py`)
- [ ] Firewall закрывает 8000 и 3306
- [ ] Бэкапы настроены (cron)
- [ ] Тесты проходят (`pytest backend/tests/ -v`)

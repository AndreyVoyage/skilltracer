# 🚀 Деплой Skill Tracer на reg.ru Host-0

Это полная инструкция по развёртыванию Skill Tracer на VPS reg.ru (Host-0 тариф).

## 📋 Требования

- **Хостинг**: reg.ru Host-0 (VPS)
- **Домен**: http://u1893136.isp.regruhosting.ru/ (будет HTTPS)
- **ОС**: Ubuntu 20.04/22.04
- **Ресурсы**: 1 CPU, 2 GB RAM, 13 GB SSD
- **SSH доступ**: нужен для настройки

## 🔐 Безопасность - Чеклист перед деплоем

- [ ] **BOT_TOKEN** в `.env`, не в коде (получить у @BotFather)
- [ ] **SECRET_KEY** изменён на случайный (32+ символа)
- [ ] **MySQL пароль** сложный (генерировать в ISPmanager)
- [ ] `/docs` отключен в production (или защищён)
- [ ] **CORS** настроен только на ваш домен
- [ ] **Rate limiting** установлен (рекомендуется)

## 🛠️ Шаг 1: Подготовка MySQL (ISPmanager)

1. Зайдите в **ISPmanager** (ссылка из письма reg.ru)
2. Перейдите в раздел **Базы данных** → **Создать**
3. Заполните:
   - **Имя базы**: `u1893136_skilltracer`
   - **Кодировка**: `utf8mb4_unicode_ci`
   - **Пользователь**: создать нового `u1893136_skilluser`
   - **Пароль**: сгенерировать сложный (сохраните!)
4. Нажмите **Сохранить**

Запишите данные подключения для `.env`:
```
Host: localhost
Database: u1893136_skilltracer
User: u1893136_skilluser
Password: [ваш_сгенерированный_пароль]
```

## 📦 Шаг 2: Подключение по SSH

```bash
# Подключитесь к серверу (логин и IP из письма reg.ru)
ssh u1893136@u1893136.isp.regruhosting.ru

# Или если используете ключ:
ssh -i ~/.ssh/your_key u1893136@u1893136.isp.regruhosting.ru
```

## 🖥️ Шаг 3: Установка зависимостей

### Автоматическая установка (рекомендуется)

```bash
# На сервере:
cd /home/u1893136

# Скопируйте setup.sh и запустите:
chmod +x setup.sh
sudo ./setup.sh u1893136
```

### Ручная установка (если скрипт не сработал)

```bash
# Обновление системы
sudo apt update

# Установка Python 3.12
sudo apt install software-properties-common -y
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install python3.12 python3.12-venv python3.12-dev -y

# MySQL библиотеки
sudo apt install libmysqlclient-dev pkg-config -y

# Caddy
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy -y
sudo systemctl enable caddy
```

## 📂 Шаг 4: Загрузка кода

### Вариант A: Через Git (рекомендуется)

```bash
# На локальной машине - запушьте код
git init
git add .
git commit -m "Initial production deploy"
git remote add origin [ваш-git-репозиторий]
git push -u origin main

# На сервере - клонируйте
cd /home/u1893136
git clone [ваш-git-репозиторий] skilltracer
cd skilltracer
```

### Вариант B: Через SFTP/SCP

```bash
# На локальной машине:
scp -r backend u1893136@u1893136.isp.regruhosting.ru:/home/u1893136/skilltracer/
scp -r deploy u1893136@u1893136.isp.regruhosting.ru:/home/u1893136/skilltracer/
```

## ⚙️ Шаг 5: Настройка окружения

```bash
cd /home/u1893136/skilltracer/backend

# Создайте виртуальное окружение
python3.12 -m venv venv
source venv/bin/activate

# Установите зависимости
pip install --upgrade pip
pip install -r requirements.txt

# Создайте .env файл
cp .env.production .env
nano .env  # Редактируйте, вставьте свои значения
```

**Важно заполнить в `.env`:**
- `BOT_TOKEN` - от @BotFather
- `DATABASE_URL` - данные из ISPmanager
- `SECRET_KEY` - `openssl rand -hex 32`

## 🗄️ Шаг 6: Миграции базы данных

```bash
# Внутри виртуального окружения:
cd /home/u1893136/skilltracer/backend
source venv/bin/activate

# Примените миграции
alembic upgrade head

# Проверьте подключение к БД
python -c "from app.database import async_engine; import asyncio; asyncio.run(async_engine.connect())"
```

## 🌐 Шаг 7: Настройка Caddy

```bash
# Скопируйте конфигурацию
sudo cp /home/u1893136/skilltracer/deploy/caddy/Caddyfile /etc/caddy/Caddyfile

# Проверьте конфигурацию
sudo caddy validate --config /etc/caddy/Caddyfile

# Перезапустите Caddy
sudo systemctl reload caddy

# Проверьте статус
sudo systemctl status caddy
```

## ⚡ Шаг 8: Systemd сервис

```bash
# Скопируйте сервис
sudo cp /home/u1893136/skilltracer/deploy/systemd/skilltracer.service /etc/systemd/system/

# Перезагрузите systemd
sudo systemctl daemon-reload

# Включите автозапуск
sudo systemctl enable skilltracer

# Запустите
sudo systemctl start skilltracer

# Проверьте статус
sudo systemctl status skilltracer
```

## ✅ Шаг 9: Проверка работы

```bash
# Проверка health endpoint
curl http://localhost:8000/health

# Проверка через домен (HTTP)
curl http://u1893136.isp.regruhosting.ru/health

# Проверка HTTPS (после выпуска сертификата, ~1-2 минуты)
curl https://u1893136.isp.regruhosting.ru/health
```

Ответ должен быть:
```json
{
  "status": "healthy",
  "database": "connected",
  "bot": "active",
  "version": "0.1.0"
}
```

## 📱 Шаг 10: Настройка Telegram Bot

1. Найдите своего бота в Telegram
2. Отправьте `/start`
3. Должно прийти приветственное сообщение с кнопкой WebApp
4. Нажмите кнопку "Открыть Skill Tracer"
5. Mini App должен открыться с вашего домена

## 🔄 Управление приложением

### Перезапуск после обновления кода

```bash
# Перейдите в директорию
cd /home/u1893136/skilltracer

# Обновите код (git)
git pull

# Или перезалейте файлы (SFTP)

# Перезапустите сервис
sudo systemctl restart skilltracer

# Проверьте статус
sudo systemctl status skilltracer
```

### Просмотр логов

```bash
# Логи приложения (в реальном времени)
sudo journalctl -u skilltracer -f

# Логи за последний час
sudo journalctl -u skilltracer --since "1 hour ago"

# Логи Caddy
sudo tail -f /var/log/caddy/skilltracer.log

# Логи ошибок
sudo journalctl -u skilltracer --priority=err
```

### Работа с БД

```bash
# Подключение к MySQL
mysql -u u1893136_skilluser -p u1893136_skilltracer

# Просмотр таблиц
SHOW TABLES;

# Проверка пользователей
SELECT id, username, first_name FROM users;
```

## 🆘 Устранение неполадок

### Приложение не запускается

```bash
# Проверьте статус
sudo systemctl status skilltracer

# Проверьте логи на ошибки
sudo journalctl -u skilltracer -n 50

# Проверьте .env файл
ls -la /home/u1893136/skilltracer/backend/.env

# Проверьте права доступа
ls -la /home/u1893136/skilltracer/
```

### Ошибка подключения к БД

```bash
# Проверьте что MySQL работает
sudo systemctl status mysql

# Проверьте подключение
mysql -u u1893136_skilluser -p -e "SELECT 1"

# Проверьте DATABASE_URL в .env
grep DATABASE_URL /home/u1893136/skilltracer/backend/.env
```

### Caddy не получает SSL

```bash
# Проверьте что домен резолвится
ping u1893136.isp.regruhosting.ru

# Проверьте логи Caddy
sudo journalctl -u caddy -f

# Перезапустите Caddy
sudo systemctl restart caddy
```

### 502 Bad Gateway

```bash
# Проверьте что приложение слушает порт 8000
sudo ss -tlnp | grep 8000

# Проверьте что сервис запущен
sudo systemctl status skilltracer

# Перезапустите оба сервиса
sudo systemctl restart skilltracer
sudo systemctl restart caddy
```

## 📊 Ограничения Host-0 (важно!)

| Ресурс | Лимит | Рекомендация |
|--------|-------|--------------|
| **CPU** | 1 core (3456 CP) | Не используйте тяжелые JSON запросы |
| **RAM** | 2 GB | 2 workers для uvicorn максимум |
| **Диск** | 13 GB | Логи ротируются, файлы не храним |
| **Процессы** | 36 max | Проверьте: `ulimit -u` |

## 🔒 Безопасность (дополнительно)

### Отключение Swagger в production

В `backend/.env`:
```env
ENVIRONMENT=production
```

В production режиме Swagger будет доступен только через VPN или localhost.

### Настройка fail2ban (рекомендуется)

```bash
sudo apt install fail2ban
sudo systemctl enable fail2ban
```

### Регулярные бэкапы БД

```bash
# Добавьте в crontab
crontab -e

# Ежедневный бэкап в 3:00
0 3 * * * mysqldump -u u1893136_skilluser -p'пароль' u1893136_skilltracer > /home/u1893136/backups/skilltracer_$(date +\%Y\%m\%d).sql
```

## 📞 Поддержка

Если что-то не работает:

1. Проверьте логи: `sudo journalctl -u skilltracer -f`
2. Проверьте health: `curl http://localhost:8000/health`
3. Убедитесь что `.env` правильный
4. Проверьте что MySQL работает

## ✅ Чеклист деплоя

- [ ] MySQL база создана в ISPmanager
- [ ] `.env` файл создан с правильными данными
- [ ] Python 3.12 установлен
- [ ] Зависимости установлены (`pip install -r requirements.txt`)
- [ ] Миграции применены (`alembic upgrade head`)
- [ ] Caddy настроен и работает
- [ ] Systemd сервис запущен и включен
- [ ] Health check проходит (`/health`)
- [ ] HTTPS работает
- [ ] Telegram бот отвечает на `/start`
- [ ] WebApp открывается по кнопке

---

**🎉 Поздравляем! Ваш Skill Tracer работает на reg.ru!**

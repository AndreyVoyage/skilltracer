# 🎯 Skill Tracer

Телеграм-бот для отслеживания навыков и прогресса обучения.

> **Оптимизировано для Reg.ru Host-0** (13GB диска, ограниченные ресурсы)

## 🚀 Быстрый старт

```bash
# 1. Клонировать репозиторий
git clone <repo-url>
cd skill-tracer

# 2. Скопировать и настроить .env
cp .env.example .env
# Отредактировать .env, добавить BOT_TOKEN

# 3. Запустить
sudo docker-compose up -d
```

## 📋 Требования

- **Docker** 20.10+
- **Docker Compose** 2.0+
- **Домен** (для production, для локального тестирования подойдёт localhost)

## ⚙️ Настройка

### 1. Telegram Bot Token

1. Напишите [@BotFather](https://t.me/botfather) в Telegram
2. Создайте нового бота: `/newbot`
3. Скопируйте токен в `.env`:
   ```
   BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxyz
   ```

### 2. Конфигурация окружения

Отредактируйте `.env` файл:

```bash
# Для локальной разработки:
ENVIRONMENT=development
DOMAIN=localhost
WEBAPP_URL=http://localhost

# Для production:
ENVIRONMENT=production
DOMAIN=your-domain.ru
WEBAPP_URL=https://your-domain.ru
```

### 3. Запуск

```bash
# Запуск всех сервисов
sudo docker-compose up -d

# Просмотр логов
sudo docker-compose logs -f

# Остановка
sudo docker-compose down
```

## ✅ Проверка работы

### Health Check

```bash
# Проверка API
curl http://localhost/health

# Ожидаемый ответ:
{
  "status": "healthy",
  "database": "connected",
  "response_time_ms": 15.23,
  "version": "0.1.0",
  "environment": "development"
}
```

### Проверка сервисов

```bash
# Список запущенных контейнеров
sudo docker-compose ps

# Проверка логов
sudo docker-compose logs backend
sudo docker-compose logs mysql
sudo docker-compose logs caddy
```

### Запуск тестов

```bash
# Запуск тестов внутри контейнера
sudo docker-compose exec backend pytest tests/ -v
```

## 📁 Структура проекта

```
skill-tracer/
├── backend/              # FastAPI + Aiogram бот
│   ├── app/
│   │   ├── main.py       # Entry point FastAPI
│   │   ├── config.py     # Настройки (Pydantic)
│   │   ├── database.py   # SQLAlchemy + async MySQL
│   │   ├── models/       # SQLAlchemy модели
│   │   └── api/          # API endpoints
│   ├── tests/            # Pytest тесты
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/             # React 18 + Vite
│   ├── src/
│   ├── index.html
│   └── package.json
├── caddy/                # Reverse proxy
│   └── Caddyfile         # Конфиг Caddy (авто HTTPS)
├── docker-compose.yml    # Orchestration
├── .env.example          # Шаблон переменных
└── README.md             # Этот файл
```

## 🐛 Устранение неполадок

### MySQL не стартует

```bash
# Проверить логи
sudo docker-compose logs mysql

# Если проблемы с правами, удалить данные и пересоздать:
sudo docker-compose down -v
sudo docker-compose up -d mysql

# Подождать 30 секунд и проверить
sudo docker-compose ps
```

### Порт 80 или 443 занят

```bash
# Найти процесс, занимающий порт
sudo lsof -i :80
sudo lsof -i :443

# Остановить процесс или изменить порты в docker-compose.yml
```

### Ошибка подключения к БД

```bash
# Проверить что MySQL healthy
sudo docker-compose ps

# Перезапустить backend после MySQL
sudo docker-compose restart backend
```

### Проблемы с Caddy / HTTPS

```bash
# Для localhost HTTPS не используется (нормально)
# Для production убедитесь что DOMAIN указан правильно

# Проверить Caddy логи
sudo docker-compose logs caddy

# Пересоздать Caddy данные
sudo docker-compose down
sudo rm -rf caddy_data/ caddy_config/
sudo docker-compose up -d
```

## ⚠️ Ограничения Host-0

Данная конфигурация оптимизирована для **Reg.ru Host-0** с ограниченными ресурсами:

| Ресурс | Лимит | Конфигурация |
|--------|-------|--------------|
| **RAM** | ~1GB | MySQL ограничен 512MB |
| **Диск** | 13GB | Логи ротируются (10MB × 3 файла) |
| **CPU** | 1 core | MySQL ограничен 0.5 CPU |

### Важные ограничения:

- **Не храните файлы в контейнерах** — используйте только `file_id` Telegram
- **Логи ротируются** — настроена ротация в Caddy и ограничение размера
- **База данных** — том `mysql_data` персистентен, но не делайте слишком больших запросов

### Почему Caddy вместо Nginx?

- **Меньше конфигурации** — Caddyfile проще nginx.conf
- **Автоматический HTTPS** — Let's Encrypt без ручной настройки
- **Меньше памяти** — alpine образ минималистичен

## 🔧 Команды для разработки

```bash
# Пересборка backend после изменений
sudo docker-compose up -d --build backend

# Выполнить команду внутри backend
sudo docker-compose exec backend python -c "print('Hello')"

# Доступ к MySQL
sudo docker-compose exec mysql mysql -uskilluser -pskillpass skilltracer

# Bash внутри контейнера
sudo docker-compose exec backend bash
```

## 📚 Документация API

При запуске в development режиме доступна документация:

- **Swagger UI**: http://localhost/docs
- **ReDoc**: http://localhost/redoc
- **OpenAPI JSON**: http://localhost/openapi.json

## 📝 Лицензия

MIT License

https://api.telegram.org/bot8685300793:AAGZ5djb-O7z9GZ_wn6kNCaz45brWMZyEEY/setWebhook?url=https://skilltracer.art-artel.su/webhook
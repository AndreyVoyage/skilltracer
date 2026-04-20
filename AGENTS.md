# Skill Tracer — Agent Guide

> **Language note:** Вся документация, комментарии в коде и README проекта написаны на русском языке. Данный файл также составлен на русском, чтобы соответствовать конвенциям проекта.

## Обзор проекта

**Skill Tracer** — это Telegram-бот и Mini App для отслеживания навыков и прогресса обучения. Пользователь заполняет ежедневные записи (настроение, трекеры, медиа) через веб-приложение внутри Telegram или напрямую через бота. Приложение агрегирует данные в недельные отчёты, которые можно публиковать и делиться с друзьями через группы.

### Технологический стек

| Компонент | Технология |
|-----------|-----------|
| Backend | Python 3.12, FastAPI, Aiogram 3, SQLAlchemy 2.0, Pydantic Settings |
| База данных | PostgreSQL 15 (primary через `asyncpg`), SQLite (`aiosqlite`) для локальной разработки |
| Frontend | React 19.2, TypeScript 6.0, Vite 8, react-router-dom 7, Axios |
| Telegram Bot | Aiogram 3 (polling в dev, webhook в production) |
| Миграции БД | Alembic |
| Reverse Proxy | Caddy 2 (автоматический HTTPS через Let's Encrypt) |
| Тестирование | pytest, pytest-asyncio, httpx |
| Отчёты | matplotlib, Pillow (PNG/JPEG) |
| Логирование | loguru, стандартный logging |

## Архитектура

### Backend (`backend/`)

Единое FastAPI-приложение (`app/main.py`), в котором внутри одного процесса запущены и REST API, и Telegram-бот.

- **Lifespan** (`app/main.py`): при старте инициализирует БД (с retry), устанавливает команды бота, запускает polling или webhook. При shutdown — graceful остановка бота и закрытие соединений с БД.
- **CORS**: в development — `*`, в production — ограниченный список (WEBAPP_URL, Telegram домены).
- **Swagger/ReDoc**: доступны только в development (`/docs`, `/redoc`). В production отключены.

#### Модули

| Путь | Назначение |
|------|-----------|
| `app/api/v1/endpoints/` | REST endpoints: `users.py`, `entries.py`, `reports.py`, `groups.py`, `trackers.py`, `media.py` |
| `app/api/deps.py` | Зависимости FastAPI: `get_db()`, `get_current_user()`, `validate_telegram_init_data()` |
| `app/bot/handlers/` | Обработчики бота: `commands.py`, `journal.py`, `collection.py`, `skills.py`, `callbacks.py`, `settings_menu.py`, `webapp_data.py` |
| `app/models/` | SQLAlchemy 2.0 модели: `User`, `CustomTracker`, `DailyEntry`, `EntryMetric`, `WeekReport`, `Comment`, `Group`, `GroupMember`, `ReportLink`, `TelegramQueue`, `JournalEntry` |
| `app/services/` | Бизнес-логика: `report_generator.py` |
| `app/database.py` | Async engine, sessionmaker, `get_db()` с авто-коммитом/rollback |
| `app/config.py` | Pydantic Settings, загрузка из `.env` |

#### Двойственная система записей

В проекте существуют **две параллельные модели записей**:
- **`DailyEntry`** — создаётся через WebApp (React Mini App).
- **`JournalEntry`** — создаётся через бота (обработчик `journal.py`).

Endpoint `/entries/week` объединяет (merge) данные из обеих таблиц для отображения недельного вида. Это важный нюанс при работе с записями.

#### Медиа

Ранее медиа хранились в отдельных полях (`photo_file_id`, `video_file_id`, `voice_file_id`). В текущей версии используется unified массив `media_files` (JSON) в `DailyEntry`. Бот-обработчик `collection.py` **добавляет** (append) медиа к сегодняшней записи. Legacy-поля пока сохраняются для обратной совместимости.

### Frontend (`frontend/`)

React SPA, собираемая Vite. Статический билд помещается в `frontend/dist/`.

- **Входная точка**: `src/main.tsx` (монтирует `<App />`, инициализирует `Telegram.WebApp`).
- **Роутинг** (`src/App.tsx`):
  - `/` — `Home` (недельный дашборд)
  - `/day/:date` — `DayDetail` (детальный вид дня, форма, медиа-галерея)
  - `/report/:token` — `PublicReport` (публичный отчёт по ссылке)
- **Авторизация**: через Telegram `initData` (HMAC-SHA256). Fallback на `user_id` в query params работает **только в development** (в production пишет warning).
- **API клиент**: Axios с base URL `/api/v1`.

### База данных и миграции

- SQLAlchemy 2.0 стиль: `Mapped[]`, `mapped_column`, type hints.
- Alembic миграции лежат в `backend/alembic/versions/`.
- Важно: первичный ключ `User.id` — это Telegram user ID (`BigInteger`), не автоинкремент.
- При первой авторизации через Mini App автоматически создаётся пользователь и 4 дефолтных трекера (Здоровье ❤️, Спорт 🏃, Учёба 📚, Отдых 🧘).

## Структура проекта

```
skill-tracer/
├── backend/                 # FastAPI + Aiogram backend
│   ├── app/
│   │   ├── main.py          # Entry point, lifespan, routes
│   │   ├── config.py        # Pydantic Settings
│   │   ├── database.py      # SQLAlchemy async engine/sessions
│   │   ├── api/
│   │   │   ├── deps.py      # Auth, DB dependencies
│   │   │   └── v1/
│   │   │       ├── api.py   # API router assembly
│   │   │       └── endpoints/ # CRUD endpoints
│   │   ├── bot/
│   │   │   ├── __init__.py  # Bot & dispatcher init
│   │   │   ├── handlers/    # Message & callback handlers
│   │   │   ├── keyboards.py # Inline & reply keyboards
│   │   │   ├── middlewares.py
│   │   │   ├── media_cache.py
│   │   │   └── notifications.py
│   │   ├── models/          # SQLAlchemy models
│   │   └── services/        # Business logic (reports)
│   ├── tests/               # pytest suite
│   ├── alembic/             # DB migrations
│   ├── cron/                # Legacy cron scripts
│   ├── scripts/             # Diagnostic & utility scripts
│   ├── requirements.txt
│   ├── Dockerfile
│   └── alembic.ini
├── frontend/                # React 19 + Vite
│   ├── src/
│   │   ├── App.tsx
│   │   ├── pages/           # Home, DayDetail, PublicReport
│   │   ├── components/      # Layout, DayGrid, EntryForm, MediaGallery, etc.
│   │   ├── hooks/           # useTelegram, useEntries, useTheme
│   │   ├── api/             # Axios client
│   │   └── utils/           # debug helpers
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json (root + app + node)
├── deploy/                  # Production configs
│   ├── caddy/Caddyfile
│   ├── scripts/setup.sh
│   └── systemd/skilltracer.service
├── scripts/                 # Root-level ops scripts
│   ├── backup.sh
│   ├── healthcheck.py
│   ├── migrate.sh
│   ├── setup_mysql.sh
│   └── verify_bot.py
├── caddy/                   # Caddy install helper
├── api/                     # Legacy PHP API (пусто, не используется)
├── config/                  # Legacy PHP config (пусто)
├── install.sh               # Native VPS installer
├── uninstall.sh             # Native VPS uninstaller
├── docker-compose.yml       # Docker dev setup (postgres + backend + caddy)
├── .env.example             # Env template
└── package.json             # Root (telegraf, legacy)
```

## Сборка и запуск

### Локальная разработка (Docker Compose)

```bash
# 1. Скопировать .env
cp .env.example .env
# Отредактировать BOT_TOKEN, WEBAPP_URL, DOMAIN

# 2. Запуск
sudo docker-compose up -d

# 3. Проверка
curl http://localhost/health

# 4. Логи
sudo docker-compose logs -f
```

Docker Compose поднимает: PostgreSQL 15-alpine (лимит 512MB RAM), FastAPI backend, Caddy reverse proxy.

### Локальная разработка frontend

```bash
cd frontend
npm install
npm run dev      # Vite dev server
npm run build    # tsc -b && vite build → dist/
npm run lint     # ESLint
```

### Native VPS deployment (production)

```bash
# Установка (требуется root)
sudo ./install.sh [username]

# Скрипт выполняет:
# - Создание системного пользователя
# - Установку Python 3.10+ (предпочтительно 3.12)
# - Создание venv в /opt/skilltracer/venv
# - Установку Caddy
# - Копирование systemd unit
# - Настройку firewall (открывает 80/443, закрывает 8000/3306)
# - backup cron на 03:00
```

Systemd unit: `deploy/systemd/skilltracer.service` (или `/etc/systemd/system/skilltracer.service`).

## Тестирование

```bash
# Внутри Docker-контейнера backend
sudo docker-compose exec backend pytest tests/ -v

# Локально (с активным venv в backend/)
cd backend
pytest tests/ -v
```

### Структура тестов

| Файл | Что тестирует |
|------|--------------|
| `tests/conftest.py` | Fixtures: `async_engine` (create/drop tables), `db_session` (rollback) |
| `tests/test_api/conftest.py` | `client` (TestClient), `auth_headers_user*` (валидный initData) |
| `tests/test_api/test_auth.py` | Валидация initData (валидный, невалидный, просроченный, отсутствующий) |
| `tests/test_api/test_entries.py` | CRUD записей, 10-дневный лимит редактирования, приватность |
| `tests/test_api/test_media.py` | API добавления/удаления медиа |
| `tests/test_models.py` | Модели: constraints, группы, комментарии, publish report |
| `tests/test_bot.py` | Моки хендлеров, media cache, keyboards |
| `tests/test_report_generator.py` | Генерация отчётов, кэширование |

Важно: `tests/conftest.py` использует ту же `DATABASE_URL`, что и приложение (не отдельную тестовую БД по умолчанию). `tests/test_media.py` создаёт отдельный engine на `skilltracer_test`.

## Стиль кода и конвенции

### Python (Backend)

- **Python 3.12**, async/await везде где возможно.
- SQLAlchemy 2.0: `Mapped[]`, `mapped_column`, аннотации типов.
- Импорты: стандартные библиотеки → сторонние → внутренние (`app.*`).
- Логирование через `logging.getLogger(__name__)` или `loguru`.
- Комментарии и docstrings — на русском языке.
- Конфигурация только через `app.config.settings` (Pydantic), никаких хардкодов в бизнес-логике.

### TypeScript / React (Frontend)

- TypeScript со строгими настройками (`noUnusedLocals`, `noUnusedParameters`).
- `verbatimModuleSyntax: true` — импорты типов через `import type`.
- ESLint 9 flat config: `@eslint/js`, `typescript-eslint`, `react-hooks`, `react-refresh`.
- Компоненты — функциональные, hooks.
- `// eslint-disable-next-line no-console` допустим для Telegram WebApp отладки.

### Общие правила

- Не оставлять секреты в коде. Использовать `.env` + `settings`.
- Не модифицировать Alembic-миграции после коммита — создавать новые.
- При добавлении полей в модели — обновить Alembic и тесты.

## Переменные окружения

Копировать `.env.example` → `.env` и заполнить:

| Переменная | Описание | Пример |
|-----------|----------|--------|
| `BOT_TOKEN` | Токен от @BotFather | `123456:ABC...` |
| `WEBAPP_URL` | URL Mini App | `https://domain.ru` |
| `DOMAIN` | Домен для Caddy/webhook | `domain.ru` |
| `DATABASE_URL` | Async DB URL | `postgresql+asyncpg://user:pass@localhost/db` |
| `SECRET_KEY` | Для подписей | `openssl rand -hex 32` |
| `ENVIRONMENT` | `development` или `production` | `production` |
| `UVICORN_WORKERS` | Кол-во workers (для 1GB RAM = 1) | `1` |
| `DB_POOL_SIZE` | Размер пула SQLAlchemy | `5` |
| `LOG_LEVEL` | Уровень логирования | `INFO` |
| `TELEGRAM_PROXY` | SOCKS5 прокси (опц.) | `socks5://user:pass@host:port` |

## Безопасность

### Критические замечания

1. **Хардкоды секретов**: В репозитории есть файлы с захардкоженными credentials:
   - `backend/cron/process_updates.py` — захардкожен `BOT_TOKEN`.
   - `backend/config/database.py` — захардкожены MySQL credentials.
   - **Не коммитить новые секреты.** Использовать `.env`.

2. **Auth fallback**: `deps.py` позволяет fallback на `user_id` в query params. В development это нормально, в production пишет warning, но всё равно работает. Не удалять без согласования — используется для Android WebView.

3. **CORS**: В development `allow_origins=["*"]`. В production ограничено.

4. **Caddy / systemd**: Production hardened — `ProtectSystem=strict`, `NoNewPrivileges=true`, `Referrer-Policy`, `X-Frame-Options`.

5. **Backup**: `scripts/backup.sh` делает SQL dump в `/opt/skilltracer/backups/` с ротацией 7 дней.

## Деплой и DevOps

### Два режима деплоя

Проект находится в переходном состоянии: документация описывает два режима, но активный — **VPS Native**.

#### A. Docker Compose (development / тестирование)
- `docker-compose.yml` — postgres + backend + caddy.
- Backend Dockerfile использует `--reload` (dev mode).
- Healthcheck на `/health`.

#### B. Native VPS (production, primary)
- `install.sh` + `uninstall.sh`.
- Caddy reverse proxy → uvicorn на `127.0.0.1:8000`.
- Systemd unit с 2 workers (рекомендуется 1 для 1GB RAM).
- `scripts/healthcheck.py` — проверяет systemd, HTTP health, БД.
- `scripts/migrate.sh` — запуск Alembic.
- `scripts/backup.sh` — ежедневный backup.

#### C. Shared Hosting (legacy, не поддерживается)
- Документирован в `DEPLOY_SUBDOMAIN.md`, `TESTING.md`, `TEST_LAUNCH.md`.
- Подразумевал PHP API (`api/*.php`) + Python cron (`backend/cron/process_updates.py`).
- **PHP файлы отсутствуют** в репозитории (`api/` и `config/` пусты). Не использовать для нового деплоя.

### Полезные команды

```bash
# Health check
python scripts/healthcheck.py

# Проверка валидности токена бота
python scripts/verify_bot.py

# Alembic миграции
cd backend && alembic upgrade head

# Backup
sudo ./scripts/backup.sh

# Доступ к БД внутри Docker
sudo docker-compose exec postgres psql -U skilluser -d skilltracer

# Bash в backend контейнере
sudo docker-compose exec backend bash
```

## Важные нюансы для агента

- **Язык проекта**: русский. Комментарии, docstrings, логи, сообщения бота — всё на русском.
- **Двойственные записи**: есть `DailyEntry` и `JournalEntry`. Endpoint `/entries/week` мержит их. Не путать.
- **Медиа эволюция**: поля `photo_file_id`, `video_file_id`, `voice_file_id` — legacy. Актуальный формат — `media_files` (JSON array).
- **Bot + FastAPI в одном процессе**: бот не отдельный сервис, а задача внутри lifespan FastAPI. Это влияет на graceful shutdown.
- **User.id = Telegram ID**: нет отдельной автоинкрементной колонки для пользователя.
- **Default trackers**: при создании пользователя через Mini App создаются 4 трекера. Если меняешь логику создания — обнови и тесты.
- **Frontend билд**: `npm run build` в `frontend/` → `frontend/dist/`. Caddy может раздавать статику оттуда (закомментировано в Caddyfile).
- **Gitignore**: `frontend/dist/` в `.gitignore`, `backend/venv/` в `.gitignore`.

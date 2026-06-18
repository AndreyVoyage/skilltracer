# SkillTracer — Development Setup Guide

## Windows + Git Bash Environment

### Python Location

Python is installed at:
```
C:\Users\andrc\AppData\Local\Python\pythoncore-3.14-64\python.exe
```

In Git Bash, use the POSIX path:
```bash
/c/Users/andrc/AppData/Local/Python/pythoncore-3.14-64/python.exe
```

### Quick Commands

```bash
# Run tests (with env vars for testing)
export DATABASE_URL="sqlite+aiosqlite:///:memory:"
export SECRET_KEY="test-secret-key-for-unit-tests-only-32"
export TELEGRAM_BOT_TOKEN="1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
/c/Users/andrc/AppData/Local/Python/pythoncore-3.14-64/python.exe -m pytest tests/ -v

# Or create .env file and run without exports
/c/Users/andrc/AppData/Local/Python/pythoncore-3.14-64/python.exe -m pytest tests/ -v

# Install dependencies
/c/Users/andrc/AppData/Local/Python/pythoncore-3.14-64/python.exe -m pip install -r requirements.txt

# Run server locally
/c/Users/andrc/AppData/Local/Python/pythoncore-3.14-64/python.exe -m uvicorn app.main:app --reload

# Alembic migrations
/c/Users/andrc/AppData/Local/Python/pythoncore-3.14-64/python.exe -m alembic revision --autogenerate -m "message"
/c/Users/andrc/AppData/Local/Python/pythoncore-3.14-64/python.exe -m alembic upgrade head
```

### Alternative: Create Alias

Add to `~/.bashrc`:
```bash
alias pywin='/c/Users/andrc/AppData/Local/Python/pythoncore-3.14-64/python.exe'
```

Then use:
```bash
pywin -m pytest tests/ -v
```

### VS Code Remote SSH

Server: `root@157.22.187.38`

VS Code extensions configured in `.vscode/extensions.json`:
- Python
- Pylance
- Remote - SSH
- Docker
- ESLint
- Prettier

### Project Structure

```
skilltracer/
├── backend/          FastAPI + SQLAlchemy + Alembic
│   ├── app/
│   ├── tests/
│   ├── alembic/
│   └── requirements.txt
├── bot/              Aiogram Telegram Bot
├── frontend/         React + Vite + Tailwind
├── nginx/            Nginx config
└── docker-compose.yml
```

### Environment Variables

Copy `.env.example` to `.env` and fill in:
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/skilltracer
SECRET_KEY=your-secret-key
TELEGRAM_BOT_TOKEN=your-bot-token
POSTGRES_PASSWORD=your-postgres-password
```

### Database (Docker)

```bash
docker compose up -d postgres
```

### First Run

```bash
cd backend
# Install dependencies
pywin -m pip install -r requirements.txt

# Create tables
pywin -m alembic upgrade head

# Run tests
pywin -m pytest tests/ -v

# Start server
pywin -m uvicorn app.main:app --reload
```

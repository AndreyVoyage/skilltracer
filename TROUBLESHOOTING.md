# SkillTracer — Troubleshooting Guide

## Common Issues & Solutions

### Issue 1: `python: command not found`

**Symptom:**
```bash
$ python -m pytest tests/ -v
bash: python: command not found
```

**Cause:** Git Bash does not include Python in PATH. Python is installed via Windows installer.

**Solution:**
Use the full path to Python:
```bash
/c/Users/andrc/AppData/Local/Python/pythoncore-3.14-64/python.exe -m pytest tests/ -v
```

Or create an alias in `~/.bashrc`:
```bash
alias pywin='/c/Users/andrc/AppData/Local/Python/pythoncore-3.14-64/python.exe'
```

---

### Issue 2: `pytest` not found after install

**Symptom:**
```bash
$ py -m pytest tests/ -v
C:\Users\andrc\AppData\Local\Python\pythoncore-3.14-64\python.exe: No module named pytest
```

**Cause:** pytest installed globally but `py` launcher picks a different Python version, or pytest was not installed.

**Solution:**
Install pytest with the same Python binary:
```bash
/c/Users/andrc/AppData/Local/Python/pythoncore-3.14-64/python.exe -m pip install pytest pytest-asyncio httpx
```

Then run:
```bash
/c/Users/andrc/AppData/Local/Python/pythoncore-3.14-64/python.exe -m pytest tests/ -v
```

---

### Issue 3: `fastapi` not found after installing requirements

**Symptom:**
```bash
$ py -m pytest tests/ -v
ModuleNotFoundError: No module named 'fastapi'
```

**Cause:** Dependencies were installed in a different Python environment.

**Solution:**
Always use the same Python binary for pip and pytest:
```bash
# One-time: install all dependencies
/c/Users/andrc/AppData/Local/Python/pythoncore-3.14-64/python.exe -m pip install -r backend/requirements.txt

# Run tests
/c/Users/andrc/AppData/Local/Python/pythoncore-3.14-64/python.exe -m pytest backend/tests/ -v
```

---

### Issue 4: Git LF/CRLF warnings

**Symptom:**
```
warning: LF will be replaced by CRLF in ...
```

**Cause:** Git on Windows converts line endings automatically.

**Solution:**
```bash
# For this repo only
git config core.autocrlf false

# Or keep LF (recommended for Docker)
git config core.autocrlf input
```

---

### Issue 5: Server nginx conflicts with Docker nginx

**Symptom:**
```
Error: port 80 already in use
```

**Cause:** System nginx running on host conflicts with Docker nginx.

**Solution:**
```bash
ssh root@157.22.187.38
systemctl stop nginx
docker compose up -d
```

Docker nginx uses host ports 80 and 443. System nginx must be stopped first.

---

### Issue 6: `.voyage/` files in .gitignore

**Symptom:**
`TASK.md` and `CONTEXT.json` are not tracked by git.

**Cause:** `.voyage/` directory is in `.gitignore`.

**Solution:**
```bash
# Option A: Remove from .gitignore (if you want to track them)
# Edit .gitignore and remove .voyage/ line

# Option B: Copy files before commit
cp .voyage/TASK.md docs/
cp .voyage/CONTEXT.json docs/
```

---

### Issue 7: Docker containers fail to start (nginx resolver)

**Symptom:**
Nginx exits with `host not found` error.

**Cause:** Docker DNS resolution fails at startup if backend container is not ready.

**Solution:**
In `nginx/default.conf`, use:
```nginx
resolver 127.0.0.11 valid=30s;
set $backend backend;
proxy_pass http://$backend:8000;
```

Instead of direct `proxy_pass http://backend:8000;`.

---

### Issue 8: Missing environment variables when running tests

**Symptom:**
```bash
$ /c/Users/andrc/AppData/Local/Python/pythoncore-3.14-64/python.exe -m pytest tests/ -v
pydantic_core._pydantic_core.ValidationError: 3 validation errors for Settings
DATABASE_URL
  Field required [type=missing, input_value={}, input_type=dict]
SECRET_KEY
  Field required [type=missing, input_value={}, input_type=dict]
TELEGRAM_BOT_TOKEN
  Field required [type=missing, input_value={}, input_type=dict]
```

**Cause:** `app/config.py` instantiates `Settings()` at module import time, which requires environment variables. `conftest.py` patches settings in fixtures, but the import happens before fixtures run.

**Solution:**
Option A — Set env vars before running tests:
```bash
export DATABASE_URL="sqlite+aiosqlite:///:memory:"
export SECRET_KEY="test-secret-key-for-unit-tests-only-32"
export TELEGRAM_BOT_TOKEN="1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
/c/Users/andrc/AppData/Local/Python/pythoncore-3.14-64/python.exe -m pytest tests/ -v
```

Option B — Create `.env` file in `backend/` directory:
```bash
cd backend
cat > .env << 'EOF'
DATABASE_URL=sqlite+aiosqlite:///:memory:
SECRET_KEY=test-secret-key-for-unit-tests-only-32
TELEGRAM_BOT_TOKEN=1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890
EOF
```

Option C — Use `.env.example` (if exists):
```bash
cp backend/.env.example backend/.env
# Edit backend/.env with actual values
```

---

### Issue 9: Russian server cannot reach Telegram API

**Symptom:**
Bot cannot connect to Telegram servers, webhook setup fails, or `api.telegram.org` is unreachable.

**Cause:** Servers in Russia may have restricted access to Telegram infrastructure.

**Solution:**
1. **Use webhook with reverse proxy** — configure bot to use local webhook endpoint
2. **Use polling instead of webhook** — polling does not require inbound connections
3. **Configure proxy** — if needed, add proxy settings to bot configuration
4. **Check DNS resolution** — ensure `api.telegram.org` resolves correctly:
   ```bash
   nslookup api.telegram.org
   curl -v https://api.telegram.org/bot<TOKEN>/getMe
   ```
5. **Consider CDN/VPN** — for persistent issues, route through external proxy

**Note:** The bot currently uses polling mode (`Dispatcher` with `start_polling`), which should work without inbound webhooks.

---

## Deployment Checklist

```bash
# 1. Local tests pass
/c/Users/andrc/AppData/Local/Python/pythoncore-3.14-64/python.exe -m pytest backend/tests/ -v

# 2. Commit and push
git add -A
git commit --no-verify -m "feat: description"
git push origin main

# 3. Server deploy
ssh root@157.22.187.38 "cd /opt/skilltracer && git pull origin main && docker compose up -d --build && docker compose exec backend alembic upgrade head"

# 4. Verify
curl https://skilltracer.ru/api/health
```

---

## Emergency Server Reset

If server has local changes blocking git pull:
```bash
ssh root@157.22.187.38 "cd /opt/skilltracer && git reset --hard HEAD && git clean -fd && git pull origin main && docker compose up -d --build"
```

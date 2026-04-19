#!/bin/bash
# Skill Tracer Diagnostics Script
# Run from project root: bash backend/scripts/diagnose.sh

DOMAIN="skilltracer.art-artel.su"
USER_ID="6072711152"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "🔍 Skill Tracer Diagnostics"
echo "=========================================="

# 1. Проверка health
echo -e "\n1️⃣  Health Check:"
HEALTH=$(curl -s "https://${DOMAIN}/health")
if echo "$HEALTH" | grep -q "healthy"; then
    echo -e "${GREEN}✅ Backend is healthy${NC}"
    echo "$HEALTH" | python3 -m json.tool 2>/dev/null || echo "$HEALTH"
else
    echo -e "${RED}❌ Health check failed${NC}"
fi

# 2. Проверка API через debug endpoint (no auth)
echo -e "\n2️⃣  API Debug (no auth required):"
TODAY=$(date +%Y-%m-%d)
API_RESP=$(curl -s "https://${DOMAIN}/api/v1/entries/week/debug?start_date=${TODAY}&user_id=${USER_ID}")
DAILY=$(echo "$API_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('daily_entries_count',0))" 2>/dev/null || echo "0")
JOURNAL=$(echo "$API_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('journal_entries_count',0))" 2>/dev/null || echo "0")
echo -e "${GREEN}✅ Daily entries: $DAILY, Journal entries: $JOURNAL${NC}"

# 3. Проверка без user_id (должен быть 401)
echo -e "\n3️⃣  API without auth (should be 401):"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://${DOMAIN}/api/v1/entries/week?start_date=${TODAY}")
if [ "$STATUS" = "401" ]; then
    echo -e "${GREEN}✅ Correctly returns 401${NC}"
else
    echo -e "${YELLOW}⚠️  Returns $STATUS (expected 401)${NC}"
fi

# 4. Проверка переменных окружения
echo -e "\n4️⃣  Environment (from systemd service file):"
ENV_FILE="/var/www/www-root/data/www/skilltracer.art-artel.su/backend/.env"
if [ -f "$ENV_FILE" ]; then
    echo -e "${GREEN}✅ .env file exists${NC}"
    grep -E "^(BOT_TOKEN|DATABASE_URL|TELEGRAM_PROXY)=" "$ENV_FILE" | while read line; do
        KEY=$(echo "$line" | cut -d= -f1)
        echo "   $KEY is set"
    done
else
    echo -e "${YELLOW}⚠️  .env file not found${NC}"
fi

# 5. Проверка БД
echo -e "\n5️⃣  Database:"
PYTHON="backend/venv/bin/python"
if [ ! -f "$PYTHON" ]; then
    echo -e "${YELLOW}⚠️  Python not found at $PYTHON${NC}"
else
    DB_CHECK=$(cd backend && PYTHONPATH=.:$PYTHONPATH ./venv/bin/python -c "
import asyncio
from app.database import AsyncSessionLocal
from app.models import User, CustomTracker, JournalEntry
from sqlalchemy import select, func
from datetime import date, timedelta

async def check():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(func.count(User.id)))
        print(f'Users: {result.scalar()}')
        
        result = await session.execute(
            select(func.count(CustomTracker.id)).where(CustomTracker.user_id == 6072711152)
        )
        print(f'Trackers for 6072711152: {result.scalar()}')
        
        start = date.today() - timedelta(days=date.today().weekday())
        end = start + timedelta(days=6)
        result = await session.execute(
            select(func.count(JournalEntry.id)).where(
                JournalEntry.user_id == 6072711152,
                JournalEntry.entry_date >= start,
                JournalEntry.entry_date <= end,
            )
        )
        print(f'Journal entries this week: {result.scalar()}')

asyncio.run(check())
" 2>&1)

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ DB connection OK${NC}"
        echo "$DB_CHECK" | sed 's/^/   /'
    else
        echo -e "${RED}❌ DB check failed${NC}"
        echo "$DB_CHECK" | sed 's/^/   /'
    fi
fi

# 6. Проверка файлов фронтенда
echo -e "\n6️⃣  Frontend files:"
if [ -f "index.html" ]; then
    echo -e "${GREEN}✅ index.html exists${NC}"
else
    echo -e "${RED}❌ index.html missing${NC}"
fi

if [ -f "telegram-web-app.js" ]; then
    echo -e "${GREEN}✅ telegram-web-app.js exists (local SDK)${NC}"
else
    echo -e "${YELLOW}⚠️  telegram-web-app.js missing${NC}"
fi

JS_COUNT=$(find "assets" -name "index-*.js" 2>/dev/null | wc -l)
CSS_COUNT=$(find "assets" -name "index-*.css" 2>/dev/null | wc -l)
echo -e "${GREEN}✅ JS assets: $JS_COUNT, CSS assets: $CSS_COUNT${NC}"

echo -e "\n=========================================="
echo "✅ Diagnose complete"
echo "=========================================="

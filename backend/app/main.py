"""
Skill Tracer API - Main Application

FastAPI приложение с интегрированным Telegram ботом (Aiogram 3).
"""

import asyncio
import time
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.config import settings
from app.database import init_db, close_db, get_db

# Настройка логирования
logging.basicConfig(
    level=logging.INFO if settings.is_production else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# =============================================================================
# Bot Integration
# =============================================================================

# Импортируем бота и диспетчер
from app.bot import bot, dp, start_polling, shutdown_bot, set_bot_commands


async def run_bot_polling():
    """Фоновая задача для polling бота."""
    try:
        logger.info("🤖 Starting bot polling...")
        await start_polling()
    except asyncio.CancelledError:
        logger.info("🤖 Bot polling cancelled")
    except Exception as e:
        logger.error(f"🤖 Bot polling error: {e}")


# =============================================================================
# Lifespan Events
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управление жизненным циклом приложения.
    
    Стартует бота и базу данных, graceful shutdown.
    """
    # Startup
    logger.info("🚀 Запуск Skill Tracer API...")
    logger.info(f"Окружение: {settings.ENVIRONMENT}")
    
    # Инициализация БД
    try:
        await init_db(retries=5, delay=3)
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
        # Не прерываем запуск, health check покажет статус
    
    # Инициализация бота
    bot_task = None
    try:
        # Устанавливаем команды меню с таймаутом (не блокируем старт приложения)
        try:
            await asyncio.wait_for(set_bot_commands(), timeout=10)
            logger.info("✅ Bot commands set")
        except asyncio.TimeoutError:
            logger.warning("⚠️ Таймаут при установке команд бота. Telegram API может быть недоступен.")
        
        # Запускаем polling или webhook в зависимости от настроек
        if settings.BOT_MODE == "polling" or settings.is_development or not settings.WEBAPP_URL.startswith("https"):
            bot_task = asyncio.create_task(run_bot_polling())
            logger.info("🤖 Bot polling started in background")
        else:
            # Для production с HTTPS используем webhook
            from app.bot import setup_webhook
            webhook_url = f"{settings.WEBAPP_URL}/webhook"
            try:
                await asyncio.wait_for(setup_webhook(webhook_url), timeout=10)
                logger.info(f"🤖 Bot webhook set: {webhook_url}")
            except asyncio.TimeoutError:
                logger.warning(f"⚠️ Таймаут при установке webhook. Проверьте доступность Telegram API.")
    
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации бота: {e}")
    
    yield
    
    # Shutdown
    logger.info("🛑 Остановка Skill Tracer API...")
    
    # Останавливаем бота
    if bot_task and not bot_task.done():
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            pass
    
    await shutdown_bot()
    
    # Закрываем БД
    await close_db()
    
    logger.info("✅ Shutdown complete")


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="Skill Tracer API",
    description="API для Skill Tracer - трекера навыков через Telegram",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

# CORS Middleware
# ВНИМАНИЕ: Для production ограничить origins!
_cors_origins = ["*"] if settings.is_development else [
    settings.WEBAPP_URL,
    "https://skilltracer.art-artel.su",
    "https://web.telegram.org",
    "https://*.telegram.org",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Webhook Endpoint (для production режима)
# =============================================================================

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Endpoint для webhook от Telegram.
    
    Используется только в production режиме.
    В development используется polling.
    """
    from aiogram.types import Update
    
    try:
        data = await request.json()
        update = Update(**data)
        await dp.feed_update(bot, update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


# =============================================================================
# API Routes
# =============================================================================

@app.get("/")
async def root():
    """
    Корневой endpoint с базовой информацией.
    """
    return {
        "message": "Skill Tracer API",
        "version": "0.1.0",
        "environment": settings.ENVIRONMENT,
        "bot": "integrated",
        "docs": "/docs" if settings.is_development else None,
    }


@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint с проверкой:
    - Статуса сервера
    - Подключения к БД
    - Бота (упрощенная проверка)
    
    Returns:
        JSON с информацией о состоянии системы
    """
    start_time = time.time()
    
    # Проверка БД
    try:
        result = await db.execute(text("SELECT 1"))
        result.fetchone()
        db_status = "connected"
    except Exception as e:
        logger.error(f"Health check DB error: {e}")
        db_status = "disconnected"
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "database": db_status,
                "error": str(e),
            }
        )
    
    response_time = round((time.time() - start_time) * 1000, 2)
    
    return {
        "status": "healthy",
        "database": db_status,
        "bot": "active",
        "response_time_ms": response_time,
        "version": "0.1.0",
        "environment": settings.ENVIRONMENT,
    }


# =============================================================================
# API Routes v1
# =============================================================================

from app.api.v1.api import api_router
app.include_router(api_router, prefix="/api/v1")


# =============================================================================
# Public Report Route
# =============================================================================

@app.get("/report/{token}", response_class=HTMLResponse)
async def public_report(token: str, db: AsyncSession = Depends(get_db)):
    """Публичный просмотр отчета по токену (без авторизации)."""
    from app.models import ReportLink, DailyEntry, CustomTracker, WeekReport
    from sqlalchemy import select, func
    from datetime import timedelta
    
    result = await db.execute(
        select(ReportLink).where(
            ReportLink.token == token,
            ReportLink.is_active == True,
        )
    )
    link = result.scalar_one_or_none()
    
    if not link:
        raise HTTPException(status_code=404, detail="Report not found")
    
    monday = link.week_start
    sunday = monday + timedelta(days=6)
    
    # Данные недели
    result = await db.execute(
        select(DailyEntry)
        .where(
            DailyEntry.user_id == link.user_id,
            DailyEntry.entry_date >= monday,
            DailyEntry.entry_date <= sunday,
        )
        .order_by(DailyEntry.entry_date)
    )
    entries = result.scalars().all()
    
    result = await db.execute(
        select(CustomTracker)
        .where(
            CustomTracker.user_id == link.user_id,
            CustomTracker.is_active == True,
        )
        .order_by(CustomTracker.sort_order)
    )
    trackers = result.scalars().all()
    
    moods = [e.mood for e in entries if e.mood is not None]
    avg_mood = round(sum(moods) / len(moods), 2) if moods else None
    
    # Собираем HTML
    days_html = ""
    days_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    for i in range(7):
        d = monday + timedelta(days=i)
        entry = next((e for e in entries if e.entry_date == d), None)
        mood = f"{entry.mood}/5" if entry and entry.mood else "—"
        days_html += f'<div style="background:#fff;padding:12px;border-radius:12px;margin-bottom:8px;"><strong>{days_names[i]} {d.strftime("%d.%m")}</strong> — Настроение: {mood}</div>'
    
    trackers_html = ""
    for t in trackers:
        trackers_html += f'<div style="display:inline-block;margin:4px;padding:8px 16px;background:#f0f0f0;border-radius:20px;">{t.icon} {t.name}</div>'
    
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Skill Tracer - Отчет недели</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #F5F1E8; margin: 0; padding: 20px; color: #2C3E50; }}
        .container {{ max-width: 600px; margin: 0 auto; }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .card {{ background: #fff; border-radius: 16px; padding: 20px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
        .stat {{ font-size: 32px; font-weight: bold; color: #E07B39; }}
        .footer {{ text-align: center; margin-top: 30px; opacity: 0.6; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Недельный отчет</h1>
            <p>{monday.strftime("%d.%m")} – {sunday.strftime("%d.%m")}</p>
        </div>
        
        <div class="card" style="text-align:center;">
            <div style="display:flex;justify-content:space-around;">
                <div>
                    <div class="stat">{len(entries)}</div>
                    <div>Дней заполнено</div>
                </div>
                <div>
                    <div class="stat">{avg_mood or '—'}</div>
                    <div>Среднее настроение</div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h3>📅 Дни недели</h3>
            {days_html}
        </div>
        
        <div class="card">
            <h3>🏃 Трекеры</h3>
            <div>{trackers_html}</div>
        </div>
        
        <div class="footer">
            Создано в <a href="https://t.me/SkillTracer_bot" style="color:#E07B39;">Skill Tracer</a>
        </div>
    </div>
</body>
</html>"""
    return html


@app.get("/api/v1/reports/public/{token}")
async def api_public_report(token: str, db: AsyncSession = Depends(get_db)):
    """JSON API для публичного отчета (React SPA)."""
    from app.models import ReportLink, DailyEntry, CustomTracker
    from sqlalchemy import select
    from datetime import timedelta
    
    result = await db.execute(
        select(ReportLink).where(
            ReportLink.token == token,
            ReportLink.is_active == True,
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Report not found")
    
    monday = link.week_start
    sunday = monday + timedelta(days=6)
    
    result = await db.execute(
        select(DailyEntry)
        .where(
            DailyEntry.user_id == link.user_id,
            DailyEntry.entry_date >= monday,
            DailyEntry.entry_date <= sunday,
        )
        .order_by(DailyEntry.entry_date)
    )
    entries = result.scalars().all()
    
    result = await db.execute(
        select(CustomTracker)
        .where(
            CustomTracker.user_id == link.user_id,
            CustomTracker.is_active == True,
        )
        .order_by(CustomTracker.sort_order)
    )
    trackers = result.scalars().all()
    
    moods = [e.mood for e in entries if e.mood is not None]
    avg_mood = round(sum(moods) / len(moods), 2) if moods else None
    
    days = []
    for i in range(7):
        d = monday + timedelta(days=i)
        entry = next((e for e in entries if e.entry_date == d), None)
        day_metrics = []
        if entry:
            for m in entry.metrics:
                tracker = next((t for t in trackers if t.id == m.tracker_id), None)
                day_metrics.append({
                    "tracker_name": tracker.name if tracker else f"Tracker {m.tracker_id}",
                    "value": m.value,
                })
        days.append({
            "entry_date": d.isoformat(),
            "mood": entry.mood if entry else None,
            "metrics": day_metrics,
        })
    
    return {
        "week_start": monday.isoformat(),
        "filled_days": len(entries),
        "avg_mood": avg_mood,
        "days": days,
    }


# =============================================================================
# Legacy API Routes (для обратной совместимости)
# =============================================================================

@app.get("/api/user/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Получение информации о пользователе для Mini App."""
    from app.models import User
    
    result = await db.execute(
        text("SELECT id, username, first_name, last_name, timezone FROM users WHERE id = :id"),
        {"id": user_id}
    )
    user = result.fetchone()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "timezone": user.timezone,
    }


@app.get("/api/user/{user_id}/trackers")
async def get_user_trackers(user_id: int, db: AsyncSession = Depends(get_db)):
    """Получение трекеров пользователя для Mini App."""
    from app.models import CustomTracker
    from sqlalchemy import select
    
    result = await db.execute(
        select(CustomTracker)
        .where(CustomTracker.user_id == user_id, CustomTracker.is_active == True)
        .order_by(CustomTracker.sort_order)
    )
    trackers = result.scalars().all()
    
    return [
        {
            "id": t.id,
            "name": t.name,
            "icon": t.icon,
            "target_value": t.target_value,
        }
        for t in trackers
    ]


@app.get("/api/user/{user_id}/today")
async def get_today_entry(user_id: int, db: AsyncSession = Depends(get_db)):
    """
    Получение записи на сегодня + cached file_id для фото.
    """
    from datetime import date
    from app.models import DailyEntry
    from sqlalchemy import select
    from app.bot.media_cache import get_cached_media
    
    today = date.today()
    
    result = await db.execute(
        select(DailyEntry).where(
            DailyEntry.user_id == user_id,
            DailyEntry.entry_date == today,
        )
    )
    entry = result.scalar_one_or_none()
    
    # Получаем cached file_id если есть
    cached_photo = get_cached_media(user_id, "photo")
    cached_video = get_cached_media(user_id, "video")
    
    if entry:
        return {
            "exists": True,
            "id": entry.id,
            "date": entry.entry_date.isoformat(),
            "mood": entry.mood,
            "text": entry.text,
            "photo_file_id": entry.photo_file_id or cached_photo,
            "cached_video": cached_video,
        }
    else:
        return {
            "exists": False,
            "date": today.isoformat(),
            "cached_photo": cached_photo,
            "cached_video": cached_video,
        }


# =============================================================================
# Error Handlers
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Глобальный обработчик ошибок."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    raise HTTPException(status_code=500, detail="Internal server error")

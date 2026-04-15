"""
Report Generator Service

Генерация PNG/JPEG недельных отчетов через Matplotlib + Pillow.
Оптимизировано для Host-0: semaphore (1 задача), кэш 5 мин, BytesIO.
"""

import asyncio
import io
import json
import logging
import time
from datetime import date, timedelta
from typing import Optional

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

# Matplotlib настройка без GUI
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from app.models import User, DailyEntry, EntryMetric, CustomTracker

logger = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================

WIDTH = 800
HEIGHT = 1200
DPI = 72
JPEG_QUALITY = 85
CACHE_TTL = 300  # 5 минут
MAX_PHOTOS = 6
PHOTO_THUMB_SIZE = 150

_report_semaphore = asyncio.Semaphore(1)
_report_cache: dict[str, tuple[io.BytesIO, float]] = {}

# Цветовая схема
COLOR_BG = "#1a1a2e"
COLOR_CARD = "#16213e"
COLOR_TEXT = "#e94560"
COLOR_ACCENT = "#0f3460"
COLOR_WHITE = "#ffffff"
COLOR_GRAY = "#a0a0a0"

MOOD_EMOJIS = {1: "😭", 2: "😟", 3: "😐", 4: "🙂", 5: "😄"}
WEEKDAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def _get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Возвращает шрифт, fallback на default если TTF не найден."""
    try:
        # Пробуем стандартный шрифт Windows (обычно есть)
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        try:
            return ImageFont.truetype("DejaVuSans.ttf", size)
        except Exception:
            return ImageFont.load_default()


def _cache_key(user_id: int, week_start: date) -> str:
    return f"{user_id}:{week_start.isoformat()}"


def _get_cached_report(user_id: int, week_start: date) -> Optional[io.BytesIO]:
    key = _cache_key(user_id, week_start)
    entry = _report_cache.get(key)
    if entry and entry[1] > time.time():
        buf = io.BytesIO(entry[0].getvalue())
        return buf
    if entry:
        del _report_cache[key]
    return None


def _set_cached_report(user_id: int, week_start: date, buf: io.BytesIO) -> None:
    key = _cache_key(user_id, week_start)
    _report_cache[key] = (io.BytesIO(buf.getvalue()), time.time() + CACHE_TTL)


def _create_sparkline_image(mood_values: list[Optional[int]], width: int, height: int) -> Image.Image:
    """
    Создает sparkline настроения через matplotlib.
    Возвращает PIL Image.
    """
    fig, ax = plt.subplots(figsize=(width / DPI, height / DPI), dpi=DPI)
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")

    days = list(range(7))
    valid = [(d, v) for d, v in zip(days, mood_values) if v is not None]

    if len(valid) >= 2:
        xs, ys = zip(*valid)
        ax.plot(xs, ys, color=COLOR_TEXT, linewidth=3, marker="o", markersize=8)
        ax.set_ylim(0.5, 5.5)
        ax.set_xlim(-0.5, 6.5)
        ax.set_xticks(days)
        ax.set_xticklabels(WEEKDAYS_RU, color=COLOR_WHITE, fontsize=10)
        ax.tick_params(axis="y", colors=COLOR_WHITE, labelsize=10)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(COLOR_GRAY)
        ax.spines["bottom"].set_color(COLOR_GRAY)
        ax.grid(True, alpha=0.2, color=COLOR_GRAY)
    else:
        ax.text(0.5, 0.5, "Недостаточно данных", transform=ax.transAxes,
                color=COLOR_GRAY, fontsize=14, ha="center", va="center")
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)

    buf = io.BytesIO()
    plt.tight_layout(pad=0)
    plt.savefig(buf, format="png", transparent=True, dpi=DPI)
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf)


async def _download_photos(bot, file_ids: list[str]) -> list[Image.Image]:
    """Скачивает фото по file_id через aiogram bot."""
    images = []
    for fid in file_ids[:MAX_PHOTOS]:
        try:
            file = await bot.get_file(fid)
            bio = io.BytesIO()
            await bot.download_file(file.file_path, bio)
            bio.seek(0)
            img = Image.open(bio)
            img.thumbnail((PHOTO_THUMB_SIZE, PHOTO_THUMB_SIZE))
            images.append(img)
        except Exception as e:
            logger.warning(f"Failed to download photo {fid[:20]}...: {e}")
    return images


def _draw_rounded_rectangle(draw: ImageDraw.ImageDraw, xy, radius, fill):
    """Рисует скругленный прямоугольник."""
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=fill)


def _sync_generate_poster(
    user: User,
    week_start: date,
    entries: list[DailyEntry],
    trackers: list[CustomTracker],
    photos: list[Image.Image],
) -> io.BytesIO:
    """
    Синхронная генерация постера (вызывается через to_thread).
    """
    img = Image.new("RGB", (WIDTH, HEIGHT), COLOR_BG)
    draw = ImageDraw.Draw(img)

    # Шрифты
    font_title = _get_font(36)
    font_subtitle = _get_font(24)
    font_body = _get_font(18)
    font_small = _get_font(14)

    week_end = week_start + timedelta(days=6)
    y_offset = 30

    # =====================================================================
    # Header
    # =====================================================================
    title = f"Моя неделя {week_start.day}-{week_end.day} {week_start.strftime('%b %Y')}"
    draw.text((WIDTH // 2, y_offset), title, font=font_title, fill=COLOR_WHITE, anchor="mm")
    y_offset += 55

    # Среднее настроение
    moods = [e.mood for e in entries if e.mood is not None]
    avg_mood = round(sum(moods) / len(moods), 1) if moods else None
    if avg_mood:
        mood_emoji = MOOD_EMOJIS.get(round(avg_mood), "📊")
        draw.text(
            (WIDTH // 2, y_offset),
            f"Среднее настроение: {mood_emoji} {avg_mood}/5",
            font=font_subtitle,
            fill=COLOR_TEXT,
            anchor="mm",
        )
    else:
        draw.text(
            (WIDTH // 2, y_offset),
            "Настроение не отмечено",
            font=font_subtitle,
            fill=COLOR_GRAY,
            anchor="mm",
        )
    y_offset += 50

    # =====================================================================
    # Photo Grid (2x3)
    # =====================================================================
    if photos:
        grid_x = (WIDTH - (2 * PHOTO_THUMB_SIZE + 20)) // 2
        grid_y = y_offset
        for idx, photo in enumerate(photos):
            col = idx % 2
            row = idx // 2
            px = grid_x + col * (PHOTO_THUMB_SIZE + 10)
            py = grid_y + row * (PHOTO_THUMB_SIZE + 10)
            # Рамка
            _draw_rounded_rectangle(draw, [px - 4, py - 4, px + PHOTO_THUMB_SIZE + 4, py + PHOTO_THUMB_SIZE + 4], 8, COLOR_CARD)
            img.paste(photo, (px, py))
        y_offset = grid_y + ((len(photos) + 1) // 2) * (PHOTO_THUMB_SIZE + 10) + 20
    else:
        y_offset += 20

    # =====================================================================
    # Mood Sparkline
    # =====================================================================
    mood_by_day = [None] * 7
    for e in entries:
        delta = (e.entry_date - week_start).days
        if 0 <= delta < 7:
            mood_by_day[delta] = e.mood

    sparkline = _create_sparkline_image(mood_by_day, WIDTH - 60, 180)
    img.paste(sparkline, (30, y_offset), sparkline if sparkline.mode == "RGBA" else None)
    y_offset += 200

    # =====================================================================
    # Trackers
    # =====================================================================
    if trackers:
        draw.text((30, y_offset), "Трекеры:", font=font_subtitle, fill=COLOR_WHITE)
        y_offset += 40

        # Считаем средние значения трекеров за неделю
        tracker_avgs: dict[int, tuple[str, str, float]] = {}
        for t in trackers:
            vals = []
            for e in entries:
                for m in e.metrics:
                    if m.tracker_id == t.id:
                        vals.append(m.value)
            avg = sum(vals) / len(vals) if vals else 0.0
            tracker_avgs[t.id] = (t.name, t.icon, avg)

        for t in trackers:
            name, icon, avg = tracker_avgs.get(t.id, (t.name, t.icon, 0.0))
            bar_width = int((avg / 5.0) * (WIDTH - 120))
            # Фон бара
            _draw_rounded_rectangle(draw, [30, y_offset, WIDTH - 30, y_offset + 24], 12, COLOR_ACCENT)
            # Заполнение
            if bar_width > 0:
                _draw_rounded_rectangle(draw, [30, y_offset, 30 + bar_width, y_offset + 24], 12, COLOR_TEXT)
            # Текст
            draw.text((40, y_offset + 2), f"{icon} {name}", font=font_small, fill=COLOR_WHITE)
            draw.text((WIDTH - 40, y_offset + 2), f"{avg:.1f}/5", font=font_small, fill=COLOR_WHITE, anchor="rm")
            y_offset += 36
        y_offset += 20

    # =====================================================================
    # Quote
    # =====================================================================
    quote_text = ""
    for e in entries:
        if e.text:
            quote_text = e.text
            break
    if not quote_text and entries:
        # Берем случайный день с текстом
        for e in entries:
            if e.text:
                quote_text = e.text
                break

    if quote_text:
        draw.text((30, y_offset), "Главная мысль недели:", font=font_subtitle, fill=COLOR_WHITE)
        y_offset += 35
        # Обрезаем текст
        max_chars = 80
        if len(quote_text) > max_chars:
            quote_text = quote_text[:max_chars - 3] + "..."
        _draw_rounded_rectangle(draw, [30, y_offset, WIDTH - 30, y_offset + 60], 8, COLOR_CARD)
        draw.text((40, y_offset + 10), f"\"{quote_text}\"", font=font_body, fill=COLOR_GRAY)
        y_offset += 80

    # =====================================================================
    # Footer
    # =====================================================================
    draw.text((WIDTH // 2, HEIGHT - 30), "@SkillTracer_bot", font=font_small, fill=COLOR_GRAY, anchor="mm")

    # Сохраняем
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    buf.seek(0)
    return buf


async def generate_week_poster(
    user_id: int,
    week_start: date,
    db: AsyncSession,
    bot=None,
) -> io.BytesIO:
    """
    Генерирует JPEG постер недели и возвращает BytesIO.
    Ограничивает до 1 одновременной генерации (semaphore).
    Кэширует результат на 5 минут.
    """
    # Проверка кэша
    cached = _get_cached_report(user_id, week_start)
    if cached:
        logger.info(f"Returning cached report for user {user_id} week {week_start}")
        return cached

    async with _report_semaphore:
        # Двойная проверка кэша внутри семафора
        cached = _get_cached_report(user_id, week_start)
        if cached:
            return cached

        logger.info(f"Generating report for user {user_id} week {week_start}")

        # Получаем пользователя
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Получаем записи за неделю
        week_end = week_start + timedelta(days=6)
        result = await db.execute(
            select(DailyEntry)
            .where(
                DailyEntry.user_id == user_id,
                DailyEntry.entry_date >= week_start,
                DailyEntry.entry_date <= week_end,
            )
            .order_by(DailyEntry.entry_date)
        )
        entries = list(result.scalars().all())

        # Получаем активные трекеры
        result = await db.execute(
            select(CustomTracker)
            .where(
                CustomTracker.user_id == user_id,
                CustomTracker.is_active == True,
            )
            .order_by(CustomTracker.sort_order)
        )
        trackers = list(result.scalars().all())

        # Собираем file_ids фото
        file_ids = [e.photo_file_id for e in entries if e.photo_file_id]

        # Скачиваем фото
        photos = []
        if bot and file_ids:
            photos = await _download_photos(bot, file_ids)

        # Генерируем в отдельном потоке
        buf = await asyncio.to_thread(_sync_generate_poster, user, week_start, entries, trackers, photos)

        # Кэшируем
        _set_cached_report(user_id, week_start, buf)
        logger.info(f"Report generated for user {user_id}, size={buf.getbuffer().nbytes} bytes")

        # Возвращаем свежий BytesIO
        return io.BytesIO(buf.getvalue())


async def send_report_to_chat(
    user_id: int,
    week_start: date,
    db: AsyncSession,
    bot,
) -> None:
    """Генерирует отчет и отправляет его пользователю через бота."""
    from app.models import TelegramQueue

    buffer = await generate_week_poster(user_id, week_start, db, bot=bot)

    # Для надежности отправки в проде можно поставить в очередь
    # Для MVP отправляем напрямую
    try:
        buffer.seek(0)
        await bot.send_photo(
            chat_id=user_id,
            photo=buffer,
            caption="Ваша неделя! 🎉",
        )
        logger.info(f"Report sent to user {user_id}")
    except Exception as e:
        logger.error(f"Failed to send report to {user_id}: {e}")
        # Ставим в очередь на повтор
        queue_item = TelegramQueue(
            user_id=user_id,
            action="send_report",
            payload=json.dumps({
                "week_start": week_start.isoformat(),
                "error": str(e),
            }),
            status="failed",
            error_message=str(e),
        )
        db.add(queue_item)
        await db.commit()
        raise

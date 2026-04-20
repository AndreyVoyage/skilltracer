"""
Journal Handlers (Моя неделя)

Обработчики для раздела "📊 Моя неделя":
- Выбор дня из Reply-клавиатуры
- Inline-оценки по 4 категориям
- Сохранение комментария и медиа в FSM
- Запись в БД
"""

import logging
import uuid
from datetime import date, timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.states import DaySelection, EntryInput
from app.bot.config import BotButtons, BotMessages
from app.bot.keyboards import (
    get_days_keyboard,
    get_entry_rating_keyboard,
    get_main_menu_keyboard,
    get_back_to_scores_keyboard,
    generate_day_labels,
)
from app.database import save_journal_entry, get_journal_entries_dates
from app.models import User

logger = logging.getLogger(__name__)

router = Router(name="journal")


async def _get_filled_dates(db: AsyncSession, user: User) -> set[date]:
    """Возвращает множество дат с записями за последние 10 дней."""
    today = date.today()
    start = today - timedelta(days=9)
    dates = await get_journal_entries_dates(db, user.id, start, today)
    return set(dates)


# =============================================================================
# Entry point: "📊 Моя неделя"
# =============================================================================

@router.message(F.text == BotButtons.MY_WEEK)
async def my_week_handler(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: User,
) -> None:
    """Показывает 10 кнопок с датами (с ✅ для заполненных)."""
    filled = await _get_filled_dates(db, user)
    await state.set_state(DaySelection.selecting_day)
    await message.answer(
        BotMessages.SELECT_DAY,
        reply_markup=get_days_keyboard(filled_dates=filled),
    )


# =============================================================================
# Day selection (Reply keyboard)
# =============================================================================

@router.message(DaySelection.selecting_day, F.text)
async def day_selected(message: Message, state: FSMContext) -> None:
    """Обрабатывает выбор дня или возврат в меню."""
    text = message.text
    clean_text = text.lstrip("✅ ").strip()

    if clean_text == BotButtons.BACK_TO_MENU:
        await state.clear()
        await message.answer(
            "Главное меню",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    labels = generate_day_labels()
    selected_date = labels.get(clean_text)
    if selected_date is None:
        await message.answer(
            "Пожалуйста, выберите день из списка ниже.",
            reply_markup=get_days_keyboard(),
        )
        return

    await state.update_data(
        selected_date=selected_date.isoformat(),
        scores={},
        comment=None,
        media=[],
    )
    await state.set_state(EntryInput.waiting_scores)

    await message.answer(
        f"📅 {selected_date.strftime('%d.%m.%Y')}\n\n{BotMessages.ENTRY_PROMPT}",
        reply_markup=get_entry_rating_keyboard(),
    )


# =============================================================================
# Rating callbacks (inline)
# =============================================================================

@router.callback_query(EntryInput.waiting_scores, F.data == "noop")
async def noop_category(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(EntryInput.waiting_scores, F.data.startswith("rate_"))
async def rate_category(callback: CallbackQuery, state: FSMContext) -> None:
    """Сохраняет оценку категории в FSM и обновляет клавиатуру."""
    parts = callback.data.split("_")
    if len(parts) != 3:
        await callback.answer()
        return

    _, category, value_str = parts
    try:
        value = int(value_str)
    except ValueError:
        await callback.answer()
        return

    data = await state.get_data()
    scores = data.get("scores", {})
    scores[category] = value
    await state.update_data(scores=scores)

    await callback.message.edit_reply_markup(
        reply_markup=get_entry_rating_keyboard(scores),
    )
    await callback.answer(f"{category.capitalize()}: {value}")


@router.callback_query(EntryInput.waiting_scores, F.data == "back_to_days")
async def back_to_days(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    user: User,
) -> None:
    """Возврат к выбору дня."""
    await state.set_state(DaySelection.selecting_day)
    filled = await _get_filled_dates(db, user)
    await callback.message.delete()
    await callback.message.answer(
        BotMessages.SELECT_DAY,
        reply_markup=get_days_keyboard(filled_dates=filled),
    )
    await callback.answer()


# =============================================================================
# Text / Media explicit buttons (edit message, wait for input)
# =============================================================================

@router.callback_query(EntryInput.waiting_scores, F.data == "entry:text")
async def request_text(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "📝 Пришли текст, фото или голосовое сообщение:",
        reply_markup=get_back_to_scores_keyboard(),
    )


@router.callback_query(EntryInput.waiting_scores, F.data == "entry:media")
async def request_media(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "📎 Пришли фото, видео, аудио или голосовое сообщение:",
        reply_markup=get_back_to_scores_keyboard(),
    )


@router.callback_query(F.data == "entry:back_to_scores")
async def back_to_scores(callback: CallbackQuery, state: FSMContext) -> None:
    """Возврат к меню оценок."""
    await callback.answer()
    await state.set_state(EntryInput.waiting_scores)
    data = await state.get_data()
    await callback.message.edit_text(
        f"📅 {data.get('selected_date', '')}\n\n{BotMessages.ENTRY_PROMPT}",
        reply_markup=get_entry_rating_keyboard(data.get("scores")),
    )


# =============================================================================
# Text / Media input (auto-save and return to ratings)
# =============================================================================

async def _return_to_ratings(message: Message, state: FSMContext, saved_text: str) -> None:
    """Вспомогательная функция: возвращает пользователя к оценкам."""
    data = await state.get_data()
    scores = data.get("scores", {})
    selected_date = data.get("selected_date", "")
    await message.answer(
        f"{saved_text}\n\n"
        f"📅 {selected_date}\n\n"
        f"Выставь оценки или сохрани:",
        reply_markup=get_entry_rating_keyboard(scores),
    )


@router.message(EntryInput.waiting_scores, F.text)
async def entry_text_in_scores_state(message: Message, state: FSMContext) -> None:
    """Принимает текстовую заметку и автоматически возвращает к оценкам."""
    await state.update_data(comment=message.text)
    await _return_to_ratings(message, state, "✅ Текст сохранён.")


@router.message(
    EntryInput.waiting_scores,
    F.photo | F.voice | F.video | F.audio,
)
async def entry_media_in_scores_state(message: Message, state: FSMContext) -> None:
    """Принимает медиа и автоматически возвращает к оценкам."""
    media_item = None
    if message.photo:
        media_item = {"id": str(uuid.uuid4()), "type": "photo", "file_id": message.photo[-1].file_id}
    elif message.voice:
        media_item = {"id": str(uuid.uuid4()), "type": "voice", "file_id": message.voice.file_id}
    elif message.video:
        media_item = {"id": str(uuid.uuid4()), "type": "video", "file_id": message.video.file_id}
    elif message.audio:
        media_item = {"id": str(uuid.uuid4()), "type": "audio", "file_id": message.audio.file_id}

    if not media_item:
        await message.answer("Не удалось распознать медиа.")
        return

    data = await state.get_data()
    media = data.get("media", [])
    media.append(media_item)
    await state.update_data(media=media)
    logger.info(f"[JOURNAL_MEDIA] Added {media_item['type']} with id={media_item['id']}, total media in state: {len(media)}")
    await _return_to_ratings(message, state, "📎 Медиа сохранено.")


# =============================================================================
# Save entry
# =============================================================================

@router.callback_query(EntryInput.waiting_scores, F.data == "save_entry")
async def save_entry_callback(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
) -> None:
    """Сохраняет запись в БД и возвращает в главное меню."""
    data = await state.get_data()
    selected_date_str = data.get("selected_date")
    scores = data.get("scores", {})
    comment = data.get("comment")
    media = data.get("media", [])

    if not selected_date_str:
        await callback.answer("Ошибка: дата не выбрана", show_alert=True)
        return

    entry_date = date.fromisoformat(selected_date_str)
    user_id = callback.from_user.id

    try:
        logger.info(f"[JOURNAL_SAVE] Saving entry for {entry_date}, media_count={len(media)}, media_ids={[m.get('id') for m in media]}")
        await save_journal_entry(
            db=db,
            user_id=user_id,
            entry_date=entry_date,
            health_score=scores.get("health"),
            sport_score=scores.get("sport"),
            study_score=scores.get("study"),
            rest_score=scores.get("rest"),
            comment=comment,
            media_urls=media if media else None,
        )
    except Exception as exc:
        logger.error(f"Failed to save journal entry: {exc}")
        await callback.answer(
            BotMessages.ERROR_DATABASE,
            show_alert=True,
        )
        return

    await callback.message.edit_text(BotMessages.ENTRY_SAVED)
    await callback.answer("Сохранено!")
    await state.clear()
    await callback.message.answer(
        "Главное меню",
        reply_markup=get_main_menu_keyboard(),
    )

"""Entry creation FSM handler for SkillTracer bot."""

from __future__ import annotations

import datetime
import logging
import tempfile
from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton

from app.services.backend import backend

logger = logging.getLogger(__name__)
router = Router()

# Emoji mapping for scores
SCORE_EMOJIS = {1: "🔴", 2: "🟠", 3: "🟡", 4: "🟢", 5: "🟢"}


class EntryStates(StatesGroup):
    """FSM states for entry creation flow."""

    rating = State()       # Collecting category ratings
    comment = State()      # Optional comment
    photo = State()        # Optional photo
    confirm = State()      # Final confirmation


def _rating_keyboard(category_id: int) -> InlineKeyboardMarkup:
    """Build inline keyboard for rating a category (1-5)."""
    buttons = [
        [
            InlineKeyboardButton(
                text=f"{SCORE_EMOJIS[i]} {i}",
                callback_data=f"rate:{category_id}:{i}",
            )
            for i in range(1, 6)
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _yes_no_skip_keyboard() -> ReplyKeyboardMarkup:
    """Build reply keyboard with skip option."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⏭ Пропустить")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def _confirm_keyboard() -> InlineKeyboardMarkup:
    """Build confirmation inline keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Сохранить", callback_data="confirm:save"),
                InlineKeyboardButton(text="❌ Отменить", callback_data="confirm:cancel"),
            ]
        ]
    )


async def _ensure_authenticated(user: Message | CallbackQuery) -> bool:
    """Ensure the backend client has a valid token."""
    # If already have token, skip
    if backend._token is not None:
        return True

    from_user = user.from_user
    if from_user is None:
        return False

    try:
        await backend.authenticate(
            telegram_id=from_user.id,
            username=from_user.username,
            first_name=from_user.first_name,
        )
        return True
    except Exception as exc:
        logger.exception("Backend authentication failed: %s", exc)
        return False


async def _show_current_category(message: Message, state: FSMContext) -> None:
    """Display the current category for rating."""
    data = await state.get_data()
    categories: list[dict[str, Any]] = data.get("categories", [])
    current_index: int = data.get("current_index", 0)
    ratings: dict[str, int] = data.get("ratings", {})

    if current_index >= len(categories):
        # All categories rated, move to comment
        await state.set_state(EntryStates.comment)
        summary = _build_rating_summary(categories, ratings)
        await message.answer(
            f"✅ Все оценки поставлены!\n\n{summary}\n\n"
            "📝 Напиши комментарий к дню (или нажми 'Пропустить'):",
            reply_markup=_yes_no_skip_keyboard(),
        )
        return

    category = categories[current_index]
    cat_name = category.get("name", "Категория")
    cat_icon = category.get("icon", "📊")
    cat_id = category.get("id", 0)

    # Show progress
    progress = f"{current_index + 1}/{len(categories)}"
    await message.answer(
        f"{cat_icon} <b>{cat_name}</b> ({progress})\n\n"
        "Оцени от 1 до 5:",
        reply_markup=_rating_keyboard(cat_id),
        parse_mode="HTML",
    )


def _build_rating_summary(categories: list[dict], ratings: dict[str, int]) -> str:
    """Build a text summary of collected ratings."""
    lines = []
    for cat in categories:
        cat_id = str(cat.get("id", ""))
        score = ratings.get(cat_id)
        if score:
            emoji = SCORE_EMOJIS.get(score, "")
            lines.append(f"{cat.get('icon', '📊')} {cat['name']}: {emoji} {score}")
    return "\n".join(lines)


@router.message(Command("entry"))
async def cmd_entry(message: Message, state: FSMContext) -> None:
    """Start the entry creation flow."""
    if not await _ensure_authenticated(message):
        await message.answer("❌ Ошибка аутентификации. Попробуй позже.")
        return

    # Clear any previous state
    await state.clear()

    try:
        categories = await backend.get_categories()
    except Exception as exc:
        logger.exception("Failed to load categories: %s", exc)
        await message.answer("❌ Не удалось загрузить категории. Попробуй позже.")
        return

    if not categories:
        await message.answer(
            "У тебя пока нет категорий. Создай их через веб-приложение!"
        )
        return

    await state.set_state(EntryStates.rating)
    await state.update_data(
        categories=categories,
        current_index=0,
        ratings={},
        comment=None,
        photos=[],
    )

    await message.answer(
        "📔 Создание новой записи\n\n"
        f"Сегодня: {datetime.date.today().strftime('%d.%m.%Y')}\n\n"
        "Давай оценим твой день по категориям!"
    )
    await _show_current_category(message, state)


@router.callback_query(F.data.startswith("rate:"), EntryStates.rating)
async def process_rating(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle rating callback for current category."""
    if callback.data is None:
        await callback.answer("Ошибка")
        return

    _, cat_id_str, score_str = callback.data.split(":")
    cat_id = int(cat_id_str)
    score = int(score_str)

    data = await state.get_data()
    ratings: dict[str, int] = data.get("ratings", {})
    ratings[str(cat_id)] = score
    current_index: int = data.get("current_index", 0)

    await state.update_data(ratings=ratings, current_index=current_index + 1)
    await callback.answer(f"Оценка: {score}")
    await callback.message.delete()  # Remove the rating keyboard
    await _show_current_category(callback.message, state)


@router.message(EntryStates.comment)
async def process_comment(message: Message, state: FSMContext) -> None:
    """Handle comment input (or skip)."""
    text = message.text or ""

    if text == "⏭ Пропустить":
        await state.update_data(comment=None)
    else:
        await state.update_data(comment=text)

    await state.set_state(EntryStates.photo)
    await message.answer(
        "📸 Пришли фото для записи (или нажми 'Пропустить'):",
        reply_markup=_yes_no_skip_keyboard(),
    )


@router.message(F.photo, EntryStates.photo)
async def process_photo(message: Message, state: FSMContext) -> None:
    """Handle photo upload."""
    if not message.photo:
        return

    # Get the largest photo
    photo = message.photo[-1]
    data = await state.get_data()
    photos: list[dict] = data.get("photos", [])
    photos.append({
        "file_id": photo.file_id,
        "file_unique_id": photo.file_unique_id,
        "width": photo.width,
        "height": photo.height,
        "file_size": photo.file_size,
    })
    await state.update_data(photos=photos)

    # Ask if more photos
    await message.answer(
        "📸 Фото добавлено. Пришли ещё (или нажми 'Пропустить' для завершения):",
        reply_markup=_yes_no_skip_keyboard(),
    )


@router.message(EntryStates.photo)
async def process_photo_skip(message: Message, state: FSMContext) -> None:
    """Handle skip or finish photo collection."""
    text = message.text or ""

    if text == "⏭ Пропустить":
        await state.set_state(EntryStates.confirm)
        data = await state.get_data()
        categories = data.get("categories", [])
        ratings = data.get("ratings", {})
        comment = data.get("comment")
        photos = data.get("photos", [])

        summary = _build_rating_summary(categories, ratings)
        photo_count = len(photos)

        msg = f"📋 <b>Проверь запись:</b>\n\n{summary}\n\n"
        if comment:
            msg += f"📝 Комментарий: {comment}\n\n"
        if photo_count > 0:
            msg += f"📸 Фото: {photo_count}\n\n"
        msg += "Всё верно?"

        await message.answer(
            msg,
            reply_markup=_confirm_keyboard(),
            parse_mode="HTML",
        )


@router.callback_query(F.data == "confirm:save", EntryStates.confirm)
async def confirm_save(callback: CallbackQuery, state: FSMContext) -> None:
    """Save the entry to backend."""
    data = await state.get_data()
    categories = data.get("categories", [])
    ratings = data.get("ratings", {})
    comment = data.get("comment")
    photos = data.get("photos", [])

    # Build ratings payload
    ratings_payload = [
        {"category_id": int(cat_id), "score": score}
        for cat_id, score in ratings.items()
    ]

    entry_date = datetime.date.today().isoformat()

    try:
        entry = await backend.create_entry(
            entry_date=entry_date,
            ratings=ratings_payload,
            comment=comment,
        )

        # Upload photos if any
        entry_id = entry.get("id")
        if entry_id and photos:
            bot = callback.bot
            for photo_info in photos:
                file_id = photo_info["file_id"]
                try:
                    file = await bot.get_file(file_id)
                    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                        await bot.download_file(file.file_path, tmp)
                        tmp_path = tmp.name
                    await backend.upload_media(entry_id, tmp_path)
                except Exception as exc:
                    logger.exception("Failed to upload photo: %s", exc)

        await callback.answer("✅ Запись сохранена!")
        await callback.message.edit_text(
            f"✅ Запись за {datetime.date.today().strftime('%d.%m.%Y')} сохранена!\n\n"
            f"Оценок: {len(ratings)}\n"
            + (f"Комментарий: {comment}\n" if comment else "")
        )

    except Exception as exc:
        logger.exception("Failed to save entry: %s", exc)
        await callback.answer("❌ Ошибка сохранения")
        await callback.message.edit_text(
            "❌ Не удалось сохранить запись. Попробуй позже."
        )

    await state.clear()


@router.callback_query(F.data == "confirm:cancel", EntryStates.confirm)
async def confirm_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel entry creation."""
    await callback.answer("Отменено")
    await callback.message.edit_text("❌ Создание записи отменено.")
    await state.clear()


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    """Cancel any active FSM flow."""
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
        await message.answer(
            "❌ Операция отменена.",
            reply_markup=ReplyKeyboardRemove(),
        )
    else:
        await message.answer("Нет активной операции.")

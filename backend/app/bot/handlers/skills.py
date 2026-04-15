"""
Skills (Trackers) Conversation Handler

Conversation для создания трекеров "на лету" через бота.
Состояния:
  1. ADDING_SKILL_NAME - ждем название
  2. ADDING_SKILL_ICON - ждем emoji иконку
"""

import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, CustomTracker
from app.bot.config import BotMessages

logger = logging.getLogger(__name__)

router = Router(name="skills")


class AddSkillStates(StatesGroup):
    ADDING_SKILL_NAME = State()
    ADDING_SKILL_ICON = State()


# =============================================================================
# Entry points
# =============================================================================

@router.message(Command("addskill"))
async def cmd_addskill(message: Message, state: FSMContext, user: User) -> None:
    """Начало conversation для добавления трекера."""
    await state.set_state(AddSkillStates.ADDING_SKILL_NAME)
    await message.answer(
        "📊 <b>Добавление трекера</b>\n\n"
        "Введи название нового трекера (например, 'Спорт', 'Английский', 'Медитация'):"
    )


@router.message(F.text == "➕ Добавить трекер")
async def btn_addskill(message: Message, state: FSMContext, user: User) -> None:
    """Кнопка добавления трекера."""
    await cmd_addskill(message, state, user)


# =============================================================================
# State: ADDING_SKILL_NAME
# =============================================================================

@router.message(AddSkillStates.ADDING_SKILL_NAME)
async def process_skill_name(message: Message, state: FSMContext, db: AsyncSession, user: User) -> None:
    """Получаем название трекера."""
    name = message.text.strip()
    
    if len(name) < 1 or len(name) > 100:
        await message.answer("❌ Название должно быть от 1 до 100 символов. Попробуй еще раз:")
        return
    
    # Проверяем что такого трекера еще нет
    result = await db.execute(
        select(func.count(CustomTracker.id))
        .where(
            CustomTracker.user_id == user.id,
            CustomTracker.name == name,
            CustomTracker.is_active == True,
        )
    )
    exists = result.scalar() or 0
    if exists > 0:
        await message.answer(
            f"❌ У тебя уже есть трекер '<b>{name}</b>'.\n\n"
            f"Введи другое название:"
        )
        return
    
    await state.update_data(skill_name=name)
    await state.set_state(AddSkillStates.ADDING_SKILL_ICON)
    await message.answer(
        f"✅ Название: <b>{name}</b>\n\n"
        f"Теперь отправь emoji-иконку для трекера (например, 🏋️, 📚, 🧘):"
    )


# =============================================================================
# State: ADDING_SKILL_ICON
# =============================================================================

@router.message(AddSkillStates.ADDING_SKILL_ICON)
async def process_skill_icon(message: Message, state: FSMContext, db: AsyncSession, user: User) -> None:
    """Получаем иконку и сохраняем трекер."""
    icon = message.text.strip()
    
    # Простая валидация: иконка должна быть 1-10 символов
    if len(icon) < 1 or len(icon) > 10:
        await message.answer("❌ Иконка слишком длинная. Отправь один emoji:")
        return
    
    data = await state.get_data()
    name = data.get("skill_name")
    
    # Получаем максимальный sort_order
    result = await db.execute(
        select(func.max(CustomTracker.sort_order))
        .where(CustomTracker.user_id == user.id)
    )
    max_order = result.scalar() or 0
    
    tracker = CustomTracker(
        user_id=user.id,
        name=name,
        icon=icon,
        sort_order=max_order + 1,
    )
    db.add(tracker)
    await db.commit()
    
    await state.clear()
    await message.answer(
        f"🎉 Трекер добавлен!\n\n"
        f"{icon} <b>{name}</b>\n\n"
        f"Теперь ты можешь отмечать его прогресс в приложении.",
        reply_markup=_get_post_add_keyboard(),
    )
    logger.info(f"User {user.id} created tracker: {name} ({icon})")


# =============================================================================
# Cancel handler
# =============================================================================

@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    """Отмена conversation."""
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.clear()
    await message.answer("❌ Добавление трекера отменено.")


# =============================================================================
# Helper keyboards
# =============================================================================

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

def _get_post_add_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура после добавления трекера."""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🚀 Открыть Skill Tracer"))
    builder.row(KeyboardButton(text="➕ Добавить трекер"))
    return builder.as_markup(resize_keyboard=True)

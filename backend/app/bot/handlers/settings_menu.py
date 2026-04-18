"""
Settings Menu Handlers

Обработчики для раздела "⚙️ Настройки" (inline keyboard).
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.config import BotButtons, BotMessages
from app.bot.keyboards import get_settings_inline_keyboard, get_main_menu_keyboard
from app.models import User

router = Router(name="settings_menu")


@router.message(F.text == BotButtons.SETTINGS)
async def settings_handler(message: Message) -> None:
    """Обработчик Reply-кнопки Настройки — показывает inline-меню."""
    await message.answer(
        BotMessages.SETTINGS_TITLE,
        reply_markup=get_settings_inline_keyboard(),
    )


@router.callback_query(F.data == "settings:back_to_menu")
async def settings_back_to_menu(callback: CallbackQuery) -> None:
    """Удаляет inline-сообщение и возвращает главное Reply-меню."""
    await callback.message.delete()
    await callback.message.answer(
        "Главное меню",
        reply_markup=get_main_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "settings:change_name")
async def settings_change_name(callback: CallbackQuery) -> None:
    await callback.answer("👤 Изменение имени будет доступно скоро!")


@router.callback_query(F.data == "settings:change_email")
async def settings_change_email(callback: CallbackQuery) -> None:
    await callback.answer("📧 Изменение email будет доступно скоро!")


@router.callback_query(F.data == "settings:toggle_notifications")
async def settings_toggle_notifications(
    callback: CallbackQuery,
    db: AsyncSession,
    user: User,
) -> None:
    settings_data = user.settings or {}
    current = settings_data.get("notifications_enabled", True)
    new_value = not current
    settings_data["notifications_enabled"] = new_value
    user.settings = settings_data
    await db.commit()
    status = "включены" if new_value else "отключены"
    await callback.answer(f"🔔 Уведомления {status}")

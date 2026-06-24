import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import CommandStart

from app.config import settings
from app.handlers import entry

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Register routers
dp.include_router(entry.router)

@dp.message(CommandStart())
async def start_handler(message: Message) -> None:
    await message.answer(
        "👋 Welcome to SkillTracer!\n\n"
        "I will help you track habits, tasks, and expenses.\n\n"
        "📔 /entry — create daily entry\n"
        "❌ /cancel — cancel current operation"
    )

async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

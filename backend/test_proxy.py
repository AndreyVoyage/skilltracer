import asyncio
import os
from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiohttp import ClientTimeout

# Загружаем .env
from dotenv import load_dotenv
load_dotenv()

async def test_connection():
    proxy = os.getenv('TELEGRAM_PROXY')
    if proxy:
        # Логируем без credentials
        proxy_display = proxy.split("@")[-1] if "@" in proxy else proxy
        print(f"Testing proxy: {proxy_display}")
    else:
        print("Testing without proxy")
    
    try:
        if proxy:
            session = AiohttpSession(
                timeout=ClientTimeout(total=15),
                proxy=proxy
            )
            bot = Bot(token=os.getenv('BOT_TOKEN'), session=session)
        else:
            bot = Bot(token=os.getenv('BOT_TOKEN'))
        
        me = await bot.get_me()
        print(f"✅ SUCCESS! Bot connected: @{me.username}")
        print(f"   Bot ID: {me.id}")
        
        # Проверим webhook
        wh = await bot.get_webhook_info()
        print(f"   Current webhook: {wh.url if wh.url else 'Not set'}")
        
        await bot.session.close()
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False
    
    return True

if __name__ == "__main__":
    result = asyncio.run(test_connection())
    exit(0 if result else 1)

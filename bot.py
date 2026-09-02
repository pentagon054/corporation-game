import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")
WEBAPP_VERSION = "14"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан в переменных окружения.")
if not WEBAPP_URL:
    raise RuntimeError("WEBAPP_URL не задан в переменных окружения.")

async def main():
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def start(message: Message):
        kb = InlineKeyboardBuilder()
        kb.button(text="🎮 Играть", web_app=WebAppInfo(url=f"{WEBAPP_URL.rstrip('/')}/?v={WEBAPP_VERSION}"))
        await message.answer("🏢 <b>Построй свою корпорацию</b>\n\nСоздавай бизнесы, инвестируй и стань №1.", reply_markup=kb.as_markup())

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")

# Меняй это число после каждого обновления WebApp.
# Сейчас используем новую версию.
WEBAPP_VERSION = "5"


# ============================================================
# VALIDATION
# ============================================================

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан в переменных окружения.")

if not WEBAPP_URL:
    raise RuntimeError("WEBAPP_URL не задан в переменных окружения.")


# ============================================================
# BOT
# ============================================================

async def main():

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML
        )
    )

    dp = Dispatcher()


    # ========================================================
    # /START
    # ========================================================

    @dp.message(CommandStart())
    async def start(message: Message):

        kb = InlineKeyboardBuilder()


        # Формируем уникальный URL WebApp.
        #
        # Например:
        # https://corporation-game-production-862a.up.railway.app/?v=5
        #
        # Это помогает Telegram отличать новую версию
        # WebApp от старой закэшированной версии.

        base_url = WEBAPP_URL.rstrip("/")

        webapp_url = (
            f"{base_url}/?v={WEBAPP_VERSION}"
        )


        kb.button(
            text="🎮 Играть",
            web_app=WebAppInfo(
                url=webapp_url
            )
        )


        await message.answer(
            "🏢 <b>Построй свою корпорацию</b>\n\n"
            "Создавай бизнесы, зарабатывай деньги "
            "и стань №1.",
            reply_markup=kb.as_markup()
        )


    # ========================================================
    # START POLLING
    # ========================================================

    await bot.delete_webhook(
        drop_pending_updates=True
    )

    await dp.start_polling(bot)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    asyncio.run(main())
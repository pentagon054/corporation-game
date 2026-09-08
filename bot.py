import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")
WEBAPP_VERSION = "220"
ADMIN_IDS = {
    int(x.strip())
    for x in (os.getenv("ADMIN_IDS") or "").split(",")
    if x.strip().isdigit()
}

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан в переменных окружения.")
if not WEBAPP_URL:
    raise RuntimeError("WEBAPP_URL не задан в переменных окружения.")


def is_admin(user_id: int | None) -> bool:
    return bool(user_id is not None and int(user_id) in ADMIN_IDS)


def admin_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(
        text="🛠 Админ-панель",
        web_app=WebAppInfo(url=f"{WEBAPP_URL.rstrip('/')}/admin?v={WEBAPP_VERSION}"),
    )
    return kb.as_markup()


async def main():
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def start(message: Message):
        kb = InlineKeyboardBuilder()
        kb.button(
            text="🎮 Играть",
            web_app=WebAppInfo(url=f"{WEBAPP_URL.rstrip('/')}/?v={WEBAPP_VERSION}"),
        )
        kb.button(
            text="🏆 Сезоны",
            web_app=WebAppInfo(url=f"{WEBAPP_URL.rstrip('/')}/seasons?v={WEBAPP_VERSION}"),
        )
        if is_admin(message.from_user.id if message.from_user else None):
            kb.button(
                text="🛠 Админ-панель",
                web_app=WebAppInfo(url=f"{WEBAPP_URL.rstrip('/')}/admin?v={WEBAPP_VERSION}"),
            )

        kb.adjust(1)

        await message.answer(
            "🏢 <b>Построй свою корпорацию</b>\n\n"
            "Создавай бизнесы, инвестируй и стань №1.",
            reply_markup=kb.as_markup(),
        )

    @dp.message(Command("myid"))
    async def my_id(message: Message):
        if not message.from_user:
            await message.answer("Не удалось определить Telegram ID.")
            return
        await message.answer(
            f"🆔 Твой Telegram ID: <code>{message.from_user.id}</code>"
        )

    @dp.message(Command("admin"))
    async def admin(message: Message):
        uid = message.from_user.id if message.from_user else None
        if not is_admin(uid):
            await message.answer(
                "⛔ Доступ запрещён. Твой Telegram ID не указан в ADMIN_IDS.\n\n"
                "Проверь ID командой /myid."
            )
            return

        await message.answer(
            "🛠 <b>Corporation Admin Control Center</b>\n\n"
            "Открой закрытую панель управления сезоном:",
            reply_markup=admin_keyboard(),
        )

    @dp.message(Command("admin_status"))
    async def admin_status(message: Message):
        uid = message.from_user.id if message.from_user else None
        await message.answer(
            "🧪 <b>Диагностика админ-доступа</b>\n\n"
            f"Telegram ID: <code>{uid}</code>\n"
            f"В ADMIN_IDS: <b>{'да' if is_admin(uid) else 'нет'}</b>\n"
            f"Версия бота: <code>{WEBAPP_VERSION}</code>"
        )

    me = await bot.get_me()
    print(
        f"[Corporation Bot] starting polling | bot_id={me.id} | "
        f"version={WEBAPP_VERSION} | admin_ids={sorted(ADMIN_IDS)}"
    )

    # На случай, если раньше использовался webhook.
    await bot.delete_webhook(drop_pending_updates=False)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

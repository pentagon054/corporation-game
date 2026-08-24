
import asyncio
import hashlib
import hmac
import json
import os
import random
import sqlite3
import time
from contextlib import closing
from urllib.parse import parse_qsl

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BOT_TOKEN = os.getenv("BOT_TOKEN", "PASTE_YOUR_BOT_TOKEN_HERE")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://YOUR-HTTPS-URL")
DB_PATH = "corporation.db"

COLLECT_COOLDOWN = 30 * 60
MAX_OFFLINE_HOURS = 8

BUSINESSES = {
    "coffee": {"name": "☕ Кофейня", "desc": "Небольшая, но стабильная точка.", "base_cost": 5000, "base_income": 350, "unlock": 0},
    "delivery": {"name": "🚚 Доставка", "desc": "Курьеры доставляют еду и товары.", "base_cost": 35000, "base_income": 2100, "unlock": 2},
    "factory": {"name": "🏭 Фабрика", "desc": "Массовое производство.", "base_cost": 150000, "base_income": 9000, "unlock": 5},
    "it": {"name": "💻 IT-студия", "desc": "Разработка цифровых продуктов.", "base_cost": 650000, "base_income": 42000, "unlock": 10},
    "finance": {"name": "🏦 Финансовая компания", "desc": "Кредиты, инвестиции и комиссии.", "base_cost": 2500000, "base_income": 180000, "unlock": 18},
    "conglomerate": {"name": "🌐 Конгломерат", "desc": "Империя из разных отраслей.", "base_cost": 10000000, "base_income": 850000, "unlock": 30},
}

TECHS = {
    "marketing": {"name": "📣 Агрессивный маркетинг", "cost": 75000, "bonus": 0.15, "desc": "+15% ко всему доходу"},
    "automation": {"name": "⚙️ Автоматизация", "cost": 300000, "bonus": 0.30, "desc": "+30% ко всему доходу"},
    "analytics": {"name": "📊 Big Data", "cost": 1000000, "bonus": 0.50, "desc": "+50% ко всему доходу"},
}

EVENTS = [
    ("📈 Бум спроса", "Рынок растёт. Доход увеличен на 40%.", 1.40),
    ("🔥 Вирусная реклама", "Ваш бренд завирусился.", 1.70),
    ("⚡ Сбой поставок", "Проблемы с логистикой.", 0.65),
    ("🏛️ Новый контракт", "Получен выгодный контракт.", 2.00),
    ("😐 Обычный день", "Рынок стабилен.", 1.00),
]

api = FastAPI(title="Build Your Corporation")
WEB_DIR = os.path.join(os.path.dirname(__file__), "web")
api.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with closing(db()) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            corp_name TEXT NOT NULL,
            money INTEGER NOT NULL DEFAULT 10000,
            reputation INTEGER NOT NULL DEFAULT 1,
            last_collect INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS businesses (
            user_id INTEGER NOT NULL,
            business_id TEXT NOT NULL,
            level INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(user_id, business_id)
        );
        CREATE TABLE IF NOT EXISTS tech (
            user_id INTEGER NOT NULL,
            tech_id TEXT NOT NULL,
            PRIMARY KEY(user_id, tech_id)
        );
        CREATE TABLE IF NOT EXISTS stats (
            user_id INTEGER PRIMARY KEY,
            total_earned INTEGER NOT NULL DEFAULT 0,
            total_spent INTEGER NOT NULL DEFAULT 0,
            companies_bought INTEGER NOT NULL DEFAULT 0
        );
        """)
        conn.commit()


def verify_init_data(init_data: str):
    # Telegram production authentication.
    # In local browser testing, use x-user-id and set ALLOW_DEV_AUTH=1.
    if not init_data:
        if os.getenv("ALLOW_DEV_AUTH") == "1":
            return None
        raise HTTPException(401, "Open this game from Telegram.")

    data = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = data.pop("hash", None)
    if not received_hash:
        raise HTTPException(401, "Missing Telegram hash")

    data_check = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    calculated = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated, received_hash):
        raise HTTPException(401, "Invalid Telegram authentication")

    try:
        user = json.loads(data["user"])
    except Exception:
        raise HTTPException(401, "Invalid Telegram user")

    return user


def user_from_request(x_telegram_init_data: str | None, x_user_id: str | None):
    tg_user = verify_init_data(x_telegram_init_data or "")
    if tg_user:
        return int(tg_user["id"]), tg_user.get("username", ""), tg_user.get("first_name", "Игрок")
    if os.getenv("ALLOW_DEV_AUTH") == "1" and x_user_id:
        return int(x_user_id), "developer", "Разработчик"
    raise HTTPException(401, "Authentication required")


def ensure_player(uid, username=""):
    with closing(db()) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO players(user_id,username,corp_name,money,reputation,last_collect,created_at) VALUES(?,?,?,?,?,?,?)",
            (uid, username, "Новая корпорация", 10000, 1, 0, int(time.time()))
        )
        conn.execute("INSERT OR IGNORE INTO stats(user_id) VALUES(?)", (uid,))
        conn.execute("UPDATE players SET username=? WHERE user_id=?", (username, uid))
        conn.commit()


def get_player(uid):
    with closing(db()) as conn:
        return conn.execute("SELECT * FROM players WHERE user_id=?", (uid,)).fetchone()


def get_levels(uid):
    with closing(db()) as conn:
        rows = conn.execute("SELECT business_id,level FROM businesses WHERE user_id=?", (uid,)).fetchall()
    return {r["business_id"]: r["level"] for r in rows}


def get_techs(uid):
    with closing(db()) as conn:
        return {r["tech_id"] for r in conn.execute("SELECT tech_id FROM tech WHERE user_id=?", (uid,)).fetchall()}


def multiplier(uid):
    return 1 + sum(TECHS[t]["bonus"] for t in get_techs(uid) if t in TECHS)


def hourly_income(uid):
    levels = get_levels(uid)
    total = sum(BUSINESSES[b]["base_income"] * lvl for b, lvl in levels.items() if b in BUSINESSES)
    return int(total * multiplier(uid))


def next_business_cost(bid, level):
    return int(BUSINESSES[bid]["base_cost"] * (1.45 ** level))


def snapshot(uid):
    p = get_player(uid)
    levels = get_levels(uid)
    techs = get_techs(uid)
    with closing(db()) as conn:
        stats = conn.execute("SELECT * FROM stats WHERE user_id=?", (uid,)).fetchone()
    return {
        "player": dict(p),
        "hourly_income": hourly_income(uid),
        "multiplier": multiplier(uid),
        "businesses": [{
            "id": bid, **b, "level": levels.get(bid, 0),
            "next_cost": next_business_cost(bid, levels.get(bid, 0)),
            "locked": p["reputation"] < b["unlock"]
        } for bid, b in BUSINESSES.items()],
        "techs": [{"id": tid, **t, "owned": tid in techs} for tid, t in TECHS.items()],
        "stats": dict(stats),
    }


class NameBody(BaseModel):
    name: str


@api.get("/")
def index():
    return FileResponse(os.path.join(WEB_DIR, "index.html"))


@api.get("/api/state")
def state(x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    uid, username, _ = user_from_request(x_telegram_init_data, x_user_id)
    ensure_player(uid, username)
    return snapshot(uid)


@api.post("/api/rename")
def rename(body: NameBody, x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    uid, username, _ = user_from_request(x_telegram_init_data, x_user_id)
    ensure_player(uid, username)
    name = body.name.strip()[:32]
    if len(name) < 2:
        raise HTTPException(400, "Название должно содержать минимум 2 символа")
    with closing(db()) as conn:
        conn.execute("UPDATE players SET corp_name=? WHERE user_id=?", (name, uid))
        conn.commit()
    return snapshot(uid)


@api.post("/api/business/{bid}/buy")
def buy_business(bid: str, x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    uid, username, _ = user_from_request(x_telegram_init_data, x_user_id)
    ensure_player(uid, username)
    if bid not in BUSINESSES:
        raise HTTPException(404, "Бизнес не найден")

    p = get_player(uid)
    levels = get_levels(uid)
    level = levels.get(bid, 0)
    cost = next_business_cost(bid, level)

    if p["reputation"] < BUSINESSES[bid]["unlock"]:
        raise HTTPException(400, f"Нужна репутация {BUSINESSES[bid]['unlock']}")
    if p["money"] < cost:
        raise HTTPException(400, f"Не хватает {cost - p['money']} ₽")

    with closing(db()) as conn:
        conn.execute("UPDATE players SET money=money-?, reputation=reputation+1 WHERE user_id=?", (cost, uid))
        conn.execute("""INSERT INTO businesses(user_id,business_id,level) VALUES(?,?,1)
                        ON CONFLICT(user_id,business_id) DO UPDATE SET level=level+1""", (uid, bid))
        conn.execute("""UPDATE stats SET total_spent=total_spent+?, companies_bought=companies_bought+1 WHERE user_id=?""", (cost, uid))
        conn.commit()
    return snapshot(uid)


@api.post("/api/tech/{tid}/buy")
def buy_tech(tid: str, x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    uid, username, _ = user_from_request(x_telegram_init_data, x_user_id)
    ensure_player(uid, username)
    if tid not in TECHS:
        raise HTTPException(404, "Технология не найдена")
    if tid in get_techs(uid):
        raise HTTPException(400, "Уже исследовано")

    p = get_player(uid)
    cost = TECHS[tid]["cost"]
    if p["money"] < cost:
        raise HTTPException(400, "Недостаточно денег")

    with closing(db()) as conn:
        conn.execute("UPDATE players SET money=money-?, reputation=reputation+2 WHERE user_id=?", (cost, uid))
        conn.execute("INSERT INTO tech(user_id,tech_id) VALUES(?,?)", (uid, tid))
        conn.execute("UPDATE stats SET total_spent=total_spent+? WHERE user_id=?", (cost, uid))
        conn.commit()
    return snapshot(uid)


@api.post("/api/collect")
def collect(x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    uid, username, _ = user_from_request(x_telegram_init_data, x_user_id)
    ensure_player(uid, username)
    p = get_player(uid)
    now = int(time.time())
    income_per_hour = hourly_income(uid)

    if income_per_hour <= 0:
        raise HTTPException(400, "Сначала купи хотя бы один бизнес")

    if p["last_collect"]:
        passed = now - p["last_collect"]
        if passed < COLLECT_COOLDOWN:
            raise HTTPException(400, f"Подожди ещё {(COLLECT_COOLDOWN-passed)//60+1} мин.")
        hours = min(passed / 3600, MAX_OFFLINE_HOURS)
    else:
        hours = 1

    base = max(int(income_per_hour * hours), max(1, income_per_hour // 2))
    event = random.choice(EVENTS)
    earned = int(base * event[2])

    with closing(db()) as conn:
        conn.execute("UPDATE players SET money=money+?, reputation=reputation+1, last_collect=? WHERE user_id=?", (earned, now, uid))
        conn.execute("UPDATE stats SET total_earned=total_earned+? WHERE user_id=?", (earned, uid))
        conn.commit()

    return {"earned": earned, "event": {"name": event[0], "desc": event[1], "multiplier": event[2]}, "state": snapshot(uid)}


@api.get("/api/rating")
def rating(x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    uid, username, _ = user_from_request(x_telegram_init_data, x_user_id)
    ensure_player(uid, username)
    with closing(db()) as conn:
        rows = conn.execute("""SELECT corp_name,money,reputation FROM players
                               ORDER BY money DESC, reputation DESC LIMIT 20""").fetchall()
    return [dict(r) for r in rows]


async def run_bot():
    if BOT_TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE":
        return
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def start(message: Message):
        kb = InlineKeyboardBuilder()
        kb.button(text="🎮 Играть", web_app=WebAppInfo(url=WEBAPP_URL))
        await message.answer(
            "🏢 <b>Построй свою корпорацию</b>\n\n"
            "Создавай бизнесы, зарабатывай деньги и стань №1.",
            reply_markup=kb.as_markup()
        )

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    init_db()
    if BOT_TOKEN != "PASTE_YOUR_BOT_TOKEN_HERE":
        asyncio.run(run_bot())
    else:
        print("BOT_TOKEN не указан. Запусти сервер командой: uvicorn app:api --host 0.0.0.0 --port 8000")

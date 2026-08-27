import asyncio
import hashlib
import hmac
import json
import os
import random
import sqlite3
import time
from contextlib import closing
from datetime import datetime
from urllib.parse import parse_qsl

from aiogram import Bot, Dispatcher
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
DB_PATH = os.getenv(
    "DB_PATH",
    "corporation.db"
)

COLLECT_COOLDOWN = 30 * 60
MAX_OFFLINE_HOURS = 8
TAX_RATE = 0.05
TAX_GRACE_SECONDS = 12 * 60 * 60


BUSINESSES = {
    "coffee": {
        "name": "☕ Кофейня",
        "desc": "Небольшая, но стабильная точка.",
        "base_cost": 5000,
        "base_income": 350,
    },
    "delivery": {
        "name": "🚚 Доставка",
        "desc": "Курьеры доставляют еду и товары.",
        "base_cost": 35000,
        "base_income": 2100,
    },
    "factory": {
        "name": "🏭 Фабрика",
        "desc": "Массовое производство.",
        "base_cost": 150000,
        "base_income": 9000,
    },
    "it": {
        "name": "💻 IT-студия",
        "desc": "Разработка цифровых продуктов.",
        "base_cost": 650000,
        "base_income": 42000,
    },
    "finance": {
        "name": "🏦 Финансовая компания",
        "desc": "Кредиты, инвестиции и комиссии.",
        "base_cost": 2500000,
        "base_income": 180000,
    },
    "conglomerate": {
        "name": "🌐 Конгломерат",
        "desc": "Империя из разных отраслей.",
        "base_cost": 10000000,
        "base_income": 850000,
    },
}


TECHS = {
    "marketing": {
        "name": "📣 Агрессивный маркетинг",
        "cost": 75000,
        "bonus": 0.15,
        "desc": "+15% ко всему доходу",
    },
    "automation": {
        "name": "⚙️ Автоматизация",
        "cost": 300000,
        "bonus": 0.30,
        "desc": "+30% ко всему доходу",
    },
    "analytics": {
        "name": "📊 Big Data",
        "cost": 1000000,
        "bonus": 0.50,
        "desc": "+50% ко всему доходу",
    },
}


STOCKS = {
    "bmw": {
        "symbol": "BMW",
        "name": "BMW",
        "description": "Немецкая компания, производящая автомобили премиального сегмента.",
        "min_price": 200.0,
        "max_price": 450.0,
        "initial_price": 325.0,
        "up_min_change": -0.01,
        "up_max_change": 0.03,
        "down_min_change": -0.03,
        "down_max_change": 0.02,
    },
    "kfc": {
        "symbol": "KFC",
        "name": "KFC",
        "description": "Международная сеть ресторанов быстрого питания, специализирующаяся на блюдах из курицы.",
        "min_price": 90.0,
        "max_price": 235.0,
        "initial_price": 162.5,
        "up_min_change": -0.01,
        "up_max_change": 0.04,
        "down_min_change": -0.04,
        "down_max_change": 0.02,
    },
    "spotify": {
        "symbol": "SPOT",
        "name": "Spotify",
        "description": "Стриминговый сервис для прослушивания музыки, подкастов и другого аудиоконтента.",
        "min_price": 110.0,
        "max_price": 210.0,
        "initial_price": 160.0,
        "up_min_change": -0.01,
        "up_max_change": 0.02,
        # В ТЗ верхняя граница для нисходящего тренда Spotify не указана.
        # Используем согласованный безопасный вариант: -3% ... +2%.
        "down_min_change": -0.03,
        "down_max_change": 0.02,
    },
}

STOCK_UPDATE_INTERVAL = 60
MAX_STOCK_HISTORY_POINTS = 720


api = FastAPI(title="Build Your Corporation")

WEB_DIR = os.path.join(os.path.dirname(__file__), "web")

api.mount(
    "/static",
    StaticFiles(directory=WEB_DIR),
    name="static"
)


# ============================================================
# DATABASE
# ============================================================

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


        CREATE TABLE IF NOT EXISTS daily_profit (
            user_id INTEGER NOT NULL,
            day TEXT NOT NULL,
            earned INTEGER NOT NULL DEFAULT 0,

            PRIMARY KEY(user_id, day)
        );

        CREATE TABLE IF NOT EXISTS stocks (
            id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            min_price REAL NOT NULL,
            max_price REAL NOT NULL,
            current_price REAL NOT NULL,
            trend TEXT NOT NULL CHECK(trend IN ('up', 'down')),
            last_update INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS stock_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_id TEXT NOT NULL,
            price REAL NOT NULL,
            created_at INTEGER NOT NULL,
            FOREIGN KEY(stock_id) REFERENCES stocks(id)
        );

        CREATE INDEX IF NOT EXISTS idx_stock_history_stock_time
        ON stock_history(stock_id, created_at);

        CREATE TABLE IF NOT EXISTS stock_holdings (
            user_id INTEGER NOT NULL,
            stock_id TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            avg_buy_price REAL NOT NULL DEFAULT 0,

            PRIMARY KEY(user_id, stock_id),
            FOREIGN KEY(stock_id) REFERENCES stocks(id)
        );

        CREATE TABLE IF NOT EXISTS taxes (
            user_id INTEGER PRIMARY KEY,
            unpaid REAL NOT NULL DEFAULT 0,
            due_since INTEGER NOT NULL DEFAULT 0,
            last_paid INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS schema_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        """)

        now = int(time.time())

        for stock_id, stock in STOCKS.items():
            existing = conn.execute(
                """
                SELECT id
                FROM stocks
                WHERE id=?
                """,
                (stock_id,)
            ).fetchone()

            if not existing:
                conn.execute(
                    """
                    INSERT INTO stocks(
                        id,
                        symbol,
                        name,
                        description,
                        min_price,
                        max_price,
                        current_price,
                        trend,
                        last_update
                    )
                    VALUES(?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        stock_id,
                        stock["symbol"],
                        stock["name"],
                        stock["description"],
                        stock["min_price"],
                        stock["max_price"],
                        stock["initial_price"],
                        "up",
                        now,
                    )
                )

                conn.execute(
                    """
                    INSERT INTO stock_history(
                        stock_id,
                        price,
                        created_at
                    )
                    VALUES(?,?,?)
                    """,
                    (
                        stock_id,
                        stock["initial_price"],
                        now
                    )
                )

        # Одноразовая миграция статистики:
        # уровень бизнеса больше не считается отдельным бизнесом,
        # а покупки акций больше не входят в общие расходы.
        migration_done = conn.execute(
            "SELECT value FROM schema_meta WHERE key='stats_v2'"
        ).fetchone()

        if not migration_done:
            user_rows = conn.execute(
                "SELECT user_id FROM players"
            ).fetchall()

            for user_row in user_rows:
                uid = user_row["user_id"]

                business_rows = conn.execute(
                    """
                    SELECT business_id, level
                    FROM businesses
                    WHERE user_id=? AND level>0
                    """,
                    (uid,)
                ).fetchall()

                current_business_count = len(business_rows)
                recalculated_spent = 0

                for row in business_rows:
                    bid = row["business_id"]
                    level = int(row["level"])

                    if bid in BUSINESSES:
                        recalculated_spent += sum(
                            int(BUSINESSES[bid]["base_cost"] * (1.45 ** lvl))
                            for lvl in range(level)
                        )

                tech_rows = conn.execute(
                    "SELECT tech_id FROM tech WHERE user_id=?",
                    (uid,)
                ).fetchall()

                recalculated_spent += sum(
                    TECHS[row["tech_id"]]["cost"]
                    for row in tech_rows
                    if row["tech_id"] in TECHS
                )

                conn.execute(
                    """
                    UPDATE stats
                    SET companies_bought=?, total_spent=?
                    WHERE user_id=?
                    """,
                    (current_business_count, recalculated_spent, uid)
                )

            conn.execute(
                "INSERT OR REPLACE INTO schema_meta(key, value) VALUES('stats_v2', '1')"
            )

        conn.commit()


# Инициализируем структуру базы данных при любом запуске приложения.
# Это важно для Railway: uvicorn запускает app.py не через __main__.
init_db()

# ============================================================
# TELEGRAM AUTH
# ============================================================

def verify_init_data(init_data: str):
    if not init_data:
        if os.getenv("ALLOW_DEV_AUTH") == "1":
            return None

        raise HTTPException(
            401,
            "Open this game from Telegram."
        )

    data = dict(
        parse_qsl(
            init_data,
            keep_blank_values=True
        )
    )

    received_hash = data.pop(
        "hash",
        None
    )

    if not received_hash:
        raise HTTPException(
            401,
            "Missing Telegram hash"
        )

    data_check = "\n".join(
        f"{k}={v}"
        for k, v in sorted(data.items())
    )

    secret = hmac.new(
        b"WebAppData",
        BOT_TOKEN.encode(),
        hashlib.sha256
    ).digest()

    calculated = hmac.new(
        secret,
        data_check.encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(
        calculated,
        received_hash
    ):
        raise HTTPException(
            401,
            "Invalid Telegram authentication"
        )

    try:
        user = json.loads(
            data["user"]
        )

    except Exception:
        raise HTTPException(
            401,
            "Invalid Telegram user"
        )

    return user


def user_from_request(
    x_telegram_init_data: str | None,
    x_user_id: str | None
):
    tg_user = verify_init_data(
        x_telegram_init_data or ""
    )

    if tg_user:
        return (
            int(tg_user["id"]),
            tg_user.get("username", ""),
            tg_user.get("first_name", "Игрок")
        )

    if (
        os.getenv("ALLOW_DEV_AUTH") == "1"
        and x_user_id
    ):
        return (
            int(x_user_id),
            "developer",
            "Разработчик"
        )

    raise HTTPException(
        401,
        "Authentication required"
    )


# ============================================================
# PLAYER
# ============================================================

def ensure_player(uid, username=""):
    with closing(db()) as conn:

        conn.execute(
            """
            INSERT OR IGNORE INTO players(
                user_id,
                username,
                corp_name,
                money,
                last_collect,
                created_at
            )

            VALUES(?,?,?,?,?,?)
            """,
            (
                uid,
                username,
                "Новая корпорация",
                10000,
                0,
                int(time.time())
            )
        )

        conn.execute(
            """
            INSERT OR IGNORE INTO stats(
                user_id
            )
            VALUES(?)
            """,
            (uid,)
        )

        conn.execute(
            """
            UPDATE players
            SET username=?
            WHERE user_id=?
            """,
            (
                username,
                uid
            )
        )

        conn.execute(
            """
            INSERT OR IGNORE INTO taxes(user_id)
            VALUES(?)
            """,
            (uid,)
        )

        conn.commit()


def get_player(uid):
    with closing(db()) as conn:
        return conn.execute(
            """
            SELECT *
            FROM players
            WHERE user_id=?
            """,
            (uid,)
        ).fetchone()


def get_levels(uid):
    with closing(db()) as conn:

        rows = conn.execute(
            """
            SELECT
                business_id,
                level

            FROM businesses

            WHERE user_id=?
            """,
            (uid,)
        ).fetchall()

    return {
        r["business_id"]: r["level"]
        for r in rows
    }


def get_techs(uid):
    with closing(db()) as conn:

        rows = conn.execute(
            """
            SELECT tech_id
            FROM tech
            WHERE user_id=?
            """,
            (uid,)
        ).fetchall()

    return {
        r["tech_id"]
        for r in rows
    }


# ============================================================
# ECONOMY
# ============================================================

def multiplier(uid):
    return 1 + sum(
        TECHS[t]["bonus"]

        for t in get_techs(uid)

        if t in TECHS
    )


def hourly_income(uid):

    levels = get_levels(uid)

    total = sum(
        BUSINESSES[b]["base_income"] * lvl

        for b, lvl in levels.items()

        if b in BUSINESSES
    )

    return int(
        total * multiplier(uid)
    )


def next_business_cost(
    bid,
    level
):
    return int(
        BUSINESSES[bid]["base_cost"]
        * (1.45 ** level)
    )


def business_capitalization(bid, level):
    if bid not in BUSINESSES or level <= 0:
        return 0

    return sum(
        next_business_cost(bid, lvl)
        for lvl in range(level)
    )


def get_tax_status(uid):
    now = int(time.time())

    with closing(db()) as conn:
        row = conn.execute(
            """
            SELECT unpaid, due_since, last_paid
            FROM taxes
            WHERE user_id=?
            """,
            (uid,)
        ).fetchone()

    unpaid = float(row["unpaid"] if row else 0)
    due_since = int(row["due_since"] if row else 0)
    last_paid = int(row["last_paid"] if row else 0)

    blocked = bool(
        unpaid > 0
        and due_since > 0
        and now - due_since >= TAX_GRACE_SECONDS
    )

    seconds_left = (
        max(0, TAX_GRACE_SECONDS - (now - due_since))
        if unpaid > 0 and due_since > 0
        else TAX_GRACE_SECONDS
    )

    return {
        "rate": TAX_RATE,
        "rate_percent": int(TAX_RATE * 100),
        "unpaid": round(unpaid, 2),
        "due_since": due_since,
        "last_paid": last_paid,
        "blocked": blocked,
        "seconds_left": seconds_left,
    }


# ============================================================
# DAILY PROFIT
# ============================================================

def current_day():
    return datetime.now().strftime(
        "%Y-%m-%d"
    )


def add_daily_profit(
    uid,
    earned
):
    day = current_day()

    with closing(db()) as conn:

        conn.execute(
            """
            INSERT INTO daily_profit(
                user_id,
                day,
                earned
            )

            VALUES(?,?,?)

            ON CONFLICT(user_id, day)

            DO UPDATE SET

            earned = earned + excluded.earned
            """,
            (
                uid,
                day,
                earned
            )
        )

        conn.commit()


def get_daily_profit(
    uid
):
    with closing(db()) as conn:

        rows = conn.execute(
            """
            SELECT
                day,
                earned

            FROM daily_profit

            WHERE user_id=?

            ORDER BY day ASC
            """,
            (uid,)
        ).fetchall()

    return [
        {
            "day": r["day"],
            "earned": r["earned"]
        }

        for r in rows
    ]


# ============================================================
# SNAPSHOT
# ============================================================

def snapshot(uid):

    p = get_player(uid)
    levels = get_levels(uid)
    techs = get_techs(uid)
    tax_status = get_tax_status(uid)
    gross_hourly_income = hourly_income(uid)
    income_multiplier = multiplier(uid)

    with closing(db()) as conn:
        stats = conn.execute(
            """
            SELECT *
            FROM stats
            WHERE user_id=?
            """,
            (uid,)
        ).fetchone()

    businesses = []

    for bid, business in BUSINESSES.items():
        level = levels.get(bid, 0)
        capitalization = business_capitalization(bid, level)

        businesses.append({
            "id": bid,
            **business,
            "level": level,
            "next_cost": next_business_cost(bid, level),
            "current_income": int(
                business["base_income"] * level * income_multiplier
            ),
            "income_after_purchase": int(
                business["base_income"] * (level + 1) * income_multiplier
            ),
            "capitalization": capitalization,
            "sell_price": int(capitalization * 0.30),
        })

    return {
        "player": dict(p),
        "hourly_income": 0 if tax_status["blocked"] else gross_hourly_income,
        "gross_hourly_income": gross_hourly_income,
        "income_blocked": tax_status["blocked"],
        "multiplier": income_multiplier,
        "businesses": businesses,
        "techs": [
            {
                "id": tid,
                **tech,
                "owned": tid in techs
            }
            for tid, tech in TECHS.items()
        ],
        "stats": dict(stats),
        "taxes": tax_status,
    }


# ============================================================
# PUBLIC PROFILE
# ============================================================

def public_profile(uid):

    player = get_player(uid)

    if not player:

        raise HTTPException(
            404,
            "Игрок не найден"
        )

    levels = get_levels(uid)

    with closing(db()) as conn:

        stats = conn.execute(
            """
            SELECT *
            FROM stats
            WHERE user_id=?
            """,
            (uid,)
        ).fetchone()

    bought_businesses = []

    for bid, level in levels.items():

        if level > 0 and bid in BUSINESSES:

            bought_businesses.append({

                "id": bid,

                "name": BUSINESSES[bid]["name"],

                "description": BUSINESSES[bid]["desc"],

                "level": level,

                "income_per_hour":

                    int(
                        BUSINESSES[bid]["base_income"]
                        * level
                    )

            })

    return {

        "player": {

            "user_id": player["user_id"],

            "username": player["username"],

            "corp_name": player["corp_name"],

            "money": player["money"],

            "created_at": player["created_at"]

        },

        "hourly_income":

            hourly_income(uid),

        "stats":

            dict(stats),

        "businesses":

            bought_businesses,

        "daily_profit":

            get_daily_profit(uid)

    }


# ============================================================
# STOCK MARKET
# ============================================================

def update_stock_market():
    now = int(time.time())

    with closing(db()) as conn:
        conn.execute("BEGIN IMMEDIATE")

        stocks = conn.execute(
            """
            SELECT *
            FROM stocks
            """
        ).fetchall()

        for stock in stocks:
            elapsed = now - stock["last_update"]

            if elapsed < STOCK_UPDATE_INTERVAL:
                continue

            steps = elapsed // STOCK_UPDATE_INTERVAL
            config = STOCKS.get(stock["id"])

            if not config:
                continue

            price = float(stock["current_price"])
            trend = stock["trend"]
            last_update = int(stock["last_update"])

            for _ in range(int(steps)):
                if trend == "up":
                    change = random.uniform(
                        config["up_min_change"],
                        config["up_max_change"]
                    )
                else:
                    change = random.uniform(
                        config["down_min_change"],
                        config["down_max_change"]
                    )

                next_price = price * (1 + change)

                # Чем ближе цена к границам, тем выше вероятность разворота.
                range_size = config["max_price"] - config["min_price"]
                position = (
                    (next_price - config["min_price"]) / range_size
                    if range_size > 0 else 0.5
                )

                if next_price <= config["min_price"]:
                    next_price = config["min_price"]
                    trend = "up"
                elif next_price >= config["max_price"]:
                    next_price = config["max_price"]
                    trend = "down"
                else:
                    if position <= 0.15 and random.random() < 0.65:
                        trend = "up"
                    elif position >= 0.85 and random.random() < 0.65:
                        trend = "down"
                    else:
                        # Небольшая вероятность естественной смены тренда.
                        if random.random() < 0.08:
                            trend = "down" if trend == "up" else "up"

                price = round(next_price, 2)
                last_update += STOCK_UPDATE_INTERVAL

                conn.execute(
                    """
                    INSERT INTO stock_history(
                        stock_id,
                        price,
                        created_at
                    )
                    VALUES(?,?,?)
                    """,
                    (
                        stock["id"],
                        price,
                        last_update
                    )
                )

            conn.execute(
                """
                UPDATE stocks
                SET
                    current_price=?,
                    trend=?,
                    last_update=?
                WHERE id=?
                """,
                (
                    price,
                    trend,
                    last_update,
                    stock["id"]
                )
            )

        conn.commit()


def stock_change_percent(conn, stock_id):
    rows = conn.execute(
        """
        SELECT price
        FROM stock_history
        WHERE stock_id=?
        ORDER BY created_at DESC, id DESC
        LIMIT 2
        """,
        (stock_id,)
    ).fetchall()

    if len(rows) < 2:
        return 0.0

    current = float(rows[0]["price"])
    previous = float(rows[1]["price"])

    if previous == 0:
        return 0.0

    return round(((current - previous) / previous) * 100, 4)


def get_stocks():
    update_stock_market()

    with closing(db()) as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM stocks
            ORDER BY name ASC
            """
        ).fetchall()

        result = []
        for row in rows:
            item = dict(row)
            item["change_percent"] = stock_change_percent(conn, row["id"])
            result.append(item)

    return result


def get_stock(stock_id):
    update_stock_market()

    with closing(db()) as conn:
        row = conn.execute(
            """
            SELECT *
            FROM stocks
            WHERE id=?
            """,
            (stock_id,)
        ).fetchone()

    if not row:
        raise HTTPException(404, "Акция не найдена")

    return row


def get_stock_history(stock_id):
    update_stock_market()

    with closing(db()) as conn:
        rows = conn.execute(
            """
            SELECT price, created_at
            FROM (
                SELECT id, price, created_at
                FROM stock_history
                WHERE stock_id=?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
            )
            ORDER BY created_at ASC, id ASC
            """,
            (
                stock_id,
                MAX_STOCK_HISTORY_POINTS
            )
        ).fetchall()

    return [dict(row) for row in rows]


def get_brokerage_account(uid):
    update_stock_market()

    with closing(db()) as conn:
        rows = conn.execute(
            """
            SELECT
                h.stock_id,
                h.quantity,
                h.avg_buy_price,
                s.symbol,
                s.name,
                s.description,
                s.current_price
            FROM stock_holdings h
            JOIN stocks s ON s.id=h.stock_id
            WHERE h.user_id=? AND h.quantity>0
            ORDER BY s.name ASC
            """,
            (uid,)
        ).fetchall()

    holdings = []
    total_invested = 0.0
    total_current_value = 0.0

    for row in rows:
        invested = row["quantity"] * row["avg_buy_price"]
        current_value = row["quantity"] * row["current_price"]
        profit = current_value - invested
        profit_percent = (
            (profit / invested) * 100
            if invested > 0 else 0
        )

        total_invested += invested
        total_current_value += current_value

        holdings.append({
            "stock_id": row["stock_id"],
            "symbol": row["symbol"],
            "name": row["name"],
            "description": row["description"],
            "quantity": row["quantity"],
            "avg_buy_price": round(row["avg_buy_price"], 2),
            "current_price": round(row["current_price"], 2),
            "invested": round(invested, 2),
            "current_value": round(current_value, 2),
            "profit": round(profit, 2),
            "profit_percent": round(profit_percent, 2),
        })

    total_profit = total_current_value - total_invested
    total_profit_percent = (
        (total_profit / total_invested) * 100
        if total_invested > 0 else 0
    )

    return {
        "holdings": holdings,
        "total_invested": round(total_invested, 2),
        "total_current_value": round(total_current_value, 2),
        "total_profit": round(total_profit, 2),
        "total_profit_percent": round(total_profit_percent, 2),
    }


# ============================================================
# REQUEST MODELS
# ============================================================

class NameBody(BaseModel):
    name: str


class QuantityBody(BaseModel):
    quantity: int


# ============================================================
# WEB
# ============================================================

@api.get("/")
def index():

    return FileResponse(
        os.path.join(
            WEB_DIR,
            "index.html"
        ),
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    )


# ============================================================
# GAME STATE
# ============================================================

@api.get("/api/state")
def state(

    x_telegram_init_data: str | None = Header(None),

    x_user_id: str | None = Header(None)

):

    uid, username, _ = user_from_request(

        x_telegram_init_data,

        x_user_id

    )

    ensure_player(
        uid,
        username
    )

    return snapshot(uid)


# ============================================================
# RENAME
# ============================================================

@api.post("/api/rename")
def rename(

    body: NameBody,

    x_telegram_init_data: str | None = Header(None),

    x_user_id: str | None = Header(None)

):

    uid, username, _ = user_from_request(

        x_telegram_init_data,

        x_user_id

    )

    ensure_player(
        uid,
        username
    )

    name = body.name.strip()[:32]

    if len(name) < 2:

        raise HTTPException(

            400,

            "Название должно содержать минимум 2 символа"

        )

    with closing(db()) as conn:

        conn.execute(

            """
            UPDATE players

            SET corp_name=?

            WHERE user_id=?
            """,

            (
                name,
                uid
            )
        )

        conn.commit()

    return snapshot(uid)


# ============================================================
# BUY BUSINESS
# ============================================================

@api.post("/api/business/{bid}/buy")
def buy_business(

    bid: str,

    x_telegram_init_data: str | None = Header(None),

    x_user_id: str | None = Header(None)

):

    uid, username, _ = user_from_request(

        x_telegram_init_data,

        x_user_id

    )

    ensure_player(
        uid,
        username
    )

    if bid not in BUSINESSES:

        raise HTTPException(
            404,
            "Бизнес не найден"
        )

    player = get_player(uid)

    levels = get_levels(uid)

    level = levels.get(
        bid,
        0
    )

    cost = next_business_cost(
        bid,
        level
    )

    if player["money"] < cost:

        raise HTTPException(

            400,

            f"Не хватает {cost - player['money']} ₽"

        )

    is_new_business = level == 0

    with closing(db()) as conn:

        conn.execute(

            """
            UPDATE players

            SET money=money-?

            WHERE user_id=?
            """,

            (
                cost,
                uid
            )
        )

        conn.execute(

            """
            INSERT INTO businesses(
                user_id,
                business_id,
                level
            )

            VALUES(?,?,1)

            ON CONFLICT(
                user_id,
                business_id
            )

            DO UPDATE SET

            level=level+1
            """,

            (
                uid,
                bid
            )
        )

        conn.execute(

            """
            UPDATE stats

            SET
                total_spent=total_spent+?,
                companies_bought=companies_bought+?

            WHERE user_id=?
            """,

            (
                cost,
                1 if is_new_business else 0,
                uid
            )
        )

        conn.commit()

    return snapshot(uid)


# ============================================================
# SELL BUSINESS
# ============================================================

@api.post("/api/business/{bid}/sell")
def sell_business(
    bid: str,
    x_telegram_init_data: str | None = Header(None),
    x_user_id: str | None = Header(None)
):
    uid, username, _ = user_from_request(
        x_telegram_init_data,
        x_user_id
    )
    ensure_player(uid, username)

    if bid not in BUSINESSES:
        raise HTTPException(404, "Бизнес не найден")

    level = int(get_levels(uid).get(bid, 0))

    if level <= 0:
        raise HTTPException(400, "У тебя нет этого бизнеса")

    capitalization = business_capitalization(bid, level)
    sell_price = int(capitalization * 0.30)

    with closing(db()) as conn:
        conn.execute("BEGIN IMMEDIATE")

        conn.execute(
            """
            DELETE FROM businesses
            WHERE user_id=? AND business_id=?
            """,
            (uid, bid)
        )

        conn.execute(
            """
            UPDATE players
            SET money=money+?
            WHERE user_id=?
            """,
            (sell_price, uid)
        )

        conn.commit()

    return {
        "message": "Бизнес продан",
        "capitalization": capitalization,
        "sell_price": sell_price,
        "state": snapshot(uid),
    }


# ============================================================
# BUY TECHNOLOGY
# ============================================================

@api.post("/api/tech/{tid}/buy")
def buy_tech(

    tid: str,

    x_telegram_init_data: str | None = Header(None),

    x_user_id: str | None = Header(None)

):

    uid, username, _ = user_from_request(

        x_telegram_init_data,

        x_user_id

    )

    ensure_player(
        uid,
        username
    )

    if tid not in TECHS:

        raise HTTPException(
            404,
            "Технология не найдена"
        )

    if tid in get_techs(uid):

        raise HTTPException(
            400,
            "Уже исследовано"
        )

    player = get_player(uid)

    cost = TECHS[tid]["cost"]

    if player["money"] < cost:

        raise HTTPException(
            400,
            "Недостаточно денег"
        )

    with closing(db()) as conn:

        conn.execute(

            """
            UPDATE players

            SET money=money-?

            WHERE user_id=?
            """,

            (
                cost,
                uid
            )
        )

        conn.execute(

            """
            INSERT INTO tech(
                user_id,
                tech_id
            )

            VALUES(?,?)
            """,

            (
                uid,
                tid
            )
        )

        conn.execute(

            """
            UPDATE stats

            SET total_spent=total_spent+?

            WHERE user_id=?
            """,

            (
                cost,
                uid
            )
        )

        conn.commit()

    return snapshot(uid)


# ============================================================
# COLLECT PROFIT
# ============================================================

@api.post("/api/collect")
def collect(
    x_telegram_init_data: str | None = Header(None),
    x_user_id: str | None = Header(None)
):
    uid, username, _ = user_from_request(
        x_telegram_init_data,
        x_user_id
    )
    ensure_player(uid, username)

    player = get_player(uid)
    now = int(time.time())
    tax_status = get_tax_status(uid)

    if tax_status["blocked"]:
        raise HTTPException(
            400,
            "Доход остановлен из-за неоплаченных налогов. Оплати налог во вкладке «Налоги»."
        )

    income_per_hour = hourly_income(uid)

    if income_per_hour <= 0:
        raise HTTPException(400, "Сначала купи хотя бы один бизнес")

    if player["last_collect"]:
        passed = now - player["last_collect"]

        if passed < COLLECT_COOLDOWN:
            raise HTTPException(
                400,
                f"Подожди ещё {(COLLECT_COOLDOWN-passed)//60+1} мин."
            )

        hours = min(passed / 3600, MAX_OFFLINE_HOURS)
    else:
        hours = 1

    earned = max(
        int(income_per_hour * hours),
        max(1, income_per_hour // 2)
    )

    tax_amount = round(earned * TAX_RATE, 2)

    with closing(db()) as conn:
        conn.execute("BEGIN IMMEDIATE")

        conn.execute(
            "UPDATE players SET money=money+?, last_collect=? WHERE user_id=?",
            (earned, now, uid)
        )

        conn.execute(
            "UPDATE stats SET total_earned=total_earned+? WHERE user_id=?",
            (earned, uid)
        )

        conn.execute(
            """
            INSERT INTO taxes(user_id, unpaid, due_since, last_paid)
            VALUES(?,?,?,0)
            ON CONFLICT(user_id)
            DO UPDATE SET
                unpaid=taxes.unpaid + excluded.unpaid,
                due_since=CASE
                    WHEN taxes.unpaid > 0 AND taxes.due_since > 0
                    THEN taxes.due_since
                    ELSE excluded.due_since
                END
            """,
            (uid, tax_amount, now)
        )

        conn.commit()

    add_daily_profit(uid, earned)

    return {
        "earned": earned,
        "tax_accrued": tax_amount,
        "state": snapshot(uid)
    }


# ============================================================
# TAXES
# ============================================================

@api.get("/api/taxes")
def taxes_status(
    x_telegram_init_data: str | None = Header(None),
    x_user_id: str | None = Header(None)
):
    uid, username, _ = user_from_request(x_telegram_init_data, x_user_id)
    ensure_player(uid, username)
    return get_tax_status(uid)


@api.post("/api/taxes/pay")
def pay_taxes(
    x_telegram_init_data: str | None = Header(None),
    x_user_id: str | None = Header(None)
):
    uid, username, _ = user_from_request(x_telegram_init_data, x_user_id)
    ensure_player(uid, username)

    with closing(db()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        tax = conn.execute(
            "SELECT unpaid, due_since FROM taxes WHERE user_id=?",
            (uid,)
        ).fetchone()
        unpaid = float(tax["unpaid"] if tax else 0)
        due_since = int(tax["due_since"] if tax else 0)

        if unpaid <= 0:
            conn.rollback()
            raise HTTPException(400, "Неоплаченных налогов нет")

        player = conn.execute("SELECT money FROM players WHERE user_id=?", (uid,)).fetchone()

        if float(player["money"]) < unpaid:
            conn.rollback()
            raise HTTPException(400, f"Недостаточно денег. Для оплаты нужно {unpaid:.2f} ₽")

        now = int(time.time())
        was_blocked = bool(
            unpaid > 0
            and due_since > 0
            and now - due_since >= TAX_GRACE_SECONDS
        )

        if was_blocked:
            conn.execute(
                "UPDATE players SET money=money-?, last_collect=? WHERE user_id=?",
                (unpaid, now, uid)
            )
        else:
            conn.execute(
                "UPDATE players SET money=money-? WHERE user_id=?",
                (unpaid, uid)
            )

        conn.execute(
            "UPDATE taxes SET unpaid=0, due_since=0, last_paid=? WHERE user_id=?",
            (now, uid)
        )
        conn.commit()

    return {
        "paid": round(unpaid, 2),
        "state": snapshot(uid)
    }


# ============================================================
# PLAYER STATISTICS
# ============================================================

@api.get("/api/statistics")
def statistics(

    x_telegram_init_data: str | None = Header(None),

    x_user_id: str | None = Header(None)

):

    uid, username, _ = user_from_request(

        x_telegram_init_data,

        x_user_id

    )

    ensure_player(
        uid,
        username
    )

    player = get_player(uid)

    with closing(db()) as conn:

        stats = conn.execute(

            """
            SELECT *

            FROM stats

            WHERE user_id=?
            """,

            (uid,)
        ).fetchone()


    return {

        "player": {

            "corp_name":

                player["corp_name"],

            "money":

                player["money"],

            "created_at":

                player["created_at"]

        },

        "hourly_income":

            hourly_income(uid),

        "total_spent":

            stats["total_spent"],

        "total_earned":

            stats["total_earned"],

        "companies_bought":

            stats["companies_bought"],

        "daily_profit":

            get_daily_profit(uid)

    }


# ============================================================
# RATING
# ============================================================

@api.get("/api/rating")
def rating(

    x_telegram_init_data: str | None = Header(None),

    x_user_id: str | None = Header(None)

):

    uid, username, _ = user_from_request(

        x_telegram_init_data,

        x_user_id

    )

    ensure_player(
        uid,
        username
    )

    with closing(db()) as conn:

        rows = conn.execute(

            """
            SELECT

                user_id,

                corp_name,

                username,

                money

            FROM players

            ORDER BY money DESC

            LIMIT 20
            """

        ).fetchall()


    return [

        dict(row)

        for row in rows

    ]


# ============================================================
# PUBLIC PLAYER PROFILE
# ============================================================

@api.get("/api/player/{player_id}")
def player_profile(

    player_id: int,

    x_telegram_init_data: str | None = Header(None),

    x_user_id: str | None = Header(None)

):

    uid, username, _ = user_from_request(

        x_telegram_init_data,

        x_user_id

    )

    ensure_player(
        uid,
        username
    )

    return public_profile(
        player_id
    )


# ============================================================
# INVESTMENTS: STOCKS
# ============================================================

@api.get("/api/stocks")
def stocks(
    x_telegram_init_data: str | None = Header(None),
    x_user_id: str | None = Header(None)
):
    uid, username, _ = user_from_request(
        x_telegram_init_data,
        x_user_id
    )
    ensure_player(uid, username)
    return get_stocks()


@api.get("/api/stocks/{stock_id}")
def stock_detail(
    stock_id: str,
    x_telegram_init_data: str | None = Header(None),
    x_user_id: str | None = Header(None)
):
    uid, username, _ = user_from_request(
        x_telegram_init_data,
        x_user_id
    )
    ensure_player(uid, username)

    stock = dict(get_stock(stock_id))
    stock["history"] = get_stock_history(stock_id)

    with closing(db()) as conn:
        stock["change_percent"] = stock_change_percent(conn, stock_id)

    return stock


@api.get("/api/brokerage-account")
def brokerage_account(
    x_telegram_init_data: str | None = Header(None),
    x_user_id: str | None = Header(None)
):
    uid, username, _ = user_from_request(
        x_telegram_init_data,
        x_user_id
    )
    ensure_player(uid, username)
    return get_brokerage_account(uid)


@api.post("/api/stocks/{stock_id}/buy")
def buy_stock(
    stock_id: str,
    body: QuantityBody,
    x_telegram_init_data: str | None = Header(None),
    x_user_id: str | None = Header(None)
):
    if body.quantity <= 0:
        raise HTTPException(400, "Количество акций должно быть больше нуля")

    uid, username, _ = user_from_request(
        x_telegram_init_data,
        x_user_id
    )
    ensure_player(uid, username)

    update_stock_market()

    with closing(db()) as conn:
        conn.execute("BEGIN IMMEDIATE")

        stock = conn.execute(
            """
            SELECT *
            FROM stocks
            WHERE id=?
            """,
            (stock_id,)
        ).fetchone()

        if not stock:
            conn.rollback()
            raise HTTPException(404, "Акция не найдена")

        player = conn.execute(
            """
            SELECT money
            FROM players
            WHERE user_id=?
            """,
            (uid,)
        ).fetchone()

        price = float(stock["current_price"])
        total_cost = round(price * body.quantity, 2)

        if player["money"] < total_cost:
            conn.rollback()
            raise HTTPException(
                400,
                f"Недостаточно денег. Нужно {total_cost:.2f} ₽"
            )

        holding = conn.execute(
            """
            SELECT quantity, avg_buy_price
            FROM stock_holdings
            WHERE user_id=? AND stock_id=?
            """,
            (uid, stock_id)
        ).fetchone()

        old_quantity = holding["quantity"] if holding else 0
        old_avg = holding["avg_buy_price"] if holding else 0.0
        new_quantity = old_quantity + body.quantity

        new_avg = (
            (old_quantity * old_avg + body.quantity * price)
            / new_quantity
        )

        conn.execute(
            """
            UPDATE players
            SET money=money-?
            WHERE user_id=?
            """,
            (total_cost, uid)
        )

        conn.execute(
            """
            INSERT INTO stock_holdings(
                user_id,
                stock_id,
                quantity,
                avg_buy_price
            )
            VALUES(?,?,?,?)
            ON CONFLICT(user_id, stock_id)
            DO UPDATE SET
                quantity=excluded.quantity,
                avg_buy_price=excluded.avg_buy_price
            """,
            (
                uid,
                stock_id,
                new_quantity,
                new_avg
            )
        )

        conn.commit()

    return {
        "message": f"Куплено акций: {body.quantity}",
        "stock_id": stock_id,
        "quantity": body.quantity,
        "price_per_stock": round(price, 2),
        "total_cost": total_cost,
        "state": snapshot(uid),
        "brokerage_account": get_brokerage_account(uid),
    }


@api.post("/api/stocks/{stock_id}/sell")
def sell_stock(
    stock_id: str,
    body: QuantityBody,
    x_telegram_init_data: str | None = Header(None),
    x_user_id: str | None = Header(None)
):
    if body.quantity <= 0:
        raise HTTPException(400, "Количество акций должно быть больше нуля")

    uid, username, _ = user_from_request(
        x_telegram_init_data,
        x_user_id
    )
    ensure_player(uid, username)

    update_stock_market()

    with closing(db()) as conn:
        conn.execute("BEGIN IMMEDIATE")

        stock = conn.execute(
            """
            SELECT current_price
            FROM stocks
            WHERE id=?
            """,
            (stock_id,)
        ).fetchone()

        if not stock:
            conn.rollback()
            raise HTTPException(404, "Акция не найдена")

        holding = conn.execute(
            """
            SELECT quantity
            FROM stock_holdings
            WHERE user_id=? AND stock_id=?
            """,
            (uid, stock_id)
        ).fetchone()

        if not holding or holding["quantity"] < body.quantity:
            conn.rollback()
            raise HTTPException(
                400,
                "У вас недостаточно акций для продажи"
            )

        price = float(stock["current_price"])
        total_income = round(price * body.quantity, 2)
        remaining = holding["quantity"] - body.quantity

        if remaining == 0:
            conn.execute(
                """
                DELETE FROM stock_holdings
                WHERE user_id=? AND stock_id=?
                """,
                (uid, stock_id)
            )
        else:
            conn.execute(
                """
                UPDATE stock_holdings
                SET quantity=?
                WHERE user_id=? AND stock_id=?
                """,
                (
                    remaining,
                    uid,
                    stock_id
                )
            )

        conn.execute(
            """
            UPDATE players
            SET money=money+?
            WHERE user_id=?
            """,
            (total_income, uid)
        )

        # Продажа акций не является производственным доходом,
        # поэтому total_earned не увеличиваем.
        conn.commit()

    return {
        "message": f"Продано акций: {body.quantity}",
        "stock_id": stock_id,
        "quantity": body.quantity,
        "price_per_stock": round(price, 2),
        "total_income": total_income,
        "state": snapshot(uid),
        "brokerage_account": get_brokerage_account(uid),
    }


# ============================================================
# TELEGRAM BOT
# ============================================================

async def run_bot():

    if BOT_TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE":

        return


    bot = Bot(

        BOT_TOKEN,

        default=DefaultBotProperties(

            parse_mode=ParseMode.HTML

        )

    )


    dp = Dispatcher()


    @dp.message(CommandStart())

    async def start(
        message: Message
    ):

        keyboard = InlineKeyboardBuilder()

        keyboard.button(

            text="🎮 Играть",

            web_app=WebAppInfo(

                url=WEBAPP_URL

            )

        )


        await message.answer(

            "🏢 <b>Построй свою корпорацию</b>\n\n"

            "Создавай бизнесы, зарабатывай деньги и стань №1.",

            reply_markup=keyboard.as_markup()

        )


    await bot.delete_webhook(

        drop_pending_updates=True

    )


    await dp.start_polling(
        bot
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    init_db()


    if BOT_TOKEN != "PASTE_YOUR_BOT_TOKEN_HERE":

        asyncio.run(
            run_bot()
        )

    else:

        print(

            "BOT_TOKEN не указан. "

            "Запусти сервер командой: "

            "uvicorn app:api --host 0.0.0.0 --port 8000"

        )
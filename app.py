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

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BOT_TOKEN = os.getenv("BOT_TOKEN", "PASTE_YOUR_BOT_TOKEN_HERE")
DB_PATH = os.getenv("DB_PATH", "corporation.db")

TAX_RATE = 0.05
TAX_GRACE_SECONDS = 12 * 60 * 60
STOCK_UPDATE_INTERVAL = 60
MAX_STOCK_HISTORY_POINTS = 720
REAL_ESTATE_DAILY_GROWTH = 0.005

BUSINESSES = {
    "coffee": {"name": "☕ Кофейня", "desc": "Небольшая, но стабильная точка.", "base_cost": 5000, "base_income": 350},
    "delivery": {"name": "🚚 Доставка", "desc": "Курьеры доставляют еду и товары.", "base_cost": 35000, "base_income": 2100},
    "factory": {"name": "🏭 Фабрика", "desc": "Массовое производство.", "base_cost": 150000, "base_income": 9000},
    "it": {"name": "💻 IT-студия", "desc": "Разработка цифровых продуктов.", "base_cost": 650000, "base_income": 42000},
    "finance": {"name": "🏦 Финансовая компания", "desc": "Кредиты, инвестиции и комиссии.", "base_cost": 2500000, "base_income": 180000},
    "conglomerate": {"name": "🌐 Конгломерат", "desc": "Империя из разных отраслей.", "base_cost": 10000000, "base_income": 850000},
}

STOCKS = {
    "bmw": {
        "symbol": "BMW", "name": "BMW",
        "description": "Немецкая компания, производящая автомобили премиального сегмента.",
        "min_price": 200.0, "max_price": 450.0, "initial_price": 325.0,
        "up_min_change": -0.01, "up_max_change": 0.03,
        "down_min_change": -0.03, "down_max_change": 0.02,
        "dividend_rate": 0.03,
    },
    "kfc": {
        "symbol": "KFC", "name": "KFC",
        "description": "Международная сеть ресторанов быстрого питания.",
        "min_price": 90.0, "max_price": 235.0, "initial_price": 162.5,
        "up_min_change": -0.01, "up_max_change": 0.04,
        "down_min_change": -0.04, "down_max_change": 0.02,
        "dividend_rate": 0.011,
    },
    "spotify": {
        "symbol": "SPOT", "name": "Spotify",
        "description": "Стриминговый сервис для музыки, подкастов и другого аудиоконтента.",
        "min_price": 110.0, "max_price": 210.0, "initial_price": 160.0,
        "up_min_change": -0.01, "up_max_change": 0.02,
        "down_min_change": -0.03, "down_max_change": 0.02,
        "dividend_rate": 0.005,
    },
}

UPGRADES = {
    "furniture": {"name": "🛋 Мебель", "cost_rate": 0.06, "income_bonus": 0.12},
    "interior": {"name": "🎨 Интерьер", "cost_rate": 0.08, "income_bonus": 0.16},
    "wifi": {"name": "📶 Wi‑Fi", "cost_rate": 0.03, "income_bonus": 0.08},
    "appliances": {"name": "🔌 Бытовые приборы", "cost_rate": 0.07, "income_bonus": 0.14},
}

REAL_ESTATE = {
    "egorlyk_economy": {
        "city_id": "egorlyk", "city": "Егорлык", "country": "Россия",
        "name": "Бюджетная квартира", "price": 5000, "base_rent_hour": 45,
        "lat": 45.5853, "lng": 41.8650,
        "photo": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Inside-apartment-design-home%20%2824244145021%29.jpg",
        "description": "Очень дешёвое жильё для первого шага в недвижимости. Скромная квартира с невысокой арендой и доступными улучшениями.",
    },
    "moscow_economy": {
        "city_id": "moscow", "city": "Москва", "country": "Россия",
        "name": "Квартира эконом-класса", "price": 450000, "base_rent_hour": 3200,
        "lat": 55.7558, "lng": 37.6173,
        "photo": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Interior.png",
        "description": "Компактная квартира недалеко от метро. Базовая отделка и стабильный спрос на аренду.",
    },
    "barcelona_economy": {
        "city_id": "barcelona", "city": "Барселона", "country": "Испания",
        "name": "Квартира эконом-класса", "price": 620000, "base_rent_hour": 4300,
        "lat": 41.3874, "lng": 2.1686,
        "photo": "https://images.unsplash.com/photo-1493809842364-78817add7ffb?auto=format&fit=crop&w=1200&q=80",
        "description": "Небольшая городская квартира для долгосрочной аренды в жилом районе.",
    },
    "paris_economy": {
        "city_id": "paris", "city": "Париж", "country": "Франция",
        "name": "Квартира эконом-класса", "price": 780000, "base_rent_hour": 5400,
        "lat": 48.8566, "lng": 2.3522,
        "photo": "https://images.unsplash.com/photo-1484154218962-a197022b5858?auto=format&fit=crop&w=1200&q=80",
        "description": "Практичная квартира с простой отделкой и высоким спросом на аренду.",
    },
    "london_economy": {
        "city_id": "london", "city": "Лондон", "country": "Великобритания",
        "name": "Квартира эконом-класса", "price": 950000, "base_rent_hour": 6700,
        "lat": 51.5072, "lng": -0.1276,
        "photo": "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=1200&q=80",
        "description": "Небольшая квартира в жилой части Лондона с устойчивым арендным потоком.",
    },
    "new_york_economy": {
        "city_id": "new_york", "city": "Нью-Йорк", "country": "США",
        "name": "Квартира эконом-класса", "price": 1150000, "base_rent_hour": 8200,
        "lat": 40.7128, "lng": -74.0060,
        "photo": "https://images.unsplash.com/photo-1502672023488-70e25813eb80?auto=format&fit=crop&w=1200&q=80",
        "description": "Функциональная квартира для арендаторов, которым важнее локация, чем роскошная отделка.",
    },
}

api = FastAPI(title="Corporation")
WEB_DIR = os.path.join(os.path.dirname(__file__), "web")
api.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


def db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def table_columns(conn, table):
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def ensure_column(conn, table, column, definition):
    if column not in table_columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db():
    now = int(time.time())
    with closing(db()) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            corp_name TEXT NOT NULL,
            money REAL NOT NULL DEFAULT 10000,
            last_collect INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS businesses (
            user_id INTEGER NOT NULL,
            business_id TEXT NOT NULL,
            level INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(user_id, business_id)
        );
        CREATE TABLE IF NOT EXISTS stats (
            user_id INTEGER PRIMARY KEY,
            total_earned REAL NOT NULL DEFAULT 0,
            total_spent REAL NOT NULL DEFAULT 0,
            companies_bought INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS daily_profit (
            user_id INTEGER NOT NULL,
            day TEXT NOT NULL,
            earned REAL NOT NULL DEFAULT 0,
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
            trend TEXT NOT NULL CHECK(trend IN ('up','down')),
            last_update INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS stock_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_id TEXT NOT NULL,
            price REAL NOT NULL,
            created_at INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_stock_history_stock_time ON stock_history(stock_id, created_at);
        CREATE TABLE IF NOT EXISTS stock_holdings (
            user_id INTEGER NOT NULL,
            stock_id TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            avg_buy_price REAL NOT NULL DEFAULT 0,
            PRIMARY KEY(user_id, stock_id)
        );
        CREATE TABLE IF NOT EXISTS taxes (
            user_id INTEGER PRIMARY KEY,
            unpaid REAL NOT NULL DEFAULT 0,
            due_since INTEGER NOT NULL DEFAULT 0,
            last_paid INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS real_estate_holdings (
            user_id INTEGER NOT NULL,
            property_id TEXT NOT NULL,
            purchase_price REAL NOT NULL,
            purchased_at INTEGER NOT NULL,
            furniture INTEGER NOT NULL DEFAULT 0,
            interior INTEGER NOT NULL DEFAULT 0,
            wifi INTEGER NOT NULL DEFAULT 0,
            appliances INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(user_id, property_id)
        );
        """)
        ensure_column(conn, "players", "last_income_sync", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(conn, "stats", "properties_bought", "INTEGER NOT NULL DEFAULT 0")
        conn.execute("UPDATE players SET last_income_sync=? WHERE last_income_sync=0", (now,))

        for stock_id, stock in STOCKS.items():
            exists = conn.execute("SELECT 1 FROM stocks WHERE id=?", (stock_id,)).fetchone()
            if not exists:
                conn.execute(
                    "INSERT INTO stocks(id,symbol,name,description,min_price,max_price,current_price,trend,last_update) VALUES(?,?,?,?,?,?,?,?,?)",
                    (stock_id, stock["symbol"], stock["name"], stock["description"], stock["min_price"], stock["max_price"], stock["initial_price"], "up", now),
                )
                conn.execute("INSERT INTO stock_history(stock_id,price,created_at) VALUES(?,?,?)", (stock_id, stock["initial_price"], now))
        conn.commit()


init_db()


def verify_init_data(init_data: str):
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
        return json.loads(data["user"])
    except Exception:
        raise HTTPException(401, "Invalid Telegram user")


def user_from_request(x_telegram_init_data, x_user_id):
    tg_user = verify_init_data(x_telegram_init_data or "")
    if tg_user:
        return int(tg_user["id"]), tg_user.get("username", ""), tg_user.get("first_name", "Игрок")
    if os.getenv("ALLOW_DEV_AUTH") == "1" and x_user_id:
        return int(x_user_id), "developer", "Разработчик"
    raise HTTPException(401, "Authentication required")


def ensure_player(uid, username=""):
    now = int(time.time())
    with closing(db()) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO players(user_id,username,corp_name,money,last_collect,created_at,last_income_sync) VALUES(?,?,?,?,?,?,?)",
            (uid, username, "Новая корпорация", 10000, 0, now, now),
        )
        conn.execute("INSERT OR IGNORE INTO stats(user_id) VALUES(?)", (uid,))
        conn.execute("INSERT OR IGNORE INTO taxes(user_id) VALUES(?)", (uid,))
        conn.execute("UPDATE players SET username=? WHERE user_id=?", (username, uid))
        conn.commit()


def get_player(uid):
    with closing(db()) as conn:
        return conn.execute("SELECT * FROM players WHERE user_id=?", (uid,)).fetchone()


def get_levels(uid):
    with closing(db()) as conn:
        rows = conn.execute("SELECT business_id,level FROM businesses WHERE user_id=?", (uid,)).fetchall()
    return {r["business_id"]: int(r["level"]) for r in rows}


def business_hourly_income(uid):
    levels = get_levels(uid)
    return sum(BUSINESSES[bid]["base_income"] * level for bid, level in levels.items() if bid in BUSINESSES)


def next_business_cost(bid, level):
    return int(BUSINESSES[bid]["base_cost"] * (1.45 ** level))


def business_capitalization(bid, level):
    return sum(next_business_cost(bid, lvl) for lvl in range(max(0, level))) if bid in BUSINESSES else 0


def update_stock_market():
    now = int(time.time())
    with closing(db()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        rows = conn.execute("SELECT * FROM stocks").fetchall()
        for stock in rows:
            elapsed = now - int(stock["last_update"])
            if elapsed < STOCK_UPDATE_INTERVAL:
                continue
            config = STOCKS.get(stock["id"])
            if not config:
                continue
            steps = elapsed // STOCK_UPDATE_INTERVAL
            price = float(stock["current_price"])
            trend = stock["trend"]
            last_update = int(stock["last_update"])
            for _ in range(int(steps)):
                change = random.uniform(
                    config["up_min_change"] if trend == "up" else config["down_min_change"],
                    config["up_max_change"] if trend == "up" else config["down_max_change"],
                )
                next_price = price * (1 + change)
                range_size = config["max_price"] - config["min_price"]
                position = (next_price - config["min_price"]) / range_size if range_size else 0.5
                if next_price <= config["min_price"]:
                    next_price, trend = config["min_price"], "up"
                elif next_price >= config["max_price"]:
                    next_price, trend = config["max_price"], "down"
                elif position <= 0.15 and random.random() < 0.65:
                    trend = "up"
                elif position >= 0.85 and random.random() < 0.65:
                    trend = "down"
                elif random.random() < 0.08:
                    trend = "down" if trend == "up" else "up"
                price = round(next_price, 2)
                last_update += STOCK_UPDATE_INTERVAL
                conn.execute("INSERT INTO stock_history(stock_id,price,created_at) VALUES(?,?,?)", (stock["id"], price, last_update))
            conn.execute("UPDATE stocks SET current_price=?,trend=?,last_update=? WHERE id=?", (price, trend, last_update, stock["id"]))
        conn.commit()


def dividend_hourly_income(uid, conn=None):
    own = conn is None
    if own:
        conn = db()
    try:
        rows = conn.execute(
            "SELECT h.stock_id,h.quantity,s.current_price FROM stock_holdings h JOIN stocks s ON s.id=h.stock_id WHERE h.user_id=? AND h.quantity>0",
            (uid,),
        ).fetchall()
        return sum(float(r["current_price"]) * int(r["quantity"]) * STOCKS.get(r["stock_id"], {}).get("dividend_rate", 0) for r in rows)
    finally:
        if own:
            conn.close()


def property_upgrade_multiplier(row):
    return 1 + sum(UPGRADES[key]["income_bonus"] for key in UPGRADES if int(row[key] or 0) > 0)


def real_estate_hourly_income(uid, conn=None):
    own = conn is None
    if own:
        conn = db()
    try:
        rows = conn.execute("SELECT * FROM real_estate_holdings WHERE user_id=?", (uid,)).fetchall()
        total = 0.0
        for row in rows:
            prop = REAL_ESTATE.get(row["property_id"])
            if prop:
                total += prop["base_rent_hour"] * property_upgrade_multiplier(row)
        return total
    finally:
        if own:
            conn.close()


def current_day():
    return datetime.now().strftime("%Y-%m-%d")


def add_daily_profit_conn(conn, uid, amount):
    if amount <= 0:
        return
    conn.execute(
        "INSERT INTO daily_profit(user_id,day,earned) VALUES(?,?,?) ON CONFLICT(user_id,day) DO UPDATE SET earned=earned+excluded.earned",
        (uid, current_day(), amount),
    )


def accrue_tax_conn(conn, uid, amount, due_since):
    if amount <= 0:
        return
    tax = round(amount * TAX_RATE, 2)
    row = conn.execute("SELECT unpaid,due_since FROM taxes WHERE user_id=?", (uid,)).fetchone()
    old_unpaid = float(row["unpaid"] if row else 0)
    old_due = int(row["due_since"] if row else 0)
    start = old_due if old_unpaid > 0 and old_due > 0 else int(due_since)
    conn.execute(
        "INSERT INTO taxes(user_id,unpaid,due_since,last_paid) VALUES(?,?,?,0) ON CONFLICT(user_id) DO UPDATE SET unpaid=taxes.unpaid+excluded.unpaid,due_since=?",
        (uid, tax, start, start),
    )


def sync_passive_income(uid):
    update_stock_market()
    now = int(time.time())
    with closing(db()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        player = conn.execute("SELECT last_income_sync FROM players WHERE user_id=?", (uid,)).fetchone()
        if not player:
            conn.rollback()
            return {"earned": 0, "business": 0, "dividends": 0, "rent": 0}
        last_sync = int(player["last_income_sync"] or now)
        if last_sync >= now:
            conn.commit()
            return {"earned": 0, "business": 0, "dividends": 0, "rent": 0}

        tax = conn.execute("SELECT unpaid,due_since FROM taxes WHERE user_id=?", (uid,)).fetchone()
        unpaid = float(tax["unpaid"] if tax else 0)
        due_since = int(tax["due_since"] if tax else 0)

        business_rate = float(business_hourly_income(uid))
        dividend_rate = float(dividend_hourly_income(uid, conn))
        rent_rate = float(real_estate_hourly_income(uid, conn))
        total_rate = business_rate + dividend_rate + rent_rate

        if unpaid > 0 and due_since > 0:
            earn_until = min(now, due_since + TAX_GRACE_SECONDS)
        elif total_rate > 0:
            earn_until = min(now, last_sync + TAX_GRACE_SECONDS)
        else:
            earn_until = now

        seconds = max(0, earn_until - last_sync)
        hours = seconds / 3600
        business_earned = business_rate * hours
        dividends_earned = dividend_rate * hours
        rent_earned = rent_rate * hours
        earned = business_earned + dividends_earned + rent_earned

        if earned > 0:
            conn.execute("UPDATE players SET money=money+? WHERE user_id=?", (earned, uid))
            conn.execute("UPDATE stats SET total_earned=total_earned+? WHERE user_id=?", (earned, uid))
            add_daily_profit_conn(conn, uid, earned)
            accrue_tax_conn(conn, uid, earned, due_since if unpaid > 0 and due_since > 0 else last_sync)

        conn.execute("UPDATE players SET last_income_sync=? WHERE user_id=?", (now, uid))
        conn.commit()
        return {
            "earned": round(earned, 2),
            "business": round(business_earned, 2),
            "dividends": round(dividends_earned, 2),
            "rent": round(rent_earned, 2),
        }


def get_tax_status(uid):
    now = int(time.time())
    with closing(db()) as conn:
        row = conn.execute("SELECT unpaid,due_since,last_paid FROM taxes WHERE user_id=?", (uid,)).fetchone()
    unpaid = float(row["unpaid"] if row else 0)
    due_since = int(row["due_since"] if row else 0)
    last_paid = int(row["last_paid"] if row else 0)
    blocked = unpaid > 0 and due_since > 0 and now >= due_since + TAX_GRACE_SECONDS
    seconds_left = max(0, due_since + TAX_GRACE_SECONDS - now) if unpaid > 0 and due_since > 0 else TAX_GRACE_SECONDS
    return {"rate": TAX_RATE, "rate_percent": 5, "unpaid": round(unpaid, 2), "due_since": due_since, "last_paid": last_paid, "blocked": blocked, "seconds_left": seconds_left}


def property_payload(uid):
    now = int(time.time())
    with closing(db()) as conn:
        owned_rows = {r["property_id"]: r for r in conn.execute("SELECT * FROM real_estate_holdings WHERE user_id=?", (uid,)).fetchall()}
    result = []
    for pid, prop in REAL_ESTATE.items():
        row = owned_rows.get(pid)
        owned = row is not None
        if owned:
            days = max(0, (now - int(row["purchased_at"])) / 86400)
            current_value = float(row["purchase_price"]) * (1 + REAL_ESTATE_DAILY_GROWTH * days)
            rent = prop["base_rent_hour"] * property_upgrade_multiplier(row)
            upgrades = {key: bool(int(row[key] or 0)) for key in UPGRADES}
            purchase_price = float(row["purchase_price"])
        else:
            current_value = prop["price"]
            rent = prop["base_rent_hour"]
            upgrades = {key: False for key in UPGRADES}
            purchase_price = prop["price"]
        upgrade_info = []
        for key, cfg in UPGRADES.items():
            upgrade_info.append({
                "id": key,
                "name": cfg["name"],
                "owned": upgrades[key],
                "cost": round(purchase_price * cfg["cost_rate"], 2),
                "income_bonus_percent": round(cfg["income_bonus"] * 100),
            })
        result.append({"id": pid, **prop, "owned": owned, "purchase_price": round(purchase_price, 2), "current_value": round(current_value, 2), "rent_hour": round(rent, 2), "growth_daily_percent": 0.5, "upgrades": upgrade_info})
    return result


def snapshot(uid):
    sync_passive_income(uid)
    p = get_player(uid)
    levels = get_levels(uid)
    tax_status = get_tax_status(uid)
    update_stock_market()
    business_rate = business_hourly_income(uid)
    dividend_rate = dividend_hourly_income(uid)
    rent_rate = real_estate_hourly_income(uid)
    total_rate = business_rate + dividend_rate + rent_rate
    with closing(db()) as conn:
        stats = conn.execute("SELECT * FROM stats WHERE user_id=?", (uid,)).fetchone()
    businesses = []
    for bid, business in BUSINESSES.items():
        level = levels.get(bid, 0)
        cap = business_capitalization(bid, level)
        businesses.append({
            "id": bid, **business, "level": level,
            "next_cost": next_business_cost(bid, level),
            "current_income": business["base_income"] * level,
            "income_after_purchase": business["base_income"] * (level + 1),
            "capitalization": cap, "sell_price": int(cap * 0.30),
        })
    return {
        "player": dict(p),
        "hourly_income": 0 if tax_status["blocked"] else round(total_rate, 2),
        "gross_hourly_income": round(total_rate, 2),
        "income_breakdown": {"business": round(business_rate, 2), "dividends": round(dividend_rate, 2), "rent": round(rent_rate, 2)},
        "income_blocked": tax_status["blocked"],
        "businesses": businesses,
        "stats": dict(stats),
        "taxes": tax_status,
        "real_estate_count": int(stats["properties_bought"] or 0),
    }


def get_daily_profit(uid):
    with closing(db()) as conn:
        rows = conn.execute("SELECT day,earned FROM daily_profit WHERE user_id=? ORDER BY day ASC", (uid,)).fetchall()
    return [dict(r) for r in rows]


def public_profile(uid):
    sync_passive_income(uid)
    player = get_player(uid)
    if not player:
        raise HTTPException(404, "Игрок не найден")
    levels = get_levels(uid)
    with closing(db()) as conn:
        stats = conn.execute("SELECT * FROM stats WHERE user_id=?", (uid,)).fetchone()
    businesses = [{"id": bid, "name": BUSINESSES[bid]["name"], "description": BUSINESSES[bid]["desc"], "level": level} for bid, level in levels.items() if level > 0 and bid in BUSINESSES]
    return {
        "player": {"user_id": player["user_id"], "username": player["username"], "corp_name": player["corp_name"], "money": player["money"], "created_at": player["created_at"]},
        "hourly_income": snapshot(uid)["hourly_income"],
        "stats": dict(stats),
        "businesses": businesses,
        "properties_bought": int(stats["properties_bought"] or 0),
        "daily_profit": get_daily_profit(uid),
    }


def stock_change_percent(conn, stock_id):
    rows = conn.execute("SELECT price FROM stock_history WHERE stock_id=? ORDER BY created_at DESC,id DESC LIMIT 2", (stock_id,)).fetchall()
    if len(rows) < 2 or float(rows[1]["price"]) == 0:
        return 0.0
    return round((float(rows[0]["price"]) - float(rows[1]["price"])) / float(rows[1]["price"]) * 100, 4)


def get_stocks():
    update_stock_market()
    with closing(db()) as conn:
        rows = conn.execute("SELECT * FROM stocks ORDER BY name ASC").fetchall()
        result = []
        for row in rows:
            item = dict(row)
            cfg = STOCKS.get(row["id"], {})
            item["change_percent"] = stock_change_percent(conn, row["id"])
            item["dividend_rate_percent"] = round(cfg.get("dividend_rate", 0) * 100, 2)
            result.append(item)
        return result


def get_stock_history(stock_id):
    update_stock_market()
    with closing(db()) as conn:
        rows = conn.execute(
            "SELECT price,created_at FROM (SELECT id,price,created_at FROM stock_history WHERE stock_id=? ORDER BY created_at DESC,id DESC LIMIT ?) ORDER BY created_at ASC,id ASC",
            (stock_id, MAX_STOCK_HISTORY_POINTS),
        ).fetchall()
    return [dict(r) for r in rows]


def get_brokerage_account(uid):
    sync_passive_income(uid)
    update_stock_market()
    with closing(db()) as conn:
        rows = conn.execute(
            "SELECT h.stock_id,h.quantity,h.avg_buy_price,s.symbol,s.name,s.description,s.current_price FROM stock_holdings h JOIN stocks s ON s.id=h.stock_id WHERE h.user_id=? AND h.quantity>0 ORDER BY s.name",
            (uid,),
        ).fetchall()
    holdings, invested_total, value_total, dividend_total = [], 0.0, 0.0, 0.0
    for row in rows:
        invested = int(row["quantity"]) * float(row["avg_buy_price"])
        value = int(row["quantity"]) * float(row["current_price"])
        profit = value - invested
        rate = STOCKS.get(row["stock_id"], {}).get("dividend_rate", 0)
        dividend_hour = value * rate
        invested_total += invested
        value_total += value
        dividend_total += dividend_hour
        holdings.append({
            "stock_id": row["stock_id"], "symbol": row["symbol"], "name": row["name"], "description": row["description"],
            "quantity": row["quantity"], "avg_buy_price": round(row["avg_buy_price"], 2), "current_price": round(row["current_price"], 2),
            "invested": round(invested, 2), "current_value": round(value, 2), "profit": round(profit, 2),
            "profit_percent": round(profit / invested * 100, 2) if invested else 0,
            "dividend_rate_percent": round(rate * 100, 2), "dividend_hour": round(dividend_hour, 2),
        })
    total_profit = value_total - invested_total
    return {"holdings": holdings, "total_invested": round(invested_total, 2), "total_current_value": round(value_total, 2), "total_profit": round(total_profit, 2), "total_profit_percent": round(total_profit / invested_total * 100, 2) if invested_total else 0, "dividend_hour": round(dividend_total, 2)}


class NameBody(BaseModel):
    name: str


class QuantityBody(BaseModel):
    quantity: int


@api.get("/")
def index():
    return FileResponse(os.path.join(WEB_DIR, "index.html"), headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0", "Pragma": "no-cache", "Expires": "0"})


def auth(x_telegram_init_data, x_user_id):
    uid, username, _ = user_from_request(x_telegram_init_data, x_user_id)
    ensure_player(uid, username)
    return uid


@api.get("/api/state")
def state(x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    return snapshot(auth(x_telegram_init_data, x_user_id))


@api.post("/api/rename")
def rename(body: NameBody, x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    uid = auth(x_telegram_init_data, x_user_id)
    name = body.name.strip()[:32]
    if len(name) < 2:
        raise HTTPException(400, "Название должно содержать минимум 2 символа")
    with closing(db()) as conn:
        conn.execute("UPDATE players SET corp_name=? WHERE user_id=?", (name, uid)); conn.commit()
    return snapshot(uid)


@api.post("/api/business/{bid}/buy")
def buy_business(bid: str, x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    uid = auth(x_telegram_init_data, x_user_id)
    if bid not in BUSINESSES:
        raise HTTPException(404, "Бизнес не найден")
    sync_passive_income(uid)
    level = get_levels(uid).get(bid, 0)
    cost = next_business_cost(bid, level)
    with closing(db()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        player = conn.execute("SELECT money FROM players WHERE user_id=?", (uid,)).fetchone()
        if float(player["money"]) < cost:
            conn.rollback(); raise HTTPException(400, f"Не хватает {round(cost-float(player['money']),2)} ₽")
        conn.execute("UPDATE players SET money=money-? WHERE user_id=?", (cost, uid))
        conn.execute("INSERT INTO businesses(user_id,business_id,level) VALUES(?,?,1) ON CONFLICT(user_id,business_id) DO UPDATE SET level=level+1", (uid, bid))
        conn.execute("UPDATE stats SET total_spent=total_spent+?,companies_bought=companies_bought+? WHERE user_id=?", (cost, 1 if level == 0 else 0, uid))
        conn.commit()
    return snapshot(uid)


@api.post("/api/business/{bid}/sell")
def sell_business(bid: str, x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    uid = auth(x_telegram_init_data, x_user_id)
    if bid not in BUSINESSES:
        raise HTTPException(404, "Бизнес не найден")
    sync_passive_income(uid)
    level = get_levels(uid).get(bid, 0)
    if level <= 0:
        raise HTTPException(400, "У тебя нет этого бизнеса")
    cap = business_capitalization(bid, level); price = int(cap * 0.30)
    with closing(db()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DELETE FROM businesses WHERE user_id=? AND business_id=?", (uid, bid))
        conn.execute("UPDATE players SET money=money+? WHERE user_id=?", (price, uid))
        conn.commit()
    return {"sell_price": price, "state": snapshot(uid)}


@api.get("/api/taxes")
def taxes_status(x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    uid = auth(x_telegram_init_data, x_user_id); sync_passive_income(uid); return get_tax_status(uid)


@api.post("/api/taxes/pay")
def pay_taxes(x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    uid = auth(x_telegram_init_data, x_user_id); sync_passive_income(uid)
    now = int(time.time())
    with closing(db()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        tax = conn.execute("SELECT unpaid FROM taxes WHERE user_id=?", (uid,)).fetchone(); unpaid = float(tax["unpaid"] if tax else 0)
        if unpaid <= 0:
            conn.rollback(); raise HTTPException(400, "Неоплаченных налогов нет")
        player = conn.execute("SELECT money FROM players WHERE user_id=?", (uid,)).fetchone()
        if float(player["money"]) < unpaid:
            conn.rollback(); raise HTTPException(400, f"Недостаточно денег. Нужно {unpaid:.2f} ₽")
        conn.execute("UPDATE players SET money=money-?,last_income_sync=? WHERE user_id=?", (unpaid, now, uid))
        conn.execute("UPDATE taxes SET unpaid=0,due_since=0,last_paid=? WHERE user_id=?", (now, uid))
        conn.commit()
    return {"paid": round(unpaid, 2), "state": snapshot(uid)}


@api.get("/api/statistics")
def statistics(x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    uid = auth(x_telegram_init_data, x_user_id); sync_passive_income(uid)
    player = get_player(uid)
    with closing(db()) as conn:
        stats = conn.execute("SELECT * FROM stats WHERE user_id=?", (uid,)).fetchone()
    return {"player": {"corp_name": player["corp_name"], "money": player["money"], "created_at": player["created_at"]}, "hourly_income": snapshot(uid)["hourly_income"], "total_spent": stats["total_spent"], "total_earned": stats["total_earned"], "companies_bought": stats["companies_bought"], "properties_bought": stats["properties_bought"], "daily_profit": get_daily_profit(uid)}


@api.get("/api/rating")
def rating(x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    uid = auth(x_telegram_init_data, x_user_id); sync_passive_income(uid)
    with closing(db()) as conn:
        rows = conn.execute("SELECT user_id,corp_name,username,money FROM players ORDER BY money DESC LIMIT 20").fetchall()
    return [dict(r) for r in rows]


@api.get("/api/player/{player_id}")
def player_profile(player_id: int, x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    auth(x_telegram_init_data, x_user_id); return public_profile(player_id)


@api.get("/api/stocks")
def stocks(x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    uid = auth(x_telegram_init_data, x_user_id); sync_passive_income(uid); return get_stocks()


@api.get("/api/stocks/{stock_id}")
def stock_detail(stock_id: str, x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    uid = auth(x_telegram_init_data, x_user_id); sync_passive_income(uid); update_stock_market()
    with closing(db()) as conn:
        row = conn.execute("SELECT * FROM stocks WHERE id=?", (stock_id,)).fetchone()
        if not row: raise HTTPException(404, "Акция не найдена")
        item = dict(row); item["change_percent"] = stock_change_percent(conn, stock_id)
    item["history"] = get_stock_history(stock_id); item["dividend_rate_percent"] = round(STOCKS.get(stock_id, {}).get("dividend_rate", 0) * 100, 2)
    return item


@api.get("/api/brokerage-account")
def brokerage_account(x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    return get_brokerage_account(auth(x_telegram_init_data, x_user_id))


@api.post("/api/stocks/{stock_id}/buy")
def buy_stock(stock_id: str, body: QuantityBody, x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    if body.quantity <= 0: raise HTTPException(400, "Количество должно быть больше нуля")
    uid = auth(x_telegram_init_data, x_user_id); sync_passive_income(uid); update_stock_market()
    with closing(db()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        stock = conn.execute("SELECT current_price FROM stocks WHERE id=?", (stock_id,)).fetchone()
        if not stock: conn.rollback(); raise HTTPException(404, "Акция не найдена")
        price = float(stock["current_price"]); total = price * body.quantity
        player = conn.execute("SELECT money FROM players WHERE user_id=?", (uid,)).fetchone()
        if float(player["money"]) < total: conn.rollback(); raise HTTPException(400, f"Недостаточно денег. Нужно {total:.2f} ₽")
        h = conn.execute("SELECT quantity,avg_buy_price FROM stock_holdings WHERE user_id=? AND stock_id=?", (uid, stock_id)).fetchone()
        old_q = int(h["quantity"] if h else 0); old_avg = float(h["avg_buy_price"] if h else 0); new_q = old_q + body.quantity
        new_avg = (old_q * old_avg + body.quantity * price) / new_q
        conn.execute("UPDATE players SET money=money-? WHERE user_id=?", (total, uid))
        conn.execute("INSERT INTO stock_holdings(user_id,stock_id,quantity,avg_buy_price) VALUES(?,?,?,?) ON CONFLICT(user_id,stock_id) DO UPDATE SET quantity=excluded.quantity,avg_buy_price=excluded.avg_buy_price", (uid, stock_id, new_q, new_avg))
        conn.commit()
    return {"quantity": body.quantity, "price_per_stock": round(price,2), "total_cost": round(total,2), "state": snapshot(uid), "brokerage_account": get_brokerage_account(uid)}


@api.post("/api/stocks/{stock_id}/sell")
def sell_stock(stock_id: str, body: QuantityBody, x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    if body.quantity <= 0: raise HTTPException(400, "Количество должно быть больше нуля")
    uid = auth(x_telegram_init_data, x_user_id); sync_passive_income(uid); update_stock_market(); now = int(time.time())
    with closing(db()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        stock = conn.execute("SELECT current_price FROM stocks WHERE id=?", (stock_id,)).fetchone()
        h = conn.execute("SELECT quantity,avg_buy_price FROM stock_holdings WHERE user_id=? AND stock_id=?", (uid, stock_id)).fetchone()
        if not stock: conn.rollback(); raise HTTPException(404, "Акция не найдена")
        if not h or int(h["quantity"]) < body.quantity: conn.rollback(); raise HTTPException(400, "Недостаточно акций для продажи")
        price = float(stock["current_price"]); avg = float(h["avg_buy_price"]); total = price * body.quantity; remaining = int(h["quantity"]) - body.quantity
        realized_profit = max(0.0, (price - avg) * body.quantity)
        if remaining == 0: conn.execute("DELETE FROM stock_holdings WHERE user_id=? AND stock_id=?", (uid, stock_id))
        else: conn.execute("UPDATE stock_holdings SET quantity=? WHERE user_id=? AND stock_id=?", (remaining, uid, stock_id))
        conn.execute("UPDATE players SET money=money+? WHERE user_id=?", (total, uid))
        if realized_profit > 0:
            conn.execute("UPDATE stats SET total_earned=total_earned+? WHERE user_id=?", (realized_profit, uid))
            add_daily_profit_conn(conn, uid, realized_profit)
            accrue_tax_conn(conn, uid, realized_profit, now)
        conn.commit()
    return {"quantity": body.quantity, "price_per_stock": round(price,2), "total_income": round(total,2), "realized_profit": round(realized_profit,2), "profit_tax": round(realized_profit*TAX_RATE,2), "state": snapshot(uid), "brokerage_account": get_brokerage_account(uid)}


@api.get("/api/real-estate")
def real_estate(x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    uid = auth(x_telegram_init_data, x_user_id); sync_passive_income(uid); return {"properties": property_payload(uid), "daily_growth_percent": 0.5}


@api.post("/api/real-estate/{property_id}/buy")
def buy_property(property_id: str, x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    uid = auth(x_telegram_init_data, x_user_id); sync_passive_income(uid)
    prop = REAL_ESTATE.get(property_id)
    if not prop: raise HTTPException(404, "Объект недвижимости не найден")
    now = int(time.time())
    with closing(db()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        exists = conn.execute("SELECT 1 FROM real_estate_holdings WHERE user_id=? AND property_id=?", (uid, property_id)).fetchone()
        if exists: conn.rollback(); raise HTTPException(400, "Эта недвижимость уже куплена")
        player = conn.execute("SELECT money FROM players WHERE user_id=?", (uid,)).fetchone()
        if float(player["money"]) < prop["price"]: conn.rollback(); raise HTTPException(400, f"Недостаточно денег. Нужно {prop['price']:.2f} ₽")
        conn.execute("UPDATE players SET money=money-? WHERE user_id=?", (prop["price"], uid))
        conn.execute("INSERT INTO real_estate_holdings(user_id,property_id,purchase_price,purchased_at) VALUES(?,?,?,?)", (uid, property_id, prop["price"], now))
        conn.execute("UPDATE stats SET total_spent=total_spent+?,properties_bought=properties_bought+1 WHERE user_id=?", (prop["price"], uid))
        conn.commit()
    return {"state": snapshot(uid), "properties": property_payload(uid)}


@api.post("/api/real-estate/{property_id}/upgrade/{upgrade_id}")
def upgrade_property(property_id: str, upgrade_id: str, x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    uid = auth(x_telegram_init_data, x_user_id); sync_passive_income(uid)
    if property_id not in REAL_ESTATE: raise HTTPException(404, "Объект не найден")
    if upgrade_id not in UPGRADES: raise HTTPException(404, "Улучшение не найдено")
    with closing(db()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM real_estate_holdings WHERE user_id=? AND property_id=?", (uid, property_id)).fetchone()
        if not row: conn.rollback(); raise HTTPException(400, "Сначала купи эту недвижимость")
        if int(row[upgrade_id] or 0) > 0: conn.rollback(); raise HTTPException(400, "Это улучшение уже установлено")
        cost = float(row["purchase_price"]) * UPGRADES[upgrade_id]["cost_rate"]
        player = conn.execute("SELECT money FROM players WHERE user_id=?", (uid,)).fetchone()
        if float(player["money"]) < cost: conn.rollback(); raise HTTPException(400, f"Недостаточно денег. Нужно {cost:.2f} ₽")
        conn.execute("UPDATE players SET money=money-? WHERE user_id=?", (cost, uid))
        conn.execute(f"UPDATE real_estate_holdings SET {upgrade_id}=1 WHERE user_id=? AND property_id=?", (uid, property_id))
        conn.execute("UPDATE stats SET total_spent=total_spent+? WHERE user_id=?", (cost, uid))
        conn.commit()
    return {"state": snapshot(uid), "properties": property_payload(uid)}

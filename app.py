import hashlib
import hmac
import json
import os
import random
import shutil
import sqlite3
import time
import threading
from contextlib import closing
from datetime import datetime
from urllib.parse import parse_qsl

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BOT_TOKEN = os.getenv("BOT_TOKEN", "PASTE_YOUR_BOT_TOKEN_HERE")
ADMIN_IDS = {int(x.strip()) for x in (os.getenv("ADMIN_IDS") or "").split(",") if x.strip().isdigit()}
STARTING_MONEY = 10000.0

# === CORPORATION_PERSISTENT_DB_V14_1 ==========================================
def _is_railway_runtime():
    return bool(
        os.getenv("RAILWAY_DEPLOYMENT_ID")
        or os.getenv("RAILWAY_PROJECT_ID")
        or os.getenv("RAILWAY_ENVIRONMENT_NAME")
        or os.getenv("RAILWAY_SERVICE_ID")
    )


def _resolve_database_path():
    configured = (os.getenv("DB_PATH") or "").strip()
    volume_mount = (os.getenv("RAILWAY_VOLUME_MOUNT_PATH") or "").strip()

    if _is_railway_runtime():
        if not volume_mount:
            raise RuntimeError(
                "Railway Volume не подключён к backend-сервису. "
                "Corporation остановлена, чтобы не создать временную базу."
            )

        volume_mount = os.path.abspath(volume_mount)
        os.makedirs(volume_mount, exist_ok=True)

        probe = os.path.join(volume_mount, ".corporation_write_test")
        try:
            with open(probe, "a", encoding="utf-8"):
                pass
            if os.path.exists(probe):
                os.remove(probe)
        except OSError as exc:
            raise RuntimeError(
                f"Railway Volume недоступен для записи: {volume_mount}: {exc}"
            ) from exc

        db_name = os.path.basename(configured) if configured else "corporation.db"
        if not db_name or db_name in (".", ".."):
            db_name = "corporation.db"

        persistent_path = os.path.abspath(os.path.join(volume_mount, db_name))
        if os.path.commonpath([persistent_path, volume_mount]) != volume_mount:
            raise RuntimeError("DB_PATH пытается выйти за пределы Railway Volume.")

        os.environ["DB_PATH"] = persistent_path
        return persistent_path

    return configured or "corporation.db"


DB_PATH = _resolve_database_path()
os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)) or ".", exist_ok=True)

if _is_railway_runtime():
    _mount = os.path.abspath(os.getenv("RAILWAY_VOLUME_MOUNT_PATH", ""))
    _exists = os.path.exists(DB_PATH)
    _size = os.path.getsize(DB_PATH) if _exists else 0
    print(
        f"[Corporation] PERSISTENT STORAGE OK | "
        f"mount={_mount} | db={DB_PATH} | exists={_exists} | size={_size}"
    )
else:
    print(f"[Corporation] Local SQLite database: {DB_PATH}")
# ============================================================================

TAX_RATE = 0.05
TAX_GRACE_SECONDS = 12 * 60 * 60
STOCK_UPDATE_INTERVAL = 60
MAX_STOCK_HISTORY_POINTS = 720
REAL_ESTATE_DAILY_GROWTH = 0.00015

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
        "volatility": 0.012, "drift": 0.0015, "dividend_rate": 0.03,
    },
    "kfc": {
        "symbol": "KFC", "name": "KFC",
        "description": "Международная сеть ресторанов быстрого питания.",
        "min_price": 90.0, "max_price": 235.0, "initial_price": 162.5,
        "volatility": 0.015, "drift": 0.0012, "dividend_rate": 0.011,
    },
    "spotify": {
        "symbol": "SPOT", "name": "Spotify",
        "description": "Стриминговый сервис для музыки, подкастов и другого аудиоконтента.",
        "min_price": 110.0, "max_price": 210.0, "initial_price": 160.0,
        "volatility": 0.013, "drift": 0.0010, "dividend_rate": 0.005,
    },
    "nvidia": {
        "symbol": "NVDA", "name": "NVIDIA",
        "description": "Разработчик графических процессоров, ускорителей вычислений и ИИ-платформ.",
        "min_price": 350.0, "max_price": 1200.0, "initial_price": 720.0,
        "volatility": 0.022, "drift": 0.0022, "dividend_rate": 0.004,
    },
    "tesla": {
        "symbol": "TSLA", "name": "Tesla",
        "description": "Производитель электромобилей, энергетических систем и технологий хранения энергии.",
        "min_price": 150.0, "max_price": 600.0, "initial_price": 315.0,
        "volatility": 0.026, "drift": 0.0017, "dividend_rate": 0.003,
    },
    "mcdonalds": {
        "symbol": "MCD", "name": "McDonald's",
        "description": "Глобальная сеть ресторанов быстрого обслуживания.",
        "min_price": 150.0, "max_price": 400.0, "initial_price": 275.0,
        "volatility": 0.010, "drift": 0.0010, "dividend_rate": 0.008,
    },
    "toyota": {
        "symbol": "TM", "name": "Toyota",
        "description": "Один из крупнейших мировых производителей автомобилей и транспортных технологий.",
        "min_price": 120.0, "max_price": 320.0, "initial_price": 205.0,
        "volatility": 0.011, "drift": 0.0011, "dividend_rate": 0.012,
    },
}

# === CORPORATION V21: MARKET NEWS ===========================================
MARKET_NEWS_INTERVAL = 60 * 60
MARKET_NEWS_REACTION_DELAY = 2 * 60
MARKET_NEWS_MIN_IMPACT = 0.20
MARKET_NEWS_MAX_IMPACT = 0.60

MARKET_NEWS_TEMPLATES = {
    "bmw": {
        "photo": "https://images.unsplash.com/photo-1555215695-3004980ad54e?auto=format&fit=crop&w=1200&h=700&q=84",
        "good": [
            ("BMW ускоряет выпуск нового поколения электромобилей после сильных предзаказов", "BMW сообщила о спросе на новую электрическую линейку выше внутренних ожиданий. Компания расширяет производственный план и рассчитывает быстрее загрузить европейские заводы, что участники рынка воспринимают как сигнал к росту выручки в премиальном сегменте."),
            ("Маржа BMW укрепилась на фоне устойчивого спроса на премиальные модели", "Немецкий автопроизводитель сообщил об улучшении рентабельности ключевого автомобильного подразделения. Более дорогие комплектации и дисциплина расходов помогли компенсировать давление логистики, усилив ожидания инвесторов по денежному потоку."),
            ("BMW заключает крупное соглашение по батареям для будущей модельной линейки", "Компания договорилась о долгосрочных поставках аккумуляторов на более выгодных условиях. Соглашение снижает риск дефицита компонентов и потенциально улучшает себестоимость электромобилей в ближайших производственных циклах."),
        ],
        "bad": [
            ("BMW предупреждает о росте затрат и давлении на автомобильную маржу", "BMW сообщила, что удорожание компонентов и логистики сильнее ожидаемого влияет на прибыльность. Руководство сохраняет инвестиционную программу, однако рынок закладывает более слабую маржу в ближайшие периоды."),
            ("BMW отзывает крупную партию автомобилей из-за технической проверки", "Автопроизводитель объявил масштабную сервисную кампанию для дополнительной проверки ряда моделей. Прямые расходы и возможная остановка части поставок усилили опасения инвесторов относительно краткосрочных финансовых показателей."),
            ("Продажи BMW в ключевом регионе оказались ниже ожиданий", "Новые данные показали ослабление спроса на премиальные автомобили на одном из крупнейших рынков компании. Аналитики пересматривают прогнозы поставок, опасаясь более жесткой ценовой конкуренции."),
        ],
    },
    "kfc": {
        "photo": "https://images.unsplash.com/photo-1513639776629-7b61b0ac49cb?auto=format&fit=crop&w=1200&h=700&q=84",
        "good": [
            ("KFC фиксирует ускорение сопоставимых продаж после обновления меню", "Новые позиции меню и рост цифровых заказов поддержали трафик в ресторанах KFC. Сеть отмечает особенно сильную динамику доставки и заказов через приложение, что повышает ожидания по выручке франчайзинговой системы."),
            ("KFC расширяет сеть быстрее плана на растущих рынках", "Компания сообщила об ускорении открытия новых ресторанов в регионах с высоким спросом на быстрый сервис. Более активная франчайзинговая экспансия может увеличить комиссионные поступления без сопоставимого роста капитальных затрат."),
            ("Цифровые продажи KFC достигли нового максимума", "Доля заказов через приложение, киоски и доставку заметно выросла. Руководство связывает это с персональными предложениями и программой лояльности, которые повышают средний чек и частоту повторных покупок."),
        ],
        "bad": [
            ("KFC сталкивается с ростом цен на сырье и давлением на рентабельность", "Удорожание курицы, упаковки и труда увеличивает расходы ресторанной сети. Часть франчайзи осторожнее относится к новым открытиям, а рынок опасается более слабой маржи в ближайшие месяцы."),
            ("KFC временно закрывает часть ресторанов после сбоя поставок", "Нарушения в цепочке поставок затронули несколько крупных регионов сети. Компания заявила, что восстанавливает логистику, однако краткосрочные потери продаж могут оказаться заметнее первоначальных оценок."),
            ("Рост трафика KFC замедлился на фоне жесткой конкуренции", "Промоакции конкурентов и более осторожные расходы потребителей привели к замедлению посещаемости. Аналитики отмечают риск усиления скидок, что способно дополнительно давить на прибыльность сети."),
        ],
    },
    "spotify": {
        "photo": "https://images.unsplash.com/photo-1614680376573-df3480f0c6ff?auto=format&fit=crop&w=1200&h=700&q=84",
        "good": [
            ("Spotify добавила подписчиков быстрее ожиданий и улучшила прогноз", "Музыкальный сервис сообщил о более сильном росте премиальной аудитории, чем ожидал рынок. Одновременно компания продолжила контролировать расходы, усилив ожидания по операционной прибыли и свободному денежному потоку."),
            ("Spotify расширяет рекламный бизнес с новой платформой для брендов", "Компания представила инструменты, которые упрощают покупку аудиорекламы и таргетинг кампаний. Рынок рассчитывает, что более эффективная монетизация бесплатной аудитории станет вторым заметным источником роста наряду с подписками."),
            ("Повышение цен Spotify прошло без заметного роста оттока", "После изменения тарифов сервис сохранил устойчивую динамику удержания подписчиков. Это повышает уверенность инвесторов в ценовой силе платформы и способности увеличивать среднюю выручку на пользователя."),
        ],
        "bad": [
            ("Spotify сообщает о замедлении прироста премиальных подписчиков", "Темпы привлечения платной аудитории оказались слабее ожиданий. Участники рынка опасаются, что более высокая конкуренция среди стриминговых сервисов потребует дополнительных расходов на маркетинг и эксклюзивный контент."),
            ("Расходы Spotify на лицензирование контента растут быстрее выручки", "Новые соглашения с правообладателями увеличивают стоимость контента для платформы. Инвесторы оценивают риск снижения маржи, если компания не сможет компенсировать расходы ценами или ростом рекламной выручки."),
            ("Spotify столкнулась с крупным техническим сбоем", "Часть пользователей несколько часов испытывала проблемы с воспроизведением и доступом к приложению. Хотя сервис восстановлен, инцидент усилил вопросы к надежности инфраструктуры в период быстрого роста аудитории."),
        ],
    },
    "nvidia": {
        "photo": "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1200&h=700&q=84",
        "good": [
            ("NVIDIA получила новую волну крупных заказов на ИИ-ускорители", "Крупные облачные провайдеры расширили заказы на вычислительные ускорители NVIDIA. Высокий спрос на инфраструктуру искусственного интеллекта усиливает ожидания по выручке дата-центров и загрузке будущих поколений чипов."),
            ("NVIDIA представила архитектуру с заметным приростом производительности", "Компания раскрыла новое поколение ускорителей, обещающее существенно более высокую эффективность в ИИ-нагрузках. Первые клиенты уже объявили планы внедрения, что снижает опасения о замедлении технологического цикла."),
            ("Поставки ключевых чипов NVIDIA растут после расширения производственных мощностей", "Партнеры по производству увеличили доступные мощности для передовых ускорителей. Улучшение предложения позволяет NVIDIA быстрее закрывать накопленный спрос и превращать заказы в фактическую выручку."),
        ],
        "bad": [
            ("NVIDIA предупреждает о новых ограничениях поставок на часть рынков", "Дополнительные экспортные ограничения могут сократить доступный рынок для высокопроизводительных ускорителей. Компания оценивает варианты адаптации продуктовой линейки, однако инвесторы закладывают риск потери части будущей выручки."),
            ("Крупный клиент NVIDIA замедляет закупки ИИ-ускорителей", "Один из заметных покупателей пересматривает темпы расширения дата-центров после периода агрессивных инвестиций. Новость усилила опасения, что часть спроса на инфраструктуру ИИ может быть перенесена на более поздние сроки."),
            ("Новая линейка NVIDIA столкнулась с задержкой поставок", "Сообщается о технических корректировках, которые сдвигают часть отгрузок нового поколения ускорителей. Даже ограниченная задержка способна перенести признание выручки и увеличить расходы на запуск продукта."),
        ],
    },
    "tesla": {
        "photo": "https://images.unsplash.com/photo-1617788138017-80ad40651399?auto=format&fit=crop&w=1200&h=700&q=84",
        "good": [
            ("Tesla отчиталась о рекордных поставках после ускорения производства", "Производитель электромобилей сообщил о сильном квартальном объеме поставок, превысившем ожидания рынка. Рост загрузки заводов улучшает перспективы операционного рычага и поддерживает прогноз по денежному потоку."),
            ("Tesla объявила о снижении себестоимости нового поколения батарей", "Компания заявила о технологическом прогрессе в производстве аккумуляторов, который должен уменьшить стоимость батарейного блока. Более низкая себестоимость дает Tesla пространство для маржи или более агрессивного ценообразования."),
            ("Энергетический бизнес Tesla ускорил рост", "Поставки систем накопления энергии заметно увеличились, а портфель заказов продолжает расширяться. Инвесторы рассматривают энергетическое направление как все более важный источник диверсификации выручки компании."),
        ],
        "bad": [
            ("Поставки Tesla не достигли ожиданий аналитиков", "Данные по отгрузкам электромобилей оказались слабее рыночного консенсуса. Инвесторы опасаются, что ценовая конкуренция и более медленный спрос могут потребовать дополнительных скидок."),
            ("Tesla снова снижает цены на ключевые модели", "Компания объявила очередное снижение цен на нескольких рынках. Для покупателей это поддерживает доступность автомобилей, однако для инвесторов повышает риск дальнейшего давления на автомобильную маржу."),
            ("Tesla приостанавливает часть производства для внеплановой модернизации", "На одном из крупных предприятий временно сокращен выпуск автомобилей. Компания называет остановку плановой технической работой, но рынок учитывает риск более низких поставок в ближайшем отчетном периоде."),
        ],
    },
    "mcdonalds": {
        "photo": "https://images.unsplash.com/photo-1552566626-52f8b828add9?auto=format&fit=crop&w=1200&h=700&q=84",
        "good": [
            ("McDonald's ускорила продажи благодаря росту цифровых заказов", "Сеть ресторанов сообщила о сильной динамике приложения и программы лояльности. Персональные предложения повышают частоту заказов, а цифровой канал помогает компании эффективнее управлять средним чеком."),
            ("McDonald's расширяет высокомаржинальную франчайзинговую сеть", "Компания ускоряет открытие ресторанов с участием франчайзи на нескольких ключевых рынках. Такой формат позволяет увеличивать системные продажи при более умеренной потребности в собственном капитале."),
            ("Новые продукты McDonald's поддержали трафик и средний чек", "Ограниченные сезонные предложения и обновленное меню показали сильный спрос. Компания отмечает рост посещаемости в ключевых регионах и более высокую конверсию участников программы лояльности."),
        ],
        "bad": [
            ("McDonald's видит давление на трафик из-за осторожности потребителей", "Часть клиентов стала реже посещать рестораны на фоне роста стоимости жизни. Сеть усиливает недорогие предложения, однако инвесторы опасаются, что промоакции могут ограничить рост маржи."),
            ("Рост зарплат увеличивает расходы ресторанов McDonald's", "Затраты на персонал заметно выросли на нескольких крупных рынках. Компания работает над производительностью и автоматизацией, но краткосрочно более высокие расходы могут давить на прибыльность."),
            ("McDonald's временно ограничивает продажи ряда позиций после перебоев поставок", "Сбои у нескольких поставщиков затронули доступность отдельных ингредиентов. Компания ожидает нормализации поставок, однако часть ресторанов может недополучить продажи в ближайшие недели."),
        ],
    },
    "toyota": {
        "photo": "https://images.unsplash.com/photo-1621007947382-bb3c3994e3fb?auto=format&fit=crop&w=1200&h=700&q=84",
        "good": [
            ("Toyota повышает прогноз производства после стабилизации поставок компонентов", "Автопроизводитель сообщил об улучшении доступности ключевых деталей и намерен увеличить выпуск автомобилей. Более высокая загрузка заводов способна поддержать продажи и распределение фиксированных затрат."),
            ("Гибриды Toyota демонстрируют сильный мировой спрос", "Продажи гибридных моделей продолжают расти на нескольких ключевых рынках. Компания выигрывает от широкой линейки и накопленного опыта, что помогает ей удерживать устойчивую прибыльность в переходный период отрасли."),
            ("Toyota раскрыла план снижения стоимости батарей нового поколения", "Компания представила технологическую дорожную карту аккумуляторов с более высокой плотностью энергии и меньшей себестоимостью. Инвесторы рассматривают это как потенциальное усиление позиций Toyota на рынке электромобилей."),
        ],
        "bad": [
            ("Toyota сокращает план выпуска из-за дефицита отдельных компонентов", "Проблемы с поставками вынуждают автопроизводителя временно уменьшить производство на ряде площадок. Более низкий объем выпуска может ограничить продажи даже при сохранении устойчивого спроса."),
            ("Toyota объявляет крупную сервисную кампанию", "Компания проведет дополнительную проверку значительного числа автомобилей. Хотя сервисные кампании типичны для отрасли, масштаб потенциальных расходов заставил рынок осторожнее оценить ближайшую прибыль."),
            ("Сильная ценовая конкуренция давит на продажи Toyota в ключевом сегменте", "Конкуренты активизировали скидки и обновили модельные ряды. Toyota сохраняет объемы, но инвесторы опасаются, что для защиты доли рынка компании придется жертвовать частью ценовой силы."),
        ],
    },
}
# ============================================================================

BONDS = {
    "ofz_ru": {
        "symbol": "ОФЗ РФ",
        "name": "ОФЗ Российской Федерации",
        "description": "Игровая государственная облигация РФ с фиксированной стоимостью и автоматической доходностью.",
        "price": 1000.0,
        "yield_rate": 0.025,
    },
    "ofz_us": {
        "symbol": "ОФЗ США",
        "name": "Государственная облигация США",
        "description": "Игровая государственная облигация США с фиксированной стоимостью и автоматической доходностью.",
        "price": 2000.0,
        "yield_rate": 0.015,
    },
}

REAL_ESTATE_UPGRADES = {
    "furniture": {"name": "🛋 Мебель", "cost_rate": 0.06, "income_bonus": 0.12},
    "interior": {"name": "🎨 Интерьер", "cost_rate": 0.08, "income_bonus": 0.16},
    "wifi": {"name": "📶 Wi‑Fi", "cost_rate": 0.03, "income_bonus": 0.08},
    "appliances": {"name": "🔌 Бытовые приборы", "cost_rate": 0.07, "income_bonus": 0.14},
}
BUSINESS_UPGRADES = {
    "marketing": {"name": "📣 Маркетинг", "column": "marketing", "cost_rate": 0.20, "income_bonus": 0.18},
    "equipment": {"name": "⚙️ Оборудование", "column": "equipment", "cost_rate": 0.30, "income_bonus": 0.25},
    "staff": {"name": "👥 Персонал", "column": "staff", "cost_rate": 0.25, "income_bonus": 0.22},
    "automation": {"name": "🤖 Автоматизация", "column": "automation", "cost_rate": 0.40, "income_bonus": 0.35},
}

BUSINESS_UPGRADE_PROFILES = {
    "coffee": {"marketing": {"name": "🎟 Программа лояльности", "cost_rate": .16, "income_bonus": .14}, "equipment": {"name": "☕ Профессиональная кофемашина", "cost_rate": .28, "income_bonus": .24}, "staff": {"name": "👨‍🍳 Бариста-чемпионы", "cost_rate": .22, "income_bonus": .20}, "automation": {"name": "📱 Мобильный предзаказ", "cost_rate": .34, "income_bonus": .30}},
    "delivery": {"marketing": {"name": "📍 Геореклама", "cost_rate": .18, "income_bonus": .16}, "equipment": {"name": "🛵 Парк электроскутеров", "cost_rate": .32, "income_bonus": .27}, "staff": {"name": "🚴 Усиленный штат курьеров", "cost_rate": .25, "income_bonus": .22}, "automation": {"name": "🗺 Умная маршрутизация", "cost_rate": .38, "income_bonus": .34}},
    "factory": {"marketing": {"name": "🤝 Контракты с торговыми сетями", "cost_rate": .20, "income_bonus": .18}, "equipment": {"name": "🏗 Новая производственная линия", "cost_rate": .35, "income_bonus": .30}, "staff": {"name": "👷 Инженерная смена", "cost_rate": .27, "income_bonus": .24}, "automation": {"name": "🦾 Роботизация цеха", "cost_rate": .44, "income_bonus": .39}},
    "it": {"marketing": {"name": "🚀 Продвижение цифровых продуктов", "cost_rate": .20, "income_bonus": .18}, "equipment": {"name": "🖥 Серверная инфраструктура", "cost_rate": .30, "income_bonus": .26}, "staff": {"name": "🧑‍💻 Senior-команда", "cost_rate": .32, "income_bonus": .29}, "automation": {"name": "⚙️ CI/CD и автотесты", "cost_rate": .38, "income_bonus": .35}},
    "finance": {"marketing": {"name": "💼 Премиум-клиенты", "cost_rate": .22, "income_bonus": .20}, "equipment": {"name": "🔐 Финтех-инфраструктура", "cost_rate": .31, "income_bonus": .27}, "staff": {"name": "📊 Команда аналитиков", "cost_rate": .30, "income_bonus": .28}, "automation": {"name": "🤖 Алгоритмический дилинг", "cost_rate": .46, "income_bonus": .42}},
    "conglomerate": {"marketing": {"name": "🌍 Глобальный бренд", "cost_rate": .24, "income_bonus": .22}, "equipment": {"name": "🏙 Корпоративные активы", "cost_rate": .34, "income_bonus": .30}, "staff": {"name": "🧠 Топ-менеджмент", "cost_rate": .33, "income_bonus": .31}, "automation": {"name": "🛰 Единый центр управления", "cost_rate": .50, "income_bonus": .46}},
}

def get_business_upgrade_cfg(bid, upgrade_id):
    return {**BUSINESS_UPGRADES[upgrade_id], **BUSINESS_UPGRADE_PROFILES.get(bid, {}).get(upgrade_id, {})}


REAL_ESTATE = {
    "egorlyk_apartment_economy": {
        "city_id": "egorlyk", "city": "Егорлык", "country": "Россия",
        "name": "Квартира эконом-класса", "segment": "economy", "property_type": "apartment",
        "price": 2800000, "base_rent_hour": 22.37,
        "lat": 45.5853, "lng": 41.865,
        "photo": "https://images.unsplash.com/photo-1493809842364-78817add7ffb?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Квартира эконом-класса в городе Егорлык. Автоматически приносит арендный доход и может быть улучшена.",
    },
    "egorlyk_apartment_business": {
        "city_id": "egorlyk", "city": "Егорлык", "country": "Россия",
        "name": "Квартира бизнес-класса", "segment": "business", "property_type": "apartment",
        "price": 4200000, "base_rent_hour": 31.16,
        "lat": 45.5853, "lng": 41.865,
        "photo": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Квартира бизнес-класса в городе Егорлык. Автоматически приносит арендный доход и может быть улучшена.",
    },
    "egorlyk_apartment_vip": {
        "city_id": "egorlyk", "city": "Егорлык", "country": "Россия",
        "name": "Квартира VIP-класса", "segment": "vip", "property_type": "apartment",
        "price": 6500000, "base_rent_hour": 40.81,
        "lat": 45.5853, "lng": 41.865,
        "photo": "https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Квартира VIP-класса в городе Егорлык. Автоматически приносит арендный доход и может быть улучшена.",
    },
    "egorlyk_house_economy": {
        "city_id": "egorlyk", "city": "Егорлык", "country": "Россия",
        "name": "Дом эконом-класса", "segment": "economy", "property_type": "house",
        "price": 4500000, "base_rent_hour": 33.39,
        "lat": 45.5853, "lng": 41.865,
        "photo": "https://images.unsplash.com/photo-1564013799919-ab600027ffc6?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Дом эконом-класса в городе Егорлык. Автоматически приносит арендный доход и может быть улучшена.",
    },
    "egorlyk_house_business": {
        "city_id": "egorlyk", "city": "Егорлык", "country": "Россия",
        "name": "Дом бизнес-класса", "segment": "business", "property_type": "house",
        "price": 7500000, "base_rent_hour": 49.66,
        "lat": 45.5853, "lng": 41.865,
        "photo": "https://images.unsplash.com/photo-1600047509807-ba8f99d2cdde?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Дом бизнес-класса в городе Егорлык. Автоматически приносит арендный доход и может быть улучшена.",
    },
    "egorlyk_house_vip": {
        "city_id": "egorlyk", "city": "Егорлык", "country": "Россия",
        "name": "Дом VIP-класса", "segment": "vip", "property_type": "house",
        "price": 12000000, "base_rent_hour": 68.49,
        "lat": 45.5853, "lng": 41.865,
        "photo": "https://images.unsplash.com/photo-1605146769289-440113cc3d00?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Дом VIP-класса в городе Егорлык. Автоматически приносит арендный доход и может быть улучшена.",
    },
    "moscow_apartment_economy": {
        "city_id": "moscow", "city": "Москва", "country": "Россия",
        "name": "Квартира эконом-класса", "segment": "economy", "property_type": "apartment",
        "price": 16000000, "base_rent_hour": 96.8,
        "lat": 55.7558, "lng": 37.6173,
        "photo": "https://images.unsplash.com/photo-1493809842364-78817add7ffb?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Квартира эконом-класса в городе Москва. Автоматически приносит арендный доход и может быть улучшена.",
    },
    "moscow_apartment_business": {
        "city_id": "moscow", "city": "Москва", "country": "Россия",
        "name": "Квартира бизнес-класса", "segment": "business", "property_type": "apartment",
        "price": 32000000, "base_rent_hour": 157.08,
        "lat": 55.7558, "lng": 37.6173,
        "photo": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Квартира бизнес-класса в городе Москва. Автоматически приносит арендный доход и может быть улучшена.",
    },
    "moscow_apartment_vip": {
        "city_id": "moscow", "city": "Москва", "country": "Россия",
        "name": "Квартира VIP-класса", "segment": "vip", "property_type": "apartment",
        "price": 75000000, "base_rent_hour": 273.97,
        "lat": 55.7558, "lng": 37.6173,
        "photo": "https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Квартира VIP-класса в городе Москва. Автоматически приносит арендный доход и может быть улучшена.",
    },
    "moscow_house_economy": {
        "city_id": "moscow", "city": "Москва", "country": "Россия",
        "name": "Дом эконом-класса", "segment": "economy", "property_type": "house",
        "price": 35000000, "base_rent_hour": 187.79,
        "lat": 55.7558, "lng": 37.6173,
        "photo": "https://images.unsplash.com/photo-1564013799919-ab600027ffc6?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Дом эконом-класса в городе Москва. Автоматически приносит арендный доход и может быть улучшена.",
    },
    "moscow_house_business": {
        "city_id": "moscow", "city": "Москва", "country": "Россия",
        "name": "Дом бизнес-класса", "segment": "business", "property_type": "house",
        "price": 80000000, "base_rent_hour": 347.03,
        "lat": 55.7558, "lng": 37.6173,
        "photo": "https://images.unsplash.com/photo-1600047509807-ba8f99d2cdde?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Дом бизнес-класса в городе Москва. Автоматически приносит арендный доход и может быть улучшена.",
    },
    "moscow_house_vip": {
        "city_id": "moscow", "city": "Москва", "country": "Россия",
        "name": "Дом VIP-класса", "segment": "vip", "property_type": "house",
        "price": 180000000, "base_rent_hour": 575.34,
        "lat": 55.7558, "lng": 37.6173,
        "photo": "https://images.unsplash.com/photo-1605146769289-440113cc3d00?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Дом VIP-класса в городе Москва. Автоматически приносит арендный доход и может быть улучшена.",
    },
    "barcelona_apartment_economy": {
        "city_id": "barcelona", "city": "Барселона", "country": "Испания",
        "name": "Квартира эконом-класса", "segment": "economy", "property_type": "apartment",
        "price": 28000000, "base_rent_hour": 166.21,
        "lat": 41.3874, "lng": 2.1686,
        "photo": "https://images.unsplash.com/photo-1493809842364-78817add7ffb?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Квартира эконом-класса в городе Барселона. Автоматически приносит арендный доход и может быть улучшена.",
    },
    "barcelona_apartment_business": {
        "city_id": "barcelona", "city": "Барселона", "country": "Испания",
        "name": "Квартира бизнес-класса", "segment": "business", "property_type": "apartment",
        "price": 48000000, "base_rent_hour": 230.14,
        "lat": 41.3874, "lng": 2.1686,
        "photo": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Квартира бизнес-класса в городе Барселона. Автоматически приносит арендный доход и может быть улучшена.",
    },
    "barcelona_apartment_vip": {
        "city_id": "barcelona", "city": "Барселона", "country": "Испания",
        "name": "Квартира VIP-класса", "segment": "vip", "property_type": "apartment",
        "price": 95000000, "base_rent_hour": 357.88,
        "lat": 41.3874, "lng": 2.1686,
        "photo": "https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Квартира VIP-класса в городе Барселона. Автоматически приносит арендный доход и может быть улучшена.",
    },
    "barcelona_house_economy": {
        "city_id": "barcelona", "city": "Барселона", "country": "Испания",
        "name": "Дом эконом-класса", "segment": "economy", "property_type": "house",
        "price": 55000000, "base_rent_hour": 301.37,
        "lat": 41.3874, "lng": 2.1686,
        "photo": "https://images.unsplash.com/photo-1564013799919-ab600027ffc6?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Дом эконом-класса в городе Барселона. Автоматически приносит арендный доход и может быть улучшена.",
    },
    "barcelona_house_business": {
        "city_id": "barcelona", "city": "Барселона", "country": "Испания",
        "name": "Дом бизнес-класса", "segment": "business", "property_type": "house",
        "price": 105000000, "base_rent_hour": 455.48,
        "lat": 41.3874, "lng": 2.1686,
        "photo": "https://images.unsplash.com/photo-1600047509807-ba8f99d2cdde?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Дом бизнес-класса в городе Барселона. Автоматически приносит арендный доход и может быть улучшена.",
    },
    "barcelona_house_vip": {
        "city_id": "barcelona", "city": "Барселона", "country": "Испания",
        "name": "Дом VIP-класса", "segment": "vip", "property_type": "house",
        "price": 210000000, "base_rent_hour": 719.18,
        "lat": 41.3874, "lng": 2.1686,
        "photo": "https://images.unsplash.com/photo-1605146769289-440113cc3d00?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Дом VIP-класса в городе Барселона. Автоматически приносит арендный доход и может быть улучшена.",
    },
    "paris_apartment_economy": {
        "city_id": "paris", "city": "Париж", "country": "Франция",
        "name": "Квартира эконом-класса", "segment": "economy", "property_type": "apartment",
        "price": 24000000, "base_rent_hour": 145.21,
        "lat": 48.8566, "lng": 2.3522,
        "photo": "https://images.unsplash.com/photo-1493809842364-78817add7ffb?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Квартира эконом-класса в городе Париж. Автоматически приносит арендный доход и может быть улучшена.",
    },
    "paris_apartment_business": {
        "city_id": "paris", "city": "Париж", "country": "Франция",
        "name": "Квартира бизнес-класса", "segment": "business", "property_type": "apartment",
        "price": 45000000, "base_rent_hour": 220.89,
        "lat": 48.8566, "lng": 2.3522,
        "photo": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Квартира бизнес-класса в городе Париж. Автоматически приносит арендный доход и может быть улучшена.",
    },
    "paris_apartment_vip": {
        "city_id": "paris", "city": "Париж", "country": "Франция",
        "name": "Квартира VIP-класса", "segment": "vip", "property_type": "apartment",
        "price": 95000000, "base_rent_hour": 379.57,
        "lat": 48.8566, "lng": 2.3522,
        "photo": "https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Квартира VIP-класса в городе Париж. Автоматически приносит арендный доход и может быть улучшена.",
    },
    "paris_house_economy": {
        "city_id": "paris", "city": "Париж", "country": "Франция",
        "name": "Дом эконом-класса", "segment": "economy", "property_type": "house",
        "price": 60000000, "base_rent_hour": 315.07,
        "lat": 48.8566, "lng": 2.3522,
        "photo": "https://images.unsplash.com/photo-1564013799919-ab600027ffc6?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Дом эконом-класса в городе Париж. Автоматически приносит арендный доход и может быть улучшена.",
    },
    "paris_house_business": {
        "city_id": "paris", "city": "Париж", "country": "Франция",
        "name": "Дом бизнес-класса", "segment": "business", "property_type": "house",
        "price": 130000000, "base_rent_hour": 549.09,
        "lat": 48.8566, "lng": 2.3522,
        "photo": "https://images.unsplash.com/photo-1600047509807-ba8f99d2cdde?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Дом бизнес-класса в городе Париж. Автоматически приносит арендный доход и может быть улучшена.",
    },
    "paris_house_vip": {
        "city_id": "paris", "city": "Париж", "country": "Франция",
        "name": "Дом VIP-класса", "segment": "vip", "property_type": "house",
        "price": 280000000, "base_rent_hour": 958.9,
        "lat": 48.8566, "lng": 2.3522,
        "photo": "https://images.unsplash.com/photo-1605146769289-440113cc3d00?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Дом VIP-класса в городе Париж. Автоматически приносит арендный доход и может быть улучшена.",
    },
    "london_apartment_economy": {
        "city_id": "london", "city": "Лондон", "country": "Великобритания",
        "name": "Квартира эконом-класса", "segment": "economy", "property_type": "apartment",
        "price": 45000000, "base_rent_hour": 308.22,
        "lat": 51.5072, "lng": -0.1276,
        "photo": "https://images.unsplash.com/photo-1493809842364-78817add7ffb?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Квартира эконом-класса в городе Лондон. Автоматически приносит арендный доход и может быть улучшена.",
    },
    "london_apartment_business": {
        "city_id": "london", "city": "Лондон", "country": "Великобритания",
        "name": "Квартира бизнес-класса", "segment": "business", "property_type": "apartment",
        "price": 80000000, "base_rent_hour": 456.62,
        "lat": 51.5072, "lng": -0.1276,
        "photo": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Квартира бизнес-класса в городе Лондон. Автоматически приносит арендный доход и может быть улучшена.",
    },
    "london_apartment_vip": {
        "city_id": "london", "city": "Лондон", "country": "Великобритания",
        "name": "Квартира VIP-класса", "segment": "vip", "property_type": "apartment",
        "price": 170000000, "base_rent_hour": 776.26,
        "lat": 51.5072, "lng": -0.1276,
        "photo": "https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Квартира VIP-класса в городе Лондон. Автоматически приносит арендный доход и может быть улучшена.",
    },
    "london_house_economy": {
        "city_id": "london", "city": "Лондон", "country": "Великобритания",
        "name": "Дом эконом-класса", "segment": "economy", "property_type": "house",
        "price": 90000000, "base_rent_hour": 544.52,
        "lat": 51.5072, "lng": -0.1276,
        "photo": "https://images.unsplash.com/photo-1564013799919-ab600027ffc6?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Дом эконом-класса в городе Лондон. Автоматически приносит арендный доход и может быть улучшена.",
    },
    "london_house_business": {
        "city_id": "london", "city": "Лондон", "country": "Великобритания",
        "name": "Дом бизнес-класса", "segment": "business", "property_type": "house",
        "price": 180000000, "base_rent_hour": 883.56,
        "lat": 51.5072, "lng": -0.1276,
        "photo": "https://images.unsplash.com/photo-1600047509807-ba8f99d2cdde?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Дом бизнес-класса в городе Лондон. Автоматически приносит арендный доход и может быть улучшена.",
    },
    "london_house_vip": {
        "city_id": "london", "city": "Лондон", "country": "Великобритания",
        "name": "Дом VIP-класса", "segment": "vip", "property_type": "house",
        "price": 380000000, "base_rent_hour": 1561.64,
        "lat": 51.5072, "lng": -0.1276,
        "photo": "https://images.unsplash.com/photo-1605146769289-440113cc3d00?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Дом VIP-класса в городе Лондон. Автоматически приносит арендный доход и может быть улучшена.",
    },
    "new_york_apartment_economy": {
        "city_id": "new_york", "city": "Нью-Йорк", "country": "США",
        "name": "Квартира эконом-класса", "segment": "economy", "property_type": "apartment",
        "price": 50000000, "base_rent_hour": 399.54,
        "lat": 40.7128, "lng": -74.006,
        "photo": "https://images.unsplash.com/photo-1493809842364-78817add7ffb?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Квартира эконом-класса в городе Нью-Йорк. Автоматически приносит арендный доход и может быть улучшена.",
    },
    "new_york_apartment_business": {
        "city_id": "new_york", "city": "Нью-Йорк", "country": "США",
        "name": "Квартира бизнес-класса", "segment": "business", "property_type": "apartment",
        "price": 90000000, "base_rent_hour": 595.89,
        "lat": 40.7128, "lng": -74.006,
        "photo": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Квартира бизнес-класса в городе Нью-Йорк. Автоматически приносит арендный доход и может быть улучшена.",
    },
    "new_york_apartment_vip": {
        "city_id": "new_york", "city": "Нью-Йорк", "country": "США",
        "name": "Квартира VIP-класса", "segment": "vip", "property_type": "apartment",
        "price": 210000000, "base_rent_hour": 1006.85,
        "lat": 40.7128, "lng": -74.006,
        "photo": "https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Квартира VIP-класса в городе Нью-Йорк. Автоматически приносит арендный доход и может быть улучшена.",
    },
    "new_york_house_economy": {
        "city_id": "new_york", "city": "Нью-Йорк", "country": "США",
        "name": "Дом эконом-класса", "segment": "economy", "property_type": "house",
        "price": 110000000, "base_rent_hour": 778.54,
        "lat": 40.7128, "lng": -74.006,
        "photo": "https://images.unsplash.com/photo-1564013799919-ab600027ffc6?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Дом эконом-класса в городе Нью-Йорк. Автоматически приносит арендный доход и может быть улучшена.",
    },
    "new_york_house_business": {
        "city_id": "new_york", "city": "Нью-Йорк", "country": "США",
        "name": "Дом бизнес-класса", "segment": "business", "property_type": "house",
        "price": 240000000, "base_rent_hour": 1369.86,
        "lat": 40.7128, "lng": -74.006,
        "photo": "https://images.unsplash.com/photo-1600047509807-ba8f99d2cdde?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Дом бизнес-класса в городе Нью-Йорк. Автоматически приносит арендный доход и может быть улучшена.",
    },
    "new_york_house_vip": {
        "city_id": "new_york", "city": "Нью-Йорк", "country": "США",
        "name": "Дом VIP-класса", "segment": "vip", "property_type": "house",
        "price": 520000000, "base_rent_hour": 2374.43,
        "lat": 40.7128, "lng": -74.006,
        "photo": "https://images.unsplash.com/photo-1605146769289-440113cc3d00?auto=format&fit=crop&w=1200&h=700&q=82",
        "description": "Дом VIP-класса в городе Нью-Йорк. Автоматически приносит арендный доход и может быть улучшена.",
    },
}


# === CORPORATION V20.1: REAL ESTATE BALANCE ================================
# Game-balance yield is hourly, like other Corporation assets.
# More expensive properties are progressively more profitable: ~1.0% to 2.2%/h
# before upgrades, while retaining 100% resale capitalization.
def _rebalance_real_estate_v20():
    prices = [float(p["price"]) for p in REAL_ESTATE.values()]
    if not prices:
        return
    lo, hi = min(prices), max(prices)
    import math
    log_lo, log_hi = math.log(max(lo, 1.0)), math.log(max(hi, 1.0))
    span = max(log_hi - log_lo, 1e-9)
    for prop in REAL_ESTATE.values():
        new_price = round(float(prop["price"]) * 0.90, 2)
        score = (math.log(max(new_price, 1.0)) - math.log(max(lo * 0.90, 1.0))) / span
        score = min(1.0, max(0.0, score))
        hourly_yield = 0.010 + 0.012 * score
        prop["price"] = new_price
        prop["base_rent_hour"] = round(new_price * hourly_yield, 2)
        prop["target_hourly_yield"] = hourly_yield

_rebalance_real_estate_v20()
# ============================================================================

api = FastAPI(title="Corporation")
WEB_DIR = os.path.join(os.path.dirname(__file__), "web")
api.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


def db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    # Better concurrent read/write behavior for Telegram Mini App traffic.
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA foreign_keys=OFF")
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
        CREATE TABLE IF NOT EXISTS bond_holdings (
            user_id INTEGER NOT NULL,
            bond_id TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(user_id, bond_id)
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
        CREATE TABLE IF NOT EXISTS game_state (
            id INTEGER PRIMARY KEY CHECK(id=1),
            is_frozen INTEGER NOT NULL DEFAULT 0,
            frozen_at INTEGER NOT NULL DEFAULT 0,
            current_season INTEGER NOT NULL DEFAULT 1,
            season_started_at INTEGER NOT NULL DEFAULT 0,
            season_ended_at INTEGER NOT NULL DEFAULT 0,
            maintenance_message TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS season_results (
            season_id INTEGER NOT NULL,
            place INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            username TEXT,
            corp_name TEXT NOT NULL,
            money REAL NOT NULL,
            captured_at INTEGER NOT NULL,
            PRIMARY KEY(season_id, place)
        );
        CREATE TABLE IF NOT EXISTS seasons (
            season_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            started_at INTEGER NOT NULL DEFAULT 0,
            ended_at INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS market_news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_id TEXT NOT NULL,
            sentiment TEXT NOT NULL CHECK(sentiment IN ('good','bad')),
            title TEXT NOT NULL,
            article TEXT NOT NULL,
            photo TEXT NOT NULL,
            published_at INTEGER NOT NULL,
            impact_at INTEGER NOT NULL,
            impact_percent REAL NOT NULL,
            price_before REAL NOT NULL DEFAULT 0,
            price_after REAL NOT NULL DEFAULT 0,
            applied_at INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_market_news_time ON market_news(published_at DESC);
        CREATE TABLE IF NOT EXISTS market_news_state (
            id INTEGER PRIMARY KEY CHECK(id=1),
            next_news_at INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '',
            created_at INTEGER NOT NULL
        );
        """)
        ensure_column(conn, "players", "last_income_sync", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(conn, "stats", "properties_bought", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(conn, "businesses", "marketing", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(conn, "businesses", "equipment", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(conn, "businesses", "staff", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(conn, "businesses", "automation", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(conn, "season_results", "capital", "REAL NOT NULL DEFAULT 0")
        ensure_column(conn, "players", "is_frozen", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(conn, "players", "frozen_at", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(conn, "players", "is_blocked", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(conn, "players", "blocked_at", "INTEGER NOT NULL DEFAULT 0")
        conn.execute("UPDATE season_results SET capital=money WHERE capital<=0")
        conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_players_last_income_sync ON players(last_income_sync);
        CREATE INDEX IF NOT EXISTS idx_businesses_user ON businesses(user_id);
        CREATE INDEX IF NOT EXISTS idx_stock_holdings_user ON stock_holdings(user_id);
        CREATE INDEX IF NOT EXISTS idx_bond_holdings_user ON bond_holdings(user_id);
        CREATE INDEX IF NOT EXISTS idx_real_estate_user ON real_estate_holdings(user_id);
        CREATE INDEX IF NOT EXISTS idx_daily_profit_user_day ON daily_profit(user_id, day);
        CREATE INDEX IF NOT EXISTS idx_season_results_season_place ON season_results(season_id, place);
        """)
        conn.execute("UPDATE players SET last_income_sync=? WHERE last_income_sync=0", (now,))
        conn.execute(
            "INSERT OR IGNORE INTO game_state(id,is_frozen,frozen_at,current_season,season_started_at,season_ended_at,maintenance_message) VALUES(1,0,0,1,?,0,'')",
            (now,),
        )
        conn.execute("INSERT OR IGNORE INTO market_news_state(id,next_news_at) VALUES(1,?)", (now,))
        gs_row = conn.execute("SELECT current_season,season_started_at,season_ended_at FROM game_state WHERE id=1").fetchone()
        conn.execute(
            "INSERT OR IGNORE INTO seasons(season_id,name,started_at,ended_at) VALUES(?,?,?,?)",
            (int(gs_row["current_season"]), f"Сезон №{int(gs_row['current_season'])}", int(gs_row["season_started_at"] or now), int(gs_row["season_ended_at"] or 0)),
        )
        for sr in conn.execute("SELECT DISTINCT season_id FROM season_results").fetchall():
            sid = int(sr["season_id"])
            conn.execute("INSERT OR IGNORE INTO seasons(season_id,name,started_at,ended_at) VALUES(?,?,0,0)", (sid, f"Сезон №{sid}"))

        # REAL_ESTATE_V18_REVALUE: keep ownership/upgrades, but rebase legacy purchase prices
        # to the new realistic market model so old low prices cannot create extreme yields.
        for property_id, prop in REAL_ESTATE.items():
            conn.execute(
                "UPDATE real_estate_holdings SET purchase_price=? WHERE property_id=?",
                (prop["price"], property_id),
            )

        for stock_id, stock in STOCKS.items():
            exists = conn.execute("SELECT 1 FROM stocks WHERE id=?", (stock_id,)).fetchone()
            if not exists:
                conn.execute(
                    "INSERT INTO stocks(id,symbol,name,description,min_price,max_price,current_price,trend,last_update) VALUES(?,?,?,?,?,?,?,?,?)",
                    (stock_id, stock["symbol"], stock["name"], stock["description"], stock["min_price"], stock["max_price"], stock["initial_price"], "up", now),
                )
                conn.execute("INSERT INTO stock_history(stock_id,price,created_at) VALUES(?,?,?)", (stock_id, stock["initial_price"], now))
            else:
                # Обновляем параметры уже существующих акций без удаления истории и портфелей.
                current = conn.execute("SELECT current_price FROM stocks WHERE id=?", (stock_id,)).fetchone()
                safe_price = min(stock["max_price"], max(stock["min_price"], float(current["current_price"])))
                conn.execute(
                    "UPDATE stocks SET symbol=?,name=?,description=?,min_price=?,max_price=?,current_price=? WHERE id=?",
                    (stock["symbol"], stock["name"], stock["description"], stock["min_price"], stock["max_price"], safe_price, stock_id),
                )
        conn.commit()


init_db()


def get_game_state():
    with closing(db()) as conn:
        row = conn.execute("SELECT * FROM game_state WHERE id=1").fetchone()
    return dict(row) if row else {"is_frozen": 0, "frozen_at": 0, "current_season": 1, "season_started_at": 0, "season_ended_at": 0, "maintenance_message": ""}


def game_is_frozen():
    return bool(int(get_game_state().get("is_frozen", 0)))


def admin_log(admin_id, action, details="", conn=None):
    own = conn is None
    if own:
        conn = db()
    try:
        conn.execute(
            "INSERT INTO admin_logs(admin_id,action,details,created_at) VALUES(?,?,?,?)",
            (int(admin_id), str(action), str(details)[:2000], int(time.time())),
        )
        if own:
            conn.commit()
    finally:
        if own:
            conn.close()


def require_admin(x_telegram_init_data, x_user_id):
    uid, _, _ = user_from_request(x_telegram_init_data, x_user_id)
    if uid not in ADMIN_IDS:
        raise HTTPException(403, "Нет доступа к админ-панели")
    return uid


def create_database_backup(reason="manual"):
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(os.path.dirname(os.path.abspath(DB_PATH)), "admin_backups")
    os.makedirs(backup_dir, exist_ok=True)
    safe_reason = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in str(reason))[:40] or "backup"
    target = os.path.join(backup_dir, f"corporation_{now}_{safe_reason}.db")
    with closing(db()) as source, closing(sqlite3.connect(target)) as dest:
        source.backup(dest)
    return target


def reset_stock_market_conn(conn, now):
    conn.execute("DELETE FROM stock_history")
    conn.execute("DELETE FROM market_news")
    conn.execute("INSERT OR REPLACE INTO market_news_state(id,next_news_at) VALUES(1,?)", (now,))
    for stock_id, stock in STOCKS.items():
        conn.execute(
            "UPDATE stocks SET symbol=?,name=?,description=?,min_price=?,max_price=?,current_price=?,trend='up',last_update=? WHERE id=?",
            (stock["symbol"], stock["name"], stock["description"], stock["min_price"], stock["max_price"], stock["initial_price"], now, stock_id),
        )
        conn.execute("INSERT INTO stock_history(stock_id,price,created_at) VALUES(?,?,?)", (stock_id, stock["initial_price"], now))


def reset_all_progress_conn(conn, now):
    for table in ("businesses", "daily_profit", "stock_holdings", "bond_holdings", "real_estate_holdings", "stats", "taxes"):
        conn.execute(f"DELETE FROM {table}")
    conn.execute(
        "UPDATE players SET money=?,last_collect=0,last_income_sync=?",
        (STARTING_MONEY, now),
    )
    conn.execute("INSERT INTO stats(user_id) SELECT user_id FROM players")
    conn.execute("INSERT INTO taxes(user_id) SELECT user_id FROM players")
    reset_stock_market_conn(conn, now)


@api.middleware("http")
async def corporation_freeze_guard(request: Request, call_next):
    path = request.url.path
    method = request.method.upper()
    if path.startswith("/api/") and not path.startswith("/api/admin/"):
        # Global freeze: reads remain available, game mutations stop.
        if method in {"POST", "PUT", "PATCH", "DELETE"} and game_is_frozen():
            state = get_game_state()
            message = state.get("maintenance_message") or "Игра заморожена администратором. Просмотр доступен, игровые действия временно отключены."
            return JSONResponse(status_code=423, content={"detail": message, "game_frozen": True})

        # Per-player moderation is enforced server-side, not only hidden in UI.
        try:
            uid, _, _ = user_from_request(request.headers.get("x-telegram-init-data"), request.headers.get("x-user-id"))
            if uid not in ADMIN_IDS:
                restrictions = get_player_restrictions(uid)
                if restrictions["is_blocked"]:
                    return JSONResponse(status_code=403, content={"detail": "Аккаунт заблокирован администратором Corporation", "player_blocked": True})
                if method in {"POST", "PUT", "PATCH", "DELETE"} and restrictions["is_frozen"]:
                    return JSONResponse(status_code=423, content={"detail": "Аккаунт заморожен администратором. Просмотр доступен, игровые действия и начисление дохода остановлены.", "player_frozen": True})
        except HTTPException:
            pass
    return await call_next(request)


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


def get_player_restrictions(uid, conn=None):
    own = conn is None
    if own:
        conn = db()
    try:
        row = conn.execute("SELECT is_frozen,frozen_at,is_blocked,blocked_at FROM players WHERE user_id=?", (uid,)).fetchone()
        if not row:
            return {"is_frozen": False, "frozen_at": 0, "is_blocked": False, "blocked_at": 0}
        return {
            "is_frozen": bool(int(row["is_frozen"] or 0)),
            "frozen_at": int(row["frozen_at"] or 0),
            "is_blocked": bool(int(row["is_blocked"] or 0)),
            "blocked_at": int(row["blocked_at"] or 0),
        }
    finally:
        if own:
            conn.close()


def get_levels(uid):
    with closing(db()) as conn:
        rows = conn.execute("SELECT business_id,level FROM businesses WHERE user_id=?", (uid,)).fetchall()
    return {r["business_id"]: int(r["level"]) for r in rows}


def get_business_rows(uid, conn=None):
    own = conn is None
    if own:
        conn = db()
    try:
        rows = conn.execute("SELECT * FROM businesses WHERE user_id=?", (uid,)).fetchall()
        return {r["business_id"]: r for r in rows}
    finally:
        if own:
            conn.close()


def business_upgrade_multiplier(row, bid=None):
    if not row:
        return 1.0
    bonus = 0.0
    for upgrade_id, base_cfg in BUSINESS_UPGRADES.items():
        cfg = get_business_upgrade_cfg(bid, upgrade_id) if bid else base_cfg
        if int(row[base_cfg["column"]] or 0) > 0:
            bonus += cfg["income_bonus"]
    return 1.0 + bonus


def business_hourly_income(uid):
    rows = get_business_rows(uid)
    total = 0.0
    for bid, row in rows.items():
        if bid in BUSINESSES and int(row["level"] or 0) > 0:
            total += BUSINESSES[bid]["base_income"] * int(row["level"]) * business_upgrade_multiplier(row, bid)
    return total


def next_business_cost(bid, level):
    # Покупка бизнеса происходит один раз. Формула оставлена для совместимости
    # со старыми уровнями существующих игроков.
    return int(BUSINESSES[bid]["base_cost"] * (1.45 ** max(0, level)))


def business_upgrade_cost(bid, upgrade_id):
    cfg = get_business_upgrade_cfg(bid, upgrade_id)
    return round(BUSINESSES[bid]["base_cost"] * cfg["cost_rate"], 2)


def business_capitalization(bid, level, row=None):
    if bid not in BUSINESSES or level <= 0:
        return 0
    legacy_cost = sum(next_business_cost(bid, lvl) for lvl in range(max(0, level)))
    upgrade_costs = 0
    if row:
        for upgrade_id, base_cfg in BUSINESS_UPGRADES.items():
            if int(row[base_cfg["column"]] or 0) > 0:
                upgrade_costs += business_upgrade_cost(bid, upgrade_id)
    return round(legacy_cost + upgrade_costs, 2)


def _eligible_news_stocks(conn, sentiment):
    eligible=[]
    for row in conn.execute("SELECT id,current_price,min_price,max_price FROM stocks").fetchall():
        price=float(row["current_price"])
        if price<=0: continue
        if sentiment=="good":
            room=float(row["max_price"])/price-1.0
        else:
            room=1.0-float(row["min_price"])/price
        if room >= MARKET_NEWS_MIN_IMPACT:
            eligible.append(row["id"])
    return eligible


def _publish_market_news_conn(conn, published_at):
    sentiment = "good" if random.random() < 0.5 else "bad"
    eligible = _eligible_news_stocks(conn, sentiment)
    stock_ids = eligible or [sid for sid in MARKET_NEWS_TEMPLATES if sid in STOCKS]
    stock_id = random.choice(stock_ids)
    template = random.choice(MARKET_NEWS_TEMPLATES[stock_id][sentiment])
    stock = conn.execute("SELECT current_price,min_price,max_price FROM stocks WHERE id=?", (stock_id,)).fetchone()
    current=float(stock["current_price"])
    if sentiment=="good":
        max_room=max(0.0, float(stock["max_price"])/current-1.0)
    else:
        max_room=max(0.0, 1.0-float(stock["min_price"])/current)
    upper=min(MARKET_NEWS_MAX_IMPACT, max_room)
    lower=min(MARKET_NEWS_MIN_IMPACT, upper)
    impact=random.uniform(lower, upper) if upper>0 else 0.0
    if impact < MARKET_NEWS_MIN_IMPACT and eligible:
        impact=MARKET_NEWS_MIN_IMPACT
    signed = impact if sentiment=="good" else -impact
    conn.execute(
        "INSERT INTO market_news(stock_id,sentiment,title,article,photo,published_at,impact_at,impact_percent) VALUES(?,?,?,?,?,?,?,?)",
        (stock_id,sentiment,template[0],template[1],MARKET_NEWS_TEMPLATES[stock_id]["photo"],int(published_at),int(published_at)+MARKET_NEWS_REACTION_DELAY,float(signed)),
    )


def process_market_news(now=None):
    now=int(now or time.time())
    if game_is_frozen():
        return
    with closing(db()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        st=conn.execute("SELECT next_news_at FROM market_news_state WHERE id=1").fetchone()
        next_at=int(st["next_news_at"] if st else now)
        # First update post is created immediately; overdue hourly posts are caught up safely.
        generated=0
        while next_at <= now and generated < 48:
            _publish_market_news_conn(conn, next_at)
            next_at += MARKET_NEWS_INTERVAL
            generated += 1
        conn.execute("INSERT OR REPLACE INTO market_news_state(id,next_news_at) VALUES(1,?)", (next_at,))

        pending=conn.execute("SELECT * FROM market_news WHERE applied_at=0 AND impact_at<=? ORDER BY impact_at ASC,id ASC", (now,)).fetchall()
        for news in pending:
            row=conn.execute("SELECT current_price,min_price,max_price FROM stocks WHERE id=?", (news["stock_id"],)).fetchone()
            if not row:
                conn.execute("UPDATE market_news SET applied_at=? WHERE id=?", (now,news["id"]))
                continue
            before=float(row["current_price"])
            pct=float(news["impact_percent"])
            after=before*(1.0+pct)
            after=min(float(row["max_price"]),max(float(row["min_price"]),after))
            after=round(after,2)
            actual_pct=(after/before-1.0) if before else 0.0
            trend="up" if actual_pct>=0 else "down"
            impact_time=int(news["impact_at"])
            conn.execute("UPDATE stocks SET current_price=?,trend=?,last_update=? WHERE id=?", (after,trend,impact_time,news["stock_id"]))
            conn.execute("INSERT INTO stock_history(stock_id,price,created_at) VALUES(?,?,?)", (news["stock_id"],after,impact_time))
            conn.execute("UPDATE market_news SET impact_percent=?,price_before=?,price_after=?,applied_at=? WHERE id=?", (actual_pct,before,after,now,news["id"]))
        conn.commit()


def get_market_news(limit=50):
    process_market_news()
    limit=max(1,min(int(limit),100))
    with closing(db()) as conn:
        rows=conn.execute("SELECT * FROM market_news ORDER BY published_at DESC,id DESC LIMIT ?", (limit,)).fetchall()
        next_row=conn.execute("SELECT next_news_at FROM market_news_state WHERE id=1").fetchone()
    now=int(time.time())
    items=[]
    for r in rows:
        d=dict(r)
        cfg=STOCKS.get(d["stock_id"],{})
        applied=bool(int(d["applied_at"] or 0))
        items.append({
            "id":d["id"],"stock_id":d["stock_id"],"company":cfg.get("name",d["stock_id"]),"symbol":cfg.get("symbol",""),
            "sentiment":d["sentiment"],"title":d["title"],"article":d["article"],"photo":d["photo"],
            "published_at":d["published_at"],"impact_at":d["impact_at"],"applied":applied,"applied_at":d["applied_at"],
            "impact_percent":round(float(d["impact_percent"])*100,2) if applied else None,
            "price_before":round(float(d["price_before"]),2) if applied else None,"price_after":round(float(d["price_after"]),2) if applied else None,
            "seconds_to_impact":max(0,int(d["impact_at"])-now) if not applied else 0,
        })
    return {"news":items,"next_news_at":int(next_row["next_news_at"] if next_row else 0),"server_time":now}


_market_news_worker_started=False
_market_update_lock = threading.Lock()
_market_update_last_check = 0.0
def _market_news_worker():
    while True:
        try:
            process_market_news()
        except Exception as exc:
            print(f"[Corporation] market news worker error: {exc}")
        time.sleep(5)


def start_market_news_worker():
    global _market_news_worker_started
    if _market_news_worker_started:
        return
    _market_news_worker_started=True
    threading.Thread(target=_market_news_worker,name="corporation-market-news",daemon=True).start()


def update_stock_market():
    """Минутная игровая модель с дешёвым throttle для большого числа параллельных запросов."""
    global _market_update_last_check
    if game_is_frozen():
        return
    monotonic_now = time.monotonic()
    if monotonic_now - _market_update_last_check < 1.0:
        return
    if not _market_update_lock.acquire(blocking=False):
        return
    try:
        monotonic_now = time.monotonic()
        if monotonic_now - _market_update_last_check < 1.0:
            return
        process_market_news()
        now = int(time.time())
        with closing(db()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            rows = conn.execute("SELECT * FROM stocks").fetchall()
            for stock in rows:
                config = STOCKS.get(stock["id"])
                if not config:
                    continue

                elapsed = now - int(stock["last_update"])
                if elapsed < STOCK_UPDATE_INTERVAL:
                    safe = min(config["max_price"], max(config["min_price"], float(stock["current_price"])))
                    if safe != float(stock["current_price"]):
                        conn.execute("UPDATE stocks SET current_price=? WHERE id=?", (safe, stock["id"]))
                    continue

                steps = min(int(elapsed // STOCK_UPDATE_INTERVAL), MAX_STOCK_HISTORY_POINTS)
                price = min(config["max_price"], max(config["min_price"], float(stock["current_price"])))
                trend = stock["trend"] if stock["trend"] in ("up", "down") else "up"
                last_update = int(stock["last_update"])
                floor = float(config["min_price"])
                ceiling = float(config["max_price"])
                midpoint = (floor + ceiling) / 2
                span = max(ceiling - floor, 1.0)

                history_batch = []
                for _ in range(steps):
                    position = (price - floor) / span
                    direction = 1 if trend == "up" else -1
                    move = random.gauss(direction * config["drift"], config["volatility"])
                    move += ((midpoint - price) / span) * 0.006
                    if random.random() < 0.035:
                        move += random.uniform(-config["volatility"] * 2.2, config["volatility"] * 2.2)
                    next_price = price * (1 + move)
                    if next_price <= floor:
                        next_price = floor; trend = "up"
                    elif next_price >= ceiling:
                        next_price = ceiling; trend = "down"
                    else:
                        if position < 0.12 and random.random() < 0.42:
                            trend = "up"
                        elif position > 0.88 and random.random() < 0.42:
                            trend = "down"
                        elif random.random() < 0.055:
                            trend = "down" if trend == "up" else "up"
                    price = round(min(ceiling, max(floor, next_price)), 2)
                    last_update += STOCK_UPDATE_INTERVAL
                    history_batch.append((stock["id"], price, last_update))
                if history_batch:
                    conn.executemany("INSERT INTO stock_history(stock_id,price,created_at) VALUES(?,?,?)", history_batch)
                conn.execute("UPDATE stocks SET current_price=?,trend=?,last_update=? WHERE id=?", (price, trend, last_update, stock["id"]))
            # Keep history bounded globally instead of letting SQLite grow forever.
            conn.execute("""DELETE FROM stock_history WHERE id IN (
                SELECT h.id FROM stock_history h
                JOIN (SELECT stock_id, MAX(id) max_id FROM stock_history GROUP BY stock_id) m ON m.stock_id=h.stock_id
                WHERE h.id < m.max_id - ?
            )""", (MAX_STOCK_HISTORY_POINTS * 2,))
            conn.commit()
        _market_update_last_check = monotonic_now
    finally:
        _market_update_lock.release()

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


def bond_hourly_income(uid, conn=None):
    own = conn is None
    if own:
        conn = db()
    try:
        rows = conn.execute(
            "SELECT bond_id,quantity FROM bond_holdings WHERE user_id=? AND quantity>0",
            (uid,),
        ).fetchall()
        return sum(
            float(BONDS[r["bond_id"]]["price"]) * int(r["quantity"]) * float(BONDS[r["bond_id"]]["yield_rate"])
            for r in rows if r["bond_id"] in BONDS
        )
    finally:
        if own:
            conn.close()


def property_upgrade_multiplier(row):
    return 1 + sum(REAL_ESTATE_UPGRADES[key]["income_bonus"] for key in REAL_ESTATE_UPGRADES if int(row[key] or 0) > 0)


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
    now = int(time.time())
    if game_is_frozen():
        return {"earned": 0, "business": 0, "dividends": 0, "bonds": 0, "rent": 0}
    restrictions = get_player_restrictions(uid)
    if restrictions["is_blocked"] or restrictions["is_frozen"]:
        return {"earned": 0, "business": 0, "dividends": 0, "bonds": 0, "rent": 0}
    update_stock_market()
    with closing(db()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        player = conn.execute("SELECT last_income_sync FROM players WHERE user_id=?", (uid,)).fetchone()
        if not player:
            conn.rollback()
            return {"earned": 0, "business": 0, "dividends": 0, "bonds": 0, "rent": 0}
        last_sync = int(player["last_income_sync"] or now)
        if last_sync >= now:
            conn.commit()
            return {"earned": 0, "business": 0, "dividends": 0, "bonds": 0, "rent": 0}

        tax = conn.execute("SELECT unpaid,due_since FROM taxes WHERE user_id=?", (uid,)).fetchone()
        unpaid = float(tax["unpaid"] if tax else 0)
        due_since = int(tax["due_since"] if tax else 0)

        business_rate = float(business_hourly_income(uid))
        dividend_rate = float(dividend_hourly_income(uid, conn))
        bond_rate = float(bond_hourly_income(uid, conn))
        rent_rate = float(real_estate_hourly_income(uid, conn))
        total_rate = business_rate + dividend_rate + bond_rate + rent_rate

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
        bonds_earned = bond_rate * hours
        rent_earned = rent_rate * hours
        earned = business_earned + dividends_earned + bonds_earned + rent_earned

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
            "bonds": round(bonds_earned, 2),
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



def property_capitalization_from_row(row, now=None):
    if not row:
        return 0.0
    now = int(now or time.time())
    purchase_price = float(row["purchase_price"])
    days = max(0.0, (now - int(row["purchased_at"])) / 86400)
    market_value = purchase_price * (1 + REAL_ESTATE_DAILY_GROWTH * days)
    upgrades_value = 0.0
    for key, cfg in REAL_ESTATE_UPGRADES.items():
        if int(row[key] or 0) > 0:
            upgrades_value += purchase_price * float(cfg["cost_rate"])
    return round(market_value + upgrades_value, 2)


def player_capital(uid, conn=None):
    own = conn is None
    if own:
        conn = db()
    try:
        now = int(time.time())
        player = conn.execute("SELECT money FROM players WHERE user_id=?", (uid,)).fetchone()
        cash = float(player["money"] if player else 0)
        business_value = 0.0
        for row in conn.execute("SELECT * FROM businesses WHERE user_id=?", (uid,)).fetchall():
            bid = row["business_id"]
            lvl = int(row["level"] or 0)
            if bid in BUSINESSES and lvl > 0:
                business_value += business_capitalization(bid, lvl, row)
        stock_value = sum(float(r["current_price"]) * int(r["quantity"]) for r in conn.execute(
            "SELECT h.quantity,s.current_price FROM stock_holdings h JOIN stocks s ON s.id=h.stock_id WHERE h.user_id=? AND h.quantity>0", (uid,)
        ).fetchall())
        bond_value = sum(float(BONDS[r["bond_id"]]["price"]) * int(r["quantity"]) for r in conn.execute(
            "SELECT bond_id,quantity FROM bond_holdings WHERE user_id=? AND quantity>0", (uid,)
        ).fetchall() if r["bond_id"] in BONDS)
        property_value = sum(property_capitalization_from_row(r, now) for r in conn.execute(
            "SELECT * FROM real_estate_holdings WHERE user_id=?", (uid,)
        ).fetchall())
        total = cash + business_value + stock_value + bond_value + property_value
        return {
            "total": round(total,2), "cash": round(cash,2), "businesses": round(business_value,2),
            "stocks": round(stock_value,2), "bonds": round(bond_value,2), "real_estate": round(property_value,2),
        }
    finally:
        if own:
            conn.close()


def _bulk_ranked_players(limit=None):
    """Full capitalization + pending passive income using one DB snapshot (no N+1 player queries)."""
    update_stock_market()
    now = int(time.time())
    with closing(db()) as conn:
        players = [dict(r) for r in conn.execute("SELECT user_id,corp_name,username,money,last_income_sync,is_frozen,frozen_at,is_blocked,blocked_at FROM players").fetchall()]
        businesses = conn.execute("SELECT * FROM businesses WHERE level>0").fetchall()
        stocks = conn.execute("SELECT h.user_id,h.stock_id,h.quantity,s.current_price FROM stock_holdings h JOIN stocks s ON s.id=h.stock_id WHERE h.quantity>0").fetchall()
        bonds = conn.execute("SELECT user_id,bond_id,quantity FROM bond_holdings WHERE quantity>0").fetchall()
        properties = conn.execute("SELECT * FROM real_estate_holdings").fetchall()
        taxes = {int(r["user_id"]): dict(r) for r in conn.execute("SELECT user_id,unpaid,due_since FROM taxes").fetchall()}

    breakdown = {int(p["user_id"]): {"cash": float(p["money"] or 0), "businesses": 0.0, "stocks": 0.0, "bonds": 0.0, "real_estate": 0.0} for p in players}
    hourly = {uid: 0.0 for uid in breakdown}
    for r in businesses:
        uid=int(r["user_id"]); bid=r["business_id"]; lvl=int(r["level"] or 0)
        if uid in breakdown and bid in BUSINESSES:
            breakdown[uid]["businesses"] += business_capitalization(bid,lvl,r)
            hourly[uid] += BUSINESSES[bid]["base_income"] * lvl * business_upgrade_multiplier(r,bid)
    for r in stocks:
        uid=int(r["user_id"]); sid=r["stock_id"]; qty=int(r["quantity"] or 0); value=float(r["current_price"])*qty
        if uid in breakdown:
            breakdown[uid]["stocks"] += value
            hourly[uid] += value * STOCKS.get(sid,{}).get("dividend_rate",0)
    for r in bonds:
        uid=int(r["user_id"]); bid=r["bond_id"]; qty=int(r["quantity"] or 0)
        if uid in breakdown and bid in BONDS:
            value=float(BONDS[bid]["price"])*qty
            breakdown[uid]["bonds"] += value
            hourly[uid] += value * float(BONDS[bid]["yield_rate"])
    for r in properties:
        uid=int(r["user_id"]); prop=REAL_ESTATE.get(r["property_id"])
        if uid in breakdown:
            breakdown[uid]["real_estate"] += property_capitalization_from_row(r,now)
            if prop:
                hourly[uid] += float(prop["base_rent_hour"]) * property_upgrade_multiplier(r)

    global_frozen = game_is_frozen()
    rows=[]
    for p in players:
        uid=int(p["user_id"]); b=breakdown[uid]
        # Project exactly the income that sync_passive_income would credit now, without writing every player.
        if not int(p.get("is_frozen") or 0) and not int(p.get("is_blocked") or 0) and not global_frozen:
            last_sync=int(p.get("last_income_sync") or now)
            rate=float(hourly.get(uid,0))
            tax=taxes.get(uid,{})
            unpaid=float(tax.get("unpaid") or 0); due_since=int(tax.get("due_since") or 0)
            if unpaid>0 and due_since>0:
                earn_until=min(now,due_since+TAX_GRACE_SECONDS)
            elif rate>0:
                earn_until=min(now,last_sync+TAX_GRACE_SECONDS)
            else:
                earn_until=now
            seconds=max(0,earn_until-last_sync)
            b["cash"] += rate*(seconds/3600)
        total=sum(b.values())
        cap={k:round(v,2) for k,v in b.items()}
        cap["total"]=round(total,2)
        rows.append({**p,"money":cap["cash"],"capital":cap["total"],"capital_breakdown":cap})
    rows.sort(key=lambda x:(-float(x["capital"]), int(x["user_id"])))
    return rows[:limit] if limit else rows

def all_ranked_players(limit=None):
    return _bulk_ranked_players(limit)

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
            upgrades = {key: bool(int(row[key] or 0)) for key in REAL_ESTATE_UPGRADES}
            purchase_price = float(row["purchase_price"])
        else:
            current_value = prop["price"]
            rent = prop["base_rent_hour"]
            upgrades = {key: False for key in REAL_ESTATE_UPGRADES}
            purchase_price = prop["price"]
        upgrade_info = []
        for key, cfg in REAL_ESTATE_UPGRADES.items():
            upgrade_info.append({
                "id": key,
                "name": cfg["name"],
                "owned": upgrades[key],
                "cost": round(purchase_price * cfg["cost_rate"], 2),
                "income_bonus_percent": round(cfg["income_bonus"] * 100),
            })
        hourly_yield_percent = (rent / purchase_price * 100) if purchase_price > 0 else 0
        annual_yield_percent = hourly_yield_percent * 8760
        capitalization = property_capitalization_from_row(row, now) if owned else float(prop["price"])
        result.append({"id": pid, **prop, "owned": owned, "purchase_price": round(purchase_price, 2), "current_value": round(current_value, 2), "capitalization": round(capitalization,2), "sell_price": round(capitalization,2) if owned else 0, "rent_hour": round(rent, 2), "hourly_yield_percent": round(hourly_yield_percent, 3), "annual_yield_percent": round(annual_yield_percent, 2), "growth_daily_percent": round(REAL_ESTATE_DAILY_GROWTH * 100, 3), "upgrades": upgrade_info})
    return result


def snapshot(uid):
    sync_passive_income(uid)
    p = get_player(uid)
    levels = get_levels(uid)
    tax_status = get_tax_status(uid)
    update_stock_market()
    business_rate = business_hourly_income(uid)
    dividend_rate = dividend_hourly_income(uid)
    bond_rate = bond_hourly_income(uid)
    rent_rate = real_estate_hourly_income(uid)
    total_rate = business_rate + dividend_rate + bond_rate + rent_rate
    with closing(db()) as conn:
        stats = conn.execute("SELECT * FROM stats WHERE user_id=?", (uid,)).fetchone()
    businesses = []
    business_rows = get_business_rows(uid)
    for bid, business in BUSINESSES.items():
        row = business_rows.get(bid)
        level = int(row["level"] if row else 0)
        owned = level > 0
        multiplier = business_upgrade_multiplier(row, bid)
        cap = business_capitalization(bid, level, row)
        upgrades = []
        for upgrade_id, base_cfg in BUSINESS_UPGRADES.items():
            cfg = get_business_upgrade_cfg(bid, upgrade_id)
            installed = bool(row and int(row[base_cfg["column"]] or 0) > 0)
            upgrades.append({
                "id": upgrade_id,
                "name": cfg["name"],
                "owned": installed,
                "cost": business_upgrade_cost(bid, upgrade_id),
                "income_bonus_percent": round(cfg["income_bonus"] * 100),
            })
        businesses.append({
            "id": bid, **business, "level": level, "owned": owned,
            "purchase_cost": business["base_cost"],
            "next_cost": business["base_cost"],
            "current_income": round(business["base_income"] * level * multiplier, 2),
            "income_after_purchase": business["base_income"],
            "capitalization": cap,
            "sell_price": round(cap * 0.30, 2),
            "upgrades": upgrades,
        })
    capital = player_capital(uid)
    return {
        "player": dict(p),
        "capital": capital["total"],
        "capital_breakdown": capital,
        "hourly_income": 0 if tax_status["blocked"] else round(total_rate, 2),
        "gross_hourly_income": round(total_rate, 2),
        "income_breakdown": {"business": round(business_rate, 2), "dividends": round(dividend_rate, 2), "bonds": round(bond_rate, 2), "rent": round(rent_rate, 2)},
        "income_blocked": tax_status["blocked"],
        "businesses": businesses,
        "stats": dict(stats),
        "taxes": tax_status,
        "real_estate_count": int(stats["properties_bought"] or 0),
        "game": get_game_state(),
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
        "capital": player_capital(uid)["total"],
        "capital_breakdown": player_capital(uid),
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
            item = {
                "id": row["id"],
                "symbol": row["symbol"],
                "name": row["name"],
                "description": row["description"],
                "current_price": round(float(row["current_price"]), 2),
                "last_update": row["last_update"],
            }
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
    path = os.path.join(WEB_DIR, "index.html")
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    tags = [
        '<script src="/static/v20.js?v=210"></script>',
        '<script src="/static/v22_performance.js?v=221"></script>',
    ]
    for tag in tags:
        if tag not in html:
            html = html.replace("</body>", tag + "\n</body>")
    return HTMLResponse(html, headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0", "Pragma": "no-cache", "Expires": "0"})


def _html_with_optional_script(filename, script_src):
    path = os.path.join(WEB_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    tag = f'<script src="{script_src}"></script>'
    if tag not in html:
        html = html.replace("</body>", tag + "\n</body>")
    return HTMLResponse(html, headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0", "Pragma": "no-cache", "Expires": "0"})


@api.get("/seasons")
def seasons_page():
    return _html_with_optional_script("seasons.html", "/static/v22_performance.js?v=221")


@api.get("/admin")
def admin_page():
    return _html_with_optional_script("admin.html", "/static/v22_admin.js?v=221")


def auth(x_telegram_init_data, x_user_id):
    uid, username, _ = user_from_request(x_telegram_init_data, x_user_id)
    ensure_player(uid, username)
    restrictions = get_player_restrictions(uid)
    if restrictions["is_blocked"] and uid not in ADMIN_IDS:
        raise HTTPException(403, "Аккаунт заблокирован администратором Corporation")
    return uid


@api.get("/api/state")
def state(x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    return snapshot(auth(x_telegram_init_data, x_user_id))


@api.post("/api/rename")
def rename(body: NameBody, x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    uid = auth(x_telegram_init_data, x_user_id)
    name = " ".join(body.name.strip().split())[:32]
    if len(name) < 2:
        raise HTTPException(400, "Название должно содержать минимум 2 символа")
    with closing(db()) as conn:
        duplicate = conn.execute(
            "SELECT user_id FROM players WHERE user_id<>? AND lower(trim(corp_name))=lower(trim(?)) LIMIT 1",
            (uid, name),
        ).fetchone()
        if duplicate:
            raise HTTPException(409, "Компания с таким названием уже существует. Выбери другое название.")
        conn.execute("UPDATE players SET corp_name=? WHERE user_id=?", (name, uid))
        conn.commit()
    return snapshot(uid)


@api.post("/api/business/{bid}/buy")
def buy_business(bid: str, x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    uid = auth(x_telegram_init_data, x_user_id)
    if bid not in BUSINESSES:
        raise HTTPException(404, "Бизнес не найден")
    sync_passive_income(uid)
    cost = BUSINESSES[bid]["base_cost"]
    with closing(db()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute("SELECT level FROM businesses WHERE user_id=? AND business_id=?", (uid, bid)).fetchone()
        if existing and int(existing["level"] or 0) > 0:
            conn.rollback()
            raise HTTPException(400, "Бизнес уже куплен. Развивай его через прокачку.")
        player = conn.execute("SELECT money FROM players WHERE user_id=?", (uid,)).fetchone()
        if float(player["money"]) < cost:
            conn.rollback()
            raise HTTPException(400, f"Не хватает {round(cost-float(player['money']),2)} ₽")
        conn.execute("UPDATE players SET money=money-? WHERE user_id=?", (cost, uid))
        conn.execute(
            "INSERT INTO businesses(user_id,business_id,level) VALUES(?,?,1) "
            "ON CONFLICT(user_id,business_id) DO UPDATE SET level=1",
            (uid, bid),
        )
        conn.execute(
            "UPDATE stats SET total_spent=total_spent+?,companies_bought=companies_bought+1 WHERE user_id=?",
            (cost, uid),
        )
        conn.commit()
    return snapshot(uid)


@api.post("/api/business/{bid}/upgrade/{upgrade_id}")
def upgrade_business(bid: str, upgrade_id: str, x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    uid = auth(x_telegram_init_data, x_user_id)
    if bid not in BUSINESSES:
        raise HTTPException(404, "Бизнес не найден")
    if upgrade_id not in BUSINESS_UPGRADES:
        raise HTTPException(404, "Прокачка не найдена")
    sync_passive_income(uid)
    base_cfg = BUSINESS_UPGRADES[upgrade_id]
    cfg = get_business_upgrade_cfg(bid, upgrade_id)
    cost = business_upgrade_cost(bid, upgrade_id)
    with closing(db()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM businesses WHERE user_id=? AND business_id=?", (uid, bid)).fetchone()
        if not row or int(row["level"] or 0) <= 0:
            conn.rollback()
            raise HTTPException(400, "Сначала купи этот бизнес")
        if int(row[base_cfg["column"]] or 0) > 0:
            conn.rollback()
            raise HTTPException(400, "Эта прокачка уже установлена")
        player = conn.execute("SELECT money FROM players WHERE user_id=?", (uid,)).fetchone()
        if float(player["money"]) < cost:
            conn.rollback()
            raise HTTPException(400, f"Недостаточно денег. Нужно {cost:.2f} ₽")
        conn.execute("UPDATE players SET money=money-? WHERE user_id=?", (cost, uid))
        conn.execute(f"UPDATE businesses SET {base_cfg['column']}=1 WHERE user_id=? AND business_id=?", (uid, bid))
        conn.execute("UPDATE stats SET total_spent=total_spent+? WHERE user_id=?", (cost, uid))
        conn.commit()
    return snapshot(uid)


@api.post("/api/business/{bid}/sell")
def sell_business(bid: str, x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    uid = auth(x_telegram_init_data, x_user_id)
    if bid not in BUSINESSES:
        raise HTTPException(404, "Бизнес не найден")
    sync_passive_income(uid)
    with closing(db()) as read_conn:
        row = read_conn.execute("SELECT * FROM businesses WHERE user_id=? AND business_id=?", (uid, bid)).fetchone()
    level = int(row["level"] if row else 0)
    if level <= 0:
        raise HTTPException(400, "У тебя нет этого бизнеса")
    cap = business_capitalization(bid, level, row)
    price = round(cap * 0.30, 2)
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
    uid = auth(x_telegram_init_data, x_user_id); sync_passive_income(uid); update_stock_market()
    player = get_player(uid)
    with closing(db()) as conn:
        stats = conn.execute("SELECT * FROM stats WHERE user_id=?", (uid,)).fetchone()
    cap = player_capital(uid)
    return {"player": {"corp_name": player["corp_name"], "money": player["money"], "created_at": player["created_at"]}, "capital": cap["total"], "capital_breakdown": cap, "hourly_income": snapshot(uid)["hourly_income"], "total_spent": stats["total_spent"], "total_earned": stats["total_earned"], "companies_bought": stats["companies_bought"], "properties_bought": stats["properties_bought"], "daily_profit": get_daily_profit(uid)}


@api.get("/api/rating")
def rating(x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    auth(x_telegram_init_data, x_user_id)
    return all_ranked_players(20)


@api.get("/api/player/{player_id}")
def player_profile(player_id: int, x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    auth(x_telegram_init_data, x_user_id); return public_profile(player_id)


@api.get("/api/market-news")
def market_news(x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    auth(x_telegram_init_data, x_user_id)
    return get_market_news()


@api.get("/api/stocks")
def stocks(x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    uid = auth(x_telegram_init_data, x_user_id); sync_passive_income(uid); return get_stocks()


@api.get("/api/stocks/{stock_id}")
def stock_detail(stock_id: str, x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    uid = auth(x_telegram_init_data, x_user_id); sync_passive_income(uid); update_stock_market()
    with closing(db()) as conn:
        row = conn.execute("SELECT * FROM stocks WHERE id=?", (stock_id,)).fetchone()
        if not row: raise HTTPException(404, "Акция не найдена")
        item = {
            "id": row["id"], "symbol": row["symbol"], "name": row["name"],
            "description": row["description"], "current_price": round(float(row["current_price"]), 2),
            "last_update": row["last_update"], "change_percent": stock_change_percent(conn, stock_id),
        }
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


def get_bonds(uid):
    with closing(db()) as conn:
        rows = {r["bond_id"]: int(r["quantity"]) for r in conn.execute(
            "SELECT bond_id,quantity FROM bond_holdings WHERE user_id=? AND quantity>0", (uid,)
        ).fetchall()}
    result = []
    for bond_id, bond in BONDS.items():
        qty = rows.get(bond_id, 0)
        value = bond["price"] * qty
        result.append({
            "id": bond_id, "symbol": bond["symbol"], "name": bond["name"],
            "description": bond["description"], "price": bond["price"],
            "yield_rate_percent": round(bond["yield_rate"] * 100, 2),
            "quantity": qty, "current_value": round(value, 2),
            "income_hour": round(value * bond["yield_rate"], 2),
        })
    return result


@api.get("/api/bonds")
def bonds(x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    uid = auth(x_telegram_init_data, x_user_id); sync_passive_income(uid); return {"bonds": get_bonds(uid)}


@api.post("/api/bonds/{bond_id}/buy")
def buy_bond(bond_id: str, body: QuantityBody, x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    if body.quantity <= 0: raise HTTPException(400, "Количество должно быть больше нуля")
    uid = auth(x_telegram_init_data, x_user_id); sync_passive_income(uid)
    bond = BONDS.get(bond_id)
    if not bond: raise HTTPException(404, "Облигация не найдена")
    total = float(bond["price"]) * body.quantity
    with closing(db()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        player = conn.execute("SELECT money FROM players WHERE user_id=?", (uid,)).fetchone()
        if float(player["money"]) < total:
            conn.rollback(); raise HTTPException(400, f"Недостаточно денег. Нужно {total:.2f} ₽")
        conn.execute("UPDATE players SET money=money-? WHERE user_id=?", (total, uid))
        conn.execute(
            "INSERT INTO bond_holdings(user_id,bond_id,quantity) VALUES(?,?,?) ON CONFLICT(user_id,bond_id) DO UPDATE SET quantity=quantity+excluded.quantity",
            (uid, bond_id, body.quantity),
        )
        conn.commit()
    return {"quantity": body.quantity, "total_cost": round(total, 2), "state": snapshot(uid), "bonds": get_bonds(uid)}


@api.post("/api/bonds/{bond_id}/sell")
def sell_bond(bond_id: str, body: QuantityBody, x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    if body.quantity <= 0: raise HTTPException(400, "Количество должно быть больше нуля")
    uid = auth(x_telegram_init_data, x_user_id); sync_passive_income(uid)
    bond = BONDS.get(bond_id)
    if not bond: raise HTTPException(404, "Облигация не найдена")
    total = float(bond["price"]) * body.quantity
    with closing(db()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT quantity FROM bond_holdings WHERE user_id=? AND bond_id=?", (uid, bond_id)).fetchone()
        if not row or int(row["quantity"]) < body.quantity:
            conn.rollback(); raise HTTPException(400, "Недостаточно облигаций для продажи")
        remaining = int(row["quantity"]) - body.quantity
        if remaining == 0:
            conn.execute("DELETE FROM bond_holdings WHERE user_id=? AND bond_id=?", (uid, bond_id))
        else:
            conn.execute("UPDATE bond_holdings SET quantity=? WHERE user_id=? AND bond_id=?", (remaining, uid, bond_id))
        conn.execute("UPDATE players SET money=money+? WHERE user_id=?", (total, uid))
        conn.commit()
    return {"quantity": body.quantity, "total_income": round(total, 2), "state": snapshot(uid), "bonds": get_bonds(uid)}


@api.get("/api/real-estate")
def real_estate(x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    uid = auth(x_telegram_init_data, x_user_id); sync_passive_income(uid); return {"properties": property_payload(uid), "daily_growth_percent": round(REAL_ESTATE_DAILY_GROWTH * 100, 3)}


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
    if upgrade_id not in REAL_ESTATE_UPGRADES: raise HTTPException(404, "Улучшение не найдено")
    with closing(db()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM real_estate_holdings WHERE user_id=? AND property_id=?", (uid, property_id)).fetchone()
        if not row: conn.rollback(); raise HTTPException(400, "Сначала купи эту недвижимость")
        if int(row[upgrade_id] or 0) > 0: conn.rollback(); raise HTTPException(400, "Это улучшение уже установлено")
        cost = float(row["purchase_price"]) * REAL_ESTATE_UPGRADES[upgrade_id]["cost_rate"]
        player = conn.execute("SELECT money FROM players WHERE user_id=?", (uid,)).fetchone()
        if float(player["money"]) < cost: conn.rollback(); raise HTTPException(400, f"Недостаточно денег. Нужно {cost:.2f} ₽")
        conn.execute("UPDATE players SET money=money-? WHERE user_id=?", (cost, uid))
        conn.execute(f"UPDATE real_estate_holdings SET {upgrade_id}=1 WHERE user_id=? AND property_id=?", (uid, property_id))
        conn.execute("UPDATE stats SET total_spent=total_spent+? WHERE user_id=?", (cost, uid))
        conn.commit()
    return {"state": snapshot(uid), "properties": property_payload(uid)}


@api.post("/api/real-estate/{property_id}/sell")
def sell_property(property_id: str, x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    uid = auth(x_telegram_init_data, x_user_id); sync_passive_income(uid)
    if property_id not in REAL_ESTATE:
        raise HTTPException(404, "Объект не найден")
    now = int(time.time())
    with closing(db()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM real_estate_holdings WHERE user_id=? AND property_id=?", (uid, property_id)).fetchone()
        if not row:
            conn.rollback(); raise HTTPException(400, "У тебя нет этой недвижимости")
        price = property_capitalization_from_row(row, now)
        conn.execute("DELETE FROM real_estate_holdings WHERE user_id=? AND property_id=?", (uid, property_id))
        conn.execute("UPDATE players SET money=money+? WHERE user_id=?", (price, uid))
        conn.commit()
    return {"sell_price": round(price,2), "state": snapshot(uid), "properties": property_payload(uid)}


def _season_public_row(row, viewer_id, is_admin):
    item = dict(row)
    if not is_admin and int(item.get("user_id") or 0) != int(viewer_id):
        item.pop("user_id", None)
        item.pop("username", None)
    return item


@api.get("/api/seasons")
def public_seasons(x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    viewer_id = auth(x_telegram_init_data, x_user_id)
    viewer_is_admin = viewer_id in ADMIN_IDS
    state = get_game_state()
    current_id = int(state["current_season"])
    current = [_season_public_row(r, viewer_id, viewer_is_admin) for r in all_ranked_players(20)]
    with closing(db()) as conn:
        meta = {int(r["season_id"]): dict(r) for r in conn.execute("SELECT * FROM seasons ORDER BY season_id DESC").fetchall()}
        rows = conn.execute("SELECT * FROM season_results ORDER BY season_id DESC,place ASC").fetchall()
    previous = {}
    for r in rows:
        sid = int(r["season_id"])
        previous.setdefault(str(sid), []).append(_season_public_row(r, viewer_id, viewer_is_admin))
    return {
        "current": {"season_id": current_id, "name": meta.get(current_id, {}).get("name", f"Сезон №{current_id}"), "leaders": current, "started_at": state.get("season_started_at",0), "ended_at": state.get("season_ended_at",0)},
        "previous": previous,
        "meta": {str(k):v for k,v in meta.items()},
    }

# === CORPORATION ADMIN PANEL V19 ============================================
class AdminFreezeBody(BaseModel):
    frozen: bool
    message: str = ""


class AdminConfirmBody(BaseModel):
    confirmation: str


class AdminSeasonNameBody(BaseModel):
    name: str


class AdminPlayerFlagBody(BaseModel):
    enabled: bool


class AdminPlayerDeleteBody(BaseModel):
    confirmation: str


@api.get("/api/admin/overview")
def admin_overview(x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    admin_id = require_admin(x_telegram_init_data, x_user_id)
    now = int(time.time())
    state = get_game_state()
    capital_rows = all_ranked_players()
    with closing(db()) as conn:
        players = int(conn.execute("SELECT COUNT(*) c FROM players").fetchone()["c"])
        active_today = int(conn.execute("SELECT COUNT(*) c FROM players WHERE last_income_sync>=?", (now-86400,)).fetchone()["c"])
        economy = sum(float(r["capital"]) for r in capital_rows)
        avg_money = economy / players if players else 0.0
        businesses_count = int(conn.execute("SELECT COUNT(*) c FROM businesses WHERE level>0").fetchone()["c"])
        properties_count = int(conn.execute("SELECT COUNT(*) c FROM real_estate_holdings").fetchone()["c"])
        stocks_count = int(conn.execute("SELECT COALESCE(SUM(quantity),0) c FROM stock_holdings").fetchone()["c"] or 0)
        bonds_count = int(conn.execute("SELECT COALESCE(SUM(quantity),0) c FROM bond_holdings").fetchone()["c"] or 0)
        leader = capital_rows[0] if capital_rows else None
        popular_business = conn.execute("SELECT business_id,COUNT(*) c FROM businesses WHERE level>0 GROUP BY business_id ORDER BY c DESC LIMIT 1").fetchone()
        popular_stock = conn.execute("SELECT stock_id,SUM(quantity) q FROM stock_holdings WHERE quantity>0 GROUP BY stock_id ORDER BY q DESC LIMIT 1").fetchone()
        logs = [dict(r) for r in conn.execute("SELECT * FROM admin_logs ORDER BY id DESC LIMIT 20").fetchall()]
    backup_dir = os.path.join(os.path.dirname(os.path.abspath(DB_PATH)), "admin_backups")
    last_backup = None
    if os.path.isdir(backup_dir):
        files = [os.path.join(backup_dir, x) for x in os.listdir(backup_dir) if x.endswith('.db')]
        if files:
            f = max(files, key=os.path.getmtime)
            last_backup = {"name": os.path.basename(f), "created_at": int(os.path.getmtime(f)), "size": os.path.getsize(f)}
    return {
        "admin_id": admin_id,
        "server_time": now,
        "game": state,
        "stats": {"players": players, "active_today": active_today, "money_in_economy": round(economy,2), "avg_money": round(avg_money,2), "businesses": businesses_count, "properties": properties_count, "stocks": stocks_count, "bonds": bonds_count},
        "leader": dict(leader) if leader else None,
        "popular_business": ({"id": popular_business["business_id"], "name": BUSINESSES.get(popular_business["business_id"], {}).get("name", popular_business["business_id"]), "count": int(popular_business["c"])} if popular_business else None),
        "popular_stock": ({"id": popular_stock["stock_id"], "name": STOCKS.get(popular_stock["stock_id"], {}).get("name", popular_stock["stock_id"]), "quantity": int(popular_stock["q"] or 0)} if popular_stock else None),
        "last_backup": last_backup,
        "logs": logs,
        "version": "v22.0",
    }


@api.get("/api/admin/players")
def admin_players(q: str = "", limit: int = 100, x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    require_admin(x_telegram_init_data, x_user_id)
    limit = max(1, min(int(limit), 250))
    q = (q or "").strip().lower()

    # Админский рейтинг использует ровно ту же модель полной капитализации,
    # что и игровой рейтинг: деньги + 100% бизнеса + акции по текущей цене +
    # облигации + 100% текущей капитализации недвижимости с улучшениями.
    ranked = all_ranked_players()
    if q:
        ranked = [
            row for row in ranked
            if q in str(row.get("user_id", "")).lower()
            or q in str(row.get("username", "") or "").lower()
            or q in str(row.get("corp_name", "") or "").lower()
        ]
    return ranked[:limit]


@api.get("/api/admin/player/{player_id}")
def admin_player_detail(player_id: int, x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    require_admin(x_telegram_init_data, x_user_id)
    if not get_player(player_id):
        raise HTTPException(404, "Игрок не найден")
    sync_passive_income(player_id)
    snap = snapshot(player_id)
    with closing(db()) as conn:
        stock_rows = [dict(r) for r in conn.execute("SELECT stock_id,quantity,avg_buy_price FROM stock_holdings WHERE user_id=? AND quantity>0", (player_id,)).fetchall()]
        bond_rows = [dict(r) for r in conn.execute("SELECT bond_id,quantity FROM bond_holdings WHERE user_id=? AND quantity>0", (player_id,)).fetchall()]
        properties = [dict(r) for r in conn.execute("SELECT property_id,purchase_price,purchased_at FROM real_estate_holdings WHERE user_id=?", (player_id,)).fetchall()]
    return {"state": snap, "stocks": stock_rows, "bonds": bond_rows, "properties": properties}


@api.post("/api/admin/player/{player_id}/freeze")
def admin_player_freeze(player_id: int, body: AdminPlayerFlagBody, x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    admin_id = require_admin(x_telegram_init_data, x_user_id)
    if player_id in ADMIN_IDS:
        raise HTTPException(400, "Администратора нельзя заморозить через панель")
    if not get_player(player_id):
        raise HTTPException(404, "Игрок не найден")
    now = int(time.time())
    if body.enabled:
        sync_passive_income(player_id)
        with closing(db()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("UPDATE players SET is_frozen=1,frozen_at=? WHERE user_id=?", (now, player_id))
            admin_log(admin_id, "freeze_player", f"player={player_id}", conn)
            conn.commit()
    else:
        with closing(db()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("UPDATE players SET is_frozen=0,frozen_at=0,last_income_sync=? WHERE user_id=?", (now, player_id))
            admin_log(admin_id, "unfreeze_player", f"player={player_id}", conn)
            conn.commit()
    return {"ok": True, "player_id": player_id, **get_player_restrictions(player_id)}


@api.post("/api/admin/player/{player_id}/block")
def admin_player_block(player_id: int, body: AdminPlayerFlagBody, x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    admin_id = require_admin(x_telegram_init_data, x_user_id)
    if player_id in ADMIN_IDS:
        raise HTTPException(400, "Администратора нельзя заблокировать через панель")
    if not get_player(player_id):
        raise HTTPException(404, "Игрок не найден")
    now = int(time.time())
    if body.enabled:
        sync_passive_income(player_id)
        with closing(db()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("UPDATE players SET is_blocked=1,blocked_at=?,is_frozen=1,frozen_at=? WHERE user_id=?", (now, now, player_id))
            admin_log(admin_id, "block_player", f"player={player_id}", conn)
            conn.commit()
    else:
        with closing(db()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("UPDATE players SET is_blocked=0,blocked_at=0,is_frozen=0,frozen_at=0,last_income_sync=? WHERE user_id=?", (now, player_id))
            admin_log(admin_id, "unblock_player", f"player={player_id}", conn)
            conn.commit()
    return {"ok": True, "player_id": player_id, **get_player_restrictions(player_id)}


@api.delete("/api/admin/player/{player_id}")
def admin_delete_player(player_id: int, body: AdminPlayerDeleteBody, x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    admin_id = require_admin(x_telegram_init_data, x_user_id)
    if player_id in ADMIN_IDS:
        raise HTTPException(400, "Администратора нельзя удалить через панель")
    if body.confirmation.strip().upper() != "DELETE PLAYER":
        raise HTTPException(400, "Для удаления введи DELETE PLAYER")
    player = get_player(player_id)
    if not player:
        raise HTTPException(404, "Игрок не найден")
    backup_path = create_database_backup(f"before_delete_{player_id}")
    with closing(db()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        for table in ("businesses", "daily_profit", "stock_holdings", "bond_holdings", "taxes", "real_estate_holdings", "stats", "season_results"):
            conn.execute(f"DELETE FROM {table} WHERE user_id=?", (player_id,))
        conn.execute("DELETE FROM players WHERE user_id=?", (player_id,))
        admin_log(admin_id, "delete_player", f"player={player_id}; backup={os.path.basename(backup_path)}", conn)
        conn.commit()
    return {"ok": True, "deleted_player_id": player_id, "backup": os.path.basename(backup_path)}


@api.get("/api/admin/seasons")
def admin_seasons(x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    require_admin(x_telegram_init_data, x_user_id)
    with closing(db()) as conn:
        rows = conn.execute("SELECT * FROM season_results ORDER BY season_id DESC,place ASC").fetchall()
        meta = {str(r["season_id"]): dict(r) for r in conn.execute("SELECT * FROM seasons ORDER BY season_id DESC").fetchall()}
    grouped = {}
    for r in rows:
        grouped.setdefault(str(r["season_id"]), []).append(dict(r))
    return {"current": get_game_state(), "results": grouped, "meta": meta}



@api.post("/api/admin/season/{season_id}/rename")
def admin_rename_season(season_id: int, body: AdminSeasonNameBody, x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    admin_id = require_admin(x_telegram_init_data, x_user_id)
    name = " ".join(body.name.strip().split())[:50]
    if len(name) < 2:
        raise HTTPException(400, "Название сезона слишком короткое")
    with closing(db()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        exists = conn.execute("SELECT 1 FROM seasons WHERE season_id=?", (season_id,)).fetchone()
        if not exists:
            conn.rollback(); raise HTTPException(404, "Сезон не найден")
        conn.execute("UPDATE seasons SET name=? WHERE season_id=?", (name, season_id))
        admin_log(admin_id, "rename_season", f"season={season_id}; name={name}", conn)
        conn.commit()
    return {"ok": True, "season_id": season_id, "name": name}

@api.post("/api/admin/freeze")
def admin_freeze(body: AdminFreezeBody, x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    admin_id = require_admin(x_telegram_init_data, x_user_id)
    now = int(time.time())
    current = get_game_state()
    desired = bool(body.frozen)
    if desired == bool(current["is_frozen"]):
        return get_game_state()

    if desired:
        with closing(db()) as conn:
            ids = [int(r["user_id"]) for r in conn.execute("SELECT user_id FROM players").fetchall()]
        for uid in ids:
            sync_passive_income(uid)
        update_stock_market()
        with closing(db()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("UPDATE game_state SET is_frozen=1,frozen_at=?,maintenance_message=? WHERE id=1", (now, body.message.strip()[:500]))
            admin_log(admin_id, "freeze_game", body.message, conn)
            conn.commit()
    else:
        frozen_at=int(current.get("frozen_at") or now)
        pause=max(0,now-frozen_at)
        with closing(db()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("UPDATE players SET last_income_sync=?", (now,))
            conn.execute("UPDATE stocks SET last_update=?", (now,))
            if pause>0:
                conn.execute("UPDATE market_news_state SET next_news_at=next_news_at+? WHERE id=1", (pause,))
                conn.execute("UPDATE market_news SET impact_at=impact_at+? WHERE applied_at=0", (pause,))
            conn.execute("UPDATE game_state SET is_frozen=0,frozen_at=0,maintenance_message='' WHERE id=1")
            admin_log(admin_id, "unfreeze_game", "", conn)
            conn.commit()
    return get_game_state()


@api.post("/api/admin/end-season")
def admin_end_season(body: AdminConfirmBody, x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    admin_id = require_admin(x_telegram_init_data, x_user_id)
    if body.confirmation.strip().upper() != "END SEASON":
        raise HTTPException(400, "Для подтверждения введи END SEASON")
    leaders = all_ranked_players()
    now = int(time.time())
    with closing(db()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        season = int(conn.execute("SELECT current_season FROM game_state WHERE id=1").fetchone()["current_season"])
        conn.execute("DELETE FROM season_results WHERE season_id=?", (season,))
        for place, r in enumerate(leaders, start=1):
            conn.execute("INSERT INTO season_results(season_id,place,user_id,username,corp_name,money,capital,captured_at) VALUES(?,?,?,?,?,?,?,?)", (season, place, r["user_id"], r["username"], r["corp_name"], r["money"], r["capital"], now))
        conn.execute("UPDATE seasons SET ended_at=? WHERE season_id=?", (now, season))
        conn.execute("UPDATE game_state SET is_frozen=1,frozen_at=?,season_ended_at=?,maintenance_message='Сезон завершён. Итоги зафиксированы.' WHERE id=1", (now, now))
        admin_log(admin_id, "end_season", f"season={season}; players={len(leaders)}", conn)
        conn.commit()
    return {"season": season, "players": len(leaders), "game": get_game_state()}


@api.post("/api/admin/reset-progress")
def admin_reset_progress(body: AdminConfirmBody, x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    admin_id = require_admin(x_telegram_init_data, x_user_id)
    if body.confirmation.strip().upper() != "RESET SEASON":
        raise HTTPException(400, "Для подтверждения введи RESET SEASON")
    backup_path = create_database_backup("before_reset")
    now = int(time.time())
    with closing(db()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        reset_all_progress_conn(conn, now)
        conn.execute("UPDATE game_state SET is_frozen=1,frozen_at=?,maintenance_message='Прогресс игроков сброшен. Ожидается запуск нового сезона.' WHERE id=1", (now,))
        admin_log(admin_id, "reset_all_progress", os.path.basename(backup_path), conn)
        conn.commit()
    return {"ok": True, "backup": os.path.basename(backup_path), "game": get_game_state()}


@api.post("/api/admin/new-season")
def admin_new_season(body: AdminConfirmBody, x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    admin_id = require_admin(x_telegram_init_data, x_user_id)
    if body.confirmation.strip().upper() != "NEW SEASON":
        raise HTTPException(400, "Для подтверждения введи NEW SEASON")
    backup_path = create_database_backup("before_new_season")
    now = int(time.time())
    with closing(db()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        current = int(conn.execute("SELECT current_season FROM game_state WHERE id=1").fetchone()["current_season"])
        reset_all_progress_conn(conn, now)
        next_season = current + 1
        conn.execute("INSERT OR REPLACE INTO seasons(season_id,name,started_at,ended_at) VALUES(?,?,?,0)", (next_season, f"Сезон №{next_season}", now))
        conn.execute("UPDATE game_state SET current_season=?,season_started_at=?,season_ended_at=0,is_frozen=0,frozen_at=0,maintenance_message='' WHERE id=1", (next_season, now))
        admin_log(admin_id, "start_new_season", f"season={next_season}; backup={os.path.basename(backup_path)}", conn)
        conn.commit()
    return {"ok": True, "season": next_season, "backup": os.path.basename(backup_path), "game": get_game_state()}


@api.post("/api/admin/backup")
def admin_backup(x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    admin_id = require_admin(x_telegram_init_data, x_user_id)
    path = create_database_backup("manual")
    admin_log(admin_id, "manual_backup", os.path.basename(path))
    return {"ok": True, "backup": os.path.basename(path), "size": os.path.getsize(path)}
# ============================================================================



# Create the first v21 news item immediately, then keep the scheduler alive.
process_market_news()
start_market_news_worker()

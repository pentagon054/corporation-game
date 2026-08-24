# Построй свою корпорацию — Telegram Mini App

## Что внутри
- `app.py` — FastAPI backend + Telegram bot
- `web/index.html` — интерфейс
- `web/style.css` — стили
- `web/app.js` — логика интерфейса
- SQLite создаётся автоматически при запуске

## Быстрый запуск для разработки

1. Установите Python 3.10+.
2. Откройте терминал в этой папке.
3. Установите зависимости:
   `pip install -r requirements.txt`
4. Для теста в браузере:
   - Windows PowerShell:
     `$env:ALLOW_DEV_AUTH="1"`
   - затем:
     `uvicorn app:api --host 0.0.0.0 --port 8000`
5. Откройте `http://127.0.0.1:8000`

## Запуск в Telegram

### 1. Создайте бота
В @BotFather используйте `/newbot` и получите токен.

### 2. Получите HTTPS URL
Для разработки можно использовать Cloudflare Tunnel:
`cloudflared tunnel --url http://localhost:8000`

### 3. Запустите API
Windows PowerShell:
`$env:BOT_TOKEN="ВАШ_ТОКЕН"`
`$env:WEBAPP_URL="https://ВАШ-АДРЕС.trycloudflare.com"`
`uvicorn app:api --host 0.0.0.0 --port 8000`

### 4. Запустите Telegram-бота
Во втором терминале:
`$env:BOT_TOKEN="ВАШ_ТОКЕН"`
`$env:WEBAPP_URL="https://ВАШ-АДРЕС.trycloudflare.com"`
`python app.py`

### 5. Откройте бота и нажмите /start

## Важно
Для настоящего запуска API проверяет Telegram initData.
Никогда не оставляйте `ALLOW_DEV_AUTH=1` на публичном сервере.
Токен бота нельзя публиковать.

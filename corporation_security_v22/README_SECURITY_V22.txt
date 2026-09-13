CORPORATION — SECURITY UPDATE v22
=================================

Что исправляет
--------------
1. Production bypass через X-User-Id закрыт. На Railway этот заголовок явно отвергается.
2. Все /api/* проходят централизованную проверку Telegram Mini App initData.
3. HMAC-SHA256 Telegram-подпись проверяется через BOT_TOKEN.
4. Проверяется auth_date; по умолчанию initData действует максимум 1 час.
5. Удалён production fallback фронтенда на DEV_ID / X-User-Id.
6. ALLOW_DEV_AUTH никогда не действует на Railway, даже если переменная случайно осталась =1.
7. Добавлены ограничения размера запросов и application-level rate limit.
8. Добавлены CSP/HSTS/nosniff/referrer-policy/permissions-policy и no-store для API.
9. admin/overview больше не обязан раскрывать имя файла резервной копии.
10. .env, БД, backups и runtime-файлы исключаются из Git.
11. Список ADMIN_IDS больше не должен печататься целиком в логах бота.

Установка
---------
1. Распакуй содержимое ZIP В КОРЕНЬ проекта Corporation, где лежат app.py, bot.py и папка web.
2. Запусти:
   .\APPLY_SECURITY_UPDATE.bat
3. Скрипт сам создаст security_backup_ДАТА_ВРЕМЯ и изменит существующие файлы.
4. Локальный DEV fallback сохранён ТОЛЬКО для localhost/127.0.0.1 и только при ALLOW_DEV_AUTH=1.
   На Railway он физически отключён кодом.

Railway variables
-----------------
Обязательно:
BOT_TOKEN=<токен Telegram бота>
ADMIN_IDS=<id1,id2,...>

Рекомендуется удалить:
ALLOW_DEV_AUTH

Опционально:
TELEGRAM_AUTH_MAX_AGE=3600
MAX_API_BODY_BYTES=65536

Важно
-----
Не задавай X-Admin-Secret во фронтенде/JS: такой секрет виден любому пользователю и не является
вторым фактором. Админские права должны выдаваться только после успешной проверки подписанного
Telegram initData и проверки user.id по ADMIN_IDS.

Нельзя гарантировать, что любой интернет-сервис "невозможно взломать". Этот патч закрывает
обнаруженную критическую дыру и заметно усиливает типовые уровни защиты приложения, но для
production также полезны Railway/WAF rate limiting, регулярные обновления зависимостей, резервные
копии и периодический security audit.

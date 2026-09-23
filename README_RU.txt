CORPORATION — PRODUCTION GAME READ LOAD TEST v4
===============================================

Проверяет конкурентную READ-нагрузку на SQLite на текущем production.
Никаких INSERT/UPDATE/DELETE нагрузочный endpoint не делает.

Лестница:
10 -> 25 -> 50 -> 100 -> 200 -> 300 -> 500 -> 750 -> 1000 VU.
На 1000 VU есть дополнительное удержание 30 секунд.

Установка временного endpoint:
Set-ExecutionPolicy -Scope Process Bypass
.\APPLY_LOAD_TEST_V4.ps1

После этого:
git add app.py
git commit -m "Add temporary read-only load test endpoint v4"
git push

Railway -> corporation-game -> Variables:
добавить LOAD_TEST_TOKEN.

Случайный token в PowerShell:
[guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N")

Дождаться успешного deploy.

Запуск:
.\RUN_GAME_READ_V4.ps1

Вставить LOAD_TEST_TOKEN.
Подтверждение:
ATTACK

Во время теста:
Railway -> corporation-game -> Metrics

После теста прислать:
results_v4\game_read_summary.json
results_v4\game_read_console.txt
+ скрин Metrics.

Удаление временного endpoint:
.\REMOVE_LOAD_TEST_V4.ps1

Затем:
git add app.py
git commit -m "Remove temporary load test endpoint v4"
git push

После успешного deploy удалить LOAD_TEST_TOKEN из Railway Variables.

Автостоп:
- >=3% ошибок game_read;
- p95 game_read >=2.5 секунды.

ВАЖНО:
Это read-only тест, но 500–1000 VU могут временно замедлить production.
Лучше запускать, когда реальных игроков мало.

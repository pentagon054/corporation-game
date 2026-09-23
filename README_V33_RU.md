# Corporation v33 — предрелиз: рефералы + игровые окна

Обновление собрано поверх текущей ветки Corporation v32.4.

## Что добавлено

- Реферальная программа по deep-link `https://t.me/CorporationGame_bot?start=ref_TELEGRAM_ID`.
- Реферал закрепляется за пригласившим один раз и до конца текущего сезона.
- Нельзя пригласить самого себя; повторно перепривязать Telegram ID к другому игроку нельзя.
- Условия бонуса: капитализация приглашённого не ниже **200 000 ₽** и минимум **5 активных дней** в текущем сезоне.
- После выполнения обоих условий приглашённый получает **10 000 ₽**, пригласивший — **20 000 ₽** внутриигровых денег.
- Выплата атомарная и идемпотентная: повторный запрос не выдаёт бонус второй раз.
- В рейтинге появилась отдельная карточка реферальной программы с личной ссылкой, статистикой и карточками друзей.
- В карточке друга отдельно показываются капитализация, остаток до 200 000 ₽ и прогресс активных дней.
- Нативные `alert`, `confirm` и `prompt` заменены на модальные окна в дизайне Corporation, включая админ-панель.

## Установка

Распакуй ZIP в любую временную папку. Затем в PowerShell из папки проекта Corporation выполни:

```powershell
$projectPath = (Get-Location).Path
$update = "C:\ПУТЬ\К\РАСПАКОВАННОМУ\Corporation_v33_PRERELEASE_REFERRALS_DIALOGS\APPLY_UPDATE_V33.ps1"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $update -ProjectPath $projectPath
```

Установщик сначала создаёт рядом с проектом папку вида `corporation-game_before_v33_YYYYMMDD_HHMMSS_mmm` и складывает туда заменяемые файлы. Локальная `corporation.db`, если она есть, также копируется в backup, но никогда не перезаписывается обновлением.

## Проверка перед отправкой на Railway

```powershell
python -m py_compile .\app.py .\bot.py .\tests\test_referrals_v33.py
node --check .\web\corporation_dialogs_v33.js
node --check .\web\referrals_v33.js
python .\tests\test_referrals_v33.py
```

Ожидаемый финал теста: `V33 referral tests: OK`.

## Git / Railway

```powershell
git status
git add app.py bot.py web tests/test_referrals_v33.py README_V33_RU.md
git commit -m "Add v33 referral program and Corporation dialogs"
git push
```

Railway задеплоит изменения из репозитория как обычно. Существующие `BOT_TOKEN`, `REQUIRED_CHANNEL`, `WEBAPP_URL`, `ADMIN_IDS` и Volume/`DB_PATH` не меняй.

Необязательно можно добавить переменную:

```text
REFERRAL_BOT_USERNAME=CorporationGame_bot
```

Если она не указана, используется `CorporationGame_bot`.

## Важное про данные игроков

Новые таблицы (`referrals`, `referral_active_days`, `referral_reward_events`) создаются через `CREATE TABLE IF NOT EXISTS`. Существующие таблицы прогресса и деньги игроков не сбрасываются. В новый сезон привязки и активные дни автоматически отделяются по `season_id`.


## v33.2 hotfix
- исправлен мобильный layout реферальной страницы;
- админ-панель: для удаления / сезонных действий больше не нужен ручной ввод фраз, достаточно подтвердить действие;
- обновлён cache-bust фронтенда до 332.


## v33.3
- реферальная программа теперь имеет глобальный вход и работает независимо от отрисовки рейтинга;
- на любой ширине виден золотой баннер после блока баланса;
- на широком ПК дополнительно показывается боковая кнопка «Рефералы +20 000 ₽»;
- cache-bust обновлён до 333.


## v33.4 desktop referrals + dialogs
- Реферальная кнопка встроена прямо в index.html и всегда видна на ПК/мобильных.
- На ПК добавлена заметная золотая плавающая кнопка +20 000 ₽.
- Вся цепочка JS получила cache generation 334, включая v29.js и subscription gate.
- Удалены оставшиеся native alert/confirm/prompt/showConfirm/showAlert/showPopup вызовы.
- Старый modal() игры маршрутизируется в единый Corporation dialog.

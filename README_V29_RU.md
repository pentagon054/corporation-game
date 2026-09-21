# Corporation v29 — Business Slots, Sliders & Rating Polish

Обновление собрано поверх `Corporation_v28_MULTI_BUSINESS_SMOOTH`.

## Что изменено

- Базовый лимит: **10 одновременно открытых бизнесов**.
- Лимит можно увеличивать по **+1 слоту**, но не чаще **одного раза в 60 минут**.
- Стоимость расширения: первый дополнительный слот — **100 000 ₽**, далее цена умножается на **1,5**: 150 000 ₽, 225 000 ₽ и т.д.
- Проверка лимита выполняется на сервере и внутри транзакции, поэтому параллельными запросами обойти её нельзя.
- Если в существующей базе до обновления у игрока уже было больше 10 бизнесов, они не удаляются: фактическое число сохраняется как его текущий лимит.
- В покупке и продаже облигаций добавлен ползунок количества с моментальным пересчётом суммы.
- В покупке автомобилей в бизнесах **Такси** и **Логистика** добавлен такой же ползунок количества.
- Вкладка **Рейтинг** визуально переработана: более цельные карточки, аккуратные места, отдельное оформление топ-3 и своей позиции, устранён эффект «обрубленной» правой части.
- Нижняя вкладка **«Бизнес»** переименована в **«Главная»**.

## Проверки

Успешно пройдены новые тесты v29, тесты мульти-бизнесов v28 и основной аудит API. `app.py`, `bot.py`, `market_v24.py` и `security_v24.py` проходят Python compile-check; `web/v29.js` проходит `node --check`.

Автоматический Playwright-прогон браузера в среде сборки не выполнялся, потому что пакет Playwright там не установлен. Серверная логика и синтаксис клиентского JavaScript проверены отдельно.

## Установка поверх текущего проекта

Скачай ZIP в папку Downloads, открой PowerShell и выполни:

```powershell
$projectPath = Read-Host 'Полный путь к папке corporation-game'
$archive = Join-Path $env:USERPROFILE 'Downloads\Corporation_v29_SLOTS_SLIDERS_RATING.zip'
$stage = Join-Path $env:TEMP ('Corporation_v29_' + [guid]::NewGuid().ToString('N'))

Expand-Archive -LiteralPath $archive -DestinationPath $stage
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $stage 'APPLY_UPDATE_V29.ps1') -ProjectPath $projectPath
if ($LASTEXITCODE -ne 0) { throw 'Обновление не применено' }

Set-Location -LiteralPath $projectPath
git diff --stat
git add -- app.py web/index.html web/v29.js web/v29.css tests/test_v29.py README_V29_RU.md
git commit -m "v29: business slots sliders and rating polish"
if ($LASTEXITCODE -ne 0) { throw 'Проверь результат git commit перед push' }
git push
```

После `git push` Railway должен автоматически начать новый deploy, если сервис связан с этим GitHub-репозиторием и автодеплой включён.

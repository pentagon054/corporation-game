# Corporation v31 — покупка бизнеса и прокрутка ПК

Обновление для v29/v30. Установщик меняет только фронтенд и добавляет тест и
инструкцию; backend, бот, база данных и настройки не меняются.

После подтверждённой сервером покупки появляется окно «Бизнес куплен» с
названием бизнеса и подсказкой, где его смотреть и прокачивать. Кнопка
«Перейти в мои бизнесы» открывает нужный раздел. Кнопка «Готово» закрывает окно.
При отказе сервера показывается ошибка, а не сообщение об успешной покупке.
Повторный клик во время запроса не отправляет вторую покупку.

Прокрутка принадлежит документу; body больше не создаёт лишний контейнер,
запрещающий передачу прокрутки. Обычное колесо над картой прокручивает страницу.
Для масштаба карты на ПК — Ctrl + колесо или кнопки +/−.
Жесты карты на телефоне и запрет масштабирования интерфейса из v30 сохранены.

## Установка
Скачать архив в Downloads и выполнить в PowerShell:

```powershell
$projectPath = 'C:\Users\Pentagon\Desktop\corporation_game_MA'
$archive = Join-Path $env:USERPROFILE 'Downloads\Corporation_v31_BUSINESS_SCROLL_FIX.zip'
$stage = Join-Path $env:TEMP ('Corporation_v31_' + [guid]::NewGuid().ToString('N'))
Expand-Archive -LiteralPath $archive -DestinationPath $stage
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $stage 'APPLY_UPDATE_V31.ps1') -ProjectPath $projectPath
if ($LASTEXITCODE -ne 0) { throw 'Update failed' }
Set-Location -LiteralPath $projectPath
git diff --stat
git add -- web/index.html web/interactive_map.js web/premium_v24.js web/gestures_v30.js web/gestures_v30.css web/v31.js web/v31.css tests/test_v31.cjs README_V31_RU.md
git commit -m "Add business purchase confirmation and fix desktop scrolling"
if ($LASTEXITCODE -ne 0) { throw 'Commit failed' }
git push
if ($LASTEXITCODE -ne 0) { throw 'Push failed' }
```

Установщик создаёт резервную копию старых файлов рядом с папкой проекта.
После успешного деплоя Railway полностью перезапустить Mini App.

## Проверки
Пройдены node --check для изменённых JS и node tests/test_v31.cjs:
успех/отказ покупки, защита от двойного запроса, ошибка перерисовки после успеха,
переход в свои бизнесы, пропуск обычного колеса и масштабирование с Ctrl.
Также пройден тест логики жестов v30.

Нативное поведение Telegram Desktop/iOS/Android и визуальный интерфейс в этой
среде не проверены. На ПК проверить колесо вверх/вниз в каталоге, своих бизнесах,
рейтинге, поверх карты и в длинном модальном окне. На телефоне проверить pinch
карты и переход в свои бизнесы после покупки.

# Corporation v32.3 — объёмная 3D-монетка

Установить поверх v32/v32.1/v32.2 с проверкой подписки.

При открытии Mini App появляется чёрный экран с вращающейся золотой монеткой Corporation. Он виден минимум 1,6 секунды, затем плавно исчезает за 0,28 секунды. Если проверка подписки или загрузка скриптов длится дольше, анимация продолжается до результата. При отсутствии подписки или ошибке появляется экран с сообщением. Повторная проверка тоже сопровождается монеткой. При системной настройке уменьшения движения монетка статична.

Монетка построена как CSS 3D-цилиндр: две грани, 64 сегмента ребристого гурта, толщина 16 px, рельефная буква C и анимированный металлический блик. Внешние изображения и библиотеки для монетки не нужны.

В архиве три файла web для замены и PowerShell-установщик с резервным копированием. Сохранены исправления запуска v32.1. Серверная проверка подписки, база данных и прогресс игроков не меняются.

1. Скачать ZIP в папку Downloads.
2. Выполнить в PowerShell:

```powershell
$projectPath = 'C:\Users\Pentagon\Desktop\corporation_game_MA'
$archive = Join-Path $env:USERPROFILE 'Downloads\Corporation_v32_3_3D_COIN.zip'
$stage = Join-Path $env:TEMP ('Corporation_v32_3_' + [guid]::NewGuid().ToString('N'))
Expand-Archive -LiteralPath $archive -DestinationPath $stage -ErrorAction Stop
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $stage 'APPLY_UPDATE_V32_3.ps1') -ProjectPath $projectPath
if ($LASTEXITCODE -ne 0) { throw 'Update failed' }
Set-Location -LiteralPath $projectPath
git add -- web/index.html web/subscription_gate_v32.js web/subscription_gate_v32.css README_V32_3_RU.md
if ($LASTEXITCODE -ne 0) { throw 'git add failed' }
git commit -m "Add 3D Corporation startup coin"
if ($LASTEXITCODE -ne 0) { throw 'git commit failed' }
git push origin main
if ($LASTEXITCODE -ne 0) { throw 'git push failed' }
```

Дождаться успешного деплоя Railway, полностью закрыть Mini App и открыть снова.

Проверка: структура HTML, геометрия гурта и баланс скобок CSS и синтаксис JS. Логика проверки подписки и тайминги не изменены относительно v32.2. В реальном Telegram WebView внешний вид нужно проверить после установки.

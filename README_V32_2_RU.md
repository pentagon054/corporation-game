# Corporation v32.2 — монетка при входе

Установить поверх v32/v32.1 с проверкой подписки.

При открытии Mini App появляется чёрный экран с вращающейся золотой монеткой Corporation. Он виден минимум 1,6 секунды, затем плавно исчезает за 0,28 секунды. Если проверка подписки или загрузка скриптов длится дольше, анимация продолжается до результата. При отсутствии подписки или ошибке появляется экран с сообщением. Повторная проверка тоже сопровождается монеткой. При системной настройке уменьшения движения монетка статична.

В архиве три файла web для замены и PowerShell-установщик с резервным копированием. Сохранены исправления запуска v32.1. Серверная проверка подписки, база данных и прогресс игроков не меняются.

1. Скачать ZIP в папку Downloads.
2. Выполнить в PowerShell:

```powershell
$projectPath = 'C:\Users\Pentagon\Desktop\corporation_game_MA'
$archive = Join-Path $env:USERPROFILE 'Downloads\Corporation_v32_2_COIN_STARTUP.zip'
$stage = Join-Path $env:TEMP ('Corporation_v32_2_' + [guid]::NewGuid().ToString('N'))
Expand-Archive -LiteralPath $archive -DestinationPath $stage -ErrorAction Stop
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $stage 'APPLY_UPDATE_V32_2.ps1') -ProjectPath $projectPath
if ($LASTEXITCODE -ne 0) { throw 'Update failed' }
Set-Location -LiteralPath $projectPath
git add -- web/index.html web/subscription_gate_v32.js web/subscription_gate_v32.css README_V32_2_RU.md
if ($LASTEXITCODE -ne 0) { throw 'git add failed' }
git commit -m "Add Corporation coin startup animation"
if ($LASTEXITCODE -ne 0) { throw 'git commit failed' }
git push origin main
if ($LASTEXITCODE -ne 0) { throw 'git push failed' }
```

Дождаться успешного деплоя Railway, полностью закрыть Mini App и открыть снова.

Проверка: синтаксис JS и сценарии запуска с имитацией DOM/сети: подписка есть, подписки нет и повторная проверка, ошибка сети, медленная проверка, ошибка скрипта, запуск вне Telegram. Реальный Telegram WebView в этой среде не проверялся.

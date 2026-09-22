# Corporation v32.4 — объёмная 3D-монетка

Установить поверх v32/v32.1/v32.2/v32.3 с проверкой подписки.

При открытии Mini App появляется чёрный экран с вращающейся золотой монеткой Corporation. Он виден минимум 1,6 секунды, затем плавно исчезает за 0,28 секунды. Если проверка подписки или загрузка скриптов длится дольше, анимация продолжается до результата. При отсутствии подписки или ошибке появляется экран с сообщением. Повторная проверка тоже сопровождается монеткой. Вращение управляется requestAnimationFrame и продолжается даже при отключении CSS-анимаций; при настройке уменьшения движения отключены дополнительные блики и пульсация тени. После скрытия загрузочного экрана цикл вращения останавливается.

Монетка построена как CSS 3D-цилиндр: две грани, 64 сегмента ребристого гурта, толщина 16 px, рельефная буква C и анимированный металлический блик. Внешние изображения и библиотеки для монетки не нужны.

В архиве три файла web для замены и PowerShell-установщик с резервным копированием. Сохранены исправления запуска v32.1. Серверная проверка подписки, база данных и прогресс игроков не меняются.

1. Скачать ZIP в папку Downloads.
2. Выполнить в PowerShell:

```powershell
$projectPath = 'C:\Users\Pentagon\Desktop\corporation_game_MA'
$archive = Join-Path $env:USERPROFILE 'Downloads\Corporation_v32_4_MOBILE_COIN_FIX.zip'
$stage = Join-Path $env:TEMP ('Corporation_v32_4_' + [guid]::NewGuid().ToString('N'))
Expand-Archive -LiteralPath $archive -DestinationPath $stage -ErrorAction Stop
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $stage 'APPLY_UPDATE_V32_4.ps1') -ProjectPath $projectPath
if ($LASTEXITCODE -ne 0) { throw 'Update failed' }
Set-Location -LiteralPath $projectPath
git add -- web/index.html web/subscription_gate_v32.js web/subscription_gate_v32.css README_V32_4_RU.md
if ($LASTEXITCODE -ne 0) { throw 'git add failed' }
git commit -m "Fix mobile Corporation coin rotation"
if ($LASTEXITCODE -ne 0) { throw 'git commit failed' }
git push origin main
if ($LASTEXITCODE -ne 0) { throw 'git push failed' }
```

Дождаться успешного деплоя Railway, полностью закрыть Mini App и открыть снова.

Проверка: синтаксис JavaScript и сценарии с имитацией DOM/сети: успешный вход, отсутствие подписки и повторная проверка, ошибка сети, медленная проверка, ошибка загрузки скрипта, открытие вне Telegram. Проверяется изменение угла в нескольких кадрах и остановка цикла после скрытия заставки. Реальный мобильный Telegram WebView в этой среде недоступен.

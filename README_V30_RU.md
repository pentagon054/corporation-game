# Corporation v30 — жесты и карта

Основа: Corporation_v29_1_INSTALLER_HOTFIX.zip.

- Запрещён браузерный масштаб страницы при двойном касании и pinch.
- Прокрутка страниц и работа ползунков сохраняются.
- Карта отдельно масштабируется от 1× до 6×, поддерживает перетаскивание,
  кнопки +/−, колесо и клавиатуру.
- Pinch можно начинать на метках городов. После перетаскивания/двухпальцевого
  жеста город случайно не открывается. Следующий обычный тап работает.
- Telegram.disableVerticalSwipes отключает сворачивание свайпом по содержимому
  на поддерживаемых клиентах (API 7.7+). Заголовок Telegram по-прежнему позволяет
  свернуть приложение. Старые клиенты нужно обновить.
- Поля ввода на сенсорных устройствах имеют шрифт не меньше 16 px, чтобы iOS
  не увеличивал страницу при фокусе.

## Установка
Скачать ZIP в Downloads. В PowerShell выполнить:

```powershell
$projectPath = 'C:\Users\Pentagon\Desktop\corporation_game_MA'
$archive = Join-Path $env:USERPROFILE 'Downloads\Corporation_v30_GESTURES_MAP_FIX.zip'
$stage = Join-Path $env:TEMP ('Corporation_v30_' + [guid]::NewGuid().ToString('N'))
Expand-Archive -LiteralPath $archive -DestinationPath $stage
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $stage 'APPLY_UPDATE_V30.ps1') -ProjectPath $projectPath
if ($LASTEXITCODE -ne 0) { throw 'Update failed. Do not commit.' }
Set-Location -LiteralPath $projectPath
git diff --stat
git add -- web/index.html web/interactive_map.js web/gestures_v30.js web/gestures_v30.css tests/test_gestures_v30.cjs tests/test_gesture_logic_v30.cjs README_V30_RU.md
git commit -m "Fix game zoom and real estate map gestures"
if ($LASTEXITCODE -ne 0) { throw 'Commit failed. Check git status.' }
git push
if ($LASTEXITCODE -ne 0) { throw 'Push failed. Check git output.' }
```

Дождаться успешного деплоя Railway и полностью закрыть/открыть Mini App.
Установщик копирует только перечисленные файлы и создаёт резервную копию
прежних файлов рядом с проектом. Backend, база данных и настройки не меняются.
PowerShell-установщик использует ASCII, чтобы избежать ошибки кодировки Windows.
В архиве также лежат исходники базовой версии; для обновления используйте именно
APPLY_UPDATE_V30.ps1, а не старые установщики.

## Проверки
Пройдено: node --check изменённых JS и node tests/test_gesture_logic_v30.cjs.
Проверены геометрия pinch, переход на один палец, захват метки, отмена жеста,
медленное перетаскивание, обычный тап после жеста, вызов Telegram API и сохранение
однопальцевой прокрутки вне карты.

Браузерный тест tests/test_gestures_v30.cjs подготовлен, но не выполнен:
в среде не установлен Chromium, скачивание браузера не удалось.
Для запуска с установленным Playwright: node tests/test_gestures_v30.cjs.
Эмуляция не заменяет проверку нативных жестов Telegram на iOS/Android.

После установки проверить на телефоне:
1. Двойные касания и разведение пальцев вне карты не меняют размер интерфейса.
2. Прокрутка, многократные покупки и ползунки работают.
3. Pinch на карте и поверх меток меняет только карту; окно не сворачивается.
4. Отпустить один палец, продолжить движение другим, затем открыть город тапом.
5. Перейти в другую вкладку и вернуться, проверить карту ещё раз.

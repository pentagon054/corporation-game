# Corporation v33.1 — рефералы видимы в интерфейсе

Это пересобранная версия предрелизного обновления. В отличие от v33, вход в реферальную программу больше не зависит только от обёртки страницы рейтинга.

## Что должно появиться после обновления

- кнопка `🎁` в верхней части интерфейса рядом с переименованием корпорации;
- большая карточка `Реферальная программа` на Главной;
- карточка реферальной программы в Рейтинге;
- отдельный экран со ссылкой, статистикой и карточками приглашённых друзей;
- прогресс по двум условиям: капитализация 200 000 ₽ и 5 активных дней;
- награды: +10 000 ₽ приглашённому и +20 000 ₽ пригласившему;
- игровые модальные окна вместо browser/Telegram-native alert/confirm/prompt.

## Установка

Из папки проекта Corporation в PowerShell:

```powershell
$projectPath = (Get-Location).Path
$archive = "$env:USERPROFILE\Downloads\Corporation_v33_1_REFERRALS_VISIBLE_FULL.zip"
$stage = Join-Path $env:TEMP ("Corporation_v33_1_" + [guid]::NewGuid().ToString('N'))
Expand-Archive -LiteralPath $archive -DestinationPath $stage
$update = Get-ChildItem $stage -Filter APPLY_UPDATE_V33_1.ps1 -Recurse | Select-Object -First 1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $update.FullName -ProjectPath $projectPath
```

Скрипт сам проверит, что новый backend и новый интерфейс реально скопированы.

## После установки

```powershell
python -m py_compile app.py bot.py
python tests/test_referrals_v33.py
node tests/test_v33_1_visibility.cjs
git status
git add .
git commit -m "Install Corporation v33.1 visible referrals"
git push
```

Если backend и Telegram bot в Railway являются разными сервисами, после push проверь, что задеплоились оба. Версия WebApp у бота теперь `331`, чтобы Telegram не держал старый интерфейс в кэше.

Локальная `corporation.db` не входит в архив и не перезаписывается.

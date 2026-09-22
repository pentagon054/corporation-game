# Corporation v32 — обязательная подписка на Telegram-канал

Обновление ставится поверх Corporation v31.

Что добавлено:

- до загрузки игры сервер проверяет подписку игрока на канал из `REQUIRED_CHANNEL`;
- используется настоящий Telegram ID только после текущей серверной проверки `Telegram.WebApp.initData`;
- неподписанный игрок видит отдельный экран с кнопками «Подписаться на канал» и «Проверить подписку»;
- игровые JavaScript-файлы не загружаются до успешной проверки;
- существующий `user_from_request()` оборачивается дополнительной серверной проверкой, поэтому обычные игровые API тоже закрыты для неподписанного пользователя;
- положительный результат кешируется на 5 минут по умолчанию, чтобы не обращаться к Telegram при каждом действии;
- отрицательный результат не кешируется: после подписки кнопка «Проверить подписку» срабатывает сразу;
- токен бота не передаётся во frontend.

## Railway

Уже должно быть:

```text
REQUIRED_CHANNEL=@Corpgame054
BOT_TOKEN=...
```

Бот Corporation должен быть администратором `@Corpgame054`.

Необязательно можно изменить время кеша:

```text
SUBSCRIPTION_CACHE_SECONDS=300
```

## Установка

```powershell
$projectPath = 'C:\Users\Pentagon\Desktop\corporation_game_MA'
$archive = Join-Path $env:USERPROFILE 'Downloads\Corporation_v32_REQUIRED_CHANNEL.zip'
$stage = Join-Path $env:TEMP ('Corporation_v32_' + [guid]::NewGuid().ToString('N'))
Expand-Archive -LiteralPath $archive -DestinationPath $stage
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $stage 'APPLY_UPDATE_V32.ps1') -ProjectPath $projectPath
if ($LASTEXITCODE -ne 0) { throw 'Update failed' }
Set-Location -LiteralPath $projectPath
git diff --stat
git add -- app.py web/index.html web/subscription_gate_v32.js web/subscription_gate_v32.css README_V32_RU.md
git commit -m "Require Telegram channel subscription before game access"
if ($LASTEXITCODE -ne 0) { throw 'Commit failed' }
git push
if ($LASTEXITCODE -ne 0) { throw 'Push failed' }
```

Установщик создаёт резервную копию изменяемых файлов рядом с папкой проекта.

## Проверка после Railway deploy

1. Открыть игру аккаунтом, который подписан на `@Corpgame054` — игра должна открыться автоматически.
2. Отписаться и подождать до 5 минут либо перезапустить backend — доступ к игровым API должен закрыться.
3. Открыть игру неподписанным аккаунтом — должен появиться экран подписки.
4. Нажать «Подписаться на канал», подписаться, вернуться в Mini App и нажать «Проверить подписку» — игра должна открыться без ручной перезагрузки.
5. Если Telegram не может проверить участника, игра не открывается и показывает ошибку проверки.

Для локальной разработки подписку можно обойти только при одновременных переменных:

```text
ALLOW_DEV_AUTH=1
ALLOW_SUBSCRIPTION_DEV_BYPASS=1
```

В Railway вторую переменную добавлять не нужно.

# Corporation Security v22 — post-deploy checklist

- [ ] `ALLOW_DEV_AUTH` удалён из Railway backend variables.
- [ ] `BOT_TOKEN` не хранится в Git и совпадает у backend и bot service.
- [ ] `ADMIN_IDS` содержит только актуальных администраторов.
- [ ] Запрос к `/api/state` без `X-Telegram-Init-Data` получает `401`.
- [ ] Запрос с `X-User-Id` на Railway получает `400`, даже если ID администратора настоящий.
- [ ] Поддельный `X-Telegram-Init-Data` получает `401`.
- [ ] Просроченный `initData` получает `401`.
- [ ] Обычный запуск игры из Telegram работает.
- [ ] Админ-панель работает только у ID из `ADMIN_IDS`.
- [ ] `admin_backups` и `.db` не доступны как `/static/...`.
- [ ] Railway Volume всё ещё подключён к backend и прогресс не сбрасывается после deploy.

## Проверка критической старой уязвимости

После deploy старый запрос вида ниже **не должен** давать доступ независимо от ID:

```powershell
curl.exe -i -H "X-User-Id: 5152849511" "https://corporation-game-production-862a.up.railway.app/api/admin/overview"
```

Ожидаемо: HTTP 400 (`Legacy authentication header is disabled`) или 401, но никогда не 200.

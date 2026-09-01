Corporation Update v12 — постоянные сохранения

Что меняется:
- backend автоматически использует RAILWAY_VOLUME_MOUNT_PATH;
- SQLite хранится внутри Railway Volume;
- DB_PATH=corporation.db можно оставить;
- без Volume Railway-backend специально не запустится, чтобы не создать пустую временную базу;
- corporation.db не входит в ZIP и не перезаписывается;
- добавляется .gitignore для SQLite runtime-файлов;
- версия WebApp поднимается до 12.

Установка:
1. Распакуй ZIP в корень проекта рядом с app.py и bot.py.
2. Запусти INSTALL_UPDATE.bat.
3. Затем:
   git add .
   git commit -m "Fix persistent player saves"
   git push origin main

Railway №1:
- Volume должен быть подключён к FastAPI backend.
- Mount Path может быть любым: /data, /storage и т.п.
  Код получит его из RAILWAY_VOLUME_MOUNT_PATH автоматически.

Важно:
Если нужный текущий прогресс существует только во временной файловой системе старого контейнера,
его нужно сохранить до первого нового деплоя. После перехода на Volume следующие деплои уже
не будут сбрасывать сохранения.

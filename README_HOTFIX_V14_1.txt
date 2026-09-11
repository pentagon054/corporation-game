Corporation v14.1 Hotfix

Исправляет SyntaxError в app.py:
configured.rstrip("/\") был некорректно экранирован установщиком v14.

Hotfix:
- не трогает corporation.db;
- не трогает web/index.html, web/style.css и web/app.js;
- сохраняет уже установленный дизайн v14;
- заменяет только persistence-блок app.py;
- перед завершением запускает py_compile;
- если синтаксис не проходит, автоматически возвращает backup.

Установка:
1. Распаковать ZIP в корень corporation_game_MA.
2. Запустить .\INSTALL_HOTFIX_V14_1.bat
3. После ГОТОВО отправить app.py в GitHub.

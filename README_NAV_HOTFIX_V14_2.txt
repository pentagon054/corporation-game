Corporation v14.2 — Bottom Navigation Hotfix

Исправляет съехавшую вправо/обрезанную нижнюю панель Telegram Mini App.

Причина:
предыдущее desktop/media правило центрировало fixed-панель через left:50% +
translateX(-50%) и одновременно оставляло старые ограничения ширины. В Telegram
Desktop/WebView реальная ширина окна игры может отличаться от ширины контейнера,
из-за чего часть меню уходила за край.

Исправление:
- left/right задают реальную ширину панели;
- width:auto;
- max-width:none;
- transform:none на всех размерах;
- все шесть колонок minmax(0,1fr);
- кнопки имеют min-width:0;
- добавлена отдельная адаптация для экранов <=390px;
- app.py и corporation.db не изменяются.

Установка:
1. Распаковать в корень corporation_game_MA.
2. Запустить:
   .\INSTALL_NAV_HOTFIX_V14_2.bat

GitHub — по одной команде:
git status
git add bot.py
git add web/index.html
git add web/style.css
git commit -m "Fix mobile bottom navigation v14.2"
git push origin main

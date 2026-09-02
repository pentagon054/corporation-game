@echo off
chcp 65001 >nul
cd /d "%~dp0"
python apply_stock_market_v17.py
if errorlevel 1 (
  echo.
  echo ОБНОВЛЕНИЕ НЕ УСТАНОВЛЕНО. Пришли мне текст ошибки.
  pause
  exit /b 1
)
echo.
echo ГОТОВО.
pause

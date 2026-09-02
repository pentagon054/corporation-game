@echo off
chcp 65001 >nul
cd /d "%~dp0"
python apply_update_v16.py
if errorlevel 1 (
  echo.
  echo ОШИБКА: обновление не применилось.
  pause
  exit /b 1
)
echo.
echo Обновление применено успешно.
pause

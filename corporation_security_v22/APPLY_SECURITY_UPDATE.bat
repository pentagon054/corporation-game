@echo off
chcp 65001 >nul
cd /d "%~dp0"
python APPLY_SECURITY_UPDATE.py
if errorlevel 1 (
  echo.
  echo Обновление НЕ установлено. Смотри ошибку выше.
  pause
  exit /b 1
)
echo.
echo Security Update v22 установлен.
pause

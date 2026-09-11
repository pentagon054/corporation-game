@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo Corporation v22.1 - refresh button hotfix
echo.
python apply_refresh_button_v22_1.py
if errorlevel 1 (
  echo.
  echo Update failed.
  pause
  exit /b 1
)
echo.
echo Done.
pause

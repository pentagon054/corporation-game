@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ================================================
echo Corporation v12 - постоянные сохранения Railway
echo ================================================
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    py apply_persistence_update.py
) else (
    python apply_persistence_update.py
)

echo.
pause

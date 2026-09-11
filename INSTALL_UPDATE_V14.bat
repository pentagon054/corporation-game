@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo Corporation Update v14
echo ======================
python apply_update_v14.py
echo.
pause

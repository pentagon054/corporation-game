@echo off
chcp 65001 >nul
python apply_update_v15.py
if errorlevel 1 (pause & exit /b 1)
echo Готово.
pause

@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Распакуй файлы архива в корень проекта Corporation, рядом с app.py.
python apply_final_alpha_v22.py
if errorlevel 1 pause & exit /b 1
python -m py_compile app.py
if errorlevel 1 pause & exit /b 1
echo Готово.
pause

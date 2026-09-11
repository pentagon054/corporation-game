@echo off
chcp 65001 >nul
cd /d "%~dp0"
python apply_nav_hotfix_v14_2.py
pause

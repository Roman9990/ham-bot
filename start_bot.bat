@echo off
chcp 65001 >nul
cd /d %~dp0
echo [Hamlo] zapusk iz %CD% ...
python -u bot.py >> bot_out.log 2>&1
pause

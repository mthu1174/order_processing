@echo off
setlocal
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
echo [STARTING] Energizer Order Automation...
if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe main.py --auto
) else (
    echo [ERROR] Virtual environment not found. Please run 'python -m venv .venv' and install requirements.
    python main.py --auto
)
echo [FINISHED]
pause

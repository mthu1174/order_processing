@echo off
setlocal
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
    echo [LOI] Chua co moi truong .venv - hay chay "venv setup.bat" truoc.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -c "import customtkinter, playwright, win32com" >nul 2>&1
if errorlevel 1 (
    echo [LOI] .venv chua cai du thu vien - hay chay lai "venv setup.bat".
    echo Chi tiet:
    ".venv\Scripts\python.exe" -c "import customtkinter, playwright, win32com"
    pause
    exit /b 1
)

start "" ".venv\Scripts\pythonw.exe" main.py
exit /b 0

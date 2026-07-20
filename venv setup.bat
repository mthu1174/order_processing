@echo off
setlocal
cd /d "%~dp0"

echo [HE THONG] Dang thiet lap moi truong cho may tinh moi...

:: 1. Kiem tra Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [LOI] Khong tim thay Python! Hay cai dat Python truoc khi chay file nay.
    pause
    exit /b
)

:: 2. Tao moi truong ao neu chua co
if not exist .venv (
    echo [HE THONG] Dang tao moi truong ao (.venv)...
    python -m venv .venv
)

:: 3. Cai dat thu vien
echo [HE THONG] Dang cai dat cac thu vien can thiet...
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt

:: 4. Cai dat Playwright Browser
echo [HE THONG] Dang cai dat trinh duyet cho tu dong hoa...
.venv\Scripts\python.exe -m playwright install chromium

echo.
echo [HOAN TAT] Moi truong da san sang! 
echo Gio con co the mo file 'Order Automation.bat' de bat dau.
pause

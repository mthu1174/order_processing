@echo off
setlocal
cd /d "%~dp0"

echo [HE THONG] Dang thiet lap moi truong cho may tinh moi...

:: 1. Kiem tra Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [LOI] Khong tim thay Python! Hay cai dat Python va tick "Add python.exe to PATH".
    pause
    exit /b 1
)

:: 2. Tao moi truong ao neu chua co
if not exist ".venv\Scripts\python.exe" (
    echo [HE THONG] Dang tao moi truong ao .venv ...
    python -m venv .venv
)

:: 3. Cai dat thu vien
:: --use-feature=truststore: dung chung chi cua Windows, tranh loi SSL khi o mang cong ty
echo [HE THONG] Dang cai dat cac thu vien can thiet...
".venv\Scripts\python.exe" -m pip install --use-feature=truststore -r requirements.txt
if errorlevel 1 (
    echo [CANH BAO] Cai bang truststore that bai, thu lai voi trusted-host...
    ".venv\Scripts\python.exe" -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
)

:: 4. Kiem tra
".venv\Scripts\python.exe" -c "import customtkinter, playwright, win32com" >nul 2>&1
if errorlevel 1 (
    echo.
    echo [LOI] Cai thu vien chua thanh cong. Xem lai thong bao loi o tren.
    pause
    exit /b 1
)

:: Tool ket noi Edge co san qua cong 9222 nen KHONG can tai Chromium cua Playwright.

echo.
echo [HOAN TAT] Moi truong da san sang!
echo Gio co the mo file "Order Automation.bat" de bat dau.
pause

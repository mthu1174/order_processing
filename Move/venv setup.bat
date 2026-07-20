@echo off
setlocal
chcp 65001 > nul
cd /d "%~dp0"

echo [HỆ THỐNG] Đang thiết lập môi trường cho máy tính mới...

:: 1. Kiểm tra Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [LỖI] Không tìm thấy Python! Hãy cài đặt Python trước khi chạy file này.
    pause
    exit /b
)

:: 2. Tạo môi trường ảo nếu chưa có
if not exist .venv (
    echo [HỆ THỐNG] Đang tạo môi trường ảo (.venv)...
    python -m venv .venv
)

:: 3. Cài đặt thư viện
echo [HỆ THỐNG] Đang cài đặt các thư viện cần thiết...
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt

:: 4. Cài đặt Playwright Browser
echo [HỆ THỐNG] Đang cài đặt trình duyệt cho tự động hóa...
.venv\Scripts\python.exe -m playwright install chromium

echo.
echo [HOÀN TẤT] Môi trường đã sẵn sàng! 
echo Giờ con có thể mở file 'Order Automation.bat' để bắt đầu.
pause

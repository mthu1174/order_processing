# Cài Order Automation lên máy mới

## 1. Cài sẵn trên máy mới
- **Python 3.11 hoặc 3.12** (python.org). Lúc cài nhớ tick **"Add python.exe to PATH"**.
- **Git** (để clone) – hoặc tải ZIP từ GitHub cũng được.
- **Microsoft Edge** (thường có sẵn trên Windows).
- **Microsoft Excel** (code dùng Excel qua win32com).
- **SAP GUI** đã đăng nhập được, và **bật SAP GUI Scripting**:
  SAP Logon → Options → Accessibility & Scripting → Scripting → tick *Enable scripting*, bỏ tick 2 ô *Notify when...*.
  (Nếu ô bị xám thì phải nhờ IT/Basis bật `sapgui/user_scripting = TRUE` trên server.)
- **OneDrive DKSH** đã sync các folder đang dùng (Order processing, Operation CG - 7. Order Dropship Monitor...).

## 2. Lấy code về
```
git clone https://github.com/mthu1174/order_processing.git
cd order_processing
```
Không đặt folder trong đường dẫn có ký tự lạ quá dài; để kiểu `C:\Tools\order_processing` là ổn.

## 3. Cài môi trường
Double-click **`venv setup.bat`** → chờ nó tạo `.venv`, cài thư viện và cài Chromium cho Playwright.

## 4. Copy file cấu hình từ máy cũ
Mấy file này bị `.gitignore` nên **không có trên GitHub**, phải copy tay (USB / OneDrive) từ folder code máy cũ sang folder code máy mới:
- `config.json`
- `shopee_config.json`, `lazada_config.json`, `tiktok_config.json` (file nào có thì copy)

Sau đó mở app → tab **Settings** → kiểm tra lại từng đường dẫn. Nếu máy mới đăng nhập Windows bằng user khác thì sửa phần `C:\Users\<user cũ>\...` cho đúng.

Không có config cũ cũng được: app tự tạo `config.json` mới, đường dẫn mặc định giờ tự lấy theo user Windows hiện tại (`C:\Users\<user hiện tại>\OneDrive - DKSH\...`).

## 5. Đăng nhập lại các web
Profile Edge dùng cho automation (`C:\ShopeeEdgeProfile`) là của riêng từng máy → lần đầu chạy sẽ phải đăng nhập lại Shopee, Lazada, TikTok, Anchanto, GHN, Power BI. Đăng nhập 1 lần là nó nhớ.
Lưu ý: tool sẽ `taskkill` Edge trước khi chạy → lưu việc đang làm trên Edge trước khi bấm chạy.

## 6. Chạy
- Mở app: **`Order Automation.bat`**
- Chạy tự động không giao diện (cho Task Scheduler): **`AutoRun.bat`**

## Lỗi hay gặp
| Lỗi | Cách xử lý |
|---|---|
| `Khong tim thay Python` | Cài lại Python và tick *Add to PATH*, mở lại máy |
| Bấm `Order Automation.bat` không thấy gì | Chạy `AutoRun.bat` hoặc mở cmd: `.venv\Scripts\python.exe main.py` để xem lỗi |
| `GetObject("SAPGUI")` lỗi | Chưa mở SAP Logon / chưa bật Scripting |
| Không tìm thấy file / folder | Sửa đường dẫn trong tab Settings (hoặc `config.json`) |
| Playwright báo thiếu browser | `.venv\Scripts\python.exe -m playwright install chromium` |

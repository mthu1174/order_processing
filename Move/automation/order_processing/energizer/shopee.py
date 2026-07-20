import os
import time
from playwright.sync_api import sync_playwright

class ShopeeAutomator:
    def __init__(self, log_callback, app_dir, config=None):
        """
        log_callback: function to print logs to the GUI
        app_dir: root directory of the application
        """
        self.log = log_callback
        self.app_dir = app_dir
        self.config = config
        self.user_data_dir = os.path.join(app_dir, "browser_data", "shopee")
        if config:
            self.download_dir = config.get("shopee_download_dir")
        else:
            self.download_dir = r"C:\Users\thu.mai.dinh\OneDrive - DKSH\1. Order processing\2. Energizer\ORDERS"
        
        # Đảm bảo thư mục tồn tại
        if self.download_dir:
            os.makedirs(self.download_dir, exist_ok=True)

    def _cleanup_folder(self):
        """Xoá toàn bộ file trong thư mục để đảm bảo chỉ có 1 file mới nhất"""
        try:
            if os.path.exists(self.download_dir):
                for f in os.listdir(self.download_dir):
                    file_path = os.path.join(self.download_dir, f)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                self.log(f"[SHOPEE] Đã dọn dẹp thư mục: {self.download_dir}")
        except Exception as e:
            self.log(f"[SHOPEE] Lỗi dọn dẹp: {e}")

    def run_download_orders(self):
        """
        Khởi chạy trình duyệt, đăng nhập Shopee (hoặc đợi user đăng nhập),
        và tải file đơn hàng về thư mục cấu hình
        """
        self._cleanup_folder()
        self.log("[SHOPEE] Kết nối trình duyệt thật bằng CDP (Anti-Bot)...")
        
        with sync_playwright() as p:
            browser = None
            try:
                browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            except Exception:
                self.log("\n[CẢNH BÁO] Không tìm thấy trình duyệt Edge bật sẵn theo yêu cầu.")
                self.log("[HỆ THỐNG] Đang tự động dọn dẹp tiến trình ngầm và ép buộc khởi động trình duyệt...")
                import subprocess
                # Khử tất cả mọi tiến trình ngầm Edge ngăn cản lỗi port
                subprocess.run(["taskkill", "/F", "/IM", "msedge.exe"], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                time.sleep(2)
                
                # Tự gọi Edge theo thiết đặt
                edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
                profile_dir = r"C:\ShopeeEdgeProfile"
                subprocess.Popen([edge_path, "--remote-debugging-port=9222", f"--user-data-dir={profile_dir}"])
                
                self.log("[HỆ THỐNG] Đang chờ Edge tải lên màn hình (5 giây)...")
                time.sleep(5)
                
                try:
                    # Cố gắng bắt tín hiệu lại
                    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
                    self.log("[HỆ THỐNG] Đã bật và kết nối Edge (Anti-bot) thành công!")
                except Exception as e:
                    self.log(f"\n[LỖI NGHIÊM TRỌNG] Đã tự kích hoạt Edge nhưng vẫn KHÔNG LÝ GIẢI ĐƯỢC kết nối.")
                    self.log(">> Có thể máy tính của bạn chặn cổng hoặc Edge lỗi.")
                    self.log(f">> Error Detail: {e}\n")
                    return None
            
            browser_context = browser.contexts[0]
            page = browser_context.pages[0] if browser_context.pages else browser_context.new_page()
            
            self.log("[SHOPEE] Đang truy cập Shopee Seller Center...")
            page.goto("https://seller.shopee.vn/", timeout=60000)

            # Kiểm tra xem có đang ở trang login không
            time.sleep(3) 
            
            if "account/signin" in page.url or "login" in page.url:
                self.log("\n[WARNING] Shopee yêu cầu đăng nhập!")
                self.log(">> Vui lòng thao tác trên cửa sổ trình duyệt Shopee vừa mở.")
                while "account/signin" in page.url or "login" in page.url:
                    time.sleep(2)
                self.log("[SHOPEE] Phát hiện đã đăng nhập thành công!")
            
            self.log("[SHOPEE] Điều hướng đến trang Đơn Hàng...")
            page.goto("https://banhang.shopee.vn/portal/sale/order", timeout=60000)
            time.sleep(3)
            
            self.log("[SHOPEE] Đang thao tác bấm gửi lệnh Xuất Đơn Hàng...")
            select_export = "#app > div > div.app-container > div.page-container.responsive-container.has-sidebar-panel > div.page-content-wrapper.responsive-content-wrapper > div > div > div.portal-root-container > div:nth-child(6) > div:nth-child(1) > div > div > div > div.latest > button"
            page.locator(select_export).first.click()
            
            # Bước mới: Xác nhận trên Popup Xuất
            self.log("[SHOPEE] Đang xác nhận yêu cầu Xuất dữ liệu...")
            time.sleep(2) # Chờ popup hiện ra
            select_confirm = "#app > div > div.app-container > div.page-container.responsive-container.has-sidebar-panel > div.page-content-wrapper.responsive-content-wrapper > div > div > div.portal-root-container > div:nth-child(6) > div:nth-child(1) > div > div > div > div.eds-modal.export-modal > div > div > div > div > div.eds-modal__footer > div"
            try:
                # Thử click vào div confirmation hoặc button bên trong nó
                page.locator(select_confirm).first.click(timeout=10000)
            except Exception as e:
                self.log(f"[SHOPEE] Cảnh báo: Không thể nhấn nút xác nhận (có thể popup không hiện): {e}")

            self.log("[SHOPEE] Đang chờ hệ thống Shopee xử lý và hiện nút Tải về...")
            with page.expect_download(timeout=120000) as download_info:
                select_download = "#app > div > div.app-container > div.page-container.responsive-container.has-sidebar-panel > div.page-content-wrapper.responsive-content-wrapper > div > div > div.portal-root-container > div:nth-child(6) > div:nth-child(1) > div > div > div > div.latest > div > div.eds-popper.eds-popover__popper.eds-popover__popper--light.with-arrow.export-button-popover > div.eds-popover__content > div > div.eds-table.list > div.eds-table__body-container > div.eds-table__main-body > div > div > div.eds-scrollbar__content > table > tbody > tr:nth-child(1) > td.is-last > div > div > button"
                page.locator(select_download).first.click(timeout=120000)
                
            download = download_info.value
            filename = download.suggested_filename
            output_path = os.path.join(self.download_dir, filename)
            
            os.makedirs(self.download_dir, exist_ok=True)
            download.save_as(output_path)
            self.log(f"[SHOPEE] Tải file đơn hàng thành công: {filename}")
            browser.close()
            return output_path

    def extract_order_ids(self, file_path):
        """Đọc file Excel Shopee và lấy danh sách Mã đơn hàng"""
        import pandas as pd
        self.log(f"[SHOPEE] Đang trích xuất Order IDs từ file: {os.path.basename(file_path)}")
        try:
            # Đọc file (sử dụng pandas để nhanh gọn)
            df = pd.read_excel(file_path)
            # Các tên cột phổ biến của Shopee
            possible_cols = ["Mã đơn hàng", "Order ID", "Order ID*"]
            order_col = None
            for col in possible_cols:
                if col in df.columns:
                    order_col = col
                    break
            
            if order_col:
                ids = df[order_col].dropna().astype(str).unique().tolist()
                self.log(f"[SHOPEE] Đã tìm thấy {len(ids)} đơn hàng cần xử lý.")
                return ids
            else:
                self.log("[CẢNH BÁO] Không tìm thấy cột 'Mã đơn hàng' trong file Shopee.")
                return []
        except Exception as e:
            self.log(f"[LỖI] Không thể đọc file Shopee: {e}")
            return []


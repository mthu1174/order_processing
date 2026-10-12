from automation.paths import find_edge_path
import time
from playwright.sync_api import sync_playwright

class PowerBIWebAutomator:
    def __init__(self, log_callback, app_dir, config=None):
        self.log = log_callback
        self.app_dir = app_dir
        self.config = config
        self.dataset_url = config.get("powerbi_semantic_model_url")

    def trigger_refresh(self):
        if not self.dataset_url:
            self.log("[LỖI] Chưa có URL Semantic Model trong cấu hình.")
            return False

        self.log("[POWER BI] Đang truy cập Power BI Service...")
        
        with sync_playwright() as p:
            browser = None
            try:
                # Thử kết nối tới Edge đang mở
                browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            except Exception:
                self.log("[POWER BI] Đang khởi động Edge với Profile chuyên dụng...")
                import subprocess
                import os
                # Dọn dẹp Edge cũ
                subprocess.run(["taskkill", "/F", "/IM", "msedge.exe"], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                time.sleep(2)
                
                # Khởi động Edge thật với profile
                edge_path = find_edge_path()
                profile_dir = r"C:\ShopeeEdgeProfile"
                subprocess.Popen([edge_path, "--remote-debugging-port=9222", f"--user-data-dir={profile_dir}"])
                time.sleep(10) # Cho Power BI thời gian load nặng
                
                try:
                    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
                except Exception as e:
                    self.log(f"[LỖI] Không thể kết nối Edge: {e}")
                    return False
            
            # Sử dụng context mặc định của Profile
            context = browser.contexts[0]
            page = context.new_page()
            
            try:
                self.log(f"[POWER BI] Mở đường dẫn: {self.dataset_url}")
                # Thay đổi: Chỉ chờ trang load xong khung cơ bản, không chờ networkidle vì Power BI rất nặng
                page.goto(self.dataset_url, timeout=90000, wait_until="load")
                
                self.log("[POWER BI] Đang chờ giao diện ổn định (15s)...")
                time.sleep(15) 
                
                # DANH SÁCH SELECTOR
                refresh_selectors = [
                    "#model-actionbar-refresh",
                    "button:has-text('Refresh now')",
                    "button[aria-label='Refresh now']",
                    "text=Refresh now"
                ]
                
                success = False
                self.log("[POWER BI] Bước 1: Đọc thời gian Refreshed hiện tại...")
                
                # Selector ô thời gian do bạn cung cấp (ưu tiên dùng class property-value để ổn định)
                time_selector = "div.property-value"
                
                initial_time = ""
                try:
                    # Tìm ô chứa thời gian Refreshed (thường nằm sau text 'Refreshed')
                    # Ta sẽ tìm label 'Refreshed' rồi lấy div tiếp theo
                    time_element = page.locator("olc-details-metadata:has-text('Refreshed') div.property-value").first
                    initial_time = time_element.inner_text().strip()
                    self.log(f"[POWER BI] Thời gian cũ: {initial_time}")
                except:
                    self.log("[CẢNH BÁO] Không đọc được thời gian cũ, sẽ dựa vào icon xoay.")

                self.log("[POWER BI] Bước 2: Mở Menu và kích hoạt Refresh...")
                
                def try_two_step_refresh(handle):
                    try:
                        btn_main = handle.locator("#model-actionbar-refresh").first
                        if btn_main.is_visible(timeout=5000):
                            btn_main.click(force=True)
                            time.sleep(2)
                            btn_sub = handle.locator("span.dropDown-displayName:has-text('Refresh now')").first
                            if not btn_sub.is_visible():
                                btn_sub = handle.locator("button:has-text('Refresh now')").first
                                
                            if btn_sub.is_visible(timeout=3000):
                                btn_sub.click(force=True)
                                return True
                    except: pass
                    return False

                if try_two_step_refresh(page):
                    success = True
                
                if not success:
                    for frame in page.frames:
                        if try_two_step_refresh(frame):
                            success = True
                            break

                if not success:
                    self.log("[!] CẢNH BÁO: Không thể kích hoạt nút Refresh.")
                    return False
                
                # Bước 3: Chờ đợi cho đến khi hoàn thành (Hybrid Polling)
                self.log("[POWER BI] Đang theo dõi tiến độ... Check 2p/lần và F5 mỗi 5 phút.")
                start_wait = time.time()
                last_reload_time = time.time()
                max_wait_minutes = 15
                
                while (time.time() - start_wait) < (max_wait_minutes * 60):
                    try:
                        # 1. Kiểm tra giờ ngay lập tức (không reload)
                        time_element = page.locator("olc-details-metadata:has-text('Refreshed') div.property-value").first
                        if time_element.is_visible(timeout=2000):
                            current_time = time_element.inner_text().strip()
                            if current_time != initial_time and initial_time != "":
                                self.log(f"[POWER BI] XÁC NHẬN: Thời gian đã cập nhật mới: {current_time}")
                                self.log("[POWER BI] === QUÁ TRÌNH REFRESH ĐÃ HOÀN TẤT THÀNH CÔNG ===")
                                return True
                        
                        # 2. Nếu đã qua 5 phút mà chưa xong thì chủ động F5
                        if (time.time() - last_reload_time) > 300:
                            self.log("[POWER BI] Đã qua 5 phút, đang F5 trang để ép cập nhật...")
                            page.reload(wait_until="load", timeout=60000)
                            time.sleep(10) # Chờ UI ổn định sau F5
                            last_reload_time = time.time()
                            
                    except Exception as e_poll:
                        # Nếu lỗi nhẹ (do đang F5 hoặc UI lag), bỏ qua để lặp tiếp
                        pass
                    
                    time.sleep(120) # Đã đổi thành 2p/lần theo yêu cầu

                self.log("[!] CẢNH BÁO: Đã quá thời gian chờ (15 phút) mà chưa thấy cập nhật.")
                return True
                
            except Exception as e:
                self.log(f"[POWER BI] Lỗi trong quá trình thao tác web: {e}")
                return False
            finally:
                page.close()

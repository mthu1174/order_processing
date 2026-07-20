import os
import time
import subprocess
import calendar
import re
from datetime import datetime
from playwright.sync_api import sync_playwright

class LazadaOrderAutomator:
    """
    Tự động tải đơn hàng Lazada Seller Center qua các file shortcut (.lnk).
    Hỗ trợ xuất báo cáo theo tháng.
    """

    BASE_URL = "https://sellercenter.lazada.vn/apps/order/list?oldVersion=1&status=all"
    CDP_PORT = 9222

    def __init__(self, log_callback, app_dir, config=None):
        self.log = log_callback or print
        self.app_dir = app_dir
        self.config = config or {}
        self._stop_requested = False
        self._login_confirmed = False

    def request_stop(self):
        self._stop_requested = True

    def confirm_login(self):
        self._login_confirmed = True

    def run_automation(self, year, months, shortcut_folder, download_dir, selected_shortcuts=None):
        self._stop_requested = False
        
        if not selected_shortcuts:
            self.log("[LỖI] Không có file shortcut nào được chọn.")
            return

        os.makedirs(download_dir, exist_ok=True)

        self.log("\n" + "="*50)
        self.log("BẮT ĐẦU QUY TRÌNH TẢI ĐƠN LAZADA")
        self.log("="*50)

        for lnk_path, shop_name in selected_shortcuts:
            if self._stop_requested: break
            
            self.log(f"\n[SHOP] {shop_name}")
            self._process_shop(lnk_path, shop_name, months, year, download_dir)

        self.log("\n" + "="*50)
        self.log("HOÀN TẤT QUY TRÌNH LAZADA")
        self.log("="*50)

    def _process_shop(self, lnk_path, shop_name, months, year, download_dir):
        with sync_playwright() as p:
            browser = self._launch_from_shortcut(p, lnk_path)
            if not browser: 
                self.log("  [LỖI] Không thể khởi chạy trình duyệt từ shortcut.")
                return
            
            try:
                page = browser.contexts[0].pages[0]
                
                # Navigate to Orders Page
                page.goto(self.BASE_URL, timeout=60000, wait_until="commit")
                
                if not self._handle_login(page, shop_name):
                    return

                for i, month in enumerate(months):
                    if self._stop_requested: break
                    
                    self.log(f"  - Đang xuất dữ liệu tháng {month}/{year}...")
                    self._export_month(page, shop_name, month, year, download_dir)
                    
                    if i < len(months) - 1:
                        self.log("    ⏳ Đợi 10s trước khi xuất tháng tiếp theo...")
                        time.sleep(10)

            except Exception as e:
                self.log(f"  [LỖI HỆ THỐNG] {e}")
            finally:
                try: browser.close()
                except: pass
                self._kill_browser()

    def _launch_from_shortcut(self, playwright, lnk_path):
        self._kill_browser() # Close any existing ones just in case
        time.sleep(1)
        
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(os.path.abspath(lnk_path))
            target_path = shortcut.TargetPath
            arguments = shortcut.Arguments
            
            # Identify browser exe name
            self.current_browser_exe = os.path.basename(target_path)
            
            # Kill existing instances of this specific browser to free up port 9222
            subprocess.run(["taskkill", "/F", "/IM", self.current_browser_exe], 
                           capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            time.sleep(1)
            
            # Launch with CDP port
            cmd = f'"{target_path}" {arguments} --remote-debugging-port={self.CDP_PORT}'
            subprocess.Popen(cmd, shell=False, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            time.sleep(5) # Wait for browser to start
            
            return playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{self.CDP_PORT}")
        except ImportError:
            self.log("  [LỖI] Thư viện win32com không khả dụng. Vui lòng cài đặt pywin32.")
            return None
        except Exception as e:
            self.log(f"  [LỖI] Khởi chạy từ shortcut thất bại: {e}")
            return None

    def _kill_browser(self):
        try:
            if hasattr(self, 'current_browser_exe') and self.current_browser_exe:
                subprocess.run(["taskkill", "/F", "/IM", self.current_browser_exe], 
                               capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            else:
                subprocess.run(["taskkill", "/F", "/IM", "msedge.exe"], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        except: pass

    def _handle_login(self, page, shop_name):
        self._login_confirmed = False
        time.sleep(3)
        
        # Check if already in order list
        if "order/list" in page.url and page.locator("button.next-menu-btn").first.is_visible(timeout=5000):
            return True
            
        self.log(f"\n⚠️ [{shop_name}] YÊU CẦU ĐĂNG NHẬP!")
        self.log("  - Vui lòng hoàn tất quá trình đăng nhập trên trình duyệt vừa mở.")
        self.log("  - Bấm 'ĐÃ ĐĂNG NHẬP XONG' để tự động tiếp tục.")
        
        start = time.time()
        while time.time() - start < 300: # 5 mins wait
            if self._stop_requested: return False
            if self._login_confirmed: return True
            if "order/list" in page.url and page.locator("button.next-menu-btn").first.is_visible(timeout=2000):
                return True
            time.sleep(2)
            
        self.log("  [LỖI] Hết thời gian chờ đăng nhập.")
        return False

    def _export_month(self, page, shop_name, month, year, download_dir):
        try:
            # 1. Open Date Picker
            self.log("    - Đang chọn ngày...")
            # Sử dụng selector người dùng cung cấp
            date_picker_trigger = page.locator("#root > section > div.a-l-page-container > div > div.mount-node-container.middle-container-width > div > div > form > div.next-card.next-card-hide-divider > div > div > div > div.expand-body > div:nth-child(1) > div.next-col.next-form-item-control > div > div:nth-child(2) > div > span")
            
            if not date_picker_trigger.is_visible(timeout=10000):
                # Fallback to general date picker span
                date_picker_trigger = page.locator("span.next-date-picker-trigger").first
                
            date_picker_trigger.click()
            time.sleep(2)

            # 2. Input Start and End Dates
            start_date_str = f"01/{month:02d}/{year}"
            last_day = calendar.monthrange(year, month)[1]
            end_date_str = f"{last_day:02d}/{month:02d}/{year}"

            start_input = page.locator("#createDateRange > div > span:nth-child(1) > input").first
            end_input = page.locator("#createDateRange > div > span:nth-child(3) > input").first
            
            if not start_input.is_visible():
                # Fallback
                start_input = page.locator("input[placeholder*='Ngày bắt đầu'], input[placeholder*='Start date']").first
                end_input = page.locator("input[placeholder*='Ngày kết thúc'], input[placeholder*='End date']").first

            # Fill dates
            start_input.click()
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            start_input.fill(start_date_str)
            page.keyboard.press("Enter")
            time.sleep(1)

            end_input.click()
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            end_input.fill(end_date_str)
            page.keyboard.press("Enter")
            time.sleep(2)
            
            # Click outside to close date picker if it's still open
            page.mouse.click(10, 10)
            time.sleep(1)

            # 3. Click "Export" Button
            self.log("    - Đang nhấn Export...")
            export_btn = page.locator("button.next-btn.next-menu-btn").filter(has_text=re.compile(r"Xuất|Export", re.IGNORECASE)).first
            if not export_btn.is_visible(timeout=5000):
                self.log("    ⚠️ Không tìm thấy nút Xuất/Export.")
                return False
                
            export_btn.click()
            time.sleep(1)

            # 4. Click "Export All" in dropdown
            export_all = page.locator("div.aplus-auto-exp").filter(has_text=re.compile(r"Export All|Xuất tất cả|Export", re.IGNORECASE)).first
            if export_all.is_visible(timeout=3000):
                export_all.click()
            else:
                # If only Export button exists without dropdown
                pass
            time.sleep(1)

            # 5. Click "OK" in confirmation modal
            self.log("    - Đang chờ file tải về...")
            ok_btn = page.locator("button").filter(has_text=re.compile(r"^OK$", re.IGNORECASE)).first
            
            if ok_btn.is_visible(timeout=5000):
                # Start waiting for download BEFORE clicking OK
                with page.expect_download(timeout=60000) as download_info:
                    ok_btn.click()
                
                download = download_info.value
                
                today_str = datetime.now().strftime("%d%m%y")
                final_filename = f"LAZ_{shop_name}_{today_str}_{month}.xlsx"
                save_path = os.path.join(download_dir, final_filename)
                
                download.save_as(save_path)
                self.log(f"      ✅ OK: {final_filename}")
                return True
            else:
                self.log("    ⚠️ Không tìm thấy nút OK.")
                return False

        except Exception as e:
            self.log(f"    ❌ Lỗi trong quá trình xuất: {str(e)[:100]}")
            return False

from automation.paths import find_edge_path
import os
import time
import json
import subprocess
import pandas as pd
from datetime import datetime, date
import calendar
from playwright.sync_api import sync_playwright


class ShopeeOrderAutomator:
    """
    Tự động tải đơn hàng Shopee Seller Center.
    Hỗ trợ tải nhiều shop, chọn tháng tùy ý.
    Quy trình: Request Export tất cả shop -> Quay lại Download tất cả shop.
    """

    BASE_URL = "https://banhang.shopee.vn/portal/sale/order"
    EDGE_PATH = find_edge_path()
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

    def run_automation(self, year, months, store_list_path, download_dir, selected_shops=None):
        """
        Quy trình chính.
        """
        self._stop_requested = False
        
        # 1. Đọc danh sách shop
        if selected_shops:
            shops = selected_shops
        else:
            shops = self._load_shops(store_list_path)
        if not shops:
            self.log("[LOI] Khong tim thay danh sach shop hoac file loi.")
            return

        # Group shops by account to avoid redundant logins
        accounts = {}
        for s in shops:
            acc = s['account']
            if acc not in accounts:
                accounts[acc] = []
            accounts[acc].append(s)

        os.makedirs(download_dir, exist_ok=True)
        tracking_list = [] # List of (shop_info, month)

        # PHASE 1: REQUEST EXPORTS
        self.log("\n" + "="*50)
        self.log("PHASE 1: GUI YEU CAU XUAT BAO CAO")
        self.log("="*50)

        for account_bu, account_shops in accounts.items():
            if self._stop_requested: break
            
            self.log(f"\n[TAI KHOAN] {account_bu}")
            
            # Use one browser session for both Phase 1 and Phase 2 of this account
            self._process_account_full(account_bu, account_shops, months, year, download_dir)

        self.log("\n" + "="*50)
        self.log("HOAN TAT QUY TRINH")
        self.log("="*50)

    # ------------------------------------------------------
    #  FULL ACCOUNT PROCESS (REQUEST + DOWNLOAD)
    # ------------------------------------------------------

    def _process_account_full(self, account_bu, account_shops, months, year, download_dir):
        profile_dir = os.path.join(self.app_dir, "browser_data", "shopee", account_bu)
        os.makedirs(profile_dir, exist_ok=True)

        with sync_playwright() as p:
            browser = self._launch_edge(p, profile_dir)
            if not browser: return
            
            try:
                page = browser.contexts[0].pages[0]
                # Start with a safe URL
                try:
                    page.goto("https://banhang.shopee.vn/portal/shop", timeout=60000, wait_until="commit")
                except Exception as e:
                    self.log(f"  [INFO] Chuyen huong ban dau: {str(e)[:50]}...")

                if not self._handle_login(page, account_bu):
                    return

                tracking_list = []

                # --- PHASE 1: REQUEST ---
                self.log(f"  > PHASE 1: Gui yeu cau xuat cho {len(account_shops)} shop...")
                for shop in account_shops:
                    if self._stop_requested: break
                    
                    shop_username = shop['shop_username']
                    self.log(f"  [SHOP] {shop['shop_name']} ({shop_username})")
                    
                    if not self._switch_to_shop_v2(page, shop_username):
                        continue

                    # Go to Order Page
                    page.goto(self.BASE_URL, timeout=60000)
                    time.sleep(2)

                    for i, month in enumerate(months):
                        if self._stop_requested: break
                        
                        # Neu day khong phai thang dau tien cua shop nay, doi 1 phut
                        if i > 0:
                            self.log(f"    ⏳ Doi 60s giua cac lan xuat cua cung shop...")
                            for remaining in range(60, 0, -10):
                                if self._stop_requested: break
                                self.log(f"      ... con {remaining}s")
                                time.sleep(10)
                        
                        self.log(f"    - Request {month}/{year}...")
                        if self._trigger_export(page, month, year):
                            tracking_list.append({'shop': shop, 'month': month})
                        else:
                            self.log(f"    ❌ Loi.")

                if self._stop_requested: return

                # --- WAIT ---
                if tracking_list:
                    self.log(f"  > Dang doi 30s de Shopee chuan bi {len(tracking_list)} file...")
                    time.sleep(30)

                    # --- PHASE 2: DOWNLOAD ---
                    self.log(f"  > PHASE 2: Tai file ve...")
                    
                    # Group tracking by shop to avoid switching back and forth
                    shop_tracking = {}
                    for item in tracking_list:
                        u = item['shop']['shop_username']
                        if u not in shop_tracking: shop_tracking[u] = []
                        shop_tracking[u].append(item)

                    for shop_username, items in shop_tracking.items():
                        if self._stop_requested: break
                        
                        shop_name = items[0]['shop']['shop_name']
                        self.log(f"  [SHOP] {shop_name}")
                        
                        if not self._switch_to_shop_v2(page, shop_username):
                            continue
                            
                        page.goto(self.BASE_URL, timeout=60000)
                        time.sleep(2)

                        for item in items:
                            if self._stop_requested: break
                            self.log(f"    - Download {item['month']}/{year}...")
                            self._download_one_report(page, item['shop'], item['month'], year, download_dir)

            except Exception as e:
                self.log(f"  [LOI HE THONG] {e}")
            finally:
                browser.close()
                self._kill_edge()

    def _switch_to_shop_v2(self, page, target_username):
        """Chuyển shop bằng cách quét bảng hoặc tìm kiếm dự phòng."""
        try:
            # 1. Đảm bảo đang ở trang danh sách shop
            if "portal/shop" not in page.url:
                page.goto("https://banhang.shopee.vn/portal/shop", timeout=30000)
                time.sleep(2)

            # 2. Nếu đang ở trong một shop rồi, bấm "Đổi shop"
            if "portal/shop" not in page.url:
                try:
                    page.locator(".shop-info, .account-info, .eds-popover__trigger").first.click(timeout=3000)
                    time.sleep(1)
                    page.locator("text='Chọn Shop', text='Switch Shop', text='Đổi shop'").first.click()
                    time.sleep(3)
                except:
                    page.goto("https://banhang.shopee.vn/portal/shop", timeout=30000)
                    time.sleep(3)

            # 3. Thử tìm trực tiếp trong bảng (khỏi cần search nếu đã thấy)
            try:
                row = page.locator("tr").filter(has_text=target_username).first
                if row.is_visible(timeout=3000):
                    btn = row.locator("button, span").filter(has_text="Chi tiết").first
                    if btn.is_visible():
                        btn.click()
                        self.log(f"      ✅ Đã chọn shop: {target_username}")
                        time.sleep(5)
                        return True
            except: pass

            # 4. Nếu không thấy, mới dùng ô tìm kiếm (Dự phòng)
            try:
                # Chọn filter "Tên đăng nhập"
                dropdown = page.locator(".eds-react-select, .trigger--normal").filter(has_text="Tên Shop").first
                if dropdown.is_visible(timeout=2000):
                    dropdown.click()
                    time.sleep(1)
                    page.locator(".eds-react-select-option").filter(has_text="Tên Đăng nhập của Shop").first.click()
                    time.sleep(1)

                search_input = page.locator("input[placeholder*='Nhập vào'], .eds-react-input__input").first
                search_input.click()
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                search_input.fill(target_username)
                page.keyboard.press("Enter")
                time.sleep(3)
                
                row = page.locator("tr").filter(has_text=target_username).first
                btn = row.locator("button, span").filter(has_text="Chi tiết").first
                if btn.is_visible(timeout=5000):
                    btn.click()
                    self.log(f"      ✅ Đã chọn shop (sau khi search): {target_username}")
                    time.sleep(5)
                    return True
            except: pass

            self.log(f"    ⚠️ Không tìm thấy shop: {target_username}")
            return False
        except Exception as e:
            self.log(f"    ⚠️ Lỗi khi chuyển shop: {str(e)[:50]}")
            return False

            self.log(f"    ⚠️ Loi khi chuyen shop: {str(e)[:100]}")
            return False

    def _trigger_export(self, page, month, year):
        try:
            # Wait for main container to appear
            try:
                page.locator(".page-content-wrapper, .eds-react-table").wait_for(state="visible", timeout=15000)
            except:
                self.log("    ⚠️ Trang tai hoi cham, tiep tuc doi...")

            # Wait for loading spinners to disappear
            # We wait for them to potentially appear first then disappear
            time.sleep(2)
            try:
                page.locator(".eds-loading, .shopee-loading, .eds-loading-spinner").wait_for(state="hidden", timeout=10000)
            except: pass
            
            time.sleep(3) # Extra buffer for heavy Shopee UI
            
            # Check language
            is_eng = page.locator("text='Home', text='Orders'").first.is_visible(timeout=2000)
            export_text = "Export" if is_eng else "Xuất"
            
            # Find the Export button
            export_btn = page.locator("button").filter(has_text=export_text).first
            if not export_btn.is_visible():
                export_btn = page.locator(".export-with-modal, .eds-button--normal").filter(has_text=export_text).first

            # If still not visible, maybe need a small scroll or longer wait
            if not export_btn.is_visible():
                time.sleep(5)
                export_btn = page.locator("button").filter(has_text=export_text).first

            if export_btn.is_visible(timeout=10000):
                # Ensure it's not disabled
                for _ in range(5):
                    if not export_btn.is_disabled():
                        break
                    self.log(f"    - Nut {export_text} dang bi vo hieu hoa, cho 2s...")
                    time.sleep(2)
                
                export_btn.click()
                time.sleep(2)
            else:
                self.log(f"    ⚠️ Khong tim thay nut {export_text} (Page might be slow).")
                # Try reloading once? 
                # page.reload()
                return False

            # Chon ngay
            if not self._select_month_range_v2(page, month, year):
                try: page.locator(".eds-modal__close, .eds-icon-close").first.click()
                except: pass
                return False
            
            # Click "Xuất" trong modal
            modal_export_btn = page.locator(".eds-modal__footer button").filter(has_text=export_text).first
            if not modal_export_btn.is_visible():
                modal_export_btn = page.locator(".eds-modal__footer button.eds-button--primary").first
                
            modal_export_btn.click(timeout=10000)
            time.sleep(3)
            return True
        except Exception as e:
            self.log(f"    ⚠️ Loi khi trigger export: {str(e)[:100]}")
            return False

    def _select_month_range_v2(self, page, target_month, target_year):
        """Navigate calendar to target month/year and select 1st to last day."""
        try:
            # 1. Click to open date picker
            picker_selectors = [
                ".eds-range-picker",
                ".eds-date-picker",
                "input[placeholder*='Chọn'], input[placeholder*='Select']",
                ".eds-react-input__input",
                "text='Thời gian đặt hàng'"
            ]
            
            opened = False
            for sel in picker_selectors:
                try:
                    p = page.locator(sel).first
                    if p.is_visible(timeout=2000):
                        p.click(force=True)
                        time.sleep(2)
                        if page.locator(".eds-calendar, .eds-daterange-picker-panel").first.is_visible(timeout=1000):
                            opened = True
                            break
                except: continue
            
            if not opened:
                self.log("    ⚠️ Khong the mo bang chon ngay.")
                return False

            # 2. Click Month-Year label to open Month Grid (Faster navigation)
            # Selector from user: div.eds-picker-header > span:nth-child(3)
            try:
                # We try to click the span that looks like "Tháng 05 2026" or similar
                month_year_btn = page.locator(".eds-picker-header span, .eds-calendar-header__label").first
                month_year_btn.click()
                time.sleep(1)
                
                # Now we should see the month table/grid
                # If target_year is not the current one, we might need to navigate years
                # For simplicity, let's look for the month in the grid.
                # Month 1 is index 0 or text 'Tháng 1'
                month_name_vn = f"Tháng {target_month}"
                month_name_en = calendar.month_name[target_month][:3]
                
                month_cell = page.locator(".eds-month-table__cell, .eds-month-table div").filter(has_text=month_name_vn).first
                if not month_cell.is_visible():
                    month_cell = page.locator(".eds-month-table__cell, .eds-month-table div").filter(has_text=month_name_en).first
                
                if month_cell.is_visible():
                    month_cell.click()
                    time.sleep(1)
                else:
                    # Fallback to the old Prev/Next method if Month Grid fails
                    self.log("    [DEBUG] Khong thay o chon thang, dung nut Pre/Next...")
                    # (Prev/Next logic already implemented in previous version, we can reuse or just skip)
            except:
                pass

            # 3. Select Days (Using month-start and month-end classes provided by user)
            # Day 1: .month-start
            # Day Last: .month-end
            try:
                day1 = page.locator(".eds-date-table__cell.month-start span, .eds-calendar-table__cell.month-start").first
                if not day1.is_visible():
                    day1 = page.locator(".eds-calendar-table__cell:not(.eds-calendar-table__cell--next-month):not(.eds-calendar-table__cell--prev-month)").get_by_text(" 1 ", exact=True).first
                
                day1.click()
                time.sleep(0.5)
                
                day_last = page.locator(".eds-date-table__cell.month-end span, .eds-calendar-table__cell.month-end").first
                if not day_last.is_visible():
                    last_day_val = calendar.monthrange(target_year, target_month)[1]
                    day_last = page.locator(".eds-calendar-table__cell:not(.eds-calendar-table__cell--next-month):not(.eds-calendar-table__cell--prev-month)").get_by_text(f" {last_day_val} ", exact=True).first
                
                day_last.click()
                time.sleep(1)
                return True
            except Exception as e:
                self.log(f"    ⚠️ Loi khi chon ngay trong bang: {str(e)[:50]}")
                return False
        except Exception as e:
            self.log(f"    ⚠️ Loi calendar: {str(e)[:100]}")
            return False

    def _download_one_report(self, page, shop, month, year, download_dir):
        try:
            is_eng = page.locator("text='Home', text='Orders'").first.is_visible(timeout=2000)
            export_text = "Export" if is_eng else "Xuất"
            history_text = "Export History" if is_eng else "Lịch sử Xuất Báo cáo"
            download_text = "Download" if is_eng else "Tải về"
            processing_text = "Processing" if is_eng else "Đang xử lý"

            # Try to click History directly first
            history_btn = page.locator(f"button:has-text('{history_text}'), .eds-button:has-text('{history_text}')").first
            if history_btn.is_visible(timeout=2000):
                history_btn.click()
            else:
                # If not visible, click Export menu first
                export_btn = page.locator(f"button:has-text('{export_text}'), .export-with-modal").first
                if export_btn.is_visible(timeout=3000):
                    export_btn.click()
                    time.sleep(1)
                    page.locator(f"button:has-text('{history_text}')").first.click()
                else:
                    self.log(f"      ⚠️ Khong thay nut {export_text} hoac {history_text}.")
                    return

            time.sleep(3)

            # Polling for the specific file
            # In history table, we check the first row usually.
            # But since we might have requested multiple months, we should look for the right one?
            # Shopee doesn't clearly label months in history, but we can assume the top one is the latest request.
            # Actually, let's just wait for the top row to be ready.
            
            found = False
            for attempt in range(10): # 100 seconds total
                first_row = page.locator("table tbody tr").first
                status_text = first_row.inner_text()
                
                if download_text in status_text:
                    found = True
                    break
                elif processing_text in status_text:
                    self.log(f"      - Dang xu ly (Attempt {attempt+1}/10)...")
                    time.sleep(10)
                    # Refresh history list - usually there's a refresh button or just close/reopen
                    page.locator(".eds-modal__close").first.click()
                    time.sleep(1)
                    page.locator(f"button:has-text('{export_text}')").first.click()
                    page.locator(f"button:has-text('{history_text}')").first.click()
                    time.sleep(2)
                else:
                    self.log("      - Khong thay trang thai hop le.")
                    break

            if found:
                download_btn = page.locator("table tbody tr").first.locator(f"button:has-text('{download_text}')")
                with page.expect_download() as download_info:
                    download_btn.click()
                download = download_info.value
                
                today_str = datetime.now().strftime("%d%m%y")
                report_name_prefix = shop.get('report_name', 'Order')
                final_filename = f"SHP_{report_name_prefix}_{today_str}_{month}.xlsx"
                save_path = os.path.join(download_dir, final_filename)
                
                download.save_as(save_path)
                self.log(f"      ✅ OK: {final_filename}")
            else:
                self.log("      ❌ Time out hoac loi.")
                # Close modal
                try: page.locator(".eds-modal__close").first.click()
                except: pass
        except Exception as e:
            self.log(f"      ❌ Loi: {str(e)[:100]}")

    # ------------------------------------------------------
    #  HELPERS
    # ------------------------------------------------------

    def _launch_edge(self, playwright, profile_dir):
        self._kill_edge()
        time.sleep(1)
        try:
            subprocess.Popen([
                self.EDGE_PATH,
                f"--remote-debugging-port={self.CDP_PORT}",
                f"--user-data-dir={profile_dir}",
                "--no-first-run",
                "--disable-features=EdgeIdentitySignInFromAccountSettings",
            ], creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            time.sleep(5)
            return playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{self.CDP_PORT}")
        except Exception as e:
            self.log(f"  [LOI] Khong the mo Edge: {e}")
            return None

    def _kill_edge(self):
        try:
            subprocess.run(["taskkill", "/F", "/IM", "msedge.exe"], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        except: pass

    def _handle_login(self, page, shop_username):
        # Tuong tu TikTok, cho user login
        self._login_confirmed = False
        time.sleep(3)
        if "sale/order" in page.url and page.locator("button:has-text('Xuất')").first.is_visible(timeout=5000):
            return True
            
        self.log(f"\n⚠️ [{shop_username}] YEU CAU DANG NHAP!")
        self.log("  - Vui long dang nhap tren Edge.")
        self.log("  - Bam 'DA DANG NHAP XONG' de tiep tuc.")
        
        start = time.time()
        while time.time() - start < 300:
            if self._stop_requested: return False
            if self._login_confirmed: return True
            if "sale/order" in page.url and page.locator("button:has-text('Xuất')").first.is_visible(timeout=2000):
                return True
            time.sleep(2)
        return False


    def _load_shops(self, path):
        try:
            df = pd.read_excel(path)
            # Tên Shop, Tên Đăng nhập của Shop, BU, Report Name
            shops = []
            for _, row in df.iterrows():
                shops.append({
                    'shop_name': str(row['Tên Shop']).strip(),
                    'shop_username': str(row['Tên Đăng nhập của Shop']).strip(),
                    'account': str(row['BU']).strip(),
                    'report_name': str(row['Report Name']).strip() if 'Report Name' in df.columns else 'Order'
                })
            return shops
        except Exception as e:
            self.log(f"Loi doc file store list: {e}")
            return []

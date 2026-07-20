import os
import time
import re
import datetime
from playwright.sync_api import sync_playwright

class AnchantoAutomator:
    def __init__(self, log_callback, app_dir, config=None):
        self.log = log_callback
        self.app_dir = app_dir
        self.config = config
        self.login_url = config.get("anchanto_url", "https://apac-oms.anchanto.com/login")
        self.temp_download_dir = config.get("anchanto_download_dir", os.path.join(app_dir, "data", "reporting"))
        self.final_dest_dir = config.get("anchanto_final_path", r"C:\Users\thu.mai.dinh\OneDrive - DKSH\Operation CG - 7. Order Dropship Monitor\A. Anchanto")
        self.days_prior = int(config.get("anchanto_days_prior", 2))
        
        os.makedirs(self.temp_download_dir, exist_ok=True)
        if not os.path.exists(self.final_dest_dir):
            try: os.makedirs(self.final_dest_dir, exist_ok=True)
            except: pass

    def run_download(self, days_prior=None):
        """
        Khởi chạy trình duyệt và tải báo cáo Anchanto.
        days_prior: Số ngày lùi lại so với hôm nay (nếu None sẽ lấy từ config)
        """
        if days_prior is not None:
            self.days_prior = int(days_prior)
            
        self.log(f"[ANCHANTO] Khởi động quy trình tải báo cáo ({self.days_prior} ngày qua)...")
        
        with sync_playwright() as p:
            browser = None
            try:
                browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            except Exception:
                self.log("[ANCHANTO] Không tìm thấy Edge đang bật port 9222. Đang tự động khởi động trình duyệt...")
                import subprocess
                # 1. Dọn dẹp Edge cũ
                subprocess.run(["taskkill", "/F", "/IM", "msedge.exe"], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                time.sleep(2)
                
                # 2. Khởi động Edge thật với profile
                edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
                profile_dir = r"C:\ShopeeEdgeProfile"
                subprocess.Popen([edge_path, "--remote-debugging-port=9222", f"--user-data-dir={profile_dir}"])
                time.sleep(7)
                
                try:
                    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
                    self.log("[ANCHANTO] Đã tự kích hoạt và kết nối Edge thành công!")
                except Exception as e:
                    self.log(f"[LỖI CỰC ĐỘ] Vẫn không thể kết nối sau khi khởi động: {e}")
                    return None
            
            context = browser.contexts[0]
            page = context.new_page()
            
            try:
                # 1. Login
                self.log(f"[ANCHANTO] Truy cập: {self.login_url}")
                page.goto(self.login_url, wait_until="networkidle", timeout=90000)
                time.sleep(3)
                
                # Kiểm tra if đã đăng nhập (thường Edge Profile lưu sẵn)
                login_btn_selector = "button:has-text('Đăng nhập'), button:has-text('Login'), .btn-login"
                
                if page.locator(login_btn_selector).is_visible(timeout=5000):
                    self.log("[ANCHANTO] Thấy nút Đăng nhập. Tiến hành click...")
                    page.click(login_btn_selector)
                    page.wait_for_load_state("networkidle")
                    time.sleep(5)
                else:
                    self.log("[ANCHANTO] Có vẻ đã đăng nhập sẵn. Bỏ qua bước login.")

                # 2. Chuyển hướng tới trang All Orders
                order_url = "https://apac-oms.anchanto.com/order/all-orders"
                self.log(f"[ANCHANTO] Chuyển hướng tới trang Order...")
                time.sleep(2)
                page.goto(order_url, wait_until="networkidle", timeout=60000)
                time.sleep(5)

                # Check trang All Orders sẵn sàng (Sử dụng icon-download như bạn chỉ dẫn)
                export_btn_selector = "app-order-common-action .icon-download"
                
                try:
                    self.log("[ANCHANTO] Đang tìm icon Download để mở Export...")
                    page.wait_for_selector(export_btn_selector, timeout=25000)
                    self.log("[ANCHANTO] Giao diện Order đã sẵn sàng.")
                except:
                    self.log("[ANCHANTO] Không tìm thấy icon. Đang thử Refresh lại trang...")
                    page.reload()
                    page.wait_for_selector(export_btn_selector, timeout=25000)

                # 3. Mở Modal Export
                self.log("[ANCHANTO] Click icon để mở Modal Export...")
                page.click(export_btn_selector)
                time.sleep(3)

                # 4. Chọn "All orders" từ dropdown
                self.log("[ANCHANTO] Mở danh sách loại báo cáo và chọn 'All orders'...")
                page.click("body > ngb-modal-window ng-select")
                time.sleep(1)
                page.click("span.ng-option-label:has-text('All orders')")
                time.sleep(1)

                # 5. Chọn Ngày
                self.log(f"[ANCHANTO] Đang chọn khoảng thời gian ({self.days_prior} ngày trước)...")
                date_input_selector = "div.select-date div > input"
                page.click(date_input_selector)
                time.sleep(1)

                # Tính toán ngày và click chọn trên lịch
                try:
                    import re
                    today_dt = datetime.datetime.now()
                    start_dt = today_dt - datetime.timedelta(days=self.days_prior)
                    
                    start_day = str(start_dt.day)
                    end_day = str(today_dt.day)
                    
                    self.log(f"[ANCHANTO] Tìm ngày bắt đầu: {start_day} và kết thúc: {end_day}")

                    # Đợi bảng lịch thực tế xuất hiện (div.md-drppicker.shown)
                    calendar_locator = page.locator("div.md-drppicker.shown").first
                    
                    try:
                        # Kiểm tra xem lịch có hiện không, nếu không thử click lại
                        if not calendar_locator.is_visible():
                            self.log("[ANCHANTO] Lịch chưa hiện, đang click lại ô input...")
                            page.click(date_input_selector)
                        
                        calendar_locator.wait_for(state="visible", timeout=10000)
                        self.log("[ANCHANTO] Đã thấy bảng lịch hiển thị.")
                    except:
                        self.log("[!] Vẫn không thấy bảng lịch. Hãy kiểm tra trình duyệt.")
                        return None

                    time.sleep(1.5)

                    # HÀM HỖ TRỢ: Tìm bảng phù hợp với tháng/năm
                    def find_calendar_pane(dt):
                        target_month_val = str(dt.month - 1) # Jan=0, Feb=1...
                        
                        for pane_type in ["left", "right"]:
                            pane = calendar_locator.locator(f"div.calendar.{pane_type}")
                            if pane.is_visible():
                                try:
                                    # Kiểm tra giá trị đang được chọn trong thẻ <select class="monthselect">
                                    current_month_val = pane.locator("select.monthselect").input_value()
                                    if target_month_val == str(current_month_val):
                                        return pane
                                except: pass
                        return None

                    # Thực hiện chọn ngày
                    start_pane = find_calendar_pane(start_dt)
                    end_pane = find_calendar_pane(today_dt)
                    
                    # Fallback nếu không xác định được tháng
                    if not start_pane: start_pane = calendar_locator.locator("div.calendar.left")
                    if not end_pane: end_pane = calendar_locator.locator("div.calendar.right")

                    self.log(f"[ANCHANTO] Chọn ngày {start_day} ở bảng {('Trái' if 'left' in str(start_pane) else 'Phải')}...")
                    start_pane.locator("td.available:not(.off)").filter(has_text=re.compile(rf"^\s*{start_day}\s*$")).first.click()
                    time.sleep(0.5)
                    
                    self.log(f"[ANCHANTO] Chọn ngày {end_day} ở bảng {('Trái' if 'left' in str(end_pane) else 'Phải')}...")
                    end_pane.locator("td.available:not(.off)").filter(has_text=re.compile(rf"^\s*{end_day}\s*$")).last.click()
                    
                    time.sleep(1)
                except Exception as e:
                    self.log(f"[!] Lỗi chọn ngày chi tiết: {e}")

                # 6. Bấm Apply và xác nhận Export
                self.log("[ANCHANTO] Bấm Apply và xác nhận Export...")
                try:
                    # Ưu tiên bấm nút Apply nằm TRONG bộ lịch
                    calendar_locator.locator("button:has-text('Apply')").click(timeout=5000)
                except:
                    page.click("button:has-text('Apply')")
                time.sleep(1)
                
                click_start_time = datetime.datetime.now()
                # Nút Export cuối cùng (span text)
                page.click("span.create-order-btn:has-text('Export')")
                time.sleep(5)
                # 7. Chờ và Polling Download
                self.log("[ANCHANTO] Đang chờ file sẵn sàng (Kiểm tra Tên & Thời gian)...")
                # Tùy chỉnh: Mặc định 30 phút, nếu tải nhiều ngày thì cộng thêm 15 phút mỗi ngày (hoặc lấy từ config nếu có)
                default_wait = 30 if self.days_prior <= 2 else (30 + (self.days_prior - 2) * 15)
                max_wait_minutes = int(self.config.get("anchanto_timeout_minutes", default_wait))
                self.log(f"[ANCHANTO] Thời gian chờ tối đa được set là {max_wait_minutes} phút (cho {self.days_prior} ngày)")
                start_wait_time = time.time()
                
                while (time.time() - start_wait_time) < (max_wait_minutes * 60):
                    # Tên báo cáo ở dòng 1: cột 2 (Dùng .first để tránh lỗi trùng lặp span icon)
                    report_name_selector = "#table-scroll table tbody tr:nth-child(1) td:nth-child(2) span"
                    # Thời gian ở dòng 1: cột 3
                    report_time_selector = "#table-scroll table tbody tr:nth-child(1) td:nth-child(3) span"
                    # Trạng thái/Download ở dòng 1: cột 5
                    status_cell_selector = "#table-scroll table tbody tr:nth-child(1) td:nth-child(5)"

                    if page.locator(report_name_selector).first.is_visible():
                        name = page.locator(report_name_selector).first.inner_text().strip()
                        timestamp_str = page.locator(report_time_selector).first.inner_text().strip()
                        
                        # Kiểm tra xem có đúng là file "All Order Export" không
                        if "All Order Export" in name:
                            # Kiểm tra thời gian (Timestamp thường format DD/MM/YYYY HH:MM)
                            # Nếu file mới tạo trong vòng 5 phút đổ lại so với click_start_time thì ok
                            self.log(f"[ANCHANTO] Thấy file: {name} lúc {timestamp_str}")
                            
                            # Kiểm tra nút Download
                            download_btn = page.locator(f"{status_cell_selector} span.down-template-text")
                            if download_btn.is_visible():
                                self.log("[ANCHANTO] File đã sẵn sàng! Bắt đầu tải...")
                                with page.expect_download(timeout=300000) as download_info: # Tăng timeout tải xuống lên 5 phút
                                    download_btn.click()
                                
                                download = download_info.value
                                temp_path = os.path.join(self.temp_download_dir, download.suggested_filename)
                                download.save_as(temp_path)
                                
                                # Xử lý Convert XLS -> XLSX
                                final_filename = self._get_next_filename(start_dt, today_dt)
                                final_path = os.path.join(self.final_dest_dir, final_filename)
                                
                                success = self._convert_and_save(temp_path, final_path)
                                if success:
                                    self.log(f"[HOÀN TẤT] Báo cáo đã lưu và chuyển đổi chuẩn XLSX: {final_path}")
                                    return final_path
                                else:
                                    # Nếu convert fail, tiến trình thất bại vì PowerBI yêu cầu file xlsx
                                    self.log(f"[LỖI] Không thể chuyển đổi file thành chuẩn XLSX cho PowerBI.")
                                    return None
                        else:
                            self.log(f"[INFO] Đang đợi file của mình (Dòng 1 hiện là: {name})...")
                    
                    time.sleep(180) # Check download progress every 3 minutes                
                raise Exception(f"Quá thời gian chờ xuất file ({max_wait_minutes} phút).")

            except Exception as e:
                self.log(f"[ANCHANTO] Lỗi quy trình: {e}")
                return None

    def _convert_and_save(self, src, dest):
        """Chuyển đổi file từ .xls (Excel 97-2003) sang .xlsx (Định dạng bắt buộc cho Dashboard)"""
        import os
        import subprocess
        src = os.path.abspath(src)
        dest = os.path.abspath(dest)
        
        self.log(f"[HỆ THỐNG] Đang chuyển đổi định dạng Excel chuẩn XLSX cho {os.path.basename(src)}...")
        
        # 0. Gỡ block file (Mark of the Web) để tránh lỗi Protected View chặn win32com
        try:
            cmd = ["powershell", "-Command", f"Unblock-File -Path '{src}'"]
            subprocess.run(cmd, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        except Exception:
            pass
        
        # Thử phương án 1: Dùng win32com (Mô phỏng thao tác mở app Excel và Save As thủ công của bạn)
        import win32com.client as win32
        excel = None
        try:
            excel = win32.Dispatch('Excel.Application')
            excel.DisplayAlerts = False
            excel.Visible = False
            
            wb = excel.Workbooks.Open(src)
            # FileFormat 51 = xlOpenXMLWorkbook (.xlsx)
            wb.SaveAs(dest, FileFormat=51)
            wb.Close()
            self.log("[HỆ THỐNG] Đã tự động Save As bằng Excel COM thành công.")
            return True
        except Exception as e:
            self.log(f"[CẢNH BÁO] Không thể Save As bằng app Excel: {e}.")
            
            # Thử phương án 2: Dùng pandas tự đọc cấu trúc file và xuất xlsx
            self.log("[HỆ THỐNG] Đang thử build lại file XLSX bằng pandas...")
            try:
                import pandas as pd
                try:
                    df = pd.read_excel(src)
                except Exception:
                    try:
                        # Thử đọc dạng tab-separated
                        df = pd.read_csv(src, sep='\t')
                    except Exception:
                        try:
                            # Thử đọc comma-separated
                            df = pd.read_csv(src)
                        except Exception:
                            # Nếu file .xls thực chất là một bảng HTML
                            df = pd.read_html(src)[0]
                
                df.to_excel(dest, index=False)
                self.log("[HỆ THỐNG] Convert bằng pandas thành công.")
                return True
            except Exception as pandas_err:
                self.log(f"[LỖI CỰC ĐỘ] Không thể tự động build file XLSX: {pandas_err}.")
                return False
        finally:
            if excel:
                try: excel.Quit()
                except: pass

    def _get_next_filename(self, start_date, end_date):
        # Format: N_DD-DD.MM.xlsx
        # Example: 2_06-08.04.xlsx
        
        start_str = start_date.strftime("%d")
        end_str = end_date.strftime("%d.%m")
        date_segment = f"{start_str}-{end_str}"
        
        # Tìm prefix số lớn nhất
        files = os.listdir(self.final_dest_dir)
        max_num = 0
        for f in files:
            match = re.match(r"^(\d+)_", f)
            if match:
                num = int(match.group(1))
                if num > max_num: max_num = num
        
        next_num = max_num + 1
        return f"{next_num}_{date_segment}.xlsx"

    def extract_order_ids(self, file_path):
        """Trích xuất danh sách Order ID DUY NHẤT từ cột G của file Excel"""
        import pandas as pd
        self.log(f"[ANCHANTO] Đang trích xuất Order IDs UNIQUE từ cột G...")
        try:
            # Đọc file (hỗ trợ .xls và .xlsx)
            df = pd.read_excel(file_path)
            
            if df.empty:
                self.log("[CẢNH BÁO] File trống, không có dữ liệu để trích xuất.")
                return []

            # Trích xuất cột G (index 6)
            # Dùng dropna() để bỏ hàng trống và unique() để chỉ lấy các ID duy nhất
            ids = df.iloc[:, 6].dropna().unique().astype(str).tolist()
            
            # Làm sạch dữ liệu (bỏ khoảng trắng thừa)
            ids = [i.strip() for i in ids if i.strip()]
            
            self.log(f"[ANCHANTO] Đã trích xuất thành công {len(ids)} đơn hàng duy nhất.")
            return ids
        except Exception as e:
            self.log(f"[LỖI TRÍCH XUẤT] {e}")
            return []

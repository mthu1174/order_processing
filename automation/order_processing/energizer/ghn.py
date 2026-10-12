from automation.paths import find_edge_path
import os
import time
from playwright.sync_api import sync_playwright
import pandas as pd

class GHNAutomator:
    def __init__(self, log_callback, app_dir, config=None):
        self.log = log_callback
        self.app_dir = app_dir
        self.config = config
        self.user_data_dir = os.path.join(app_dir, "browser_data", "ghn")
        if config:
            self.download_dir = config.get("ghn_output_dir")
        else:
            self.download_dir = os.path.join(app_dir, "data", "ghn")
            
        # Đảm bảo thư mục tồn tại
        if self.download_dir:
            os.makedirs(self.download_dir, exist_ok=True)

    def run_ghn_workflow(self, excel_file_path):
        """
        Khởi chạy trình duyệt thật (Bypass Cloudflare) và thực hiện các bước đã ghi hình.
        """
        import subprocess
        import re
        self.log("[GHN] Đang khởi tạo trình duyệt Edge (Anti-Bot Cloudflare)...")
        
        # 1. Dọn dẹp Edge cũ để mở cổng CDP
        subprocess.run(["taskkill", "/F", "/IM", "msedge.exe"], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        time.sleep(2)
        
        # 2. Khởi động Edge thật với profile Shopee để dùng chung cookie/đăng nhập
        edge_path = find_edge_path()
        profile_dir = r"C:\ShopeeEdgeProfile"
        subprocess.Popen([edge_path, "--remote-debugging-port=9222", f"--user-data-dir={profile_dir}"])
        time.sleep(7) # Tăng thêm thời gian chờ Edge bung hẳn

        with sync_playwright() as p:
            try:
                browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
                self.log("[GHN] Đã kết nối với trình duyệt thành công.")
            except Exception as e:
                self.log(f"[LỖI] Không thể kết nối trình duyệt qua CDP: {e}")
                return None
                
            # Thử tìm page có sẵn hoặc tạo mới một cách an toàn
            context = browser.contexts[0]
            if len(context.pages) > 0:
                page = context.pages[0]
            else:
                page = context.new_page()
            
            try:
                self.log("[GHN] Đang truy cập trang chủ GHN...")
                # Thử lại tối đa 3 lần nếu bị đóng trình duyệt đột ngột hoặc lỗi mạng
                for attempt in range(3):
                    try:
                        page.goto("https://khachhang.ghn.vn/", timeout=60000)
                        break
                    except Exception as e_goto:
                        if attempt == 2: raise e_goto
                        self.log(f"[GHN] Thử lại lần {attempt+1} do lỗi: {e_goto}")
                        time.sleep(2)
                
                # Đợi trang tải hoàn tất các thành phần động
                page.wait_for_load_state("networkidle")
                
                # Kiểm tra đăng nhập (đã lưu trong profile)
                time.sleep(3)
                if "login" in page.url or "sso" in page.url:
                    self.log("[CẢNH BÁO] Vui lòng đăng nhập vào GHN để tiếp tục...")
                    while "login" in page.url or "sso" in page.url:
                        time.sleep(2)
                    self.log("[GHN] Phát hiện đã đăng nhập thành công.")
                
                # Đợi ổn định hiển thị kho
                time.sleep(2)

                # --- BẮT ĐẦU CÁC BƯỚC ĐÃ GHI HÌNH (CẬP NHẬT) ---
                self.log("[GHN] Đang kiểm tra và lựa chọn Store 'CG Store'...")
                switcher_selector = "#root > div.app > header > div.default-header > div.m-r-12.flex-right > div.switch-shop > div > div > div.switch-shop-header"
                
                store_verified = False
                for attempt in range(3):
                    try:
                        # 1. Kiểm tra xem có đang ở CG Store sẵn không
                        page.wait_for_selector(switcher_selector, timeout=15000)
                        current_store = page.locator(switcher_selector).inner_text()
                        
                        if "CG Store" in current_store or "CG" in current_store:
                            self.log(f"[GHN] Đã xác nhận đang ở đúng Store: {current_store.strip()}")
                            store_verified = True
                            break
                        
                        # 2. Nếu chưa đúng thì mở danh sách Store
                        self.log(f"[GHN] Store hiện tại ({current_store.strip()}) chưa đúng. Đang mở danh sách chọn lại (Lần {attempt+1})...")
                        page.locator(switcher_selector).click()
                        time.sleep(2)
                        
                        # 3. Tìm và click chọn CG Store
                        try:
                            target_store = page.get_by_text("CG Store", exact=False)
                            if target_store.count() > 0:
                                target_store.last.click(timeout=10000)
                            else:
                                # Cách dự phòng dùng regex
                                page.locator("div").filter(has_text=re.compile(r"CG Store")).last.click(timeout=10000)
                        except:
                            # Thử click vào bất kỳ item nào có text "CG Store" trong dropdown
                            page.locator(".ant-select-item-option-content").filter(has_text="CG Store").click(timeout=5000)

                        # 4. QUAN TRỌNG: Chờ trang refresh sau khi chọn Store (theo feedback người dùng)
                        self.log("[GHN] Đã bấm chọn CG Store, đang chờ trang refresh và ổn định...")
                        page.wait_for_load_state("networkidle")
                        # Thêm thời gian chờ cứng để chắc chắn database/UI đã cập nhật giá trị mới
                        time.sleep(5) 
                        
                        # 5. Kiểm tra lại lần nữa sau khi refresh
                        current_store_after = page.locator(switcher_selector).inner_text()
                        if "CG Store" in current_store_after or "CG" in current_store_after:
                            self.log(f"[GHN] Đã chọn Store thành công: {current_store_after.strip()}")
                            store_verified = True
                            break
                        else:
                            self.log(f"[GHN] CẢNH BÁO: Sau refresh vẫn hiển thị Store: {current_store_after.strip()}")
                    except Exception as e_store:
                        self.log(f"[GHN] Thao tác chọn store gặp lỗi (Lần {attempt+1}): {str(e_store)}")
                        time.sleep(3)

                if not store_verified:
                    self.log("[GHN] [LỖI NGHIÊM TRỌNG] Không thể xác nhận 'CG Store'. Dừng tiến trình để tránh lên đơn sai kho!")
                    return None
                
                self.log("[GHN] 1. Điều hướng tới trang Import (Lên đơn hàng loạt)...")
                page.goto("https://khachhang.ghn.vn/import", wait_until="networkidle")
                
                time.sleep(2)
                self.log("[GHN] 2. Click nút hành động chính (Chọn hình thức) và Tải file lên...")
                
                # Sử dụng expect_file_chooser để chặn ngay khi bấm nút 2
                try:
                    with page.expect_file_chooser(timeout=15000) as fc_info:
                        # Đây là selector thứ 2 bạn cung cấp, nó sẽ kích hoạt dialog chọn file
                        page.locator("#root > div.app > div.app-body.sss > main > div.container-fluid > div > div.import-home-content > div.import-home-left > div:nth-child(4) > div.action-info > span > button").click()
                    
                    file_chooser = fc_info.value
                    file_chooser.set_files(excel_file_path)
                    self.log(f"[GHN] Đã chọn và tải file lên thành công: {os.path.basename(excel_file_path)}")
                except Exception as e_upload:
                    self.log(f"[GHN] CẢNH BÁO: expect_file_chooser thất bại, thử set_input_files trực tiếp...")
                    try:
                        page.set_input_files("input[type='file']", excel_file_path)
                    except:
                        self.log(f"[GHN] LỖI KHÔNG THỂ TẢI FILE: {e_upload}")

                self.log("[GHN] Đang chờ file tải lên hoàn tất và chuyển sang trang Review...")
                
                # 3. Đợi chuyển sang trang review và kiểm tra tab lỗi/cảnh báo
                try:
                    page.wait_for_url("**/import/review*", timeout=60000)
                    self.log("[GHN] Đã chuyển sang trang Review. Đang kiểm tra các tab cảnh báo/lỗi...")
                except Exception as e_url:
                    self.log(f"[GHN] Cảnh báo: Không thể nhận diện URL review, vẫn tiếp tục kiểm tra tab: {e_url}")
                
                time.sleep(3)
                
                needs_pause = False
                warning_msg = []
                
                def get_tab_count(selector):
                    try:
                        if page.locator(selector).count() > 0:
                            text = page.locator(selector).inner_text(timeout=2000)
                            import re
                            m = re.search(r'\d+', text)
                            if m: return int(m.group())
                    except: pass
                    return 0
                
                warn_count = get_tab_count("div.import-review-tab > div.tab-warning")
                if warn_count > 0:
                    needs_pause = True
                    warning_msg.append(f"- {warn_count} đơn Đề xuất chỉnh sửa")
                    
                err_count = get_tab_count("div.import-review-tab > div.tab-error")
                if err_count > 0:
                    needs_pause = True
                    warning_msg.append(f"- {err_count} đơn Chưa hợp lệ")
                    
                rate_count = get_tab_count("div.import-review-tab > div.tab-rate")
                if rate_count > 0:
                    needs_pause = True
                    warning_msg.append(f"- {rate_count} đơn ở tab Rate")
                
                if needs_pause:
                    msg = "Phát hiện cần kiểm tra:\n" + "\n".join(warning_msg) + "\n\nVui lòng kiểm tra và xử lý trực tiếp trên trình duyệt GHN.\nSau khi xong, nhấn OK để tool tiếp tục Hoàn tất."
                    self.log(f"[CẢNH BÁO] {msg.replace(chr(10), ' ')}")
                    import tkinter as tk
                    from tkinter import messagebox
                    root = tk.Tk()
                    root.attributes('-topmost', True)
                    root.withdraw()
                    messagebox.showinfo("Tạm dừng Tool", msg, parent=root)
                    root.destroy()
                    self.log("[GHN] Người dùng đã xác nhận tiếp tục. Đang tiến hành Hoàn tất...")

                self.log("[GHN] 4. Click nút Tạo đơn hàng (Footer)...")
                try:
                    # Dùng thẳng selector chính xác do user cung cấp
                    create_btn_selector = "#root > div.app > div.app-body.sss > main > div.container-fluid > div > div.coin-footer.coin-footer-show > div.import-footer-action > button"
                    page.locator(create_btn_selector).wait_for(state="visible", timeout=60000)
                    time.sleep(1)
                    page.locator(create_btn_selector).click()
                except Exception as e:
                    self.log(f"[GHN] Cảnh báo lỗi bấm nút Tạo đơn: {e}")
                    # Nếu lỗi thì thử dùng fallback bằng regex text
                    try:
                        fallback_btn = page.locator("button").filter(has_text=re.compile(r"Tạo đơn hàng|Hoàn tất|Xác nhận")).last
                        fallback_btn.click(timeout=10000)
                    except:
                        pass
                
                self.log("[GHN] 5. Xác nhận Popup cuối cùng...")
                time.sleep(2)
                try:
                    confirm_btn = page.locator("div.modal.show button").filter(has_text=re.compile(r"Tiếp tục|Xác nhận|Đồng ý")).last
                    confirm_btn.click(timeout=10000)
                except:
                    page.locator("div.modal.show div.popup-confirm-footer > button").click(timeout=10000)
                
                # Đợi một chút sau khi bấm xác nhận để trang load danh sách hoàn tất
                time.sleep(5)
                
                self.log("[GHN] 6. Đang bấm nút Xuất file Excel kết quả...")
                # Selector người dùng cung cấp để xuất file Excel
                export_selector = "#root > div.app > div.app-body.sss > main > div.container-fluid > div > div:nth-child(3) > div > span:nth-child(3) > button"
                
                try:
                    # Chờ và thực hiện tải file về
                    with page.expect_download(timeout=60000) as download_info:
                        page.locator(export_selector).click()
                    
                    download = download_info.value
                    today_str = time.strftime("%d.%m")
                    download_path = os.path.join(self.download_dir, f"GHN_RETURN_ENERGIZER_{today_str}.xlsx")
                    
                    # Tạo thư mục nếu chưa có
                    os.makedirs(self.download_dir, exist_ok=True)
                    download.save_as(download_path)
                    
                    self.log(f"[GHN] Đã tải file kết quả về: {os.path.basename(download_path)}")
                    self.log("[GHN] Tải file lên GHN hoàn tất thành công!")
                    return download_path
                    
                except Exception as e_download:
                    self.log(f"[GHN] CẢNH BÁO: Không thể tải file kết quả: {e_download}")
                    return excel_file_path # Trả về file gốc nếu ko tải được file kết quả

            except Exception as e:
                self.log(f"[GHN] [LỖI] Thao tác thất bại: {str(e)}")
                return None
            finally:
                # Không đóng browser để user xem kết quả
                pass

    def extract_and_map_do(self, ghn_return_file, data_excel_file):
        """
        "lọc lấy mã vận đơn và order ID, r map với DO, có cái này thì gửi KHO"
        Dùng win32com để đọc file nếu đang mở, tránh lỗi Permission Denied.
        """
        import pythoncom
        import win32com.client
        
        self.log(f"[DO_MAP] Đang thực hiện Map DO từ Sharepoint vào file GHN...")
        pythoncom.CoInitialize()
        excel = None
        try:
            excel = win32com.client.GetActiveObject("Excel.Application")
        except:
            excel = win32com.client.Dispatch("Excel.Application")
        
        try:
            # 1. Đọc dữ liệu từ Sharepoint (thường đang mở)
            self.log(f"[DO_MAP] Đang lấy dữ liệu từ Template: {os.path.basename(data_excel_file)}")
            wb_sp = None
            try:
                wb_sp = excel.Workbooks(os.path.basename(data_excel_file))
            except:
                wb_sp = excel.Workbooks.Open(data_excel_file, ReadOnly=True)
            
            ws_sp = wb_sp.Sheets(1)
            last_row_sp = ws_sp.Cells(ws_sp.Rows.Count, 1).End(-4162).Row
            
            # Đọc cột A (Order ID) và cột M (DO)
            # Giả định Order ID ở cột A (1) và DO ở cột M (13)
            # Lọc lấy data vào list để mapping nhanh
            data_map = {}
            # Thử tìm header "Mã đơn hàng" hoặc "Order ID" trong hàng 2 hoặc 3
            # Dựa trên excel.py, dữ liệu bắt đầu từ dòng 3
            for r in range(3, last_row_sp + 1):
                order_id = str(ws_sp.Cells(r, 1).Value).strip() if ws_sp.Cells(r, 1).Value else None
                do_val = str(ws_sp.Cells(r, 13).Value).strip() if ws_sp.Cells(r, 13).Value else ""
                if order_id and order_id != "None" and order_id != "":
                    data_map[order_id] = do_val
            
            self.log(f"[DO_MAP] Đã tải {len(data_map)} bộ mã từ Template.")

            # 2. Xử lý file GHN Return
            self.log(f"[DO_MAP] Đang cập nhật file GHN: {os.path.basename(ghn_return_file)}")
            wb_ghn = None
            try:
                wb_ghn = excel.Workbooks(os.path.basename(ghn_return_file))
            except:
                wb_ghn = excel.Workbooks.Open(ghn_return_file)
            
            ws_ghn = wb_ghn.Sheets(1)
            last_row_ghn = ws_ghn.Cells(ws_ghn.Rows.Count, 1).End(-4162).Row
            
            # Tìm header trong GHN file (mở rộng phạm vi tìm kiếm)
            headers_dict = {}
            max_col = 0
            for c in range(1, 100):
                h = str(ws_ghn.Cells(1, c).Value).strip()
                if h and h != "None":
                    headers_dict[h] = c
                    max_col = c
            
            self.log("[DO_MAP] Đang dọn dẹp các cột dư thừa trong file GHN...")
            # Xóa các cột không cần thiết (chỉ giữ 'Mã đơn hàng' và 'Mã đơn hàng riêng')
            # Phải xóa từ phải qua trái để không bị lệch index
            for c in range(max_col, 0, -1):
                h = str(ws_ghn.Cells(1, c).Value).strip()
                if h not in ["Mã đơn hàng", "Mã đơn hàng riêng"]:
                    ws_ghn.Columns(c).Delete()
            
            # Sau khi xóa, cập nhật lại index
            headers_cleaned = {}
            for c in range(1, 10): # Bây giờ chỉ còn vài cột
                h = str(ws_ghn.Cells(1, c).Value).strip()
                if h and h != "None":
                    headers_cleaned[h] = c
            
            col_order_id_ghn = headers_cleaned.get("Mã đơn hàng riêng")
            col_do_ghn = headers_cleaned.get("Mã DO (DKSH)")
            
            if not col_do_ghn:
                col_do_ghn = len(headers_cleaned) + 1
                ws_ghn.Cells(1, col_do_ghn).Value = "Mã DO (DKSH)"
            
            count_mapped = 0
            self.log(f"[DO_MAP] Đang thực hiện map DO vào file đã dọn dẹp...")
            
            for r in range(2, last_row_ghn + 1):
                oid_ghn = str(ws_ghn.Cells(r, col_order_id_ghn).Value).strip()
                if oid_ghn.endswith(".0"):
                    oid_ghn = oid_ghn[:-2]
                
                if oid_ghn in data_map:
                    ws_ghn.Cells(r, col_do_ghn).Value = data_map[oid_ghn]
                    count_mapped += 1
            
            wb_ghn.Save()
            self.log(f"[DO_MAP] Hoàn tất! Đã map thành công {count_mapped} đơn hàng.")
            return ghn_return_file

        except Exception as e:
            self.log(f"[DO_MAP] Lỗi: {str(e)}")
            return None
        finally:
            pythoncom.CoUninitialize()


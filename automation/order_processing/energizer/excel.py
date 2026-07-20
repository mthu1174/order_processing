import os
import win32com.client
import pythoncom
import pandas as pd
from datetime import datetime
import time

class ExcelProcessor:
    def __init__(self, log_callback, app_dir, config=None):
        self.log = log_callback
        self.app_dir = app_dir
        self.config = config
        if config:
            self.output_dir = config.get("ghn_output_dir")
        else:
            self.output_dir = os.path.join(app_dir, "data")
            
        # Đảm bảo thư mục tồn tại
        if self.output_dir:
            os.makedirs(self.output_dir, exist_ok=True)

    def refresh_excel(self, file_path):
        """Khởi động Excel ngầm, mở file và bấm Refresh All"""
        self.log(f"[EXCEL] Đang mở Excel để Refresh data: {os.path.basename(file_path)}...")
        
        # Đảm bảo COM được khởi tạo cho thread
        pythoncom.CoInitialize()
        excel = None
        try:
            excel = win32com.client.DispatchEx("Excel.Application")
            excel.Visible = False
            excel.DisplayAlerts = False
            
            wb = excel.Workbooks.Open(file_path)
            self.log("[EXCEL] Đang Refresh All (Cập nhật kết nối dữ liệu)...")
            wb.RefreshAll()
            
            # Đợi refresh xong (BackgroundQuery = False trong kết nối là tốt nhất)
            # Hoặc force calculate
            excel.CalculateUntilAsyncQueriesDone()
            time.sleep(2)
            
            wb.Save()
            wb.Close(SaveChanges=True)
            self.log("[EXCEL] Refresh và lưu thành công.")
            return True
        except Exception as e:
            self.log(f"[EXCEL] Lỗi Refresh Excel: {str(e)}")
            return False
        finally:
            if excel:
                excel.Quit()
            pythoncom.CoUninitialize()

    def process_and_generate_ghn_file(self, shopee_order_file, refreshed_data_file):
        """
        Đọc file template Energizer, copy sang file mẫu upload GHN và lọc.
        """
        import shutil
        self.log("[EXCEL] Bắt đầu quy trình xử lý dữ liệu lên GHN...")
        
        # Luôn tìm file mẫu ghn (phôi) để làm căn bản: DKSH_ENERGIZER_xx.xx.xlsx
        # Ta sẽ dùng file cuối cùng trong config làm 'phôi'
        phoi_ghn_path = self.config.get("ghn_upload_template_path") if self.config else None
        
        today_str = datetime.now().strftime("%d.%m")
        new_file_name = f"DKSH_ENERGIZER_{today_str}.xlsx"
        output_file = os.path.join(os.path.dirname(phoi_ghn_path) if phoi_ghn_path else self.output_dir, new_file_name)

        if not phoi_ghn_path or not os.path.exists(phoi_ghn_path):
            self.log(f"[CẢNH BÁO] Không tìm thấy file phôi GHN tại: {phoi_ghn_path}")
            # Thử tìm file bất kỳ có tên DKSH_ENERGIZER_ trong thư mục đó
            if phoi_ghn_path:
                dir_name = os.path.dirname(phoi_ghn_path)
                files = [f for f in os.listdir(dir_name) if f.startswith("DKSH_ENERGIZER_") and f.endswith(".xlsx")]
                if files:
                    phoi_ghn_path = os.path.join(dir_name, files[0])
                    self.log(f"[EXCEL] Đã tự động chọn file phôi thay thế: {files[0]}")
            
        if not phoi_ghn_path or not os.path.exists(phoi_ghn_path):
            self.log("[DỪNG] Không có file phôi GHN để tạo file upload mới.")
            return None

        # 1. Khởi tạo Excel
        pythoncom.CoInitialize()
        excel = None
        try:
            excel = win32com.client.Dispatch("Excel.Application")
            excel.Visible = True 
            excel.DisplayAlerts = False
            
            # 2. XỬ LÝ FILE TEMPLATE (Sharepoint) TRƯỚC - ĐÂY LÀ NƠI CÓ POWER QUERY
            self.log(f"[EXCEL] Đang mở Template Sharepoint để Refresh: {os.path.basename(refreshed_data_file)}")
            wb_temp = excel.Workbooks.Open(refreshed_data_file)
            
            self.log("[EXCEL] Đang Refresh All (Kéo dữ liệu từ SAP vào Template)...")
            try:
                wb_temp.RefreshAll()
                # Chờ Excel hoàn tất refresh ngầm (Power Query thường chạy background)
                time.sleep(10)
                excel.CalculateUntilAsyncQueriesDone()
            except Exception as e_refresh:
                self.log(f"[CẢNH BÁO] RefreshAll gặp sự cố: {e_refresh}")
            
            wb_temp.Save()
            ws_temp = wb_temp.Sheets(1)
            self.log("[EXCEL] Template đã được refresh và lưu.")

            # 3. TẠO FILE GHN HÀNG NGÀY TỪ PHÔI
            self.log(f"[EXCEL] Đang tạo file GHN ngày {today_str} từ phôi...")
            if os.path.exists(output_file):
                try:
                    # Nếu file đang mở thì đóng lại để overwite
                    temp_wb = excel.Workbooks(new_file_name)
                    temp_wb.Close(SaveChanges=False)
                except: pass
                os.remove(output_file)
            
            shutil.copy2(phoi_ghn_path, output_file)
            
            # Gỡ bộ lọc nếu có để tính toán chính xác
            try:
                if ws_temp.AutoFilterMode:
                    ws_temp.AutoFilterMode = False
            except:
                ws_temp = wb_temp.Sheets(1)
                if ws_temp.AutoFilterMode:
                    ws_temp.AutoFilterMode = False
                
            last_row_temp = ws_temp.Cells(ws_temp.Rows.Count, 1).End(-4162).Row # xlUp = -4162
            
            if last_row_temp >= 3:
                self.log("[EXCEL] Đang ép lại công thức cho Table 'ORDERS' tại Cột O...")
                for i in range(3):
                    try:
                        formula_o = "=RIGHT([@[Số điện thoại]],LEN([@[Số điện thoại]])-2)"
                        ws_temp.Range(f"O3:O{last_row_temp}").Formula = formula_o
                        break
                    except Exception as e_formula:
                        if i == 2:
                            self.log(f"[CẢNH BÁO] Không thể gán công thức sau 3 lần thử: {e_formula}")
                        else:
                            time.sleep(2)
                
                time.sleep(1)
            
            self.log("[EXCEL] Lọc các đơn thỏa mãn (B: Trạng thái, L: DO khác #N/A)...")
            
            # Đảm bảo gỡ toàn bộ filter cũ (kể cả trong ListObject nếu có) trước khi tạo filter mới
            try:
                if ws_temp.AutoFilterMode:
                    ws_temp.AutoFilterMode = False
                if ws_temp.FilterMode:
                    ws_temp.ShowAllData()
                # Xoá filter trên các table (nếu có)
                if ws_temp.ListObjects.Count > 0:
                    for lo_idx in range(1, ws_temp.ListObjects.Count + 1):
                        lo = ws_temp.ListObjects(lo_idx)
                        if lo.AutoFilter and lo.AutoFilter.FilterMode:
                            lo.AutoFilter.ShowAllData()
            except: pass
            
            for i in range(3):
                try:
                    ws_temp.Range(f"A2:AH{last_row_temp}").AutoFilter(
                        Field=2, 
                        Criteria1=["Chờ giao hàng", "Đang giao"], 
                        Operator=7
                    )
                    ws_temp.Range(f"A2:AH{last_row_temp}").AutoFilter(
                        Field=12,
                        Criteria1="<>#N/A",
                        Operator=1, # 1 means xlAnd
                        Criteria2="<>0"
                    )
                    break
                except Exception as e_filter:
                    if i == 2: self.log(f"[CẢNH BÁO] Lỗi Filter: {e_filter}")
                    time.sleep(2)
            
            self.log("[EXCEL] Thiết lập khu vực copy từ Q3 đến AH...")
            try:
                copy_range = ws_temp.Range(f"Q3:AH{last_row_temp}").SpecialCells(12)
                has_data = True
            except:
                has_data = False
                
            if has_data:
                self.log(f"[EXCEL] Mở file Upload Đích: {new_file_name}")
                wb_target = excel.Workbooks.Open(output_file)
                ws_target = wb_target.Sheets(1)
                
                self.log("[EXCEL] Xoá dữ liệu cũ từ dòng 5...")
                ws_target.Rows("5:10000").Delete()
                
                self.log("[EXCEL] Đang Copy dữ liệu từ Template...")
                copy_range.Copy()
                
                self.log("[EXCEL] Dán (Paste Values) vào ô A5...")
                ws_target.Range("A5").PasteSpecial(Paste=-4163)
                
                wb_target.Save()
                wb_target.Close()
                self.log(f"[EXCEL] Hoàn tất cập nhật vào file Upload GHN: {new_file_name}!")
            else:
                self.log("[CẢNH BÁO] Không tìm thấy dữ liệu nào thoả mãn trong Template!")
                wb_target = excel.Workbooks.Open(output_file)
                ws_target = wb_target.Sheets(1)
                ws_target.Rows("5:10000").Delete()
                wb_target.Save()
                wb_target.Close()

            # Trả lại trạng thái không lọc cho file template trước khi lưu
            if ws_temp.AutoFilterMode:
                ws_temp.AutoFilterMode = False
            wb_temp.Save()
            # Không đóng để user kiểm tra nếu muốn
            
            return output_file
        except Exception as e:
            self.log(f"[EXCEL] Lỗi nghiêm trọng do thao tác Excel: {str(e)}")
            return None
        finally:
            # excel.Quit() # Không đóng Excel để đề phòng lúc user đang coi file khác
            pythoncom.CoUninitialize()


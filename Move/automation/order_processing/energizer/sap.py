import win32com.client
import pythoncom
import time
import os
import pyperclip

class SAPAutomator:
    def __init__(self, log_callback, app_dir, config=None):
        self.log = log_callback
        self.app_dir = app_dir
        self.config = config
        if config:
            self.download_dir = config.get("sap_export_dir")
        else:
            self.download_dir = os.path.join(app_dir, "data", "sap")
            
        # Đảm bảo thư mục tồn tại
        if self.download_dir:
            os.makedirs(self.download_dir, exist_ok=True)

    def _cleanup_folder(self):
        """Xoá các file cũ trong thư mục SAP để tránh nhầm lẫn"""
        try:
            if os.path.exists(self.download_dir):
                for f in os.listdir(self.download_dir):
                    if f.endswith(".xlsx") or f.endswith(".XLSX"):
                        os.remove(os.path.join(self.download_dir, f))
                self.log(f"[SAP] Đã dọn dẹp thư mục: {self.download_dir}")
        except Exception as e:
            self.log(f"[SAP] Lỗi dọn dẹp: {e}")

    def run_sap_export(self, tcode, order_ids, shopee_filename="", forced_start_date=None, export_subtype="Regular"):
        """
        Khởi chạy automation SAP.
        forced_start_date: Nếu có, sẽ ưu tiên dùng ngày này (format DD.MM.YYYY)
        export_subtype: "Regular" hoặc "Reporting"
        """
        # Bỏ qua bước dọn dẹp nếu là subtype Reporting để bảo vệ file cũ và Template
        if export_subtype != "Reporting":
            self._cleanup_folder()
        else:
            self.log("[SAP] Chế độ Reporting: Giữ lại toàn bộ file cũ và Template.")
            
        import re
        from datetime import datetime
        
        # Mặc định lấy ngày hôm nay if không có info gì khác
        start_date = datetime.now().strftime("%d.%m.%Y")
        
        if forced_start_date:
            start_date = forced_start_date
            self.log(f"[SAP] Sử dụng ngày bắt đầu được chỉ định: {start_date}")
        elif shopee_filename:
            # Tìm kiếm chuỗi định dạng YYYYMMDD_ ví dụ 20260307_
            match = re.search(r'(\d{4})(\d{2})(\d{2})_', shopee_filename)
            if match:
                y, m, d = match.groups()
                start_date = f"{d}.{m}.{y}"
                self.log(f"[SAP] Ngày lấy từ Shopee File: {start_date}")

        try:
            # Khởi tạo COM để dùng trong thread
            pythoncom.CoInitialize()
            
            # --- XÁC ĐỊNH ĐƯỜNG DẪN VÀ TÊN FILE THEO SUBTYPE ---
            if export_subtype == "Reporting":
                export_dir = r"C:\Users\thu.mai.dinh\OneDrive - DKSH\Operation CG - 7. Order Dropship Monitor\5. SAP"
                # Tìm số thứ tự lớn nhất trong folder (0, 1, 2, 3...)
                max_num = -1
                if os.path.exists(export_dir):
                    for f in os.listdir(export_dir):
                        # Tìm các file có định dạng là số (0.xlsx, 1.xlsx...)
                        name_match = re.match(r'^(\d+)\.xlsx$', f, re.IGNORECASE)
                        if name_match:
                            num = int(name_match.group(1))
                            if num > max_num: max_num = num
                
                export_name = f"{max_num + 1}.xlsx"
                self.log(f"[SAP] Chế độ Reporting: Sẽ lưu file là '{export_name}'")
            else:
                export_dir = r"C:\Users\thu.mai.dinh\OneDrive - DKSH\1. Order processing\2. Energizer\SAP"
                export_name = "sap_energizer_data.xlsx"

            export_file_path = os.path.join(export_dir, export_name)
            os.makedirs(export_dir, exist_ok=True)

            self.log("[SAP] Đang kiểm tra trạng thái phần mềm SAP...")
            try:
                sap_gui_auto = win32com.client.GetObject("SAPGUI")
            except Exception:
                self.log("[SAP] SAP đang KHÔNG BẬT. Tiến hành tự động đánh thức SAP qua hệ thống SSO...")
                import subprocess
                # Đường dẫn phổ biến của SAP Logon
                sap_exe = r"C:\Program Files (x86)\SAP\FrontEnd\SAPgui\saplogon.exe"
                if not os.path.exists(sap_exe):
                    sap_exe = r"C:\Program Files\SAP\FrontEnd\SAPgui\saplogon.exe"
                
                subprocess.Popen([sap_exe])
                
                # Chờ tối đa 15s để SAP Logon bung lên RAM
                for _ in range(15):
                    time.sleep(1)
                    try:
                        sap_gui_auto = win32com.client.GetObject("SAPGUI")
                        break
                    except:
                        pass
                else:
                    self.log("[SAP] LỖI CỰC ĐỘ: Không thể khởi động được SAP. Xin hãy mở thủ công!")
                    return None

            application = sap_gui_auto.GetScriptingEngine
            
            # GỌI CÀI ĐẶT SSO TỰ ĐỘNG
            if application.Connections.Count == 0:
                self.log("[SAP] Đang truy cập máy chủ đặc quyền: 01A  P00 HERMES [PROD]...")
                try:
                    # Chữ True thứ 2 là Sync (đợi tải xong mới phản hồi)
                    connection = application.OpenConnection("01A  P00 HERMES [PROD]", True)
                    time.sleep(3) # Cấp thời gian cho SSO nhảy múa
                except Exception as e:
                    self.log(f"[SAP] LỖI KHÔNG THỂ BẤM VÀO SERVER TRONG DANH SÁCH: {e}")
                    return None
            else:
                connection = application.Children(0)

            session = connection.Children(0)
            
            # --- XỬ LÝ LOGIN (NẾU KHÔNG PHẢI SSO) ---
            try:
                # Kiểm tra xem có đang ở màn hình Login không
                # Browser field id: usr/txtRSYST-BNAME
                sap_user = self.config.get("sap_user")
                sap_pass = self.config.get("sap_password")
                
                if sap_user and sap_pass:
                    try:
                        user_field = session.findById("wnd[0]/usr/txtRSYST-BNAME")
                        pass_field = session.findById("wnd[0]/usr/pwdRSYST-BCODE")
                        
                        if user_field:
                            self.log(f"[SAP] Đang thực hiện đăng nhập thủ công với User: {sap_user}...")
                            user_field.text = sap_user
                            pass_field.text = sap_pass
                            session.findById("wnd[0]").sendVKey(0) # Nhấn Enter để Login
                            time.sleep(3)
                    except:
                        # Nếu không tìm thấy field login, có thể là do SSO đã pass
                        pass
            except Exception as e:
                self.log(f"[CẢNH BÁO] Lỗi trong quá trình kiểm tra Login: {e}")
            
            # --- CẬP NHẬT: TỰ ĐỘNG XỬ LÝ WINDOW THÔNG BÁO LICENSE (MULTIPLE LOGONS) ---
            try:
                time.sleep(3) # Đợi popup ổn định
                # Kiểm tra số lượng children của session (thường wnd[0] và wnd[1] nếu có popup)
                if session.Children.Count > 1:
                    popup = session.findById("wnd[1]")
                    wnd_title = popup.text
                    
                    if "License Information" in wnd_title or "Multiple Logons" in wnd_title:
                        self.log("[SAP] Phát hiện thông báo Multiple Logons. Đang thực hiện đá các phiên khác...")
                        
                        try:
                            popup.findById("usr/radMULTI_LOGON_OPT2").select()
                            self.log("[SAP] Đã chọn Option 2 'Continue and end' theo code mẫu.")
                        except:
                            try:
                                popup.findById("usr/radMULTI_LOGON_OPT1").select()
                                self.log("[SAP] Đã chọn Option 1.")
                            except Exception as e_rad:
                                self.log(f"[CẢNH BÁO] Không tìm thấy Radio Button: {e_rad}")
                        
                        try:
                            popup.findById("tbar[0]/btn[0]").press()
                            self.log("[SAP] Đã nhấn Xác nhận (Đá các phiên khác thành công).")
                        except Exception as e_btn:
                            self.log(f"[CẢNH BÁO] Không thể nhấn Xác nhận: {e_btn}")
                        
                        time.sleep(2)
            except Exception as e_license:
                self.log(f"[SAP-DEBUG] Kiểm tra License: {e_license}")

            self.log(f"[SAP] Ép thoát các tiến trình cũ và vào T-Code gốc: /n{tcode}...")
            session.findById("wnd[0]").maximize()
            session.findById("wnd[0]/tbar[0]/okcd").text = f"/n{tcode}"
            session.findById("wnd[0]").sendVKey(0) # Nhấn Enter
            time.sleep(1)

            self.log(f"[SAP] Đang chọn variant '{os.getenv('SAP_VARIANT', 'ecom')}'...")
            try:
                session.findById("wnd[0]").sendVKey(17) # Shift+F5
                time.sleep(1)
                session.findById("wnd[1]/usr/txtV-LOW").text = "ecom"
                try:
                    session.findById("wnd[1]/usr/txtENAME-LOW").text = ""
                except: pass
                session.findById("wnd[1]/tbar[0]/btn[8]").press()
                self.log("[SAP] Đã áp dụng Variant 'ecom'.")
            except Exception as e_var:
                self.log(f"[CẢNH BÁO] Không thể chọn Variant: {str(e_var)}")
                time.sleep(2)

            self.log("[SAP] Dán Order IDs từ Clipboard vào Multiple Selection...")
            clipboard_text = "\r\n".join([str(x) for x in order_ids])
            pyperclip.copy(clipboard_text)

            session.findById("wnd[0]/usr/btn%_S_BSTKD_%_APP_%-VALU_PUSH").press()
            session.findById("wnd[1]/tbar[0]/btn[24]").press() # Upload from clipboard
            session.findById("wnd[1]/tbar[0]/btn[8]").press()  # Execute (Transfer)
            
            self.log(f"[SAP] Điền ngày bắt đầu: {start_date}...")
            session.findById("wnd[0]/usr/ctxtS_ERDAT-LOW").text = start_date
            session.findById("wnd[0]/usr/ctxtS_ERDAT-LOW").setFocus()
            session.findById("wnd[0]/usr/ctxtS_ERDAT-LOW").caretPosition = 2

            self.log("[SAP] Thực thi báo cáo (F8)...")
            session.findById("wnd[0]/tbar[1]/btn[8]").press()
            time.sleep(3)

            self.log("[SAP] Đang chờ xuất file...")
            session.findById("wnd[0]").sendVKey(43) # Spreadsheet lookup
            time.sleep(1)
            
            try:
                session.findById("wnd[1]/tbar[0]/btn[0]").press()
            except: pass
            
            # Ép ghi đường dẫn không cần bật popup chọn thư mục bằng Windows
            session.findById("wnd[1]/usr/ctxtDY_PATH").text = export_dir
            session.findById("wnd[1]/usr/ctxtDY_FILENAME").text = export_name
            
            try:
                # Nếu file đã tồn tại, nút Replace thường là btn[11]
                session.findById("wnd[1]/tbar[0]/btn[11]").press()
            except:
                # Nếu file chưa tồn tại, bấm nút Generate btn[0]
                session.findById("wnd[1]/tbar[0]/btn[0]").press()
            
            time.sleep(5)
            self._close_excel_file(export_name)
            
            self.log(f"[SAP] Xuất file thành công ra: {export_file_path}")
            return export_file_path

        except Exception as e:
            self.log(f"[SAP] [LỖI] SAP Automation Error: {str(e)}")
            return None
        finally:
            pythoncom.CoUninitialize()

    def _close_excel_file(self, filename):
        """Đóng file Excel cụ thể bằng tên if đang mở"""
        try:
            excel = win32com.client.GetActiveObject("Excel.Application")
            for wb in excel.Workbooks:
                if wb.Name.lower() == filename.lower():
                    wb.Close(SaveChanges=True)
                    self.log(f"[SAP] Đã tự động đóng file Excel: {filename}")
                    break
        except Exception:
            # Nếu không tìm thấy Excel đang chạy thì thôi
            pass


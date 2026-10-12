import os
import shutil
import re
from datetime import datetime
import win32com.client as win32

class HandoverOrderAutomation:
    def __init__(self, config_manager=None, log_callback=None):
        self.config_manager = config_manager
        self.log_callback = log_callback if log_callback else print

    def log(self, message):
        self.log_callback(message)

    def process(self):
        source_file = os.path.join(os.path.expanduser("~"), r"OneDrive - DKSH\1. Order processing\4. Pending_dontUse\PENDING_ORDER_CHECK 1.xlsx")
        processed_dir = os.path.join(os.path.expanduser("~"), r"OneDrive - DKSH\1. Order processing\4. Pending_dontUse\Processed Files")
        
        if self.config_manager:
            source_file = self.config_manager.get("handover_source_file", source_file)
            processed_dir = self.config_manager.get("handover_processed_dir", processed_dir)
        
        platforms = {
            "shopee": "Shopee",
            "lazada": "Lazada",
            "tiktokshop": "Tiktokshop"
        }

        self.log(f"Bắt đầu xử lý Đơn bàn giao...")
        
        excel = None
        try:
            self.log(f"Đang mở file: {os.path.basename(source_file)}")
            excel = win32.DispatchEx("Excel.Application")
            excel.Visible = False
            excel.DisplayAlerts = False
            
            wb_source = excel.Workbooks.Open(source_file)
            
            self.log("Đang làm mới dữ liệu (Refresh All)... Quá trình này có thể mất vài phút.")
            # Disable background refresh for all connections to make RefreshAll synchronous
            for conn in wb_source.Connections:
                try:
                    if conn.Type == 1: # OLEDB
                        conn.OLEDBConnection.BackgroundQuery = False
                    elif conn.Type == 2: # ODBC
                        conn.ODBCConnection.BackgroundQuery = False
                except Exception as e:
                    pass
            
            wb_source.RefreshAll()
            try:
                excel.CalculateUntilAsyncQueriesDone()
            except Exception:
                pass
            self.log("Làm mới dữ liệu thành công.")
            
            wb_source.Save()
            
            today_str = datetime.now().strftime('%d.%m')
            
            for tab_name, folder_name in platforms.items():
                self.log(f"--------------------------------------------------")
                self.log(f"Đang xử lý nền tảng: {tab_name.upper()}...")
                
                # Check if tab exists
                try:
                    ws_source = wb_source.Sheets(tab_name)
                except Exception:
                    self.log(f"Lỗi: Không tìm thấy sheet '{tab_name}' trong file nguồn.")
                    continue
                
                # Find last row in source
                last_row_source = ws_source.Cells(ws_source.Rows.Count, "A").End(-4162).Row # xlUp
                if last_row_source < 6:
                    self.log(f"Không có dữ liệu mới cho {tab_name}.")
                    continue
                
                # Target folder
                target_folder = os.path.join(processed_dir, folder_name)
                if not os.path.exists(target_folder):
                    self.log(f"Lỗi: Không tìm thấy folder đích {target_folder}")
                    continue
                
                # Find template file in folder
                template_file = None
                for f in os.listdir(target_folder):
                    if f.endswith('.xlsx') and not f.startswith('~$'):
                        template_file = f
                        break
                
                if not template_file:
                    self.log(f"Lỗi: Không tìm thấy file mẫu trong folder {folder_name}")
                    continue
                
                template_path = os.path.join(target_folder, template_file)
                
                # Generate new filename
                match = re.search(r'\d{2}\.\d{2}', template_file)
                if match:
                    new_file_name = template_file[:match.start()] + today_str + template_file[match.end():]
                else:
                    new_file_name = template_file.replace('.xlsx', f'_{today_str}.xlsx')
                
                new_file_path = os.path.join(target_folder, new_file_name)
                
                # Backup and copy template to new file
                if os.path.exists(new_file_path):
                    self.log(f"File {new_file_name} đã tồn tại, sẽ ghi đè...")
                shutil.copy2(template_path, new_file_path)
                
                self.log(f"Đã tạo file mới: {new_file_name}")
                
                # Open new file
                wb_target = excel.Workbooks.Open(new_file_path)
                ws_target = wb_target.Sheets(1)
                
                # Clear old data in target starting from row 2
                last_row_target_old = ws_target.Cells(ws_target.Rows.Count, "A").End(-4162).Row
                if last_row_target_old >= 2:
                    ws_target.Range(f"A2:H{last_row_target_old}").ClearContents()
                
                # Copy from source
                source_range = ws_source.Range(f"A6:H{last_row_source}")
                source_range.Copy()
                
                # Paste to target
                target_range = ws_target.Range("A2")
                target_range.PasteSpecial(Paste=-4163) # xlPasteValues
                target_range.PasteSpecial(Paste=-4122) # xlPasteFormats
                
                # AutoFit columns
                ws_target.Columns("A:H").AutoFit()
                
                wb_target.Save()
                wb_target.Close(SaveChanges=True)
                
                self.log(f"Đã lưu thành công {last_row_source - 5} dòng dữ liệu vào {new_file_name}")
            
            self.log(f"--------------------------------------------------")
            wb_source.Close(SaveChanges=False)
            self.log("HOÀN THÀNH TẤT CẢ QUÁ TRÌNH!")
            
        except Exception as e:
            self.log(f"LỖI NGHIÊM TRỌNG: {str(e)}")
        finally:
            if excel:
                try:
                    excel.Quit()
                except:
                    pass

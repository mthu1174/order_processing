import customtkinter as ctk
import threading
import os
import tkinter.messagebox as messagebox
from gui.views.base_view import BaseView

class AnchantoReportView(BaseView):
    def __init__(self, master, config_manager, **kwargs):
        super().__init__(master, config_manager, **kwargs)
        
        self.create_header("Anchanto Daily Reporting")
        
        # Main layout
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.grid(row=1, column=0, padx=30, pady=10, sticky="nsew")
        self.container.grid_columnconfigure(0, weight=3) # Console
        self.container.grid_columnconfigure(1, weight=1) # Controls
        self.container.grid_rowconfigure(0, weight=1)

        # 1. Console Card
        self.console_card = self.create_card(self.container)
        self.console_card.grid(row=0, column=0, padx=(0, 15), sticky="nsew")
        self.console_card.grid_columnconfigure(0, weight=1)
        self.console_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self.console_card, 
            text="LIVE CONSOLE", 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#999999"
        ).grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")

        self.log_textbox = ctk.CTkTextbox(
            self.console_card, 
            state="disabled", 
            wrap="word", 
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color="#FDFDFD",
            border_width=1,
            border_color="#F0F0F0",
            text_color="#333333"
        )
        self.log_textbox.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")

        # Pipeline State
        self.pipeline_context = {
            "anchanto_file": None,
            "order_ids": None
        }
        self._stop_requested = False
        self._is_running = False

        # 2. Control Card
        self.control_card = self.create_card(self.container)
        self.control_card.grid(row=0, column=1, sticky="nsew")
        
        ctk.CTkLabel(
            self.control_card, 
            text="QUY TRÌNH BÁO CÁO", 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#999999"
        ).pack(pady=(20, 10))
        
        # Config Options Frame
        self.settings_frame = ctk.CTkFrame(self.control_card, fg_color="transparent")
        self.settings_frame.pack(fill="x", padx=20, pady=(10, 0))
        
        ctk.CTkLabel(self.settings_frame, text="Khoảng tgian (Ngày lùi / DD.MM-DD.MM):", font=ctk.CTkFont(size=11)).pack(side="left", padx=5)
        self.days_entry = ctk.CTkEntry(self.settings_frame, width=40, font=ctk.CTkFont(size=11))
        self.days_entry.pack(side="left", padx=5)
        self.days_entry.insert(0, "2")

        # Steps Container
        self.steps_frame = ctk.CTkFrame(self.control_card, fg_color="transparent")
        self.steps_frame.pack(fill="x", padx=20, pady=5)

        self.step_widgets = {}
        steps_config = [
            ("anchanto", "1. Tải Anchanto Report"),
            ("sap", "2. SAP Export Data"),
            ("confirm_so", "3. Confirm SO"),
            ("powerbi", "4. Refresh Power BI")
        ]

        for step_id, step_name in steps_config:
            frame = ctk.CTkFrame(self.steps_frame, fg_color="transparent")
            frame.pack(fill="x", pady=2)
            
            check_var = ctk.BooleanVar(value=True)
            cb = ctk.CTkCheckBox(frame, text=step_name, variable=check_var, font=ctk.CTkFont(size=12), checkbox_width=18, checkbox_height=18)
            cb.pack(side="left", padx=(0, 5))
            
            run_btn = ctk.CTkButton(
                frame, text="▶", width=25, height=25, 
                fg_color="transparent", text_color="#C30021", hover_color="#F0F0F0",
                command=lambda s=step_id: self.start_single_step(s)
            )
            run_btn.pack(side="right")
            
            status_dot = ctk.CTkFrame(frame, width=8, height=8, corner_radius=4, fg_color="#DDDDDD")
            status_dot.pack(side="right", padx=5)

            self.step_widgets[step_id] = {
                "checkbox": cb,
                "var": check_var,
                "status_dot": status_dot
            }

        self.status_label = ctk.CTkLabel(self.control_card, text="Trạng thái: Sẵn sàng", font=ctk.CTkFont(size=12))
        self.status_label.pack(pady=(15, 5))

        self.start_button = ctk.CTkButton(
            self.control_card, 
            text="CHẠY CÁC MỤC CHỌN", 
            command=self.start_automation,
            fg_color="#C30021",
            hover_color="#A0001B",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=40,
            corner_radius=8
        )
        self.start_button.pack(padx=20, pady=5, fill="x")

        self.stop_button = ctk.CTkButton(
            self.control_card, 
            text="DỪNG QUY TRÌNH", 
            command=self.stop_automation,
            fg_color="white",
            text_color="#666666",
            border_color="#CCCCCC",
            border_width=1,
            hover_color="#F5F5F5",
            height=35,
            corner_radius=8
        )
        self.stop_button.pack(padx=20, pady=5, fill="x")
        self.stop_button.configure(state="disabled")

    def set_status(self, text, color="#27AE60"):
        self.status_label.configure(text=f"Trạng thái: {text}")

    def update_step_status(self, step_id, status):
        """status: pending, running, success, error"""
        colors = {"pending": "#DDDDDD", "running": "#E67E22", "success": "#27AE60", "error": "#C30021"}
        if step_id in self.step_widgets:
            self.step_widgets[step_id]["status_dot"].configure(fg_color=colors.get(status, "#DDDDDD"))

    def stop_automation(self):
        self._stop_requested = True
        self.log("\n[HỆ THỐNG] Đang yêu cầu dừng quy trình...")
        self.stop_button.configure(state="disabled", text="ĐANG DỪNG...")

    def start_automation(self):
        selected_steps = [s_id for s_id, w in self.step_widgets.items() if w["var"].get()]
        if not selected_steps:
             messagebox.showwarning("Cảnh báo", "Vui lòng chọn ít nhất một bước để chạy.")
             return
        
        self.log("\n" + "="*50)
        self.log(f"[HỆ THỐNG] Bắt đầu chạy các bước đã chọn: {', '.join(selected_steps)}")
        self._stop_requested = False
        thread = threading.Thread(target=self.run_pipeline_thread, args=(selected_steps,))
        thread.daemon = True
        thread.start()

    def run_full_automation(self):
        """Method called by Scheduler to run the entire pipeline"""
        if self._is_running:
            self.log("[SCHEDULER] Không thể chạy Báo cáo: Một quy trình khác đang chạy.")
            return False
            
        # All steps for reporting
        all_steps = ["anchanto", "sap", "confirm_so", "powerbi"]
        self.log("\n" + "="*50)
        self.log(f"[SCHEDULER] Kích hoạt chạy tự động toàn bộ quy trình Báo cáo")
        self._stop_requested = False
        thread = threading.Thread(target=self.run_pipeline_thread, args=(all_steps,))
        thread.daemon = True
        thread.start()
        return True

    def start_single_step(self, step_id):
        if self._is_running:
            messagebox.showwarning("Cảnh báo", "Quy trình khác đang chạy.")
            return
        
        self.log("\n" + "="*50)
        self.log(f"[HỆ THỐNG] Chạy riêng lẻ bước: {step_id}")
        self._stop_requested = False
        thread = threading.Thread(target=self.run_pipeline_thread, args=([step_id],))
        thread.daemon = True
        thread.start()

    def run_pipeline_thread(self, steps_to_run):
        self._is_running = True
        self.set_status("Đang chạy...", "#E67E22")
        self.start_button.configure(state="disabled", fg_color="#CCCCCC")
        self.stop_button.configure(state="normal", text="DỪNG QUY TRÌNH")
        
        try:
            for step_id in steps_to_run:
                if self._stop_requested:
                    self.log("\n[HỆ THỐNG] Đã dừng theo yêu cầu người dùng.")
                    break
                
                self.update_step_status(step_id, "running")
                success = self._execute_step(step_id)
                
                if success:
                    self.update_step_status(step_id, "success")
                else:
                    self.update_step_status(step_id, "error")
                    self.log(f"[LỖI] Bước '{step_id}' thất bại.")
                    break
            
            if self._stop_requested: self.set_status("Đã dừng", "#E67E22")
            elif all(self.step_widgets[s]["status_dot"].cget("fg_color") == "#27AE60" for s in steps_to_run):
                self.set_status("Hoàn tất", "#27AE60")
            else: self.set_status("Bị lỗi", "#C30021")

        except Exception as e:
            self.log(f"\n[LỖI] Sự cố hệ thống: {str(e)}")
            self.set_status("Lỗi hệ thống", "#C30021")
        finally:
            self._is_running = False
            self.start_button.configure(state="normal", fg_color="#C30021")
            self.stop_button.configure(state="disabled", text="DỪNG QUY TRÌNH")

    def _execute_step(self, step_id):
        try:
            if step_id == "anchanto": return self._step_anchanto()
            if step_id == "sap": return self._step_sap()
            if step_id == "confirm_so": return self._step_confirm_so()
            if step_id == "powerbi": return self._step_powerbi()
            return False
        except Exception as e:
            self.log(f"[ERROR] Step {step_id}: {e}")
            return False

    def _get_today_anchanto_file(self, directory):
        import glob
        import re
        from datetime import datetime, timedelta
        
        files = glob.glob(os.path.join(directory, "*.xlsx"))
        if not files: return None
        
        latest_file = sorted(files, key=os.path.getmtime, reverse=True)[0]
        filename = os.path.basename(latest_file)
        
        # Parse format: N_DD-DD.MM.xlsx (e.g., 2_06-08.04.xlsx)
        match = re.search(r"^\d+_(\d{2})-(\d{2})\.(\d{2})\.xlsx$", filename)
        if match:
            start_day = int(match.group(1))
            end_day = int(match.group(2))
            month = int(match.group(3))
            year = datetime.now().year
            
            # Xử lý bước nhảy tháng (nếu ngày bắt đầu > ngày kết thúc)
            start_month = month
            start_year = year
            if start_day > end_day:
                start_month -= 1
                if start_month == 0:
                    start_month = 12
                    start_year -= 1
            
            try:
                report_start_date = datetime(start_year, start_month, start_day)
                self.pipeline_context["report_start_date"] = report_start_date
                self.log(f"[INFO] Tự động nhận diện ngày bắt đầu từ file: {report_start_date.strftime('%d.%m.%Y')}")
            except: pass
            
        return latest_file

    def _step_anchanto(self):
        from automation.reporting.daily_reporting.anchanto import AnchantoAutomator
        from datetime import datetime, timedelta
        
        time_input = self.days_entry.get().strip()
        if not time_input:
            self.log(f"[BƯỚC 1] Ô thời gian trống. Sẽ tải file đầu tiên có sẵn trên Anchanto...")
        else:
            self.log(f"[BƯỚC 1] Đang tải báo cáo từ Anchanto (Input: {time_input})...")
        bot = AnchantoAutomator(self.log, os.getcwd(), self.config_manager)
        file_path = bot.run_download(time_input=time_input)
        
        if file_path:
            self.pipeline_context["anchanto_file"] = file_path
            self.pipeline_context["order_ids"] = bot.extract_order_ids(file_path)
            
            # Lấy ngày D (start date) từ tên file
            import re
            basename = os.path.basename(file_path)
            # Chấp nhận cả DD.MM-DD.MM và DD-DD.MM
            match = re.search(r"(\d{1,2})(?:\.\d{1,2})?-(\d{1,2}\.\d{1,2})", basename)
            if match:
                s_str = match.group(1)
                e_str = match.group(2)
                y = datetime.now().year
                try:
                    if '.' in s_str:
                        s_d, s_m = map(int, s_str.split('.'))
                    else:
                        s_d = int(s_str)
                        e_d, e_m = map(int, e_str.split('.'))
                        if s_d > e_d:
                            s_m = e_m - 1 if e_m > 1 else 12
                            if s_m == 12: y -= 1
                        else:
                            s_m = e_m
                    self.pipeline_context["report_start_date"] = datetime(y, s_m, s_d)
                except:
                    self.pipeline_context["report_start_date"] = datetime.now()
            else:
                self.pipeline_context["report_start_date"] = datetime.now()
                
            return True
        return False

    def _step_sap(self):
        from automation.order_processing.energizer.sap import SAPAutomator
        from datetime import timedelta
        
        order_ids = self.pipeline_context.get("order_ids")
        anchanto_file = self.pipeline_context.get("anchanto_file")
        report_start_date = self.pipeline_context.get("report_start_date")
        
        if not order_ids:
            self.log("[INFO] Order IDs trống, đang tìm báo cáo Anchanto gần nhất...")
            anchanto_dir = self.config_manager.get("anchanto_final_path", os.path.join(os.getcwd(), "data"))
            anchanto_file = self._get_today_anchanto_file(anchanto_dir)
            if anchanto_file:
                from automation.reporting.daily_reporting.anchanto import AnchantoAutomator
                bot_anchanto = AnchantoAutomator(self.log, os.getcwd(), self.config_manager)
                order_ids = bot_anchanto.extract_order_ids(anchanto_file)
                # report_start_date được cập nhật trong _get_today_anchanto_file
                report_start_date = self.pipeline_context.get("report_start_date")
        
        if not order_ids:
            self.log("[LỖI] Không tìm thấy Order IDs để chạy SAP.")
            return False

        self.log("[BƯỚC 2] Đang Export dữ liệu từ SAP cho Reporting...")
        bot = SAPAutomator(self.log, os.getcwd(), self.config_manager)
        tcode = self.config_manager.get("sap_tcode_reporting", "YSD_OC_GEN_R004")
        
        # Tính toán ngày D-1
        forced_date = None
        if report_start_date:
            sap_date = report_start_date - timedelta(days=1)
            forced_date = sap_date.strftime("%d.%m.%Y")
            self.log(f"[INFO] Ngày bắt đầu Anchanto (D) là {report_start_date.strftime('%d.%m')}. Thiết lập SAP (D-1) là: {forced_date}")

        sap_file = bot.run_sap_export(
            tcode=tcode, 
            order_ids=order_ids, 
            export_subtype="Reporting", 
            forced_start_date=forced_date
        )
        if sap_file: 
            self.pipeline_context["sap_file"] = sap_file
            return True
        return False

    def _step_powerbi(self):
        from automation.reporting.daily_reporting.powerbi_web import PowerBIWebAutomator
        self.log("[BƯỚC 4] Đang kích hoạt Refresh Power BI Dataset...")
        bot = PowerBIWebAutomator(self.log, os.getcwd(), self.config_manager)
        return bot.trigger_refresh()

    def _step_confirm_so(self):
        from automation.order_processing.energizer.sap import SAPAutomator
        
        import os
        import re

        sap_file = self.pipeline_context.get("sap_file")
        if not sap_file:
            self.log("[INFO] Không tìm thấy kết quả từ bước trước, đang tìm file SAP mới nhất...")
            sap_dir = self.config_manager.get("sap_final_path", os.path.join(os.path.expanduser("~"), r"OneDrive - DKSH\Operation CG - 7. Order Dropship Monitor\5. SAP"))
            
            if os.path.exists(sap_dir):
                max_num = -1
                latest_f = None
                for f in os.listdir(sap_dir):
                    match = re.match(r"^(\d+)\.xlsx$", f, re.IGNORECASE)
                    if match:
                        num = int(match.group(1))
                        if num > max_num:
                            max_num = num
                            latest_f = f
                if latest_f:
                    sap_file = os.path.join(sap_dir, latest_f)
                    self.log(f"[INFO] Đã tìm thấy file SAP mới nhất: {latest_f}")

        if not sap_file:
            self.log("[LỖI] Không tìm thấy file SAP. Không thể Confirm SO.")
            return False

        self.log("[BƯỚC 3] Tiến hành Confirm SO trên SAP (Tcode VL10a)...")
        bot = SAPAutomator(self.log, os.getcwd(), self.config_manager)
        
        # Read file SAP to find SO without DO (E has SO, G has DO)
        import pandas as pd
        import shutil
        import os
        try:
            temp_copy = sap_file + ".tmp.xlsx"
            shutil.copy2(sap_file, temp_copy)
            df = pd.read_excel(temp_copy)
            try:
                os.remove(temp_copy)
            except:
                pass
            # Column E is index 4, Column G is index 6
            # Fillna to check easily
            so_list = []
            for index, row in df.iterrows():
                try:
                    so = str(row.iloc[4]).strip()
                    do = str(row.iloc[6]).strip()
                    if so and so.lower() != 'nan' and (not do or do.lower() == 'nan' or do == 'None'):
                        so_list.append(so)
                except Exception:
                    pass
            
            # Remove duplicates
            so_list = list(set(so_list))
        except Exception as e:
            self.log(f"[LỖI] Lỗi đọc file SAP: {e}")
            return False

        if not so_list:
            self.log("[INFO] Tất cả SO đều đã có DO. Bỏ qua chạy VL10a.")
            return True

        self.log(f"[INFO] Tìm thấy {len(so_list)} SO chưa có DO. Đang chạy VL10a...")
        
        # Run confirm_so function in SAPAutomator
        new_sap_file = bot.run_confirm_so(so_list, self.config_manager.get("sap_tcode_reporting", "YSD_OC_GEN_R004"))
        
        if new_sap_file:
            # Update pipeline with new file so it's clear
            self.pipeline_context["sap_file"] = new_sap_file
            return True
        return False


import customtkinter as ctk
import threading
import os
import tkinter.messagebox as messagebox
from gui.views.base_view import BaseView

class EnergizerView(BaseView):
    def __init__(self, master, config_manager, **kwargs):
        super().__init__(master, config_manager, **kwargs)
        
        self.create_header("Energizer Automation")
        
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

        # State for pipeline
        self.pipeline_context = {
            "shopee_file": None,
            "order_ids": None,
            "sap_file": None,
            "ghn_file": None,
            "ghn_return_file": None
        }
        self._stop_requested = False
        self._is_running = False

        # 2. Control Card
        self.control_card = self.create_card(self.container)
        self.control_card.grid(row=0, column=1, sticky="nsew")
        
        ctk.CTkLabel(
            self.control_card, 
            text="QUY TRÌNH", 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#999999"
        ).pack(pady=(20, 10))
        
        # Steps Container
        self.steps_frame = ctk.CTkFrame(self.control_card, fg_color="transparent")
        self.steps_frame.pack(fill="x", padx=20, pady=5)

        self.step_widgets = {}
        steps_config = [
            ("shopee", "1. Tải Shopee Orders"),
            ("sap", "2. SAP Export Data"),
            ("excel", "3. Xử lý File Excel"),
            ("ghn", "4. Upload GHN & Label"),
            ("warehouse", "5. Gán DO cho Kho")
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
                "status_dot": status_dot,
                "frame": frame
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

        self.test_ghn_button = ctk.CTkButton(
            self.control_card, 
            text="🧪 Test GHN Upload", 
            command=self.start_test_ghn, 
            fg_color="transparent",
            text_color="#E67E22",
            font=ctk.CTkFont(size=11),
            height=30
        )
        self.test_ghn_button.pack(padx=20, pady=(10, 0), fill="x")

    def set_status(self, text, color="#27AE60"):
        self.status_label.configure(text=f"Trạng thái: {text}")

    def update_step_status(self, step_id, status):
        """status: pending, running, success, error"""
        colors = {"pending": "#DDDDDD", "running": "#E67E22", "success": "#27AE60", "error": "#C30021"}
        if step_id in self.step_widgets:
            self.step_widgets[step_id]["status_dot"].configure(fg_color=colors.get(status, "#DDDDDD"))

    def stop_automation(self):
        self._stop_requested = True
        self.log("\n[HỆ THỐNG] Đang yêu cầu dừng quy trình... Vui lòng đợi bước hiện tại kết thúc.")
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
            self.log("[SCHEDULER] Không thể chạy Energizer: Một quy trình khác đang chạy.")
            return False
        
        # All steps for Energizer
        all_steps = ["shopee", "sap", "excel", "ghn", "warehouse"]
        self.log("\n" + "="*50)
        self.log(f"[SCHEDULER] Kích hoạt chạy tự động toàn bộ quy trình Energizer")
        self._stop_requested = False
        thread = threading.Thread(target=self.run_pipeline_thread, args=(all_steps,))
        thread.daemon = True
        thread.start()
        return True

    def start_single_step(self, step_id):
        if self._is_running:
            messagebox.showwarning("Cảnh báo", "Quy trình khác đang chạy. Vui lòng đợi hoặc dừng lại.")
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
                    self.log(f"[LỖI] Bước '{step_id}' thất bại. Dừng quy trình.")
                    break
            
            if self._stop_requested:
                self.set_status("Đã dừng", "#E67E22")
            elif all(self.step_widgets[s]["status_dot"].cget("fg_color") == "#27AE60" for s in steps_to_run):
                self.set_status("Hoàn tất", "#27AE60")
            else:
                self.set_status("Bị lỗi", "#C30021")

        except Exception as e:
            self.log(f"\n[LỖI] Sự cố hệ thống: {str(e)}")
            self.set_status("Lỗi hệ thống", "#C30021")
        finally:
            self._is_running = False
            self.start_button.configure(state="normal", fg_color="#C30021")
            self.stop_button.configure(state="disabled", text="DỪNG QUY TRÌNH")

    def _execute_step(self, step_id):
        """Điều hướng thực thi từng bước"""
        try:
            if step_id == "shopee": return self._step_shopee()
            if step_id == "sap": return self._step_sap()
            if step_id == "excel": return self._step_excel()
            if step_id == "ghn": return self._step_ghn()
            if step_id == "warehouse": return self._step_warehouse()
            return False
        except Exception as e:
            self.log(f"[ERROR] Step {step_id}: {e}")
            return False

    def _get_today_file(self, pattern, directory):
        """Tìm file gần nhất theo pattern trong ngày hôm nay"""
        import glob
        from datetime import datetime
        today = datetime.now().strftime("%d.%m")
        # Logic tìm file gợi ý nếu context trống
        files = glob.glob(os.path.join(directory, pattern.format(date=today)))
        if files:
            return sorted(files, key=os.path.getmtime, reverse=True)[0]
        return None

    def _step_shopee(self):
        from automation.order_processing.energizer.shopee import ShopeeAutomator
        self.log("[BƯỚC 1] Đang tải đơn hàng từ Shopee...")
        bot = ShopeeAutomator(self.log, os.getcwd(), self.config_manager)
        file_path = bot.run_download_orders()
        if file_path:
            self.pipeline_context["shopee_file"] = file_path
            self.pipeline_context["order_ids"] = bot.extract_order_ids(file_path)
            return True
        return False

    def _step_sap(self):
        from automation.order_processing.energizer.sap import SAPAutomator
        order_ids = self.pipeline_context.get("order_ids")
        shopee_file = self.pipeline_context.get("shopee_file")
        
        if not order_ids:
            self.log("[INFO] Order IDs trống, đang cố gắng đọc từ file Shopee gần nhất...")
            if not shopee_file:
                shopee_dir = self.config_manager.get("shopee_download_dir", os.path.join(os.getcwd(), "data"))
                shopee_file = self._get_today_file("Order.all.*.xlsx", shopee_dir)
            if shopee_file:
                from automation.order_processing.energizer.shopee import ShopeeAutomator
                bot_shopee = ShopeeAutomator(self.log, os.getcwd(), self.config_manager)
                order_ids = bot_shopee.extract_order_ids(shopee_file)
        
        if not order_ids:
            self.log("[LỖI] Không tìm thấy Order IDs để chạy SAP.")
            return False

        self.log("[BƯỚC 2] Đang Export dữ liệu từ SAP...")
        bot = SAPAutomator(self.log, os.getcwd(), self.config_manager)
        tcode = self.config_manager.get("sap_tcode", "YSD_OC_GEN_R004")
        sap_file = bot.run_sap_export(tcode, order_ids, os.path.basename(shopee_file) if shopee_file else "Manual_Run")
        if sap_file:
            self.pipeline_context["sap_file"] = sap_file
            return True
        return False

    def _step_excel(self):
        from automation.order_processing.energizer.excel import ExcelProcessor
        shopee_file = self.pipeline_context.get("shopee_file")
        if not shopee_file:
            shopee_dir = self.config_manager.get("shopee_download_dir", os.path.join(os.getcwd(), "data"))
            shopee_file = self._get_today_file("Order.all.*.xlsx", shopee_dir)
        
        sharepoint_file = self.config_manager.get("sharepoint_template_path")
        
        self.log("[BƯỚC 3] Đang xử lý file Excel & Refresh Data...")
        bot = ExcelProcessor(self.log, os.getcwd(), self.config_manager)
        ghn_file = bot.process_and_generate_ghn_file(shopee_file, sharepoint_file)
        if ghn_file:
            self.pipeline_context["ghn_file"] = ghn_file
            return True
        return False

    def _step_ghn(self):
        from automation.order_processing.energizer.ghn import GHNAutomator
        ghn_file = self.pipeline_context.get("ghn_file")
        if not ghn_file:
            ghn_file = self._get_today_file("DKSH_ENERGIZER_*.xlsx", self.config_manager.get("ghn_output_dir", os.path.join(os.getcwd(), "data")))
        
        if not ghn_file:
            self.log("[LỖI] Không tìm thấy file upload GHN.")
            return False
            
        self.log(f"[CHỜ] Xác nhận file: {os.path.basename(ghn_file)}")
        is_ok = messagebox.askokcancel("Xác nhận GHN", f"Sẵn sàng upload file:\n{os.path.basename(ghn_file)}\n\nBấm OK để tiếp tục.")
        if not is_ok: return False

        self.log("[BƯỚC 4] Đang upload lên GHN & lấy mã vận đơn...")
        bot = GHNAutomator(self.log, os.getcwd(), self.config_manager)
        ghn_return = bot.run_ghn_workflow(ghn_file)
        if ghn_return:
            self.pipeline_context["ghn_return_file"] = ghn_return
            return True
        return False

    def _step_warehouse(self):
        from automation.order_processing.energizer.ghn import GHNAutomator
        ghn_return = self.pipeline_context.get("ghn_return_file")
        if not ghn_return:
            ghn_dir = self.config_manager.get("ghn_output_dir", os.path.join(os.getcwd(), "data"))
            ghn_return = self._get_today_file("GHN_RETURN_ENERGIZER_*.xlsx", ghn_dir)
            
        if not ghn_return:
            self.log("[LỖI] Không tìm thấy file kết quả từ GHN.")
            return False

        sharepoint_file = self.config_manager.get("sharepoint_template_path")
        self.log("[BƯỚC 5] Đang ánh xạ DO và tạo file bàn giao Kho...")
        bot = GHNAutomator(self.log, os.getcwd(), self.config_manager)
        warehouse_file = bot.extract_and_map_do(ghn_return, sharepoint_file)
        if warehouse_file:
            self.log(f"[KHO] File bàn giao: {warehouse_file}")
            return True
        return False

    def start_test_ghn(self):
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(title="Chọn file Excel", filetypes=[("Excel files", "*.xlsx")])
        if not file_path: return
        self.log(f"\n[TEST GHN] Bắt đầu test với file: {os.path.basename(file_path)}")
        thread = threading.Thread(target=self.run_test_ghn_thread, args=(file_path,))
        thread.daemon = True
        thread.start()

    def run_test_ghn_thread(self, file_path):
        from automation.order_processing.energizer.ghn import GHNAutomator
        app_dir = os.getcwd()
        self.config_manager.load_config()
        self.test_ghn_button.configure(state="disabled")
        try:
            ghn_bot = GHNAutomator(self.log, app_dir, self.config_manager)
            ghn_return_file = ghn_bot.run_ghn_workflow(file_path)
            if ghn_return_file: self.log(f"[TEST GHN] Hoàn tất! File: {ghn_return_file}")
            else: self.log("[TEST GHN] Thất bại.")
        except Exception as e: self.log(f"[TEST GHN] Lỗi: {e}")
        finally: self.test_ghn_button.configure(state="normal")

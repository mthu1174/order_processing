import customtkinter as ctk
import threading
import os
import json
from datetime import datetime
import tkinter.messagebox as messagebox
from tkinter import filedialog
from gui.views.base_view import BaseView


class LazadaOrderView(BaseView):
    """GUI View cho chức năng Tải Đơn hàng Lazada."""

    def __init__(self, master, config_manager, **kwargs):
        super().__init__(master, config_manager, **kwargs)

        self.create_header("Lazada Order Downloader")

        # Main layout
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.grid(row=1, column=0, padx=30, pady=10, sticky="nsew")
        self.container.grid_columnconfigure(0, weight=3)  # Console
        self.container.grid_columnconfigure(1, weight=1)  # Controls
        self.container.grid_rowconfigure(0, weight=1)

        # ── 1. Console Card ──
        self.console_card = self.create_card(self.container)
        self.console_card.grid(row=0, column=0, padx=(0, 15), sticky="nsew")
        self.console_card.grid_columnconfigure(0, weight=1)
        self.console_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self.console_card,
            text="LIVE CONSOLE",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#999999",
        ).grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")

        self.log_textbox = ctk.CTkTextbox(
            self.console_card,
            state="disabled",
            wrap="word",
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color="#FDFDFD",
            border_width=1,
            border_color="#F0F0F0",
            text_color="#333333",
        )
        self.log_textbox.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")

        # ── 2. Control Card ──
        self.control_card = self.create_card(self.container)
        self.control_card.grid(row=0, column=1, sticky="nsew")

        # Scrollable container for controls
        self.scroll_frame = ctk.CTkScrollableFrame(
            self.control_card, fg_color="transparent"
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # ── SETTINGS SECTION ──
        ctk.CTkLabel(
            self.scroll_frame,
            text="CÀI ĐẶT TẢI ĐƠN",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#999999",
        ).pack(pady=(10, 10))

        # Year Selection
        self.year_var = ctk.IntVar(value=datetime.now().year)
        self._create_label_input(self.scroll_frame, "Chọn Năm:", self.year_var, list(range(2023, 2027)))

        # Month Selection (Multi-select)
        ctk.CTkLabel(
            self.scroll_frame,
            text="Chọn Tháng:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#333333",
        ).pack(padx=15, pady=(10, 2), anchor="w")

        self.month_vars = {}
        month_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        month_frame.pack(fill="x", padx=15)
        
        # Grid of 4x3 for months
        for i in range(1, 13):
            self.month_vars[i] = ctk.BooleanVar(value=False)
            cb = ctk.CTkCheckBox(
                month_frame, 
                text=f"T{i}", 
                variable=self.month_vars[i],
                font=ctk.CTkFont(size=11),
                width=50
            )
            cb.grid(row=(i-1)//4, column=(i-1)%4, padx=2, pady=2, sticky="w")

        # Shortcut Folder Path
        self.shortcut_folder_var = ctk.StringVar(value="")
        self._create_path_section(
            self.scroll_frame, 
            "Thư mục chứa Shortcut:", 
            self.shortcut_folder_var, 
            self._browse_shortcut_folder
        )

        # Download Path
        self.download_path_var = ctk.StringVar(value="data/order/lazada")
        self._create_path_section(
            self.scroll_frame, 
            "Thư Mục Lưu:", 
            self.download_path_var, 
            self._browse_download_dir
        )

        # ── STORE SELECTION SECTION ──
        ctk.CTkLabel(
            self.scroll_frame,
            text="CHỌN SHOP CẦN TẢI:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#999999",
        ).pack(pady=(15, 5))

        self.shop_checkbox_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        self.shop_checkbox_frame.pack(fill="x", padx=15)
        
        self.shop_vars = {} # {lnk_path: var}
        
        ctk.CTkButton(
            self.scroll_frame,
            text="🔄 LOAD DANH SÁCH SHOP",
            command=self._load_shops_to_gui,
            font=ctk.CTkFont(size=11),
            height=28,
            fg_color="#f0f0f0",
            text_color="#333333",
            hover_color="#e0e0e0"
        ).pack(padx=15, pady=5, fill="x")

        # ── Status ──
        self.status_label = ctk.CTkLabel(
            self.scroll_frame,
            text="Trạng thái: Sẵn sàng",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#27AE60"
        )
        self.status_label.pack(pady=(20, 5))

        # ── Run Button ──
        self.run_button = ctk.CTkButton(
            self.scroll_frame,
            text="▶  BẮT ĐẦU TẢI ĐƠN",
            command=self._start_automation,
            fg_color="#0F146D", # Lazada Dark Blue
            hover_color="#0B0E4D",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=45,
            corner_radius=8,
        )
        self.run_button.pack(padx=15, pady=(10, 5), fill="x")

        # ── Confirm Login Button ──
        self.confirm_login_button = ctk.CTkButton(
            self.scroll_frame,
            text="✅ ĐÃ ĐĂNG NHẬP XONG",
            command=self._confirm_login_clicked,
            fg_color="#27AE60",
            hover_color="#219150",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=35,
            corner_radius=8,
        )
        self.confirm_login_button.pack(padx=15, pady=(10, 5), fill="x")
        self.confirm_login_button.configure(state="disabled")

        # ── Stop Button ──
        self.stop_button = ctk.CTkButton(
            self.scroll_frame,
            text="DỪNG LẠI",
            command=self._stop_automation,
            fg_color="white",
            text_color="#666666",
            border_color="#CCCCCC",
            border_width=1,
            hover_color="#F5F5F5",
            height=35,
            corner_radius=8,
        )
        self.stop_button.pack(padx=15, pady=5, fill="x")
        self.stop_button.configure(state="disabled")

        # ── State ──
        self._is_running = False
        self._automator = None
        
        self._load_config()

    # ─────────────── UI Helpers ───────────────

    def _create_label_input(self, parent, label_text, variable, values):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(frame, text=label_text, font=ctk.CTkFont(size=11, weight="bold")).pack(side="left")
        menu = ctk.CTkOptionMenu(frame, variable=variable, values=[str(v) for v in values], width=100)
        menu.pack(side="right")

    def _create_path_section(self, parent, label_text, variable, command):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=15, pady=8)
        ctk.CTkLabel(frame, text=label_text, font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        
        inner_frame = ctk.CTkFrame(frame, fg_color="transparent")
        inner_frame.pack(fill="x", pady=2)
        
        ctk.CTkEntry(inner_frame, textvariable=variable, font=ctk.CTkFont(size=10), height=25).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(inner_frame, text="📂", width=30, height=25, command=command).pack(side="right")

    # ─────────────── Config ───────────────

    def _load_config(self):
        try:
            config_path = os.path.join(os.getcwd(), "lazada_config.json")
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config = json.load(f)
                self.year_var.set(config.get("year", datetime.now().year))
                self.shortcut_folder_var.set(config.get("shortcut_folder", ""))
                self.download_path_var.set(config.get("download_path", "data/order/lazada"))
                
                selected_months = config.get("selected_months", [])
                for m in selected_months:
                    if m in self.month_vars:
                        self.month_vars[m].set(True)
        except: pass

    def _save_config(self):
        try:
            config = {
                "year": self.year_var.get(),
                "selected_months": [m for m, v in self.month_vars.items() if v.get()],
                "shortcut_folder": self.shortcut_folder_var.get(),
                "download_path": self.download_path_var.get()
            }
            with open("lazada_config.json", "w") as f:
                json.dump(config, f, indent=4)
        except: pass

    # ─────────────── Callbacks ───────────────

    def _browse_shortcut_folder(self):
        p = filedialog.askdirectory()
        if p: self.shortcut_folder_var.set(p)

    def _browse_download_dir(self):
        p = filedialog.askdirectory()
        if p: self.download_path_var.set(p)

    def _load_shops_to_gui(self):
        path = self.shortcut_folder_var.get()
        if not path or not os.path.exists(path):
            messagebox.showwarning("Lỗi", "Vui lòng chọn thư mục chứa Shortcut (.lnk) hợp lệ.")
            return
            
        # Clear existing
        for widget in self.shop_checkbox_frame.winfo_children():
            widget.destroy()
        self.shop_vars = {}

        try:
            count = 0
            for f in os.listdir(path):
                if f.lower().endswith(".lnk"):
                    shop_name = os.path.splitext(f)[0]
                    lnk_path = os.path.join(path, f)
                    
                    var = ctk.BooleanVar(value=True)
                    cb = ctk.CTkCheckBox(
                        self.shop_checkbox_frame, 
                        text=f"{shop_name} (.lnk)", 
                        variable=var,
                        font=ctk.CTkFont(size=11)
                    )
                    cb.pack(anchor="w", padx=5, pady=2)
                    self.shop_vars[lnk_path] = {"var": var, "name": shop_name}
                    count += 1
            if count == 0:
                messagebox.showinfo("Thông báo", "Không tìm thấy file .lnk nào trong thư mục.")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể đọc thư mục: {e}")

    def _confirm_login_clicked(self):
        if self._automator: self._automator.confirm_login()

    def _start_automation(self):
        if self._is_running: return
        
        months = [m for m, v in self.month_vars.items() if v.get()]
        if not months:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng chọn ít nhất một tháng.")
            return

        # Get selected shortcuts
        selected_shortcuts = []
        for lnk_path, data in self.shop_vars.items():
            if data['var'].get():
                selected_shortcuts.append((lnk_path, data['name']))
        
        if not selected_shortcuts and self.shop_vars:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng chọn ít nhất một shop.")
            return

        shortcut_folder = self.shortcut_folder_var.get()
        if not os.path.exists(shortcut_folder):
            messagebox.showwarning("Lỗi", "Không tìm thấy thư mục Shortcut.")
            return

        self._save_config()
        
        thread = threading.Thread(target=self._run_thread, args=(self.year_var.get(), months, shortcut_folder, self.download_path_var.get(), selected_shortcuts))
        thread.daemon = True
        thread.start()

    def _stop_automation(self):
        if self._automator: self._automator.request_stop()
        self.stop_button.configure(state="disabled", text="ĐANG DỪNG...")

    def _run_thread(self, year, months, shortcut_folder, download_dir, selected_shortcuts=None):
        self._is_running = True
        self.run_button.configure(state="disabled", text="ĐANG CHẠY...")
        self.stop_button.configure(state="normal")
        self.confirm_login_button.configure(state="normal")
        self.status_label.configure(text="Trạng thái: Đang xử lý...")

        try:
            from automation.operation.lazada_order import LazadaOrderAutomator
            self._automator = LazadaOrderAutomator(self.log, os.getcwd())
            self._automator.run_automation(year, months, shortcut_folder, download_dir, selected_shortcuts)
            self.status_label.configure(text="Trạng thái: Hoàn tất")
        except Exception as e:
            self.log(f"\n[LỖI HỆ THỐNG] {e}")
            self.status_label.configure(text="Trạng thái: Lỗi")
        finally:
            self._is_running = False
            self._automator = None
            self.run_button.configure(state="normal", text="▶  BẮT ĐẦU TẢI ĐƠN")
            self.stop_button.configure(state="disabled", text="DỪNG LẠI")
            self.confirm_login_button.configure(state="disabled")

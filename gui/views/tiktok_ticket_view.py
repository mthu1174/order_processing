import customtkinter as ctk
import threading
import os
import json
import glob
from datetime import datetime
import tkinter.messagebox as messagebox
from tkinter import filedialog
from gui.views.base_view import BaseView


class TikTokTicketView(BaseView):
    """GUI View cho chức năng Raise Ticket TikTok Shop."""

    def __init__(self, master, config_manager, **kwargs):
        super().__init__(master, config_manager, **kwargs)

        self.create_header("TikTok Raise Ticket")

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

        # ── GUIDE SECTION ──
        guide_frame = ctk.CTkFrame(self.scroll_frame, fg_color="#F0F4F8", corner_radius=10)
        guide_frame.pack(fill="x", padx=15, pady=(10, 20))
        
        ctk.CTkLabel(
            guide_frame,
            text="📖 HƯỚNG DẪN NHANH",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#2C5282"
        ).pack(pady=(10, 5), padx=15, anchor="w")
        
        ctk.CTkLabel(
            guide_frame,
            text="1. Chọn file Excel gốc (có cột Brand/Orders).\n2. Bot tự tìm folder brand (Vd: 7.05).\n3. Chọn 1 file ảnh chung nếu cần.\n4. Bấm Chạy và Login nếu Edge yêu cầu.",
            font=ctk.CTkFont(size=11),
            text_color="#4A5568",
            justify="left"
        ).pack(pady=(0, 15), padx=15, anchor="w")

        ctk.CTkLabel(
            self.scroll_frame,
            text="CÀI ĐẶT QUY TRÌNH",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#999999",
        ).pack(pady=(0, 10))

        # ── State Variables ──
        self.input_file_var = ctk.StringVar(value="Chưa chọn file")
        self.brand_dir_var = ctk.StringVar(value="")
        self.img_file_var = ctk.StringVar(value="Chưa chọn")

        # ── Input File ──
        self._create_input_section(
            self.scroll_frame, 
            "1. FILE GỐC (EXCEL)", 
            "File chứa danh sách Order ID",
            self.input_file_var, 
            "📂 CHỌN FILE GỐC", 
            self._browse_input_file
        )

        # ── Brand Files Folder ──
        self._create_input_section(
            self.scroll_frame, 
            "2. THƯ MỤC BRAND (D.MM)", 
            "Thư mục chứa các file đã tách",
            self.brand_dir_var, 
            "📁 CHỌN THƯ MỤC", 
            self._browse_brand_dir
        )

        # ── Image File ──
        self._create_input_section(
            self.scroll_frame, 
            "3. ẢNH ĐÍNH KÈM (CHUNG)", 
            "Ảnh upload cho tất cả ticket",
            self.img_file_var, 
            "🖼️ CHỌN ẢNH", 
            self._browse_img_file
        )

        # ── Reason Text ──
        ctk.CTkLabel(
            self.scroll_frame,
            text="4. LÝ DO RAISE TICKET",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#333333",
        ).pack(padx=15, pady=(15, 2), anchor="w")

        self.reason_text = ctk.CTkTextbox(
            self.scroll_frame,
            height=60,
            font=ctk.CTkFont(size=11),
            fg_color="#FDFDFD",
            border_width=1,
            border_color="#E0E0E0",
            corner_radius=8,
        )
        self.reason_text.pack(fill="x", padx=15, pady=(0, 5))
        self.reason_text.insert(
            "1.0",
            "ĐVVC không đến lấy, nhờ team pushs và reject tỷ lệ giao hàng trễ"
        )

        # ── Ticket URL ──
        ctk.CTkLabel(
            self.scroll_frame,
            text="4.1 LINK TẠO TICKET",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#333333",
        ).pack(padx=15, pady=(15, 2), anchor="w")
        
        self.ticket_url_var = ctk.StringVar(value="https://seller-vn.tiktok.com/ticket/create?shop_region=VN")
        ctk.CTkEntry(
            self.scroll_frame, 
            textvariable=self.ticket_url_var, 
            font=ctk.CTkFont(size=10), 
            height=28
        ).pack(fill="x", padx=15, pady=(0, 5))

        # ── BRAND SELECTION SECTION ──
        ctk.CTkLabel(
            self.scroll_frame,
            text="5. CHỌN BRAND CẦN RAISE:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#333333",
        ).pack(padx=15, pady=(15, 2), anchor="w")

        self.brand_checkbox_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        self.brand_checkbox_frame.pack(fill="x", padx=15)
        
        self.brand_vars = {} # {brand_name: var}
        
        ctk.CTkButton(
            self.scroll_frame,
            text="🔄 LOAD DANH SÁCH BRAND TỪ FILE EXCEL",
            command=self._load_brands_to_gui,
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
            text="▶  BẮT ĐẦU TỰ ĐỘNG",
            command=self._start_automation,
            fg_color="#C30021",
            hover_color="#A0001B",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=45,
            corner_radius=8,
        )
        self.run_button.pack(padx=15, pady=(10, 5), fill="x")

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


        # ── State ──
        self._input_file_path = None
        self._brand_dir_path = None
        self._img_file_path = None
        self._is_running = False
        self._automator = None

        # Load saved config
        self._load_tiktok_config()

    # ─────────────── UI Helpers ───────────────

    def _create_input_section(self, parent, title, subtitle, variable, button_text, command):
        """Helper để tạo cụm input: Label + Sublabel + Current Value + Button"""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=15, pady=8)
        
        ctk.CTkLabel(
            frame, 
            text=title, 
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#333333"
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            frame, 
            text=subtitle, 
            font=ctk.CTkFont(size=10),
            text_color="#999999"
        ).pack(anchor="w", pady=(0, 2))
        
        val_lbl = ctk.CTkLabel(
            frame, 
            textvariable=variable,
            font=ctk.CTkFont(size=10),
            text_color="#666666",
            wraplength=220,
            justify="left"
        )
        val_lbl.pack(fill="x", pady=2)
        
        btn = ctk.CTkButton(
            frame,
            text=button_text,
            command=command,
            fg_color="white",
            text_color="#333333",
            border_color="#CCCCCC",
            border_width=1,
            hover_color="#F5F5F5",
            font=ctk.CTkFont(size=11),
            height=28,
            corner_radius=8,
        )
        btn.pack(fill="x", pady=(2, 0))
        return frame

    # ─────────────── Config Management ───────────────

    def _load_tiktok_config(self):
        """Load cấu hình đã lưu từ tiktok_config.json."""
        try:
            config_path = os.path.join(os.getcwd(), "tiktok_config.json")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)

                if config.get("input_folder"):
                    self._try_auto_detect_input(config["input_folder"])

                if config.get("img_path") and os.path.exists(config["img_path"]):
                    self._img_file_path = config["img_path"]
                    self.img_file_var.set(os.path.basename(config["img_path"]))

                if config.get("reason_text"):
                    self.reason_text.delete("1.0", "end")
                    self.reason_text.insert("1.0", config["reason_text"])

                if config.get("ticket_url"):
                    self.ticket_url_var.set(config["ticket_url"])

                self.log("[CONFIG] Đã tải cấu hình TikTok từ file.")
        except Exception as e:
            self.log(f"[CONFIG] Lỗi đọc config: {e}")

    def _save_tiktok_config(self):
        """Lưu cấu hình vào tiktok_config.json."""
        try:
            config_path = os.path.join(os.getcwd(), "tiktok_config.json")
            config = {}
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)

            if self._input_file_path:
                config["input_folder"] = os.path.dirname(self._input_file_path)
            if self._img_file_path:
                config["img_path"] = self._img_file_path
            config["reason_text"] = self.reason_text.get("1.0", "end-1c").strip()
            if hasattr(self, 'ticket_url_var'):
                config["ticket_url"] = self.ticket_url_var.get().strip()

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
        except Exception:
            pass

    def _try_auto_detect_input(self, folder):
        """Tự động tìm file input trong folder theo pattern ngày."""
        today_pattern = datetime.now().strftime("%#d.%m") if os.name == "nt" else datetime.now().strftime("%-d.%m")
        # Tìm file theo pattern *_dd.MM_*.xlsx
        patterns = [
            os.path.join(folder, f"*_{today_pattern}_*.xlsx"),
            os.path.join(folder, f"*{today_pattern}*.xlsx"),
        ]
        for pattern in patterns:
            files = glob.glob(pattern)
            if files:
                latest = sorted(files, key=os.path.getmtime, reverse=True)[0]
                self._input_file_path = latest
                self.input_file_var.set(os.path.basename(latest))

                # Auto detect brand dir
                brand_dir = os.path.join(folder, today_pattern)
                if os.path.isdir(brand_dir):
                    self._brand_dir_path = brand_dir
                    self.brand_dir_var.set(brand_dir)
                return

    # ─────────────── UI Callbacks ───────────────

    def _browse_input_file(self):
        file_path = filedialog.askopenfilename(
            title="Chọn file Excel input",
            filetypes=[("Excel files", "*.xlsx *.xls")],
        )
        if file_path:
            self._input_file_path = file_path
            self.input_file_var.set(os.path.basename(file_path))
            self.log(f"[FILE] Input: {file_path}")

            # Auto-detect brand dir
            parent = os.path.dirname(file_path)
            today_pattern = datetime.now().strftime("%#d.%m") if os.name == "nt" else datetime.now().strftime("%-d.%m")
            brand_dir = os.path.join(parent, today_pattern)
            if os.path.isdir(brand_dir) and not self._brand_dir_path:
                self._brand_dir_path = brand_dir
                self.brand_dir_var.set(brand_dir)
                self.log(f"[AUTO] Phát hiện thư mục brand: {brand_dir}")

    def _browse_brand_dir(self):
        dir_path = filedialog.askdirectory(title="Chọn thư mục chứa file brand")
        if dir_path:
            self._brand_dir_path = dir_path
            self.brand_dir_var.set(dir_path)
            self.log(f"[THƯ MỤC] Brand files: {dir_path}")

    def _browse_img_file(self):
        file_path = filedialog.askopenfilename(
            title="Chọn file ảnh đính kèm",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")],
        )
        if file_path:
            self._img_file_path = file_path
            self.img_file_var.set(os.path.basename(file_path))
            self.log(f"[ẢNH] {file_path}")

    def _load_brands_to_gui(self):
        if not self._input_file_path or not os.path.exists(self._input_file_path):
            messagebox.showwarning("Lỗi", "Vui lòng chọn file gốc (Excel) trước.")
            return
            
        # Clear existing
        for widget in self.brand_checkbox_frame.winfo_children():
            widget.destroy()
        self.brand_vars = {}

        try:
            import pandas as pd
            df = pd.read_excel(self._input_file_path, dtype=str)
            
            # Find brand col
            brand_col = None
            for c in df.columns:
                if str(c).strip().lower() == "brand":
                    brand_col = c
                    break
                    
            if not brand_col:
                messagebox.showerror("Lỗi", "Không tìm thấy cột 'Brand' trong file Excel.")
                return
                
            brands = df[brand_col].dropna().unique().tolist()
            brands = [str(b).strip() for b in brands if str(b).strip() and str(b).strip() != "nan"]
            
            for brand_name in brands:
                var = ctk.BooleanVar(value=True)
                cb = ctk.CTkCheckBox(
                    self.brand_checkbox_frame, 
                    text=f"{brand_name}", 
                    variable=var,
                    font=ctk.CTkFont(size=11)
                )
                cb.pack(anchor="w", padx=5, pady=2)
                self.brand_vars[brand_name] = var
                
            self.log(f"[HỆ THỐNG] Đã tải {len(brands)} brand(s) từ file Excel.")
                
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể đọc file: {e}")


    def _confirm_login_clicked(self):
        if self._automator:
            self._automator.confirm_login()
            self.log("[HỆ THỐNG] Đã gửi xác nhận đăng nhập đến bot.")
        else:
            self.log("[HỆ THỐNG] Bot chưa chạy, không thể xác nhận.")

    # ─────────────── Automation Control ───────────────

    def _start_automation(self):
        if self._is_running:
            messagebox.showwarning("Cảnh báo", "Đang xử lý, vui lòng đợi...")
            return

        # Validate inputs
        if not self._input_file_path or not os.path.exists(self._input_file_path):
            messagebox.showwarning("Thiếu file", "Vui lòng chọn file input Excel.")
            return

        if not self._brand_dir_path or not os.path.isdir(self._brand_dir_path):
            messagebox.showwarning("Thiếu thư mục", "Vui lòng chọn thư mục chứa file brand.")
            return

        reason = self.reason_text.get("1.0", "end-1c").strip()
        if not reason:
            messagebox.showwarning("Thiếu lý do", "Vui lòng nhập lý do raise ticket.")
            return

        # Get selected brands
        selected_brands = None
        if hasattr(self, 'brand_vars') and self.brand_vars:
            selected_brands = [b for b, var in self.brand_vars.items() if var.get()]
            if not selected_brands:
                messagebox.showwarning("Thiếu thông tin", "Vui lòng chọn ít nhất một brand.")
                return

        # Save config
        self._save_tiktok_config()

        # Confirm
        brand_files = [f for f in os.listdir(self._brand_dir_path) if f.endswith(".xlsx")]
        confirm_msg = f"Sẵn sàng raise ticket cho {len(brand_files)} brand(s)?\n\n"
        if selected_brands is not None:
            confirm_msg = f"Sẵn sàng raise ticket cho {len(selected_brands)} brand(s) đã chọn?\n\n"
            
        confirm = messagebox.askokcancel(
            "Xác nhận",
            confirm_msg +
            f"Input: {os.path.basename(self._input_file_path)}\n"
            f"Brand dir: {self._brand_dir_path}\n"
            f"Ảnh: {os.path.basename(self._img_file_path) if self._img_file_path else 'Không'}\n\n"
            f"⚠️ Nếu bị yêu cầu đăng nhập, hãy đăng nhập\n"
            f"trên cửa sổ Edge rồi bot sẽ tự tiếp tục."
        )
        if not confirm:
            return

        # Start
        thread = threading.Thread(
            target=self._run_automation_thread,
            args=(
                self._input_file_path,
                self._brand_dir_path,
                self._img_file_path,
                reason,
                selected_brands,
            ),
        )
        thread.daemon = True
        thread.start()

    def _stop_automation(self):
        if self._automator:
            self._automator.request_stop()
        self.log("\n[HỆ THỐNG] Đang yêu cầu dừng...")
        self.stop_button.configure(state="disabled", text="ĐANG DỪNG...")

    def _run_automation_thread(self, input_file, brand_dir, img_path, reason, selected_brands=None):
        self._is_running = True
        self.run_button.configure(state="disabled", fg_color="#CCCCCC", text="ĐANG XỬ LÝ...")
        self.stop_button.configure(state="normal", text="DỪNG QUY TRÌNH")
        self.confirm_login_button.configure(state="normal")
        self.status_label.configure(text="Trạng thái: Đang chạy...")

        try:
            from automation.operation.tiktok_ticket import TikTokTicketAutomator

            tiktok_config = TikTokTicketAutomator.load_tiktok_config(os.getcwd())
            self._automator = TikTokTicketAutomator(self.log, os.getcwd(), tiktok_config)

            results = self._automator.run_all_brands(
                input_file=input_file,
                brand_files_dir=brand_dir,
                img_path=img_path or "",
                reason_text=reason,
                selected_brands=selected_brands,
            )

            if results:
                self.status_label.configure(text=f"Trạng thái: Hoàn tất ({len(results)} ticket)")
            else:
                self.status_label.configure(text="Trạng thái: Không có ticket nào")

        except Exception as e:
            self.log(f"\n[LỖI] Sự cố hệ thống: {e}")
            self.status_label.configure(text="Trạng thái: Lỗi")
        finally:
            self._is_running = False
            self._automator = None
            self.run_button.configure(
                state="normal", fg_color="#C30021", text="▶  BẮT ĐẦU TỰ ĐỘNG"
            )
            self.stop_button.configure(state="disabled", text="DỪNG LẠI")
            self.confirm_login_button.configure(state="disabled")

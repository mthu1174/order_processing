import customtkinter as ctk
import threading
import os
import tkinter.messagebox as messagebox
from tkinter import filedialog
from gui.views.base_view import BaseView


class OperationView(BaseView):
    def __init__(self, master, config_manager, **kwargs):
        super().__init__(master, config_manager, **kwargs)

        self.create_header("Operation Tools")

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

        ctk.CTkLabel(
            self.control_card,
            text="TÁCH FILE THEO BRAND",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#999999",
        ).pack(pady=(20, 10))

        # ── File selection ──
        self.file_frame = ctk.CTkFrame(self.control_card, fg_color="transparent")
        self.file_frame.pack(fill="x", padx=20, pady=5)

        self.selected_file_var = ctk.StringVar(value="Chưa chọn file")
        self.file_label = ctk.CTkLabel(
            self.file_frame,
            textvariable=self.selected_file_var,
            font=ctk.CTkFont(size=11),
            text_color="#666666",
            wraplength=200,
        )
        self.file_label.pack(fill="x", pady=(0, 5))

        self.browse_button = ctk.CTkButton(
            self.file_frame,
            text="📂 CHỌN FILE EXCEL",
            command=self.browse_file,
            fg_color="white",
            text_color="#333333",
            border_color="#CCCCCC",
            border_width=1,
            hover_color="#F5F5F5",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=35,
            corner_radius=8,
        )
        self.browse_button.pack(fill="x")

        # ── Column name input ──
        ctk.CTkLabel(
            self.control_card,
            text="TÊN CỘT BRAND",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#999999",
        ).pack(padx=20, pady=(15, 2), anchor="w")

        self.column_entry = ctk.CTkEntry(
            self.control_card,
            placeholder_text="VD: Brand Name",
            font=ctk.CTkFont(size=12),
            height=35,
            corner_radius=8,
        )
        self.column_entry.pack(fill="x", padx=20, pady=(0, 5))

        # ── Output directory ──
        ctk.CTkLabel(
            self.control_card,
            text="THƯ MỤC XUẤT FILE",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#999999",
        ).pack(padx=20, pady=(15, 2), anchor="w")

        self.output_dir_var = ctk.StringVar(value="")
        self.output_dir_label = ctk.CTkLabel(
            self.control_card,
            textvariable=self.output_dir_var,
            font=ctk.CTkFont(size=10),
            text_color="#666666",
            wraplength=200,
        )
        self.output_dir_label.pack(fill="x", padx=20)

        self.output_dir_button = ctk.CTkButton(
            self.control_card,
            text="📁 CHỌN THƯ MỤC",
            command=self.browse_output_dir,
            fg_color="white",
            text_color="#333333",
            border_color="#CCCCCC",
            border_width=1,
            hover_color="#F5F5F5",
            font=ctk.CTkFont(size=11),
            height=30,
            corner_radius=8,
        )
        self.output_dir_button.pack(fill="x", padx=20, pady=(2, 5))

        # ── Run button ──
        self.run_button = ctk.CTkButton(
            self.control_card,
            text="▶  TÁCH FILE",
            command=self.start_split,
            fg_color="#C30021",
            hover_color="#A0001B",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=40,
            corner_radius=8,
        )
        self.run_button.pack(padx=20, pady=(20, 10), fill="x")

        # ── State ──
        self._selected_file_path = None
        self._output_dir = None
        self._is_running = False

    # ─────────────── UI Callbacks ───────────────

    def browse_file(self):
        file_path = filedialog.askopenfilename(
            title="Chọn file Excel cần tách",
            filetypes=[("Excel files", "*.xlsx *.xls *.csv")],
        )
        if file_path:
            self._selected_file_path = file_path
            self.selected_file_var.set(os.path.basename(file_path))
            # Auto-set output dir = same folder as source file
            from datetime import datetime
            folder_name = datetime.now().strftime("%-d.%m") if os.name != "nt" else datetime.now().strftime("%#d.%m")
            default_output = os.path.join(os.path.dirname(file_path), folder_name)
            self._output_dir = default_output
            self.output_dir_var.set(default_output)
            self.log(f"[FILE] Đã chọn: {file_path}")

    def browse_output_dir(self):
        dir_path = filedialog.askdirectory(title="Chọn thư mục xuất file")
        if dir_path:
            self._output_dir = dir_path
            self.output_dir_var.set(dir_path)
            self.log(f"[THƯ MỤC] Xuất tại: {dir_path}")

    # ─────────────── Core Logic ───────────────

    def start_split(self):
        if self._is_running:
            messagebox.showwarning("Cảnh báo", "Đang xử lý, vui lòng đợi...")
            return

        if not self._selected_file_path:
            messagebox.showwarning("Thiếu file", "Vui lòng chọn file Excel trước.")
            return

        column_name = self.column_entry.get().strip()
        if not column_name:
            messagebox.showwarning("Thiếu tên cột", "Vui lòng nhập tên cột Brand Name.")
            return

        thread = threading.Thread(
            target=self._run_split_thread,
            args=(self._selected_file_path, column_name, self._output_dir),
        )
        thread.daemon = True
        thread.start()

    def _run_split_thread(self, file_path, column_name, output_dir):
        self._is_running = True
        self.run_button.configure(state="disabled", fg_color="#CCCCCC", text="ĐANG XỬ LÝ...")
        try:
            from automation.operation.split_by_brand import BrandSplitter
            splitter = BrandSplitter(log_callback=self.log)
            splitter.split(file_path, column_name, output_dir)
        except Exception as e:
            self.log(f"\n[LỖI] Sự cố: {e}")
        finally:
            self._is_running = False
            self.run_button.configure(state="normal", fg_color="#C30021", text="▶  TÁCH FILE")

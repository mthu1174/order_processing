import customtkinter as ctk
import threading
import tkinter.messagebox as messagebox
from gui.views.base_view import BaseView

class HandoverOrderView(BaseView):
    def __init__(self, master, config_manager, **kwargs):
        super().__init__(master, config_manager, **kwargs)

        self.create_header("Đơn Bàn Giao")

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
            text="CÔNG CỤ XỬ LÝ",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#999999",
        ).pack(pady=(20, 10))

        description = ctk.CTkLabel(
            self.control_card,
            text="Làm mới PENDING_ORDER_CHECK 1 và tách file bàn giao cho từng nền tảng (Shopee, Lazada, Tiktokshop).",
            font=ctk.CTkFont(size=12),
            text_color="#666666",
            wraplength=200,
            justify="center"
        )
        description.pack(pady=(10, 20), padx=20)

        # ── Run button ──
        self.run_button = ctk.CTkButton(
            self.control_card,
            text="▶  CHẠY TỰ ĐỘNG",
            command=self.start_process,
            fg_color="#C30021",
            hover_color="#A0001B",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=40,
            corner_radius=8,
        )
        self.run_button.pack(padx=20, pady=(20, 10), fill="x")

        # ── State ──
        self._is_running = False

    # ─────────────── Core Logic ───────────────

    def start_process(self):
        if self._is_running:
            messagebox.showwarning("Cảnh báo", "Đang xử lý, vui lòng đợi...")
            return

        thread = threading.Thread(target=self._run_process_thread)
        thread.daemon = True
        thread.start()

    def _run_process_thread(self):
        self._is_running = True
        self.run_button.configure(state="disabled", fg_color="#CCCCCC", text="ĐANG XỬ LÝ...")
        self.log("\n[BẮT ĐẦU] Khởi động quá trình xử lý đơn bàn giao...")
        try:
            from automation.handover_order import HandoverOrderAutomation
            bot = HandoverOrderAutomation(config_manager=self.config_manager, log_callback=self.log)
            bot.process()
        except Exception as e:
            self.log(f"\n[LỖI] Sự cố: {e}")
        finally:
            self._is_running = False
            self.run_button.configure(state="normal", fg_color="#C30021", text="▶  CHẠY TỰ ĐỘNG")

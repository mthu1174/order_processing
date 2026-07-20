import customtkinter as ctk
from gui.views.base_view import BaseView

class HomeView(BaseView):
    def __init__(self, master, config_manager, nav_callback=None, **kwargs):
        super().__init__(master, config_manager, **kwargs)
        self.nav_callback = nav_callback
        
        self.create_header("Dashboard Overview")
        
        # Scrollable area for content
        self.scroll_area = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_area.grid(row=1, column=0, sticky="nsew", padx=20)
        self.scroll_area.grid_columnconfigure(0, weight=1)

        # 1. Welcome Card
        welcome_card = self.create_card(self.scroll_area)
        welcome_card.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        welcome_text = ctk.CTkLabel(
            welcome_card, 
            text="Hệ Thống Tự Động Hóa Xử Lý Đơn & Báo Cáo",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#333333"
        )
        welcome_text.pack(padx=30, pady=(30, 10), anchor="w")
        
        sub_text = ctk.CTkLabel(
            welcome_card,
            text="Chào mừng trở lại! Bạn có thể chọn dịch vụ từ thanh bên hoặc bấm trực tiếp vào các thẻ bên dưới.",
            font=ctk.CTkFont(size=14),
            text_color="#666666"
        )
        sub_text.pack(padx=30, pady=(0, 30), anchor="w")

        # 2. Services Grid
        self.create_function_header(self.scroll_area, "📂 XỬ LÝ ĐƠN HÀNG (ORDER PROCESSING)", 1)
        
        services_frame = ctk.CTkFrame(self.scroll_area, fg_color="transparent")
        services_frame.grid(row=2, column=0, sticky="ew")
        services_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.create_service_card(services_frame, "ENERGIZER", "🔥", "Shopee, SAP, GHN", "Sẵn sàng", "Energizer", 0)
        self.create_service_card(services_frame, "OFF-PLATFORM", "📦", "Đơn ngoài sàn", "Sắp tới", "Off-Platform", 1, state="disabled")
        self.create_service_card(services_frame, "KOL", "✨", "Đơn KOL Ads", "Sắp tới", "KOL", 2, state="disabled")

        self.create_function_header(self.scroll_area, "📂 VẬN HÀNH (OPERATION)", 3)

        operation_frame = ctk.CTkFrame(self.scroll_area, fg_color="transparent")
        operation_frame.grid(row=4, column=0, sticky="ew")
        operation_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.create_service_card(operation_frame, "TÁCH FILE BRAND", "🛠", "Split Excel by Brand", "Sẵn sàng", "Operation", 0)
        self.create_service_card(operation_frame, "TIKTOK TICKET", "🎫", "Raise TikTok Tickets", "Sẵn sàng", "TikTokTicket", 1)

        self.create_function_header(self.scroll_area, "📂 BÁO CÁO (REPORTING)", 5)
        
        reporting_frame = ctk.CTkFrame(self.scroll_area, fg_color="transparent")
        reporting_frame.grid(row=6, column=0, sticky="ew")
        reporting_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        self.create_service_card(reporting_frame, "ANCHANTO", "📊", "Daily Reporting", "Sẵn sàng", "AnchantoReport", 0)

    def create_function_header(self, parent, text, row):
        lbl = ctk.CTkLabel(
            parent, text=text, 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#BBBBBB"
        )
        lbl.grid(row=row, column=0, padx=10, pady=(20, 5), sticky="w")

    def create_service_card(self, parent, title, icon, subtitle, status, view_name, column, state="normal"):
        card = self.create_card(parent)
        card.grid(row=0, column=column, padx=10, pady=10, sticky="nsew")
        
        icon_lbl = ctk.CTkLabel(card, text=icon, font=ctk.CTkFont(size=40))
        icon_lbl.pack(pady=(25, 5))
        
        title_lbl = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=16, weight="bold"), text_color="#333333")
        title_lbl.pack()
        
        sub_lbl = ctk.CTkLabel(card, text=subtitle, font=ctk.CTkFont(size=12), text_color="#999999")
        sub_lbl.pack(pady=(0, 15))
        
        btn_text = "BẮT ĐẦU" if state == "normal" else "SẮP CÓ"
        btn_color = "#C30021" if state == "normal" else "#EEEEEE"
        text_color = "white" if state == "normal" else "#AAAAAA"
        
        start_btn = ctk.CTkButton(
            card, 
            text=btn_text, 
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=btn_color,
            text_color=text_color,
            height=32,
            width=120,
            corner_radius=6,
            state=state,
            command=lambda: self.nav_callback(view_name) if self.nav_callback else None
        )
        start_btn.pack(pady=(0, 25))

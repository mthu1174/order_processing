import customtkinter as ctk
import os
from PIL import Image

class SidebarNavigation(ctk.CTkFrame):
    def __init__(self, master, active_callback, **kwargs):
        super().__init__(master, **kwargs)
        self.active_callback = active_callback
        self.buttons = {}
        
        self.configure(fg_color="#FFFFFF", border_width=1, border_color="#EEEEEE")
        
        # Logo area
        self.logo_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.logo_frame.grid(row=0, column=0, padx=20, pady=(30, 15))
        
        # Load and display brand logo
        logo_path = None
        for ext in [".png", ".jpg", ".jpeg"]:
            path = os.path.join(os.getcwd(), "assets", f"logo{ext}")
            if os.path.exists(path):
                logo_path = path
                break
                
        if logo_path:
            self.brand_image = ctk.CTkImage(
                light_image=Image.open(logo_path),
                dark_image=Image.open(logo_path),
                size=(120, 120)
            )
            self.logo_label = ctk.CTkLabel(self.logo_frame, image=self.brand_image, text="")
            self.logo_label.pack()
        else:
            self.logo_label = ctk.CTkLabel(
                self.logo_frame, 
                text="DKSH", 
                font=ctk.CTkFont(size=32, weight="bold"),
                text_color="#C30021"
            )
            self.logo_label.pack()
            
        self.sub_logo = ctk.CTkLabel(
            self.logo_frame,
            text="AUTOMATION DASHBOARD",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#999999"
        )
        self.sub_logo.pack(pady=(5, 0))

        # Navigation
        curr_row = 1
        
        # Home Section (No folder)
        self.create_nav_button("Home", "🏠 Trang chủ", curr_row, indent=0)
        curr_row += 1
        
        # ORDER PROCESSING FOLDER
        self.create_folder_header("📂 XỬ LÝ ĐƠN HÀNG", curr_row)
        curr_row += 1
        self.create_nav_button("Energizer", "🔥 Energizer", curr_row, indent=30)
        curr_row += 1
        self.create_nav_button("KOL", "✨ KOL Orders", curr_row, indent=30, state="disabled")
        curr_row += 1
        self.create_nav_button("Off-Platform", "📦 Off-Platform", curr_row, indent=30, state="disabled")
        curr_row += 1
        
        # OPERATION FOLDER
        self.create_folder_header("📂 VẬN HÀNH (OPERATION)", curr_row)
        curr_row += 1
        self.create_nav_button("Operation", "🛠 Tách file theo Brand", curr_row, indent=30)
        curr_row += 1
        self.create_nav_button("TikTokTicket", "🎫 TikTok Raise Ticket", curr_row, indent=30)
        curr_row += 1
        
        # REPORTING FOLDER
        self.create_folder_header("📂 BÁO CÁO (REPORT)", curr_row)
        curr_row += 1
        self.create_nav_button("AnchantoReport", "📊 Anchanto Daily", curr_row, indent=30)
        curr_row += 1
        self.create_nav_button("ShopeeOrder", "🛍️ Tải đơn Shopee", curr_row, indent=30)
        curr_row += 1
        self.create_nav_button("LazadaOrder", "🛒 Tải đơn Lazada", curr_row, indent=30)
        curr_row += 1
        
        self.grid_rowconfigure(curr_row, weight=1)
        curr_row += 1
        self.create_nav_button("Scheduler", "⏰ Hẹn giờ", curr_row, indent=0)
        curr_row += 1
        self.create_nav_button("Settings", "⚙ Cài đặt", curr_row, indent=0)

    def create_folder_header(self, text, row):
        lbl = ctk.CTkLabel(
            self, 
            text=text, 
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#333333"
        )
        lbl.grid(row=row, column=0, padx=20, pady=(25, 5), sticky="w")

    def create_nav_button(self, name, text, row, indent=0, state="normal"):
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=row, column=0, sticky="ew")
        btn_frame.grid_columnconfigure(1, weight=1)
        
        marker = ctk.CTkFrame(btn_frame, width=4, height=30, fg_color="transparent")
        marker.grid(row=0, column=0, padx=(0, 5))
        
        btn = ctk.CTkButton(
            btn_frame, 
            text=text, 
            corner_radius=0, 
            height=38, 
            fg_color="transparent",
            text_color="#666666", 
            hover_color="#F5F5F7",
            anchor="w",
            state=state,
            font=ctk.CTkFont(size=13),
            command=lambda: self.button_clicked(name)
        )
        btn.grid(row=0, column=1, sticky="ew", padx=(indent, 0))
        
        self.buttons[name] = {"btn": btn, "marker": marker}
        if state == "disabled":
            btn.configure(text_color="#CCCCCC")

    def button_clicked(self, name):
        self.select_button(name)
        self.active_callback(name)

    def select_button(self, name):
        for b_name, b_info in self.buttons.items():
            b_info["btn"].configure(fg_color="transparent", text_color="#666666", font=ctk.CTkFont(size=13))
            b_info["marker"].configure(fg_color="transparent")
        
        if name in self.buttons:
            self.buttons[name]["btn"].configure(
                fg_color="transparent", 
                text_color="#C30021",
                font=ctk.CTkFont(size=13, weight="bold")
            )
            self.buttons[name]["marker"].configure(fg_color="#C30021")

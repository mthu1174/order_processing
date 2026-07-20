import customtkinter as ctk
import os
from tkinter import filedialog, messagebox
from gui.views.base_view import BaseView

class SettingsView(BaseView):
    def __init__(self, master, config_manager, **kwargs):
        super().__init__(master, config_manager, **kwargs)
        
        self.create_header("Cấu hình hệ thống")
        
        # Scrollable area for grouped settings
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.grid(row=1, column=0, padx=30, pady=(0, 20), sticky="nsew")
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        self.entries = {}
        
        # 1. ORDER PROCESSING SECTION
        self.create_settings_group(
            "XỬ LÝ ĐƠN HÀNG (ENERGIZER & GHN)", 
            [
                ("shopee_download_dir", "📁 Thư mục Tải Shopee"),
                ("sap_export_dir", "📁 Thư mục Xuất SAP"),
                ("sharepoint_template_path", "📄 File Template Sharepoint"),
                ("sap_tcode", "⚙ SAP T-Code"),
                ("sap_variant", "⚙ SAP Variant"),
                ("sap_user", "👤 SAP Username"),
                ("sap_password", "🔒 SAP Password (If no SSO)"),
                ("ghn_upload_template_path", "📄 File Template GHN"),
                ("ghn_output_dir", "📁 Thư mục Lọc GHN")
            ]
        )

        # 2. ĐƠN BÀN GIAO (HANDOVER ORDER)
        self.create_settings_group(
            "ĐƠN BÀN GIAO (PENDING ORDER CHECK)", 
            [
                ("handover_source_file", "📄 File Nguồn (Pending Order Check)"),
                ("handover_processed_dir", "📁 Thư mục Lưu File Đã Xử Lý")
            ]
        )

        # 2. REPORTING SECTION
        self.create_settings_group(
            "BÁO CÁO (REPORTING)", 
            [
                ("anchanto_url", "🔗 Anchanto Login URL"),
                ("powerbi_semantic_model_url", "📊 PowerBI Semantic Model URL"),
                ("anchanto_download_dir", "📁 Thư mục Tải Anchanto"),
                ("anchanto_final_path", "📂 Thư mục Lưu Anchanto (OneDrive)"),
                ("anchanto_days_prior", "📅 Số ngày lùi (Days Prior)")
            ]
        )

        # Control area at bottom
        self.control_area = ctk.CTkFrame(self, fg_color="transparent")
        self.control_area.grid(row=2, column=0, padx=30, pady=(0, 30), sticky="ew")
        
        self.save_btn = ctk.CTkButton(
            self.control_area, text="LƯU THAY ĐỔI", 
            command=self.save_settings, 
            fg_color="#C30021", hover_color="#A0001B",
            font=ctk.CTkFont(size=14, weight="bold"), height=45, width=200
        )
        self.save_btn.pack(side="right")

    def create_settings_group(self, title, items):
        group_card = self.create_card(self.scroll_frame)
        group_card.pack(fill="x", pady=10)
        group_card.grid_columnconfigure(1, weight=1)
        
        lbl_title = ctk.CTkLabel(group_card, text=title, font=ctk.CTkFont(size=13, weight="bold"), text_color="#C30021")
        lbl_title.grid(row=0, column=0, columnspan=3, padx=20, pady=(15, 10), sticky="w")
        
        row = 1
        for key, label_text in items:
            value = self.config_manager.config.get(key, "")
            
            lbl = ctk.CTkLabel(group_card, text=label_text, font=ctk.CTkFont(size=12), text_color="#333333")
            lbl.grid(row=row, column=0, padx=(20, 10), pady=10, sticky="w")
            
            entry = ctk.CTkEntry(group_card, height=32, fg_color="#FDFDFD", border_color="#E0E0E0")
            if "password" in key:
                entry.configure(show="*")
            entry.insert(0, str(value))
            entry.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
            self.entries[key] = entry
            
            if "dir" in key or "path" in key:
                btn_browse = ctk.CTkButton(
                    group_card, text="BROWSE", width=70, height=32,
                    fg_color="white", text_color="#C30021", border_color="#C30021", border_width=1,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    command=lambda k=key: self.browse_path(k)
                )
                btn_browse.grid(row=row, column=2, padx=(0, 20), pady=10)
            
            row += 1

    def browse_path(self, key):
        entry = self.entries[key]
        current_val = entry.get()
        if "path" in key and not "dir" in key:
            file_path = filedialog.askopenfilename()
            if file_path:
                entry.delete(0, "end"); entry.insert(0, file_path)
        else:
            dir_path = filedialog.askdirectory()
            if dir_path:
                entry.delete(0, "end"); entry.insert(0, dir_path)

    def save_settings(self):
        new_config = self.config_manager.config.copy()
        for key, entry in self.entries.items():
            val = entry.get()
            # Try to convert to int if it's days_prior
            if key == "anchanto_days_prior":
                try: val = int(val)
                except: pass
            new_config[key] = val
        
        if self.config_manager.save_config(new_config):
            self.config_manager.config = new_config
            messagebox.showinfo("Thành công", "Cấu hình đã được cập nhật!")
        else:
            messagebox.showerror("Lỗi", "Không thể lưu tệp cấu hình.")

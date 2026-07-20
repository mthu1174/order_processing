import customtkinter as ctk
import tkinter.messagebox as messagebox
from datetime import datetime
import uuid
from gui.views.base_view import BaseView

class SchedulerView(BaseView):
    def __init__(self, master, config_manager, app_instance=None, **kwargs):
        super().__init__(master, config_manager, **kwargs)
        self.app_instance = app_instance
        
        self.create_header("⏰ Quản lý Hẹn giờ")
        
        # Main layout
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.grid(row=1, column=0, padx=30, pady=10, sticky="nsew")
        self.container.grid_columnconfigure(0, weight=2) # List of schedules
        self.container.grid_columnconfigure(1, weight=1) # Add new schedule
        self.container.grid_rowconfigure(0, weight=1)

        # 1. Schedule List Card
        self.list_card = self.create_card(self.container)
        self.list_card.grid(row=0, column=0, padx=(0, 15), sticky="nsew")
        self.list_card.grid_columnconfigure(0, weight=1)
        self.list_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self.list_card, 
            text="DANH SÁCH LỊCH HẸN", 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#999999"
        ).grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")

        self.scroll_list = ctk.CTkScrollableFrame(self.list_card, fg_color="transparent")
        self.scroll_list.grid(row=1, column=0, padx=10, pady=(0, 15), sticky="nsew")
        self.scroll_list.grid_columnconfigure(0, weight=1)

        # 2. Add New Schedule Card
        self.add_card = self.create_card(self.container)
        self.add_card.grid(row=0, column=1, sticky="nsew")
        
        ctk.CTkLabel(
            self.add_card, 
            text="THÊM HẸN GIỜ MỚI", 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#999999"
        ).pack(pady=(20, 10))

        # Form fields
        self.task_var = ctk.StringVar(value="Energizer")
        ctk.CTkLabel(self.add_card, text="Chọn tác vụ:", font=ctk.CTkFont(size=12)).pack(padx=20, pady=(10, 0), anchor="w")
        self.task_dropdown = ctk.CTkOptionMenu(
            self.add_card, 
            values=["Energizer", "Anchanto Reporting"],
            variable=self.task_var,
            fg_color="#FDFDFD",
            text_color="#333333",
            button_color="#CCCCCC",
            button_hover_color="#BBBBBB"
        )
        self.task_dropdown.pack(padx=20, pady=5, fill="x")

        ctk.CTkLabel(self.add_card, text="Thời gian (Giờ:Phút):", font=ctk.CTkFont(size=12)).pack(padx=20, pady=(10, 0), anchor="w")
        
        time_frame = ctk.CTkFrame(self.add_card, fg_color="transparent")
        time_frame.pack(padx=20, pady=5, fill="x")
        
        self.hour_entry = ctk.CTkEntry(time_frame, placeholder_text="HH", width=50)
        self.hour_entry.pack(side="left", padx=(0, 5))
        ctk.CTkLabel(time_frame, text=":").pack(side="left")
        self.minute_entry = ctk.CTkEntry(time_frame, placeholder_text="MM", width=50)
        self.minute_entry.pack(side="left", padx=(5, 0))

        self.add_btn = ctk.CTkButton(
            self.add_card, 
            text="THÊM VÀO LỊCH", 
            command=self.add_schedule,
            fg_color="#C30021",
            hover_color="#A0001B",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=35
        )
        self.add_btn.pack(padx=20, pady=25, fill="x")

        # Load existing
        self.refresh_list()

    def refresh_list(self):
        # Clear current list
        for child in self.scroll_list.winfo_children():
            child.destroy()
        
        schedules = self.config_manager.get("schedules", [])
        if not schedules:
            ctk.CTkLabel(self.scroll_list, text="Chưa có lịch hẹn nào.", font=ctk.CTkFont(size=12), text_color="#999999").pack(pady=20)
            return

        for sched in schedules:
            self.create_schedule_item(sched)

    def create_schedule_item(self, sched):
        item_frame = ctk.CTkFrame(self.scroll_list, fg_color="#F9F9FB", corner_radius=8, border_width=1, border_color="#EEEEEE")
        item_frame.pack(fill="x", pady=5, padx=5)
        
        # Icon
        icon = "🔥" if "Energizer" in sched["task"] else "📊"
        ctk.CTkLabel(item_frame, text=icon, font=ctk.CTkFont(size=18)).pack(side="left", padx=15, pady=10)
        
        # Details
        details_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        details_frame.pack(side="left", fill="both", expand=True, pady=5)
        
        ctk.CTkLabel(details_frame, text=sched["task"], font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(details_frame, text=f"Chạy lúc: {sched['time']}", font=ctk.CTkFont(size=12), text_color="#666666").pack(anchor="w")
        
        # Actions
        actions_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        actions_frame.pack(side="right", padx=15)
        
        is_enabled = sched.get("enabled", True)
        switch = ctk.CTkSwitch(
            actions_frame, text="", width=40, 
            command=lambda s=sched: self.toggle_schedule(s),
        )
        if is_enabled: switch.select()
        switch.pack(side="left", padx=5)
        
        delete_btn = ctk.CTkButton(
            actions_frame, text="🗑", width=30, height=30, 
            fg_color="transparent", text_color="#666666", hover_color="#FFEEEE",
            command=lambda s=sched: self.delete_schedule(s)
        )
        delete_btn.pack(side="left", padx=5)

    def add_schedule(self):
        h = self.hour_entry.get().strip()
        m = self.minute_entry.get().strip()
        
        try:
            h_int = int(h)
            m_int = int(m)
            if not (0 <= h_int < 24 and 0 <= m_int < 60): raise ValueError
            time_str = f"{h_int:02d}:{m_int:02d}"
        except:
            messagebox.showerror("Lỗi", "Thời gian không hợp lệ. Vui lòng nhập HH: 0-23 và MM: 0-59.")
            return

        new_sched = {
            "id": str(uuid.uuid4()),
            "task": self.task_var.get(),
            "time": time_str,
            "enabled": True
        }
        
        schedules = self.config_manager.get("schedules", [])
        schedules.append(new_sched)
        
        self.config_manager.config["schedules"] = schedules
        self.config_manager.save_config(self.config_manager.config)
        
        self.hour_entry.delete(0, "end")
        self.minute_entry.delete(0, "end")
        self.refresh_list()
        
        if self.app_instance:
            self.app_instance.log(f"[HẸN GIỜ] Đã thêm lịch mới cho {new_sched['task']} lúc {time_str}")
            self.app_instance.scheduler.notify_change()

    def toggle_schedule(self, sched):
        schedules = self.config_manager.get("schedules", [])
        for s in schedules:
            if s["id"] == sched["id"]:
                s["enabled"] = not s.get("enabled", True)
                break
        self.config_manager.config["schedules"] = schedules
        self.config_manager.save_config(self.config_manager.config)
        if self.app_instance:
            self.app_instance.scheduler.notify_change()

    def delete_schedule(self, sched):
        schedules = self.config_manager.get("schedules", [])
        schedules = [s for s in schedules if s["id"] != sched["id"]]
        self.config_manager.config["schedules"] = schedules
        self.config_manager.save_config(self.config_manager.config)
        self.refresh_list()
        if self.app_instance:
            self.app_instance.scheduler.notify_change()

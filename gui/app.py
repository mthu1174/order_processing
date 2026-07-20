import customtkinter as ctk
import os
import ctypes
from PIL import Image
from automation.config_manager import ConfigManager
from gui.navigation import SidebarNavigation
from gui.views.home_view import HomeView
from gui.views.energizer_view import EnergizerView
from gui.views.settings_view import SettingsView
from gui.views.reporting_view import AnchantoReportView
from gui.views.scheduler_view import SchedulerView
from gui.views.operation_view import OperationView
from gui.views.tiktok_ticket_view import TikTokTicketView
from gui.views.shopee_order_view import ShopeeOrderView
from gui.views.lazada_order_view import LazadaOrderView
from gui.views.handover_order_view import HandoverOrderView
from automation.scheduler_manager import SchedulerManager

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Fix for Windows Taskbar Icon
        try:
            myappid = 'dksh.orderautomation.dashboard.v1'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

        self.title("DKSH - Order Automation Dashboard")
        self.geometry("1100x700")
        
        # Set Window Icon
        try:
            icon_found = False
            # Check common image extensions
            for ext in [".ico", ".png", ".jpg", ".jpeg"]:
                icon_path = os.path.join(os.getcwd(), "assets", f"logo{ext}")
                if os.path.exists(icon_path):
                    # Use Pillow to open because the file might be a renamed JPG (even if .ico)
                    img = Image.open(icon_path)
                    
                    # For Taskbar icon to work best on Windows with Python scripts:
                    # We use ImageTk to create a PhotoImage and wm_iconphoto
                    from PIL import ImageTk
                    self.icon_photo = ImageTk.PhotoImage(img)
                    self.wm_iconphoto(True, self.icon_photo) # True applies to all future windows too
                    
                    icon_found = True
                    break
        except Exception as e:
            print(f"[CẢNH BÁO] Không thể tải icon cửa sổ: {e}")
        
        # Initialize Config
        self.app_dir = os.getcwd()
        self.config_manager = ConfigManager(self.app_dir)
        
        # Configure layout
        self.grid_columnconfigure(0, weight=0) # Sidebar
        self.grid_columnconfigure(1, weight=1) # Main View
        self.grid_rowconfigure(0, weight=1)

        # 1. Sidebar
        self.sidebar = SidebarNavigation(self, self.show_view, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        # 2. Main View Container
        self.view_container = ctk.CTkFrame(self, fg_color="#F9F9FB", corner_radius=0)
        self.view_container.grid(row=0, column=1, sticky="nsew")
        self.view_container.grid_columnconfigure(0, weight=1)
        self.view_container.grid_rowconfigure(0, weight=1)

        # Initialize Views
        self.views = {
            "Home": HomeView(self.view_container, self.config_manager, nav_callback=self.show_view_from_home),
            "Energizer": EnergizerView(self.view_container, self.config_manager),
            "Operation": OperationView(self.view_container, self.config_manager),
            "TikTokTicket": TikTokTicketView(self.view_container, self.config_manager),
            "AnchantoReport": AnchantoReportView(self.view_container, self.config_manager),
            "HandoverOrder": HandoverOrderView(self.view_container, self.config_manager),
            "ShopeeOrder": ShopeeOrderView(self.view_container, self.config_manager),
            "LazadaOrder": LazadaOrderView(self.view_container, self.config_manager),
            "Scheduler": SchedulerView(self.view_container, self.config_manager, app_instance=self),
            "Settings": SettingsView(self.view_container, self.config_manager)
        }

        # Initialize and Start Scheduler
        self.scheduler = SchedulerManager(
            self.config_manager, 
            trigger_callback=self.scheduler_trigger_bridge,
            log_callback=self.log_to_active_view
        )
        self.scheduler.start()

        # Show default view
        self.show_view("Home")
        self.sidebar.select_button("Home")

    def show_view_from_home(self, view_name):
        # Wrapper to also update sidebar marker
        self.sidebar.select_button(view_name)
        self.show_view(view_name)

    def show_view(self, name):
        """Switch between views by grid management"""
        # Hide all views
        for view in self.views.values():
            view.grid_forget()
        
        # Show selected view
        if name in self.views:
            self.views[name].grid(row=0, column=0, sticky="nsew")
            self.active_view_name = name

    def log_to_active_view(self, message):
        """Log message to whichever view is currently active, or both if they have loggers"""
        for name in ["Energizer", "AnchantoReport", "Scheduler"]:
            view = self.views.get(name)
            if view and hasattr(view, "log"):
                view.log(message)

    def scheduler_trigger_bridge(self, task_name):
        """Bridge between SchedulerManager and the specific View's automation logic"""
        if task_name == "Energizer":
            self.views["Energizer"].run_full_automation()
        elif task_name == "Anchanto Reporting":
            self.views["AnchantoReport"].run_full_automation()
            
    def run_automation_headless(self):
        """
        Legacy support for headless execution if needed.
        Note: This would need to be moved to a core runner class if heavily used.
        """
        print("[HỆ THỐNG] Chạy chế độ Headless (Tự động)...")
        # Reuse logic from EnergizerView if it was modularized further, 
        # or just call core logic here.
        # For now, let's keep it simple for GUI users.
        pass

if __name__ == "__main__":
    app = App()
    app.mainloop()

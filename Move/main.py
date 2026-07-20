import customtkinter as ctk
from gui.app import App
import os

import sys

def main():
    # Init app
    app = App()

    # Kiểm tra tham số dòng lệnh --auto để chạy không giao diện
    if "--auto" in sys.argv:
        app.run_automation_headless()
        # Không gọi mainloop() để app tự kết thúc sau khi xong
    else:
        # Cấu hình giao diện ban đầu
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("blue") 
        app.mainloop()

if __name__ == "__main__":
    main()

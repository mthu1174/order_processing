import os
import sys
import traceback

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ERROR_LOG = os.path.join(APP_DIR, "error.log")


def _report_crash():
    """Ghi lỗi ra error.log và hiện popup, vì pythonw không có cửa sổ để in lỗi."""
    err = traceback.format_exc()
    try:
        with open(ERROR_LOG, "w", encoding="utf-8") as f:
            f.write(err)
    except Exception:
        pass
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        last_line = err.strip().splitlines()[-1] if err.strip() else "Unknown error"
        hint = ""
        if "ModuleNotFoundError" in err:
            hint = "\n\nThiếu thư viện → chạy lại bước cài (pip install -r requirements.txt)."
        messagebox.showerror(
            "Order Automation - Lỗi khởi động",
            f"{last_line}{hint}\n\nChi tiết lỗi đã lưu ở:\n{ERROR_LOG}",
        )
        root.destroy()
    except Exception:
        print(err)


def main():
    os.chdir(APP_DIR)  # đảm bảo đọc config.json đúng folder dù chạy từ đâu

    import customtkinter as ctk
    from gui.app import App

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
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        _report_crash()
        sys.exit(1)

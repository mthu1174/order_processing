import json
import os

class ConfigManager:
    def __init__(self, app_dir):
        self.app_dir = app_dir
        self.config_path = os.path.join(app_dir, "config.json")
        self.config = self.load_config()

    def load_config(self):
        """Tải cấu hình từ file config.json hoặc tạo mới nếu chưa có"""
        default_config = {
            "shopee_download_dir": r"C:\Users\thu.mai.dinh\OneDrive - DKSH\1. Order processing\2. Energizer\ORDERS",
            "sap_export_dir": r"C:\Users\thu.mai.dinh\OneDrive - DKSH\1. Order processing\2. Energizer\SAP",
            "sharepoint_template_path": r"C:\Users\thu.mai.dinh\OneDrive - DKSH\1. Order processing\2. Energizer\Template Energizer_14.07.xlsx",
            "ghn_upload_template_path": r"C:\Users\thu.mai.dinh\OneDrive - DKSH\1. Order processing\2. Energizer\DKSH_ENERGIZER_07.04.xlsx",
            "ghn_output_dir": r"C:\Users\thu.mai.dinh\OneDrive - DKSH\1. Order processing\2. Energizer\GHN_RETURN",
            "sap_tcode": "YSD_OC_GEN_R004",
            "sap_variant": "ecom",
            "handover_source_file": r"C:\Users\thu.mai.dinh\OneDrive - DKSH\1. Order processing\4. Pending_dontUse\PENDING_ORDER_CHECK 1.xlsx",
            "handover_processed_dir": r"C:\Users\thu.mai.dinh\OneDrive - DKSH\1. Order processing\4. Pending_dontUse\Processed Files"
        }

        if not os.path.exists(self.config_path):
            self.save_config(default_config)
            return default_config

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default_config

    def save_config(self, config_data):
        """Lưu cấu hình vào file config.json"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
            return True
        except Exception:
            return False

    def get(self, key, default=None):
        return self.config.get(key, default)

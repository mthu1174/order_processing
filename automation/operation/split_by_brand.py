import os
import pandas as pd
from datetime import datetime


class BrandSplitter:
    """Đọc file Excel/CSV và tách thành nhiều file nhỏ theo cột Brand Name."""

    def __init__(self, log_callback=None):
        self.log = log_callback or print

    # ─────────────── Public API ───────────────

    def split(self, file_path, column_name, output_dir=None):
        """
        Tách file theo brand.

        Args:
            file_path:   Đường dẫn file nguồn (.xlsx / .xls / .csv)
            column_name: Tên cột chứa brand name
            output_dir:  Thư mục xuất (mặc định = cùng thư mục, tên = ngày d.MM)

        Returns:
            output_dir nếu thành công, None nếu thất bại
        """
        self.log("\n" + "=" * 50)
        self.log(f"[BẮT ĐẦU] Đọc file: {os.path.basename(file_path)}")

        # ── Đọc file ──
        df = self._read_file(file_path)
        if df is None:
            return None

        self.log(f"[INFO] Tổng số dòng: {len(df):,}")
        self.log(f"[INFO] Các cột: {', '.join(df.columns.tolist())}")

        # ── Xác nhận cột ──
        column_name = self._resolve_column(df, column_name)
        if column_name is None:
            return None

        # ── Tạo thư mục xuất ──
        output_dir = self._resolve_output_dir(file_path, output_dir)
        os.makedirs(output_dir, exist_ok=True)

        # ── Tách & lưu ──
        brands = df[column_name].dropna().unique()
        self.log(f"[INFO] Tìm thấy {len(brands)} brand(s): {', '.join(str(b) for b in brands)}")

        if len(brands) == 0:
            self.log("[LỖI] Cột brand rỗng, không có dữ liệu để tách.")
            return None

        saved_count = 0
        for brand in brands:
            brand_df = df[df[column_name] == brand]
            safe_brand = self._sanitize_filename(str(brand))
            output_file = os.path.join(output_dir, f"{safe_brand}.xlsx")

            try:
                brand_df.to_excel(output_file, index=False, engine="openpyxl")
                saved_count += 1
                self.log(f"  ✅ {safe_brand}.xlsx — {len(brand_df):,} dòng")
            except Exception as e:
                self.log(f"  ❌ Lỗi khi lưu '{safe_brand}': {e}")

        # ── Dòng không có brand ──
        nan_df = df[df[column_name].isna()]
        if len(nan_df) > 0:
            nan_file = os.path.join(output_dir, "_KHONG_CO_BRAND.xlsx")
            nan_df.to_excel(nan_file, index=False, engine="openpyxl")
            self.log(f"  ⚠️ _KHONG_CO_BRAND.xlsx — {len(nan_df):,} dòng (brand trống)")
            saved_count += 1

        self.log(f"\n[HOÀN TẤT] Đã tách thành {saved_count} file(s) tại:")
        self.log(f"  📁 {output_dir}")
        self.log("=" * 50)
        return output_dir

    # ─────────────── Helpers ───────────────

    def _read_file(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext == ".csv":
                return pd.read_csv(file_path, dtype=str)
            else:
                return pd.read_excel(file_path, dtype=str)
        except Exception as e:
            self.log(f"[LỖI] Không thể đọc file: {e}")
            return None

    def _resolve_column(self, df, column_name):
        """Tìm cột khớp (case-insensitive nếu cần)."""
        if column_name in df.columns:
            return column_name

        matched = [c for c in df.columns if c.strip().lower() == column_name.strip().lower()]
        if matched:
            self.log(f"[INFO] Tìm thấy cột khớp: '{matched[0]}'")
            return matched[0]

        self.log(f"[LỖI] Không tìm thấy cột '{column_name}' trong file.")
        self.log(f"[GỢI Ý] Các cột có sẵn: {', '.join(df.columns.tolist())}")
        return None

    @staticmethod
    def _resolve_output_dir(file_path, output_dir):
        if output_dir:
            return output_dir
        folder_name = datetime.now().strftime("%#d.%m") if os.name == "nt" else datetime.now().strftime("%-d.%m")
        return os.path.join(os.path.dirname(file_path), folder_name)

    @staticmethod
    def _sanitize_filename(name):
        """Remove or replace characters that are invalid in filenames."""
        invalid_chars = '<>:"/\\|?*'
        for ch in invalid_chars:
            name = name.replace(ch, "_")
        return name.strip().strip(".")

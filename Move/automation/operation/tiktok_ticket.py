import os
import time
import json
import subprocess
import pandas as pd
from datetime import datetime
import threading
import re
from playwright.sync_api import sync_playwright


class TikTokTicketAutomator:
    """
    Tự động raise ticket trên TikTok Shop Seller Center.
    Sử dụng Edge thật + CDP để tránh anti-bot detection.
    Mỗi brand có Edge profile riêng để giữ session.
    """

    TICKET_URL = "https://seller-vn.tiktok.com/ticket/create?shop_region=VN"
    EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    CDP_PORT = 9223  # Khác port với Shopee (9222)

    # Delays (seconds) — dựa trên UiPath timing
    DELAY_AFTER_LAUNCH = 10
    DELAY_BEFORE_TOPIC = 7
    DELAY_BETWEEN_CLICKS = 2
    DELAY_AFTER_SUBMIT = 5

    def __init__(self, log_callback, app_dir, tiktok_config=None):
        self.log = log_callback or print
        self.app_dir = app_dir
        self.config = tiktok_config or {}
        self._stop_requested = False
        self._login_confirmed = False

        # Override defaults from config
        if self.config.get("cdp_port"):
            self.CDP_PORT = self.config["cdp_port"]
        delays = self.config.get("delays", {})
        if delays.get("after_launch"):
            self.DELAY_AFTER_LAUNCH = delays["after_launch"]
        if delays.get("before_topic_click"):
            self.DELAY_BEFORE_TOPIC = delays["before_topic_click"]
        if delays.get("between_clicks"):
            self.DELAY_BETWEEN_CLICKS = delays["between_clicks"]
        if delays.get("after_submit"):
            self.DELAY_AFTER_SUBMIT = delays["after_submit"]

    def request_stop(self):
        """Yêu cầu dừng quy trình sau brand hiện tại."""
        self._stop_requested = True

    def confirm_login(self):
        """Xác nhận người dùng đã đăng nhập xong (gọi từ GUI)."""
        self._login_confirmed = True

    # ------------------------------------------------------
    #  PUBLIC API
    # ------------------------------------------------------

    def run_all_brands(self, input_file, brand_files_dir, img_path, reason_text, selected_brands=None):
        """
        Quy trình chính: raise ticket cho tất cả brands.

        Args:
            input_file:      File gốc (có cột Brand, Orders, Ticket No.)
            brand_files_dir: Thư mục chứa file brand.xlsx đã tách (output split_by_brand)
            img_path:        Đường dẫn file ảnh chung
            reason_text:     Lý do cố định

        Returns:
            dict: {brand_name: ticket_number} cho các brand thành công
        """
        self._stop_requested = False
        results = {}

        # 1. Đọc input file → lấy brands + order IDs
        self.log("-" * 50)
        self.log(f"[TIKTOK] Doc file input: {os.path.basename(input_file)}")

        try:
            df = pd.read_excel(input_file, dtype=str)
        except Exception as e:
            self.log(f"  [LOI] Khong the doc file input: {e}")
            return results

        # Tìm cột Brand và Orders (case-insensitive)
        brand_col = self._find_column(df, "Brand")
        orders_col = self._find_column(df, "Orders")
        ticket_col = self._find_column(df, "Ticket No.")

        if not brand_col or not orders_col:
            self.log("  [LOI] Khong tim thay cot 'Brand' hoac 'Orders' trong file input.")
            return results

        # Tạo cột Ticket No. nếu chưa có
        if not ticket_col:
            df["Ticket No."] = ""
            ticket_col = "Ticket No."
            self.log("[INFO] Đã tạo cột 'Ticket No.' mới.")

        # 2. Lấy danh sách unique brands
        brands = df[brand_col].dropna().unique().tolist()
        self.log(f"[TIKTOK] Tìm thấy {len(brands)} brand(s): {', '.join(str(b) for b in brands)}")

        # 3. Xử lý từng brand
        for i, brand in enumerate(brands, 1):
            if self._stop_requested:
                self.log("\n[HE THONG] Da dung theo yeu cau nguoi dung.")
                break

            brand_name = str(brand).strip()

            if selected_brands is not None and brand_name not in selected_brands:
                self.log(f"  [BỎ QUA] Brand '{brand_name}' không được chọn.")
                continue

            self.log("-" * 40)
            self.log(f"[BRAND {i}/{len(brands)}] {brand_name}")
            self.log("-" * 40)

            # Tìm file brand
            brand_file = os.path.join(brand_files_dir, f"{brand_name}.xlsx")
            if not os.path.exists(brand_file):
                self.log(f"  [CANH BAO] Khong tim thay file: {brand_file}")
                self.log(f"  - Bo qua brand nay.")
                continue

            # Lấy Order ID đầu tiên
            brand_orders = df[df[brand_col] == brand][orders_col].dropna().astype(str).tolist()
            first_order_id = brand_orders[0] if brand_orders else ""

            self.log(f"  - File: {os.path.basename(brand_file)}")
            self.log(f"  - Order ID: {first_order_id}")

            # Raise ticket
            ticket_number = self._raise_ticket_for_brand(
                brand_name=brand_name,
                order_id=first_order_id,
                reason_text=reason_text,
                brand_file_path=brand_file,
                img_path=img_path
            )

            if ticket_number:
                results[brand_name] = ticket_number
                # Ghi ticket number vào tất cả rows của brand
                mask = df[brand_col].astype(str).str.strip().str.upper() == brand_name.upper()
                df.loc[mask, ticket_col] = ticket_number
                self.log(f"  > Ticket: {ticket_number}")
            else:
                self.log(f"  [LOI] Raise ticket that bai cho {brand_name}")

        # 4. Ghi kết quả lại vào file input
        if results:
            try:
                df.to_excel(input_file, index=False, engine="openpyxl")
                self.log(f"\n[TIKTOK] Đã ghi {len(results)} Ticket No. vào file input.")
            except Exception as e:
                self.log(f"  [LOI] Khong the ghi lai file input: {e}")

        self.log("-" * 50)
        self.log(f"[HOAN TAT] Da xu ly {len(results)}/{len(brands)} brand(s) thanh cong.")
        self.log("-" * 50)
        return results

    # ══════════════════════════════════════════════════════
    #  CORE: Raise ticket cho 1 brand
    # ══════════════════════════════════════════════════════

    def _raise_ticket_for_brand(self, brand_name, order_id, reason_text, brand_file_path, img_path):
        """
        Raise 1 ticket cho 1 brand.
        Returns: ticket_number (str) hoặc None nếu thất bại.
        """
        profile_dir = os.path.join(self.app_dir, "browser_data", "tiktok", brand_name)
        os.makedirs(profile_dir, exist_ok=True)

        with sync_playwright() as p:
            browser = None
            try:
                # 1. Khởi động Edge với profile riêng
                browser = self._launch_edge_profile(p, profile_dir, brand_name)
                if not browser:
                    return None

                browser_context = browser.contexts[0]
                page = browser_context.pages[0] if browser_context.pages else browser_context.new_page()

                # 2. Navigate tới ticket/create
                self.log(f"🌐 Đang truy cập trang tạo ticket...")
                page.goto(self.TICKET_URL, timeout=60000)
                time.sleep(5)

                # 3. Kiểm tra login
                if not self._handle_login(page, brand_name):
                    return None

                # 4. Điền form
                self.log(f"📝 Đang điền form ticket...")
                if not self._fill_ticket_form(page, order_id, reason_text, brand_file_path, img_path):
                    return None

                # 5. Submit
                self.log(f"🚀 Đang gửi ticket...")
                if not self._submit_ticket(page):
                    return None

                # 6. Lấy ticket number
                ticket_number = self._capture_ticket_number(page)
                return ticket_number

            except Exception as e:
                self.log(f"  [LOI] Exception: {e}")
                # Đợi 1 chút để user xem lỗi trước khi đóng (nếu muốn)
                time.sleep(5)
                return None
            finally:
                if browser:
                    try:
                        browser.close()
                    except Exception:
                        pass
                # Kill Edge process cho port này
                self._kill_edge()

    # ------------------------------------------------------
    #  BROWSER MANAGEMENT
    # ------------------------------------------------------

    def _launch_edge_profile(self, playwright, profile_dir, brand_name):
        """Mở Edge với profile riêng, connect CDP."""
        self.log(f"  > Khoi dong Edge (profile: {brand_name})...")

        # Kill Edge cũ trên port này
        self._kill_edge()
        time.sleep(2)

        # Khởi động Edge mới
        try:
            subprocess.Popen(
                [
                    self.EDGE_PATH,
                    f"--remote-debugging-port={self.CDP_PORT}",
                    f"--user-data-dir={profile_dir}",
                    "--no-first-run",
                    "--disable-features=EdgeIdentitySignInFromAccountSettings",
                    "--disable-popup-blocking",
                ],
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        except FileNotFoundError:
            self.log(f"  [LOI] Khong tim thay Edge tai: {self.EDGE_PATH}")
            return None

        self.log(f"  > Cho Edge khoi dong ({self.DELAY_AFTER_LAUNCH}s)...")
        time.sleep(self.DELAY_AFTER_LAUNCH)

        # Connect CDP
        try:
            browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{self.CDP_PORT}")
            self.log(f"  > Da ket noi Edge thanh cong!")
            return browser
        except Exception as e:
            self.log(f"  [LOI] Khong the ket noi Edge CDP: {e}")
            return None

    def _kill_edge(self):
        """Kill tất cả Edge processes."""
        try:
            subprocess.run(
                ["taskkill", "/F", "/IM", "msedge.exe"],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        except Exception:
            pass

    # ------------------------------------------------------
    #  LOGIN HANDLING
    # ------------------------------------------------------

    def _handle_login(self, page, brand_name):
        """
        Detect trang login -> cho user giải CAPTCHA + OTP.
        Returns True nếu đã login (thấy form), False nếu timeout.
        """
        self.log(f"🔍 Đang kiểm tra trạng thái đăng nhập...")
        self._login_confirmed = False  # Reset cho brand này
        
        # Chờ trang load ổn định
        time.sleep(5)
        
        login_indicators = ["/passport/", "/login", "account/login", "signin"]
        ticket_path = "ticket/create"

        # 1. Kiểm tra nhanh xem đã ở đúng trang và có form chưa
        for _ in range(3):
            current_url = page.url.lower()
            is_on_ticket = ticket_path in current_url
            
            # Chỉ coi là đã login nếu ở đúng URL ticket và thấy element đặc trưng
            if is_on_ticket:
                try:
                    # Kiểm tra dropdown "Chủ đề" (topic) hoặc input Order ID
                    # Quan trọng: element phải visible và không bị che khuất bởi overlay login
                    topic_el = page.locator("#topic, [id*='topic']").first
                    if topic_el.is_visible(timeout=3000):
                        self.log(f"✅ Đã đăng nhập (phát hiện form ticket)")
                        return True
                except:
                    pass

            time.sleep(2)

        # 2. Nếu chưa thấy form, bắt đầu chờ người dùng
        self.log(f"\n⚠️ [CẢNH BÁO] [{brand_name}] CHƯA ĐĂNG NHẬP HOẶC CHƯA VÀO FORM!")
        self.log(f"  - Vui lòng đăng nhập trên cửa sổ Edge.")
        self.log(f"  - Giải CAPTCHA + nhập OTP nếu yêu cầu.")
        self.log(f"  - Sau khi vào đến trang tạo Ticket, bot sẽ tự tiếp tục.")
        self.log(f"  - HOẶC: Bấm nút 'ĐÃ ĐĂNG NHẬP XONG' trên phần mềm.")
        self.log(f"  > Đang chờ... (tối đa 5 phút)")

        # Chờ đến khi thấy form ticket tại đúng URL
        try:
            start_wait = time.time()
            # Danh sách selectors chuẩn của form ticket (không quá generic)
            strict_selectors = ["#topic", "[id*='topic']", "#faq_order_id_input", "textarea[id*='issues']"]
            
            while time.time() - start_wait < 300: # 5 phút
                if self._stop_requested: return False
                
                # Kiểm tra nút bấm từ GUI
                if self._login_confirmed:
                    self.log(f"✅ Người dùng đã xác nhận đăng nhập thủ công.")
                    return True

                current_url = page.url.lower()
                is_on_login = any(ind in current_url for ind in login_indicators)
                
                # Chỉ kiểm tra form nếu KHÔNG ở trang login
                if not is_on_login:
                    found = False
                    
                    def check_container(container):
                        for sel in strict_selectors:
                            try:
                                if container.locator(sel).first.is_visible(timeout=1000):
                                    return True
                            except: continue
                        return False

                    if check_container(page):
                        found = True
                    
                    if not found:
                        for frame in page.frames:
                            if check_container(frame):
                                found = True
                                break
                    
                    if found:
                        self.log(f"✅ Đã phát hiện form ticket. Tiếp tục...")
                        time.sleep(2)
                        return True
                
                # Nếu đã login rồi nhưng đang ở trang dashboard/home -> quay lại trang ticket
                if any(ind in current_url for ind in ["homepage", "dashboard", "university"]) and not is_on_login:
                    if "ticket/create" not in current_url:
                        self.log(f"🔄 Đã đăng nhập, đang chuyển hướng về trang ticket...")
                        page.goto(self.TICKET_URL)
                        time.sleep(5)
                
                # Log trạng thái mỗi 30s
                if int(time.time() - start_wait) % 30 == 0:
                    self.log(f"  [Đang chờ] Đang quét form ticket hoặc chờ xác nhận... ({int(time.time() - start_wait)}s)")

                time.sleep(3)
            
            self.log(f"❌ [LỖI] Quá thời gian chờ (5 phút).")
            return False
        except Exception:
            self.log(f"  [LOI] Co loi xay ra khi cho dang nhap.")
            return False

    # ------------------------------------------------------
    #  FILL TICKET FORM
    # ------------------------------------------------------

    def _fill_ticket_form(self, page, order_id, reason_text, brand_file_path, img_path):
        """
        Điền form tạo ticket:
        1. Chọn Chủ đề (4 levels dropdown)
        2. Nhập Order ID
        3. Nhập lý do
        4. Upload 2 files
        """
        try:
            # ── Bước 1: Click "Chủ đề" dropdown ──
            self.log(f"📋 Chọn chủ đề...")
            time.sleep(self.DELAY_BEFORE_TOPIC)

            # Click vào dropdown chủ đề
            topic_selector = "div[id='topic'] div, #topic div"
            try:
                page.locator("#topic").first.click(timeout=15000)
            except Exception:
                # Fallback: tìm bằng text
                page.get_by_text("Chủ đề").first.click(timeout=10000)
                time.sleep(1)
                # Click vào input area
                page.locator("div[parentid='topic']").first.click(timeout=5000)

            time.sleep(self.DELAY_BETWEEN_CLICKS)

            # ── Bước 2: Chọn "Thực hiện đơn hàng & Hậu cần (3PL/4PL)" ──
            self.log(f"  - Thuc hien don hang & Hau can (3PL/4PL)")
            page.get_by_text("Thực hiện đơn hàng & Hậu cần (3PL/4PL)").first.click(timeout=10000)
            time.sleep(self.DELAY_BETWEEN_CLICKS)

            # ── Bước 3: Chọn "Đón và trả hàng (4PL)" ──
            self.log(f"  - Don va tra hang (4PL)")
            page.get_by_text("Đón và trả hàng (4PL)").first.click(timeout=10000)
            time.sleep(self.DELAY_BETWEEN_CLICKS)

            # ── Bước 4: Chọn "Nhà cung cấp dịch vụ hậu cần chậm trễ nhận hàng" ──
            self.log(f"  - Nha cung cap dich vu hau can cham tre nhan hang")
            page.get_by_text("Nhà cung cấp dịch vụ hậu cần chậm trễ nhận hàng").first.click(timeout=10000)
            time.sleep(self.DELAY_BETWEEN_CLICKS)

            # ── Bước 5: Nhập Order ID ──
            if order_id:
                self.log(f"  > Nhap Order ID: {order_id}")
                try:
                    order_input = page.locator("#faq_order_id_input, textarea[id*='order_id']").first
                    order_input.click(timeout=5000)
                    order_input.fill(order_id)
                except Exception:
                    # Fallback: tìm bằng placeholder
                    order_input = page.get_by_placeholder("Vui lòng nhập ID đơn hàng").first
                    order_input.click()
                    order_input.fill(order_id)
                time.sleep(1)

            # ── Bước 6: Nhập lý do ──
            self.log(f"  > Nhap ly do...")
            try:
                reason_input = page.locator("#issues_input, textarea[id*='issues']").first
                reason_input.click(timeout=5000)
                reason_input.fill(reason_text)
            except Exception:
                # Fallback: tìm bằng placeholder
                reason_input = page.get_by_placeholder("Vui lòng giải thích chi tiết").first
                reason_input.click()
                reason_input.fill(reason_text)
            time.sleep(1)

            # ── Bước 7: Upload file brand ──
            self.log(f"  > Upload file brand: {os.path.basename(brand_file_path)}")
            self._upload_file(page, brand_file_path, upload_index=0)
            time.sleep(3)

            # ── Bước 8: Upload file ảnh ──
            if img_path and os.path.exists(img_path):
                self.log(f"  > Upload anh: {os.path.basename(img_path)}")
                self._upload_file(page, img_path, upload_index=1)
                time.sleep(3)

            self.log(f"  > Da dien xong form!")
            return True

        except Exception as e:
            self.log(f"  [LOI] Dien form that bai: {e}")
            return False

    def _upload_file(self, page, file_path, upload_index=0):
        """
        Upload file với cơ chế đợi thông minh.
        """
        try:
            # Selector cho các nút tải lên của TikTok (Arco Design)
            btn_selector = "button:has-text('Tải lên'), button[class*='arco-btn']:has-text('Tải lên'), .arco-upload-trigger"
            
            # Đợi một chút để UI ổn định (nhất là sau khi upload file 1)
            if upload_index > 0:
                time.sleep(3)

            # Tìm context (page hoặc frame) chứa nút upload
            target_context = page
            found_btn = page.locator(btn_selector).nth(upload_index)
            
            if found_btn.count() == 0:
                # Thử tìm trong các frames
                for frame in page.frames:
                    if frame.locator(btn_selector).nth(upload_index).count() > 0:
                        target_context = frame
                        break
            
            # Kiểm tra lại số lượng nút trong context tìm thấy
            btns = target_context.locator(btn_selector)
            count = btns.count()
            
            # Nếu muốn upload file 2 nhưng chỉ thấy 1 nút -> dùng luôn nút 0
            idx = upload_index if upload_index < count else 0
            
            self.log(f"    - Thực hiện upload (mục {upload_index+1}, sử dụng nút index {idx})...")
            
            # Thực hiện upload bằng File Chooser
            try:
                with target_context.expect_file_chooser(timeout=15000) as fc_info:
                    btns.nth(idx).click(timeout=10000)
                file_chooser = fc_info.value
                file_chooser.set_files(file_path)
            except Exception as e:
                self.log(f"    - Cách 1 thất bại, thử cách 2 (set input directly)...")
                # Cách 2: Set trực tiếp vào input file
                inputs = target_context.locator("input[type='file']")
                in_count = inputs.count()
                in_idx = upload_index if upload_index < in_count else 0
                inputs.nth(in_idx).set_input_files(file_path)

            self.log(f"    - Upload thành công: {os.path.basename(file_path)}")

        except Exception as e:
            self.log(f"    ❌ [LỖI] Không thể upload file {os.path.basename(file_path)}: {e}")

    # ------------------------------------------------------
    #  SUBMIT & CAPTURE TICKET
    # ------------------------------------------------------

    def _submit_ticket(self, page):
        """Click Gửi → Tiếp theo."""
        try:
            # Click "Gửi" / "Submit"
            self.log(f"  > Click 'Gui' / 'Submit'...")
            submit_btn = page.locator(
                "button:has-text('Gửi'):not(:has-text('Gửi lại')), button:has-text('Submit')"
            ).first
            submit_btn.click(timeout=10000)
            time.sleep(self.DELAY_BETWEEN_CLICKS)

            # Click "Tiếp theo" / "Next" (xác nhận sau submit)
            self.log(f"  > Click 'Tiep theo' / 'Next'...")
            try:
                next_btn = page.get_by_text(re.compile(r"^(Tiếp theo|Next)$", re.IGNORECASE)).first
                next_btn.click(timeout=15000)
            except Exception:
                # Có thể nút tên khác
                try:
                    page.locator("button[class*='btn-primary']:has-text('Tiếp'), button[class*='btn-primary']:has-text('Next')").first.click(timeout=10000)
                except Exception:
                    self.log(f"    - Khong tim thay nut 'Tiep theo' hoac 'Next', co the da chuyen trang.")

            time.sleep(self.DELAY_AFTER_SUBMIT)
            return True

        except Exception as e:
            self.log(f"  [LOI] Submit that bai: {e}")
            return False

    def _capture_ticket_number(self, page):
        """
        Sau khi submit, lấy ticket number từ trang danh sách ticket.
        """
        try:
            # Click tab "Tất cả"
            self.log(f"  > Dang tim Ticket Number...")
            time.sleep(self.DELAY_AFTER_SUBMIT)

            try:
                page.get_by_text("Tất cả", exact=True).first.click(timeout=10000)
                time.sleep(3)
            except Exception:
                self.log(f"    - Khong tim thay tab 'Tat ca', thu doc truc tiep...")

            # Lấy ngày hôm nay
            today = datetime.now().strftime("%d/%m/%Y")

            # Tìm dòng đầu tiên trong bảng ticket
            # Cấu trúc: table > tbody > tr:first > td (chứa ticket ID và date)
            try:
                # Cố gắng đọc ngày từ row đầu tiên
                first_row_date = page.locator("table tbody tr").first.locator("td").nth(-1).inner_text(timeout=10000)

                if today in first_row_date:
                    # Đọc ticket ID
                    raw_ticket_text = page.locator(
                        "table tbody tr:first-child td div[class*='titleColor'], "
                        "table tbody tr:first-child td a[href*='ticket']"
                    ).first.inner_text(timeout=10000)

                    # Parse ticket number: "ID phiếu:202604210312204905" → "202604210312204905"
                    if ":" in raw_ticket_text:
                        ticket_number = raw_ticket_text.split(":")[-1].strip()
                    else:
                        ticket_number = raw_ticket_text.strip()

                    self.log(f"  - Ticket Number: {ticket_number}")
                    return ticket_number
                else:
                    self.log(f"    - Ticket dau tien khong phai hom nay ({first_row_date})")
                    # Vẫn thử lấy ticket ID
                    raw_ticket_text = page.locator(
                        "table tbody tr:first-child td div[class*='titleColor']"
                    ).first.inner_text(timeout=5000)
                    if ":" in raw_ticket_text:
                        ticket_number = raw_ticket_text.split(":")[-1].strip()
                    else:
                        ticket_number = raw_ticket_text.strip()
                    self.log(f"  - Ticket (chua xac nhan ngay): {ticket_number}")
                    return ticket_number

            except Exception as e:
                self.log(f"    - Khong doc duoc ticket tu bang: {e}")
                # Thử đọc từ URL (ticket detail page)
                if "ticket/" in page.url and "create" not in page.url:
                    ticket_from_url = page.url.split("ticket/")[-1].split("?")[0]
                    if ticket_from_url:
                        self.log(f"  - Ticket (tu URL): {ticket_from_url}")
                        return ticket_from_url

                return "Đã tạo (không lấy được số)"

        except Exception as e:
            self.log(f"  [LOI] Khong the lay ticket number: {e}")
            return None

    # ------------------------------------------------------
    #  HELPERS
    # ------------------------------------------------------

    @staticmethod
    def _find_column(df, name):
        """Tìm cột theo tên (case-insensitive)."""
        if name in df.columns:
            return name
        matched = [c for c in df.columns if c.strip().lower() == name.strip().lower()]
        return matched[0] if matched else None

    @staticmethod
    def load_tiktok_config(app_dir):
        """Load config từ tiktok_config.json."""
        config_path = os.path.join(app_dir, "tiktok_config.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    @staticmethod
    def save_tiktok_config(app_dir, config):
        """Lưu config vào tiktok_config.json."""
        config_path = os.path.join(app_dir, "tiktok_config.json")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)

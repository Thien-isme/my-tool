"""
Google Account Registration Bot
Sử dụng Playwright + Stealth để tự động đăng ký tài khoản Google
"""
import time
import random
import os
from datetime import datetime

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth


class GoogleRegisterBot:
    """Bot tự động đăng ký tài khoản Google"""

    SIGNUP_URL = "https://accounts.google.com/signup?hl=en"

    # User agents thực tế
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    ]

    def __init__(self, headless=False, log_callback=None, screenshot_dir=None):
        """
        Args:
            headless: Chạy trình duyệt ẩn hay không
            log_callback: Hàm callback để ghi log (nhận 1 tham số string)
            screenshot_dir: Thư mục lưu screenshot debug
        """
        self.headless = headless
        self.log_callback = log_callback
        self.screenshot_dir = screenshot_dir or os.path.join(os.path.dirname(__file__), "screenshots")
        self._running = True
        self.pw = None
        self.browser = None

        # Tạo thư mục screenshot nếu chưa có
        os.makedirs(self.screenshot_dir, exist_ok=True)

    def log(self, msg):
        """Ghi log message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_msg = f"[{timestamp}] {msg}"
        if self.log_callback:
            self.log_callback(full_msg)
        print(full_msg)

    def stop(self):
        """Dừng bot"""
        self._running = False
        self.log("⏹ Đã nhận lệnh dừng")

    def is_running(self):
        return self._running

    def random_sleep(self, min_s=0.5, max_s=1.5):
        """Chờ ngẫu nhiên để giả lập hành vi người dùng"""
        duration = random.uniform(min_s, max_s)
        time.sleep(duration)

    def human_type(self, page, selector, text):
        """
        Gõ phím giống người thật - từng ký tự với delay ngẫu nhiên
        """
        page.click(selector)
        self.random_sleep(0.1, 0.3)

        # Xóa text cũ nếu có
        page.keyboard.press("Control+a")
        page.keyboard.press("Backspace")
        self.random_sleep(0.05, 0.15)

        # Gõ từng ký tự
        for char in text:
            page.keyboard.type(char)
            time.sleep(random.uniform(0.04, 0.14))

        self.random_sleep(0.2, 0.4)

    def take_screenshot(self, page, step_name):
        """Chụp screenshot để debug"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{step_name}.png"
            filepath = os.path.join(self.screenshot_dir, filename)
            page.screenshot(path=filepath)
            self.log(f"📸 Screenshot: {filename}")
        except Exception as e:
            self.log(f"⚠️ Không thể chụp screenshot: {e}")

    def click_next_button(self, page):
        """Click nút Next/Tiếp theo với nhiều selector dự phòng"""
        selectors = [
            'button:has-text("Next")',
            'button:has-text("Tiếp theo")',
            'button:has-text("Suivant")',
            'span:has-text("Next")',
            '//button[contains(.,"Next")]',
            '//button[contains(.,"Tiếp")]',
        ]
        for sel in selectors:
            try:
                locator = page.locator(sel).first
                if locator.is_visible(timeout=2000):
                    locator.click()
                    self.log("➡️ Đã click Next")
                    return True
            except Exception:
                continue

        raise Exception("Không tìm thấy nút Next")

    def start_browser(self):
        """Khởi động Playwright và browser"""
        self.log("🚀 Đang khởi động browser...")
        self.pw = sync_playwright().start()

        launch_args = {
            "headless": self.headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-infobars",
                "--disable-extensions",
                "--ignore-certificate-errors",
                "--window-size=1280,800",
            ]
        }

        self.browser = self.pw.chromium.launch(**launch_args)
        self.log("✅ Browser đã sẵn sàng")

    def test_proxy(self, proxy_config=None):
        """
        Test proxy bằng cách tải một trang đơn giản.
        Trả về (success: bool, message: str)
        """
        if not self.browser:
            self.start_browser()

        context_opts = {
            "viewport": {"width": 1280, "height": 800},
            "locale": "en-US",
            "ignore_https_errors": True,
        }
        if proxy_config:
            context_opts["proxy"] = proxy_config
            self.log(f"🧪 Test proxy: {proxy_config['server']}")
        else:
            self.log("🧪 Test kết nối trực tiếp (không proxy)...")

        context = self.browser.new_context(**context_opts)
        page = context.new_page()

        try:
            # Test 1: Trang nhẹ để kiểm tra kết nối
            self.log("   → Đang test kết nối cơ bản...")
            page.goto("https://httpbin.org/ip", wait_until="domcontentloaded", timeout=20000)
            body_text = page.inner_text("body")
            self.log(f"   → Kết nối OK! Response: {body_text.strip()[:100]}")

            # Test 2: Thử truy cập Google (timeout dài hơn vì proxy residential chậm)
            self.log("   → Đang test kết nối tới Google (có thể mất 1-2 phút)...")
            page.goto("https://accounts.google.com/", wait_until="domcontentloaded", timeout=120000)
            title = page.title()
            self.log(f"   → Google OK! Title: {title}")

            return True, f"Proxy hoạt động. IP: {body_text.strip()[:50]}"

        except Exception as e:
            error_msg = str(e).split('\n')[0]  # Lấy dòng đầu
            self.log(f"   → ❌ Lỗi kết nối: {error_msg}")
            return False, f"Proxy không hoạt động: {error_msg}"
        finally:
            context.close()

    def register_one(self, account_info, proxy_config=None):
        """
        Đăng ký 1 tài khoản Google.
        
        Args:
            account_info: dict chứa thông tin tài khoản
            proxy_config: dict proxy cho tài khoản này (optional)
        
        Returns:
            dict: Kết quả đăng ký
        """
        if not self._running:
            return None

        if not self.browser:
            self.start_browser()

        # Tạo context mới cho mỗi tài khoản (cookies sạch)
        context_opts = {
            "viewport": {"width": 1280, "height": 800},
            "user_agent": random.choice(self.USER_AGENTS),
            "locale": "en-US",
            "timezone_id": "America/New_York",
            "color_scheme": "light",
            "ignore_https_errors": True,
        }

        if proxy_config:
            context_opts["proxy"] = proxy_config
            self.log(f"🌐 Proxy: {proxy_config['server']}")

        context = self.browser.new_context(**context_opts)
        page = context.new_page()

        # Áp dụng stealth
        stealth = Stealth()
        stealth.apply_stealth_sync(page)

        try:
            result = self._do_registration(page, account_info)
            return result
        except Exception as e:
            self.log(f"❌ Lỗi nghiêm trọng: {str(e)}")
            self.take_screenshot(page, "error")
            return {
                'email': f"{account_info['username']}@gmail.com",
                'password': account_info['password'],
                'first_name': account_info['first_name'],
                'last_name': account_info['last_name'],
                'status': 'error',
                'detail': str(e),
            }
        finally:
            try:
                context.close()
            except Exception:
                pass

    def _do_registration(self, page, info):
        """Thực hiện các bước đăng ký"""
        email = f"{info['username']}@gmail.com"
        result_base = {
            'email': email,
            'password': info['password'],
            'first_name': info['first_name'],
            'last_name': info['last_name'],
        }

        # ============ BƯỚC 1: Truy cập trang đăng ký ============
        self.log("📄 Đang truy cập trang đăng ký Google...")
        page.goto(self.SIGNUP_URL, wait_until="domcontentloaded", timeout=120000)
        self.random_sleep(1.5, 3)
        self.take_screenshot(page, "01_signup_page")

        if not self._running:
            return {**result_base, 'status': 'cancelled', 'detail': 'Đã dừng bởi người dùng'}

        # ============ BƯỚC 2: Điền Họ Tên ============
        self.log(f"✍️ Điền tên: {info['first_name']} {info['last_name']}")

        # Đợi form tải xong
        page.wait_for_selector('#firstName', timeout=15000)
        self.random_sleep(0.5, 1)

        self.human_type(page, '#firstName', info['first_name'])
        self.human_type(page, '#lastName', info['last_name'])

        self.take_screenshot(page, "02_name_filled")
        self.random_sleep(0.5, 1)

        # Click Next
        self.click_next_button(page)
        page.wait_for_load_state('domcontentloaded', timeout=30000)
        self.random_sleep(2, 4)

        if not self._running:
            return {**result_base, 'status': 'cancelled', 'detail': 'Đã dừng bởi người dùng'}

        # ============ BƯỚC 3: Ngày sinh & Giới tính ============
        self.log(f"📅 Điền ngày sinh: {info['birth_month']}/{info['birth_day']}/{info['birth_year']}")

        try:
            page.wait_for_selector('#month', timeout=10000)
        except Exception:
            # Có thể Google hiển thị bước khác, kiểm tra
            self.take_screenshot(page, "03_unexpected_page")
            current_url = page.url
            page_text = page.inner_text('body')
            self.log(f"⚠️ Trang không đúng kỳ vọng. URL: {current_url}")
            return {**result_base, 'status': 'error', 'detail': f'Unexpected page after name. URL: {current_url}'}

        # Chọn tháng
        page.select_option('#month', value=info['birth_month'])
        self.random_sleep(0.3, 0.6)

        # Điền ngày
        self.human_type(page, '#day', info['birth_day'])

        # Điền năm
        self.human_type(page, '#year', info['birth_year'])

        # Chọn giới tính
        self.random_sleep(0.3, 0.6)
        page.select_option('#gender', value=str(info['gender']))

        self.take_screenshot(page, "03_birthday_filled")
        self.random_sleep(0.5, 1)

        # Click Next
        self.click_next_button(page)
        page.wait_for_load_state('domcontentloaded', timeout=30000)
        self.random_sleep(2, 4)

        if not self._running:
            return {**result_base, 'status': 'cancelled', 'detail': 'Đã dừng bởi người dùng'}

        # ============ BƯỚC 4: Chọn Email ============
        self.log(f"📧 Chọn email: {email}")
        self.take_screenshot(page, "04_email_page")

        # Thử click "Tạo địa chỉ Gmail của riêng bạn"
        try:
            create_own_selectors = [
                'text=Create your own Gmail address',
                'text=Tạo địa chỉ Gmail',
                'div:has-text("Create your own Gmail address")',
            ]
            for sel in create_own_selectors:
                try:
                    locator = page.locator(sel).first
                    if locator.is_visible(timeout=3000):
                        locator.click()
                        self.random_sleep(0.5, 1)
                        self.log("📝 Đã chọn tạo email tùy chỉnh")
                        break
                except Exception:
                    continue
        except Exception:
            pass

        # Điền username
        username_filled = False
        username_selectors = ['input[name="Username"]', '#username', 'input[aria-label="Username"]']
        for sel in username_selectors:
            try:
                if page.locator(sel).first.is_visible(timeout=3000):
                    self.human_type(page, sel, info['username'])
                    username_filled = True
                    self.log(f"✅ Đã điền username: {info['username']}")
                    break
            except Exception:
                continue

        if not username_filled:
            self.log("⚠️ Không tìm thấy ô nhập username, có thể Google đã chọn sẵn")
            self.take_screenshot(page, "04_no_username_field")

        self.random_sleep(0.5, 1)

        # Click Next
        self.click_next_button(page)
        page.wait_for_load_state('domcontentloaded', timeout=30000)
        self.random_sleep(2, 4)

        # Kiểm tra nếu username bị trùng
        try:
            error_selectors = [
                'text=That username is taken',
                'text=Tên người dùng này đã có người sử dụng',
                'div[class*="error"]:has-text("username")',
            ]
            for sel in error_selectors:
                try:
                    if page.locator(sel).first.is_visible(timeout=2000):
                        self.log(f"⚠️ Username '{info['username']}' đã tồn tại!")
                        self.take_screenshot(page, "04_username_taken")
                        return {**result_base, 'status': 'username_taken', 'detail': 'Username đã tồn tại'}
                except Exception:
                    continue
        except Exception:
            pass

        if not self._running:
            return {**result_base, 'status': 'cancelled', 'detail': 'Đã dừng bởi người dùng'}

        # ============ BƯỚC 5: Mật khẩu ============
        self.log("🔒 Điền mật khẩu...")
        self.take_screenshot(page, "05_password_page")

        password_filled = False
        passwd_selectors = ['input[name="Passwd"]', 'input[type="password"]']
        for sel in passwd_selectors:
            try:
                if page.locator(sel).first.is_visible(timeout=5000):
                    self.human_type(page, sel, info['password'])
                    password_filled = True
                    break
            except Exception:
                continue

        if not password_filled:
            self.log("⚠️ Không tìm thấy ô mật khẩu")
            self.take_screenshot(page, "05_no_passwd_field")
            return {**result_base, 'status': 'error', 'detail': 'Không tìm thấy ô nhập mật khẩu'}

        # Xác nhận mật khẩu
        confirm_selectors = ['input[name="PasswdAgain"]', 'input[name="ConfirmPasswd"]']
        for sel in confirm_selectors:
            try:
                if page.locator(sel).first.is_visible(timeout=3000):
                    self.human_type(page, sel, info['password'])
                    self.log("✅ Đã xác nhận mật khẩu")
                    break
            except Exception:
                continue

        self.take_screenshot(page, "05_password_filled")
        self.random_sleep(0.5, 1)

        # Click Next
        self.click_next_button(page)
        page.wait_for_load_state('domcontentloaded', timeout=30000)
        self.random_sleep(2, 4)

        if not self._running:
            return {**result_base, 'status': 'cancelled', 'detail': 'Đã dừng bởi người dùng'}

        # ============ BƯỚC 6: Xử lý các bước xác minh ============
        self.log("🔍 Kiểm tra các bước xác minh...")
        self.take_screenshot(page, "06_verification")

        # Thử bỏ qua số điện thoại / email khôi phục
        skip_attempts = 0
        max_skip_attempts = 3
        while skip_attempts < max_skip_attempts:
            skip_clicked = False
            skip_selectors = [
                'button:has-text("Skip")',
                'button:has-text("Bỏ qua")',
                'span:has-text("Skip")',
                '//button[contains(.,"Skip")]',
            ]
            for sel in skip_selectors:
                try:
                    locator = page.locator(sel).first
                    if locator.is_visible(timeout=2000):
                        locator.click()
                        self.log("⏭️ Đã bỏ qua bước xác minh")
                        page.wait_for_load_state('domcontentloaded', timeout=15000)
                        self.random_sleep(1.5, 3)
                        skip_clicked = True
                        self.take_screenshot(page, f"06_skip_{skip_attempts}")
                        break
                except Exception:
                    continue

            if not skip_clicked:
                break
            skip_attempts += 1

        if not self._running:
            return {**result_base, 'status': 'cancelled', 'detail': 'Đã dừng bởi người dùng'}

        # ============ BƯỚC 7: Điều khoản dịch vụ ============
        self.log("📋 Tìm và chấp nhận điều khoản...")
        self.take_screenshot(page, "07_terms")

        agree_selectors = [
            'button:has-text("I agree")',
            'button:has-text("Tôi đồng ý")',
            'button:has-text("J\'accepte")',
            'span:has-text("I agree")',
            '//button[contains(.,"I agree")]',
            '//button[contains(.,"agree")]',
        ]

        terms_accepted = False
        for sel in agree_selectors:
            try:
                locator = page.locator(sel).first
                if locator.is_visible(timeout=3000):
                    # Scroll xuống nếu cần
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    self.random_sleep(0.5, 1)
                    locator.click()
                    page.wait_for_load_state('domcontentloaded', timeout=30000)
                    self.random_sleep(2, 4)
                    terms_accepted = True
                    self.log("✅ Đã chấp nhận điều khoản")
                    break
            except Exception:
                continue

        self.take_screenshot(page, "08_final")

        # ============ KIỂM TRA KẾT QUẢ ============
        self.random_sleep(2, 3)
        current_url = page.url

        if 'myaccount.google.com' in current_url or 'mail.google.com' in current_url:
            self.log(f"🎉 ĐĂNG KÝ THÀNH CÔNG: {email}")
            return {**result_base, 'status': 'success', 'detail': 'Đăng ký thành công'}

        elif 'accounts.google.com/speedbump' in current_url:
            self.log(f"⚠️ Cần xác minh thêm (speed bump): {email}")
            return {**result_base, 'status': 'needs_verification', 'detail': 'Google yêu cầu xác minh thêm (speed bump)'}

        elif 'challenge' in current_url or 'interstitial' in current_url:
            self.log(f"⚠️ Cần xác minh (challenge): {email}")
            return {**result_base, 'status': 'needs_verification', 'detail': f'Google yêu cầu xác minh. URL: {current_url}'}

        elif terms_accepted:
            self.log(f"✅ Có thể đã thành công: {email}")
            return {**result_base, 'status': 'possibly_success', 'detail': f'Điều khoản đã chấp nhận. URL: {current_url}'}

        else:
            self.log(f"❓ Kết quả không xác định: {email}")
            page_title = page.title()
            return {**result_base, 'status': 'unknown', 'detail': f'URL: {current_url}, Title: {page_title}'}

    def close(self):
        """Đóng browser và dọn dẹp"""
        try:
            if self.browser:
                self.browser.close()
                self.browser = None
            if self.pw:
                self.pw.stop()
                self.pw = None
            self.log("🔒 Đã đóng browser")
        except Exception as e:
            self.log(f"⚠️ Lỗi khi đóng browser: {e}")

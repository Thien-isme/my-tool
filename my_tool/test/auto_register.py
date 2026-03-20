"""
Auto Register Tool - Playwright (Improved)
============================================
Tự động đăng ký tài khoản Google bằng Playwright.

Cách dùng:
  1. Cài đặt:
       pip install playwright
       playwright install chromium
  2. Chỉnh sửa phần CONFIG bên dưới
  3. Chạy: python auto_register.py

⚠️ Lưu ý: Google có hệ thống chống bot rất mạnh (CAPTCHA, xác minh SĐT).
   Script này chỉ mang tính chất học tập / demo automation.
"""

import csv
import json
import logging
import os
import random
import string
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext

# ============================================================
# ⚙️  CONFIG
# ============================================================
@dataclass
class Config:
    """Cấu hình chính cho script."""
    # URL trang đăng ký Google
    signup_url: str = "https://accounts.google.com/signup"

    # Số tài khoản muốn tạo
    num_accounts: int = 1

    # False = hiển thị trình duyệt, True = chạy ngầm
    headless: bool = False

    # Khoảng delay giữa các lần tạo (giây) — [min, max]
    delay_between_accounts: tuple = (5, 10)

    # Delay ngẫu nhiên giữa các thao tác (giây) — [min, max]
    # Tăng cao để giống người thật hơn
    action_delay: tuple = (1.0, 3.0)

    # Delay khi gõ từng ký tự (ms) — [min, max]
    typing_delay: tuple = (80, 200)

    # Timeout chờ element xuất hiện (ms)
    element_timeout: int = 15000

    # Số lần retry khi thất bại
    max_retries: int = 2

    # Thư mục lưu screenshot lỗi
    screenshot_dir: str = "screenshots"

    # File lưu tài khoản đã tạo
    output_csv: str = "created_accounts.csv"

    # File log
    log_file: str = "auto_register.log"

    # ===== MẸO CHỐNG PHÁT HIỆN BOT =====

    # Thư mục lưu browser profile (cookies, history, cache)
    # Dùng profile thật giúp Google tin tưởng hơn
    user_data_dir: str = "browser_profile"

    # Chờ người dùng xử lý xác minh thủ công (QR code, SMS...)
    # True = script tạm dừng, chờ bạn xác minh, rồi tự tiếp tục
    # False = script bỏ qua bước xác minh (sẽ thất bại)
    wait_for_human_verification: bool = True

    # Thời gian tối đa chờ người dùng xác minh (giây)
    verification_timeout: int = 300  # 5 phút

    # ===== PROXY (giúp skip verification) =====
    # Dùng Residential Proxy để Google không yêu cầu xác minh
    # Để trống = không dùng proxy (dùng IP mạng nhà bạn)
    #
    # Ví dụ:
    #   proxy_server = "http://proxy.example.com:8080"
    #   proxy_username = "user123"
    #   proxy_password = "pass456"
    #
    # Dịch vụ Residential Proxy phổ biến:
    #   - Bright Data (brightdata.com)
    #   - Smartproxy (smartproxy.com)
    #   - IPRoyal (iproyal.com)
    #   - Proxy-Cheap (proxy-cheap.com)
    #   - Webshare (webshare.io) — có gói free
    proxy_server: str = ""        # VD: "http://host:port" hoặc "socks5://host:port"
    proxy_username: str = ""      # Username xác thực proxy (nếu có)
    proxy_password: str = ""      # Password xác thực proxy (nếu có)

    # Viewport ngẫu nhiên — danh sách các kích thước phổ biến
    viewports: list = field(default_factory=lambda: [
        {"width": 1920, "height": 1080},
        {"width": 1366, "height": 768},
        {"width": 1536, "height": 864},
        {"width": 1440, "height": 900},
        {"width": 1280, "height": 720},
    ])

    # Danh sách User-Agent phổ biến
    user_agents: list = field(default_factory=lambda: [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ])


# ============================================================
# 📋  DỮ LIỆU MẪU
# ============================================================
FIRST_NAMES = [
    "Minh", "Anh", "Hoa", "Nam", "Linh", "Tuan", "Lan", "Hung", "Thu", "Duc",
    "Ha", "Khanh", "Phuong", "Bao", "Trang", "Long", "Mai", "Viet", "Ngan", "Thi",
    "Dung", "Hieu", "Ngoc", "Khoa", "Thao", "Quang", "Huong", "Son", "Yen", "Tai",
]

LAST_NAMES = [
    "Nguyen", "Tran", "Le", "Pham", "Hoang", "Phan", "Vu", "Dang", "Bui", "Do",
    "Ho", "Ngo", "Duong", "Ly", "Dinh", "Cao", "Truong", "Vo", "Doan", "Luong",
    "Thai", "Lam", "Quach", "Tang", "Mai", "To", "Trinh", "Ha", "La", "Chau",
]


# ============================================================
# 📊  DATA CLASS CHO TÀI KHOẢN
# ============================================================
@dataclass
class AccountInfo:
    """Thông tin một tài khoản được tạo."""
    firstname: str
    lastname: str
    username: str
    password: str
    birth_day: int
    birth_month: int
    birth_year: int
    gender: str
    status: str = "pending"        # pending / success / failed
    error_message: str = ""
    created_at: str = ""

    @property
    def email(self) -> str:
        return f"{self.username}@gmail.com"

    def to_dict(self) -> dict:
        return {
            "firstname": self.firstname,
            "lastname": self.lastname,
            "email": self.email,
            "username": self.username,
            "password": self.password,
            "birthday": f"{self.birth_day:02d}/{self.birth_month:02d}/{self.birth_year}",
            "gender": self.gender,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at,
        }


# ============================================================
# 🛠️  LOGGER SETUP
# ============================================================
def setup_logger(log_file: str) -> logging.Logger:
    """Tạo logger ghi ra cả console và file."""
    logger = logging.getLogger("AutoRegister")
    logger.setLevel(logging.DEBUG)

    # Formatter
    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # File handler
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


# ============================================================
# 🎲  RANDOM GENERATORS
# ============================================================
def random_str(n: int = 8) -> str:
    """Tạo chuỗi ngẫu nhiên gồm chữ thường + số."""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def generate_account_info() -> AccountInfo:
    """Tạo thông tin tài khoản ngẫu nhiên."""
    firstname = random.choice(FIRST_NAMES)
    lastname = random.choice(LAST_NAMES)

    # Username: kết hợp tên + họ + số ngẫu nhiên → dễ đọc hơn
    username = f"{firstname.lower()}.{lastname.lower()}.{random_str(4)}"

    # Password: đủ mạnh (chữ hoa, chữ thường, số, ký tự đặc biệt)
    password = generate_strong_password()

    year = random.randint(1975, 2006)
    month = random.randint(1, 12)
    day = random.randint(1, 28)

    gender = random.choice(["male", "female"])

    return AccountInfo(
        firstname=firstname,
        lastname=lastname,
        username=username,
        password=password,
        birth_day=day,
        birth_month=month,
        birth_year=year,
        gender=gender,
    )


def generate_strong_password(length: int = 14) -> str:
    """Tạo mật khẩu mạnh đảm bảo có đủ loại ký tự."""
    lower = string.ascii_lowercase
    upper = string.ascii_uppercase
    digits = string.digits
    special = "!@#$%&*"

    # Đảm bảo có ít nhất 1 ký tự mỗi loại
    password = [
        random.choice(lower),
        random.choice(upper),
        random.choice(digits),
        random.choice(special),
    ]

    # Phần còn lại random từ tất cả
    all_chars = lower + upper + digits + special
    password += random.choices(all_chars, k=length - 4)

    # Xáo trộn
    random.shuffle(password)
    return "".join(password)


# ============================================================
# 🤖  AUTO REGISTER CLASS
# ============================================================
class AutoRegister:
    """Class chính xử lý việc tự động đăng ký."""

    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logger(config.log_file)
        self.results: list[AccountInfo] = []

        # Tạo thư mục screenshot nếu chưa có
        Path(config.screenshot_dir).mkdir(parents=True, exist_ok=True)

    # ------------ Helpers ------------

    def _human_delay(self):
        """Delay ngẫu nhiên giữa các thao tác, mô phỏng người thật."""
        delay = random.uniform(*self.config.action_delay)
        time.sleep(delay)

    def _random_typing_delay(self) -> int:
        """Trả về delay (ms) khi gõ từng ký tự."""
        return random.randint(*self.config.typing_delay)

    def _human_type(self, page: Page, selector: str, text: str):
        """Gõ chữ từng ký tự với tốc độ ngẫu nhiên như người thật."""
        page.click(selector)
        self._human_delay()
        for char in text:
            page.keyboard.type(char, delay=self._random_typing_delay())

    def _safe_click(self, page: Page, selector: str, timeout: Optional[int] = None):
        """Click an toàn: chờ element → di chuột tới → click."""
        timeout = timeout or self.config.element_timeout
        element = page.wait_for_selector(selector, timeout=timeout)
        if element:
            element.scroll_into_view_if_needed()
            self._human_delay()
            element.click()

    def _screenshot(self, page: Page, name: str):
        """Chụp screenshot với timestamp."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(self.config.screenshot_dir, f"{name}_{ts}.png")
        page.screenshot(path=path, full_page=True)
        self.logger.debug(f"Screenshot saved: {path}")
        return path

    # ------------ Browser Setup ------------

    def _create_stealth_context(self, browser: Browser) -> BrowserContext:
        """Tạo browser context với các thiết lập chống phát hiện bot."""
        viewport = random.choice(self.config.viewports)
        user_agent = random.choice(self.config.user_agents)

        context = browser.new_context(
            viewport=viewport,
            user_agent=user_agent,
            locale="vi-VN",
            timezone_id="Asia/Ho_Chi_Minh",
            # Giả lập có nhiều plugin như trình duyệt thật
            java_script_enabled=True,
            ignore_https_errors=True,
        )

        # Thêm script ẩn dấu hiệu Playwright / headless
        context.add_init_script("""
            // Ẩn navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });

            // Giả lập plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                    { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                    { name: 'Native Client', filename: 'internal-nacl-plugin' },
                ],
            });

            // Giả lập languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['vi-VN', 'vi', 'en-US', 'en'],
            });

            // Ẩn chrome runtime
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {},
            };
        """)

        return context

    # ------------ Browser Warmup ------------

    def warmup_browser(self, context: BrowserContext):
        """Làm ấm browser profile: lướt web tạo history/cookies.
        
        Giúp Google tin tưởng browser hơn → giảm yêu cầu xác minh.
        """
        self.logger.info("")
        self.logger.info("🌡️  Làm ấm browser profile...")
        self.logger.info("   Lướt web tạo history/cookies để Google tin tưởng hơn.")
        self.logger.info("")

        page = context.new_page()

        warmup_actions = [
            # --- Google Search ---
            {
                "name": "Google Search",
                "steps": [
                    ("goto", "https://www.google.com"),
                    ("wait", 3),
                    ("type", "input[name='q']", "thời tiết hôm nay"),
                    ("wait", 1),
                    ("press", "Enter"),
                    ("wait", 4),
                    ("scroll", 300),
                    ("wait", 2),
                ],
            },
            # --- YouTube ---
            {
                "name": "YouTube",
                "steps": [
                    ("goto", "https://www.youtube.com"),
                    ("wait", 4),
                    ("scroll", 500),
                    ("wait", 3),
                    ("scroll", 300),
                    ("wait", 2),
                ],
            },
            # --- Google Maps ---
            {
                "name": "Google Maps",
                "steps": [
                    ("goto", "https://www.google.com/maps"),
                    ("wait", 4),
                    ("scroll", 200),
                    ("wait", 2),
                ],
            },
            # --- Wikipedia ---
            {
                "name": "Wikipedia",
                "steps": [
                    ("goto", "https://vi.wikipedia.org"),
                    ("wait", 3),
                    ("scroll", 400),
                    ("wait", 2),
                    ("scroll", 300),
                    ("wait", 1),
                ],
            },
            # --- Google lần 2 (tìm kiếm khác) ---
            {
                "name": "Google Search 2",
                "steps": [
                    ("goto", "https://www.google.com"),
                    ("wait", 2),
                    ("type", "input[name='q']", "tin tức việt nam"),
                    ("wait", 1),
                    ("press", "Enter"),
                    ("wait", 4),
                    ("scroll", 500),
                    ("wait", 3),
                ],
            },
            # --- Gmail (trang đăng nhập) ---
            {
                "name": "Gmail Login Page",
                "steps": [
                    ("goto", "https://mail.google.com"),
                    ("wait", 3),
                ],
            },
        ]

        for action in warmup_actions:
            try:
                self.logger.info(f"   🌐 {action['name']}...")
                for step in action["steps"]:
                    cmd = step[0]

                    if cmd == "goto":
                        page.goto(step[1], wait_until="domcontentloaded", timeout=15000)
                    elif cmd == "wait":
                        delay = step[1] + random.uniform(0.5, 2.0)
                        time.sleep(delay)
                    elif cmd == "type":
                        try:
                            el = page.wait_for_selector(step[1], timeout=5000)
                            if el:
                                el.click()
                                for char in step[2]:
                                    page.keyboard.type(char, delay=random.randint(80, 200))
                        except Exception:
                            pass
                    elif cmd == "press":
                        page.keyboard.press(step[1])
                    elif cmd == "scroll":
                        page.mouse.wheel(0, step[1])
                    elif cmd == "click":
                        try:
                            self._safe_click(page, step[1], timeout=3000)
                        except Exception:
                            pass

            except Exception as e:
                self.logger.debug(f"   ⚠️ Warmup '{action['name']}' lỗi: {e}")
                continue

        page.close()

        self.logger.info("")
        self.logger.info("✅  Làm ấm hoàn tất! Browser đã có history/cookies.")
        self.logger.info("")

    def _step_open_signup(self, page: Page):
        """Bước 1: Mở trang đăng ký."""
        self.logger.debug("→ Mở trang đăng ký...")
        page.goto(self.config.signup_url, wait_until="networkidle")
        self._human_delay()

    def _step_select_personal(self, page: Page):
        """Bước 2: Click 'Tạo tài khoản' và chọn 'Cho mục đích cá nhân'."""
        self.logger.debug("→ Click 'Tạo tài khoản'...")

        # Thử nhiều selector cho nút "Tạo tài khoản"
        create_selectors = [
            "text=Tạo tài khoản",
            "text=Create account",
            "[data-action='sign up']",
        ]
        clicked = False
        for sel in create_selectors:
            try:
                self._safe_click(page, sel, timeout=5000)
                clicked = True
                break
            except Exception:
                continue

        if not clicked:
            self.logger.warning("Không tìm thấy nút 'Tạo tài khoản', thử tiếp...")

        page.wait_for_load_state("networkidle")
        self._human_delay()

        # Chọn "Cho mục đích cá nhân"
        personal_selectors = [
            "text=Cho mục đích cá nhân",
            "text=For my personal use",
            "li:has-text('cá nhân')",
        ]
        for sel in personal_selectors:
            try:
                self._safe_click(page, sel, timeout=5000)
                break
            except Exception:
                continue

        page.wait_for_load_state("networkidle")
        self._human_delay()

    def _step_fill_name(self, page: Page, account: AccountInfo):
        """Bước 3: Điền Họ và Tên."""
        self.logger.debug(f"→ Điền tên: {account.firstname} {account.lastname}")

        # Thử nhiều selector cho ô tên
        name_selectors = [
            ("[name='firstName']", "[name='lastName']"),
            ("#firstName", "#lastName"),
            ("input[autocomplete='given-name']", "input[autocomplete='family-name']"),
        ]

        filled = False
        for first_sel, last_sel in name_selectors:
            try:
                page.wait_for_selector(first_sel, timeout=5000)
                self._human_type(page, first_sel, account.firstname)
                self._human_delay()
                self._human_type(page, last_sel, account.lastname)
                filled = True
                break
            except Exception:
                continue

        if not filled:
            raise RuntimeError("Không tìm thấy ô nhập Họ/Tên")

        self._human_delay()

        # Click "Tiếp theo"
        self._click_next(page)

    def _step_fill_birthday_gender(self, page: Page, account: AccountInfo):
        """Bước 4: Điền ngày sinh và giới tính."""
        self.logger.debug(
            f"→ Điền ngày sinh: {account.birth_day:02d}/{account.birth_month:02d}/{account.birth_year} "
            f"| Giới tính: {account.gender}"
        )

        page.wait_for_load_state("networkidle")
        self._human_delay()

        # ---- THÁNG (select dropdown) ----
        # Google dùng <select> nhưng có thể không có id/name cố định.
        # Chiến lược: tìm tất cả <select> trên trang, select đầu tiên = tháng, select cuối = giới tính.
        month_filled = False

        # Cách 1: Tìm bằng các selector phổ biến
        month_selectors = [
            "#month",
            "[name='month']",
            "select[id='month']",
            "select[aria-label='Tháng']",
            "select[aria-label='Month']",
        ]
        for sel in month_selectors:
            try:
                el = page.wait_for_selector(sel, timeout=3000)
                if el:
                    page.select_option(sel, str(account.birth_month))
                    month_filled = True
                    self.logger.debug(f"  ✓ Tháng: chọn bằng selector '{sel}'")
                    break
            except Exception:
                continue

        # Cách 2: Lấy tất cả <select> trên trang, select đầu tiên = tháng
        if not month_filled:
            try:
                selects = page.query_selector_all("select")
                self.logger.debug(f"  Tìm thấy {len(selects)} <select> trên trang")
                if len(selects) >= 1:
                    selects[0].select_option(str(account.birth_month))
                    month_filled = True
                    self.logger.debug("  ✓ Tháng: chọn bằng select[0]")
            except Exception as e:
                self.logger.debug(f"  ✗ Tháng select[0] thất bại: {e}")

        # Cách 3: Custom dropdown (div-based) — click để mở, rồi chọn option
        if not month_filled:
            try:
                # Tháng tiếng Việt
                MONTH_NAMES_VI = [
                    "", "Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4",
                    "Tháng 5", "Tháng 6", "Tháng 7", "Tháng 8",
                    "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12",
                ]
                MONTH_NAMES_EN = [
                    "", "January", "February", "March", "April",
                    "May", "June", "July", "August",
                    "September", "October", "November", "December",
                ]
                month_name_vi = MONTH_NAMES_VI[account.birth_month]
                month_name_en = MONTH_NAMES_EN[account.birth_month]

                # Click dropdown "Tháng" / "Month"
                dropdown_selectors = [
                    "div[aria-label='Tháng']",
                    "div[aria-label='Month']",
                    "div:has-text('Tháng'):not(:has(div:has-text('Tháng')))",
                ]
                for sel in dropdown_selectors:
                    try:
                        self._safe_click(page, sel, timeout=3000)
                        self._human_delay()
                        # Chọn tháng từ danh sách option
                        for month_text in [month_name_vi, month_name_en, str(account.birth_month)]:
                            try:
                                page.click(f"li[role='option']:has-text('{month_text}')", timeout=3000)
                                month_filled = True
                                self.logger.debug(f"  ✓ Tháng: chọn bằng custom dropdown '{month_text}'")
                                break
                            except Exception:
                                continue
                        if month_filled:
                            break
                    except Exception:
                        continue
            except Exception as e:
                self.logger.debug(f"  ✗ Tháng custom dropdown thất bại: {e}")

        if not month_filled:
            raise RuntimeError("Không thể chọn tháng sinh")

        self._human_delay()

        # ---- NGÀY (input text) ----
        day_filled = False
        day_selectors = [
            "#day",
            "[name='day']",
            "input[aria-label='Ngày']",
            "input[aria-label='Day']",
            "input[placeholder='Ngày']",
            "input[placeholder='Day']",
        ]
        for sel in day_selectors:
            try:
                el = page.wait_for_selector(sel, timeout=3000)
                if el:
                    el.click()
                    el.fill(str(account.birth_day))
                    day_filled = True
                    self.logger.debug(f"  ✓ Ngày: điền bằng selector '{sel}'")
                    break
            except Exception:
                continue

        # Fallback: tìm tất cả input[type=text] hoặc input[type=tel] trên trang
        if not day_filled:
            try:
                inputs = page.query_selector_all("input")
                for inp in inputs:
                    placeholder = inp.get_attribute("placeholder") or ""
                    aria = inp.get_attribute("aria-label") or ""
                    if any(kw in placeholder.lower() or kw in aria.lower() for kw in ["ngày", "day"]):
                        inp.click()
                        inp.fill(str(account.birth_day))
                        day_filled = True
                        self.logger.debug("  ✓ Ngày: điền bằng tìm input theo placeholder/aria")
                        break
            except Exception as e:
                self.logger.debug(f"  ✗ Ngày fallback thất bại: {e}")

        if not day_filled:
            self.logger.warning("  ⚠ Không thể điền ngày sinh")

        self._human_delay()

        # ---- NĂM (input text) ----
        year_filled = False
        year_selectors = [
            "#year",
            "[name='year']",
            "input[aria-label='Năm']",
            "input[aria-label='Year']",
            "input[placeholder='Năm']",
            "input[placeholder='Year']",
        ]
        for sel in year_selectors:
            try:
                el = page.wait_for_selector(sel, timeout=3000)
                if el:
                    el.click()
                    el.fill(str(account.birth_year))
                    year_filled = True
                    self.logger.debug(f"  ✓ Năm: điền bằng selector '{sel}'")
                    break
            except Exception:
                continue

        # Fallback: tìm tất cả input theo placeholder/aria
        if not year_filled:
            try:
                inputs = page.query_selector_all("input")
                for inp in inputs:
                    placeholder = inp.get_attribute("placeholder") or ""
                    aria = inp.get_attribute("aria-label") or ""
                    if any(kw in placeholder.lower() or kw in aria.lower() for kw in ["năm", "year"]):
                        inp.click()
                        inp.fill(str(account.birth_year))
                        year_filled = True
                        self.logger.debug("  ✓ Năm: điền bằng tìm input theo placeholder/aria")
                        break
            except Exception as e:
                self.logger.debug(f"  ✗ Năm fallback thất bại: {e}")

        if not year_filled:
            self.logger.warning("  ⚠ Không thể điền năm sinh")

        self._human_delay()

        # ---- GIỚI TÍNH (custom dropdown — Google không dùng <select>) ----
        gender_filled = False

        gender_text_map = {
            "male": ["Nam", "Male"],
            "female": ["Nữ", "Female"],
        }
        gender_texts = gender_text_map.get(account.gender, ["Không muốn nói", "Rather not say"])

        # Cách 1 (ưu tiên): Click vào dropdown "Giới tính" bằng ID #gender
        gender_click_selectors = [
            "#gender",
            "[id='gender']",
        ]
        for sel in gender_click_selectors:
            try:
                el = page.wait_for_selector(sel, timeout=3000)
                if el:
                    tag = el.evaluate("el => el.tagName.toLowerCase()")
                    self.logger.debug(f"  Gender element '{sel}' tag: {tag}")

                    if tag == "select":
                        # Nếu bất ngờ là <select>
                        gender_map = {"male": "1", "female": "2"}
                        gender_value = gender_map.get(account.gender, "3")
                        page.select_option(sel, gender_value)
                        gender_filled = True
                        self.logger.debug(f"  ✓ Giới tính: select_option bằng '{sel}'")
                    else:
                        # Custom dropdown: click để mở
                        el.click()
                        self._human_delay()
                        # Chọn option từ danh sách
                        for g_text in gender_texts:
                            try:
                                page.click(f"li:has-text('{g_text}')", timeout=3000)
                                gender_filled = True
                                self.logger.debug(f"  ✓ Giới tính: chọn '{g_text}' qua #{sel}")
                                break
                            except Exception:
                                continue
                        if not gender_filled:
                            # Thử role=option
                            for g_text in gender_texts:
                                try:
                                    page.click(f"[role='option']:has-text('{g_text}')", timeout=3000)
                                    gender_filled = True
                                    self.logger.debug(f"  ✓ Giới tính: chọn '{g_text}' qua role=option")
                                    break
                                except Exception:
                                    continue
                    if gender_filled:
                        break
            except Exception:
                continue

        # Cách 2: Click bằng text label "Giới tính" hoặc "Gender"
        if not gender_filled:
            label_texts = ["Giới tính", "Gender"]
            for label in label_texts:
                try:
                    # Tìm element dropdown chứa text label
                    dropdown = page.locator(f"div:has-text('{label}')").last
                    if dropdown:
                        dropdown.click(timeout=3000)
                        self._human_delay()
                        for g_text in gender_texts:
                            try:
                                page.click(f"li:has-text('{g_text}')", timeout=3000)
                                gender_filled = True
                                self.logger.debug(f"  ✓ Giới tính: chọn '{g_text}' qua label '{label}'")
                                break
                            except Exception:
                                continue
                        if not gender_filled:
                            for g_text in gender_texts:
                                try:
                                    page.click(f"[role='option']:has-text('{g_text}')", timeout=3000)
                                    gender_filled = True
                                    self.logger.debug(f"  ✓ Giới tính: chọn '{g_text}' qua role=option (label)")
                                    break
                                except Exception:
                                    continue
                        if gender_filled:
                            break
                except Exception:
                    continue

        # Cách 3: Tìm tất cả div[role=listbox] hoặc aria-label dạng dropdown
        if not gender_filled:
            dropdown_aria_selectors = [
                "div[aria-label='Giới tính']",
                "div[aria-label='Gender']",
                "[aria-haspopup='listbox']:last-of-type",
            ]
            for sel in dropdown_aria_selectors:
                try:
                    self._safe_click(page, sel, timeout=3000)
                    self._human_delay()
                    for g_text in gender_texts:
                        try:
                            page.click(f"li:has-text('{g_text}')", timeout=3000)
                            gender_filled = True
                            self.logger.debug(f"  ✓ Giới tính: chọn '{g_text}' qua aria selector '{sel}'")
                            break
                        except Exception:
                            continue
                    if gender_filled:
                        break
                except Exception:
                    continue

        if not gender_filled:
            self.logger.warning("  ⚠ Không thể chọn giới tính — sẽ bị Google từ chối ở bước tiếp.")

        self._human_delay()
        self._click_next(page)

    def _step_choose_username(self, page: Page, account: AccountInfo):
        """Bước 5: Chọn địa chỉ Gmail (username)."""
        self.logger.debug(f"→ Chọn username: {account.username}")

        page.wait_for_load_state("networkidle")
        self._human_delay()

        # Có thể Google đề xuất username hoặc cho tự nhập
        # Thử click "Tạo địa chỉ Gmail của riêng bạn"
        custom_selectors = [
            "text=Tạo địa chỉ Gmail của riêng bạn",
            "text=Create your own Gmail address",
            "#selectionc4",
        ]
        for sel in custom_selectors:
            try:
                self._safe_click(page, sel, timeout=5000)
                break
            except Exception:
                continue

        self._human_delay()

        # Điền username
        username_selectors = [
            "[name='Username']",
            "#username",
            "input[type='text']",
        ]
        filled = False
        for sel in username_selectors:
            try:
                page.wait_for_selector(sel, timeout=5000)
                self._human_type(page, sel, account.username)
                filled = True
                break
            except Exception:
                continue

        if not filled:
            raise RuntimeError("Không tìm thấy ô nhập username")

        self._human_delay()
        self._click_next(page)

    def _step_fill_password(self, page: Page, account: AccountInfo):
        """Bước 6: Nhập mật khẩu."""
        self.logger.debug(f"→ Nhập mật khẩu: {'*' * len(account.password)}")

        page.wait_for_load_state("networkidle")
        self._human_delay()

        # Ô mật khẩu
        password_selectors = [
            "[name='Passwd']",
            "#passwd",
            "input[type='password']",
        ]
        filled = False
        for sel in password_selectors:
            try:
                page.wait_for_selector(sel, timeout=5000)
                self._human_type(page, sel, account.password)
                filled = True
                break
            except Exception:
                continue

        if not filled:
            raise RuntimeError("Không tìm thấy ô nhập mật khẩu")

        self._human_delay()

        # Ô xác nhận mật khẩu
        confirm_selectors = [
            "[name='PasswdAgain']",
            "[name='ConfirmPasswd']",
            "#confirm-passwd",
        ]
        for sel in confirm_selectors:
            try:
                page.wait_for_selector(sel, timeout=3000)
                self._human_type(page, sel, account.password)
                break
            except Exception:
                continue

        self._human_delay()
        self._click_next(page)

    def _step_handle_verification(self, page: Page):
        """Bước 7: Xử lý TẤT CẢ loại xác minh (QR code, SĐT, CAPTCHA...).
        
        Nếu config.wait_for_human_verification = True:
          → Script tạm dừng, hiện thông báo, chờ người dùng xử lý thủ công
          → Sau khi người dùng xác minh xong → script tự động tiếp tục
        """
        self.logger.debug("→ Kiểm tra yêu cầu xác minh...")
        page.wait_for_load_state("networkidle")
        self._human_delay()

        # Các dấu hiệu nhận biết trang xác minh
        verification_indicators = [
            # QR code verification
            "text=Quét mã QR bằng điện thoại",
            "text=Scan the QR code",
            "text=Xác minh một số thông tin",
            "text=Verify it's you",
            # Phone verification  
            "text=Xác minh số điện thoại",
            "text=Verify your phone number",
            "text=Thêm số điện thoại",
            "text=Add phone number",
            "[name='phoneNumberId']",
            "#phoneNumberId",
            # CAPTCHA
            "text=Xác minh rằng bạn không phải là rô-bốt",
            "text=Verify you're not a robot",
            "iframe[title='reCAPTCHA']",
        ]

        verification_found = False
        for sel in verification_indicators:
            try:
                el = page.wait_for_selector(sel, timeout=2000)
                if el:
                    verification_found = True
                    self.logger.warning(f"⚠️ Phát hiện yêu cầu xác minh: {sel}")
                    break
            except Exception:
                continue

        if not verification_found:
            # Kiểm tra URL có chứa keyword xác minh không
            url = page.url.lower()
            if any(kw in url for kw in ["challenge", "verify", "captcha", "signin/rejected"]):
                verification_found = True
                self.logger.warning(f"⚠️ Phát hiện trang xác minh từ URL: {url}")

        if not verification_found:
            self.logger.debug("→ Không yêu cầu xác minh ✓")
            return True

        # --- CÓ YÊU CẦU XÁC MINH ---
        self._screenshot(page, "verification_required")

        # Thử bỏ qua nếu có nút Skip
        skip_selectors = [
            "text=Bỏ qua",
            "text=Skip",
            "text=Không phải bây giờ",
            "text=Not now",
            "button:has-text('Skip')",
            "button:has-text('Bỏ qua')",
        ]
        for skip_sel in skip_selectors:
            try:
                self._safe_click(page, skip_sel, timeout=2000)
                self.logger.info("→ ✅ Đã bỏ qua xác minh!")
                page.wait_for_load_state("networkidle")
                return True
            except Exception:
                continue

        # Không thể bỏ qua → chờ người dùng xử lý thủ công
        if not self.config.wait_for_human_verification:
            raise RuntimeError(
                "Yêu cầu xác minh (QR/SĐT/CAPTCHA) — "
                "Bật wait_for_human_verification=True để chờ xử lý thủ công."
            )

        # === CHẾ ĐỘ BÁN TỰ ĐỘNG ===
        self.logger.info("")
        self.logger.info("" + "=" * 55)
        self.logger.info("📱  CẦN XÁC MINH THỦ CÔNG")
        self.logger.info("=" * 55)
        self.logger.info("  Google yêu cầu xác minh trước khi tạo tài khoản.")
        self.logger.info("  Hãy thực hiện xác minh trên cửa sổ trình duyệt:")
        self.logger.info("    • Quét mã QR bằng điện thoại, HOẶC")
        self.logger.info("    • Nhập số điện thoại + mã OTP, HOẶC")
        self.logger.info("    • Giải CAPTCHA")
        self.logger.info("")
        self.logger.info(f"  ⏳ Script sẽ chờ tối đa {self.config.verification_timeout}s...")
        self.logger.info("  ✅ Sau khi xác minh xong, script sẽ tự động tiếp tục!")
        self.logger.info("=" * 55)
        self.logger.info("")

        # Chờ trang chuyển đi (xác minh thành công)
        start_time = time.time()
        original_url = page.url

        while time.time() - start_time < self.config.verification_timeout:
            time.sleep(2)  # Check mỗi 2 giây
            current_url = page.url

            # Nếu URL thay đổi → có thể đã xác minh xong
            if current_url != original_url:
                self.logger.info(f"→ URL đã thay đổi: {current_url[:80]}...")

                # Kiểm tra xem vẫn ở trang xác minh hay đã qua
                still_verifying = False
                for sel in verification_indicators:
                    try:
                        el = page.wait_for_selector(sel, timeout=1000)
                        if el:
                            still_verifying = True
                            break
                    except Exception:
                        continue

                if not still_verifying:
                    self.logger.info("→ ✅ Xác minh thành công! Tiếp tục tự động...")
                    page.wait_for_load_state("networkidle")
                    self._human_delay()
                    return True
                else:
                    # URL thay đổi nhưng vẫn ở trang xác minh khác
                    original_url = current_url

            # Kiểm tra xem đã vào trang tiếp chưa (username, password, success...)
            progress_indicators = [
                "[name='Username']",
                "[name='Passwd']",
                "text=Chào mừng",
                "text=Welcome",
                "text=Tạo địa chỉ Gmail",
                "text=Create your Gmail address",
                "text=Tạo mật khẩu",
                "text=Create a strong password",
            ]
            for sel in progress_indicators:
                try:
                    el = page.wait_for_selector(sel, timeout=500)
                    if el:
                        self.logger.info(f"→ ✅ Xác minh thành công! Phát hiện: {sel}")
                        return True
                except Exception:
                    continue

            elapsed = int(time.time() - start_time)
            if elapsed % 30 == 0 and elapsed > 0:
                self.logger.info(f"  ⏳ Đã chờ {elapsed}s / {self.config.verification_timeout}s...")

        # Hết thời gian chờ
        raise RuntimeError(
            f"Hết thời gian chờ xác minh ({self.config.verification_timeout}s). "
            "Hãy tăng verification_timeout hoặc xác minh nhanh hơn."
        )

    def _step_agree_terms(self, page: Page):
        """Bước 8: Đồng ý điều khoản sử dụng."""
        self.logger.debug("→ Kiểm tra và đồng ý điều khoản...")

        page.wait_for_load_state("networkidle")
        self._human_delay()

        # Có thể có trang recovery email/phone trước khi đến terms
        # Thử bỏ qua nếu có
        skip_selectors = [
            "text=Bỏ qua",
            "text=Skip",
            "text=Không phải bây giờ",
            "text=Not now",
        ]
        for sel in skip_selectors:
            try:
                self._safe_click(page, sel, timeout=3000)
                self.logger.debug(f"→ Bỏ qua bước phụ: {sel}")
                page.wait_for_load_state("networkidle")
                self._human_delay()
            except Exception:
                continue

        # Đồng ý điều khoản
        agree_selectors = [
            "text=Tôi đồng ý",
            "text=I agree",
            "button:has-text('Đồng ý')",
            "button:has-text('Agree')",
            "button:has-text('Chấp nhận')",
            "button:has-text('Accept')",
        ]

        for sel in agree_selectors:
            try:
                self._safe_click(page, sel, timeout=5000)
                self.logger.debug("→ Đã đồng ý điều khoản.")
                page.wait_for_load_state("networkidle")
                return
            except Exception:
                continue

        self.logger.debug("→ Không tìm thấy nút đồng ý (có thể đã qua bước này).")

    def _click_next(self, page: Page):
        """Click nút 'Tiếp theo' / 'Next'."""
        next_selectors = [
            "text=Tiếp theo",
            "text=Next",
            "button:has-text('Tiếp')",
            "button:has-text('Next')",
            "#identifierNext",
            "#next",
        ]

        page.wait_for_load_state("networkidle")

        for sel in next_selectors:
            try:
                self._safe_click(page, sel, timeout=5000)
                page.wait_for_load_state("networkidle")
                return
            except Exception:
                continue

        self.logger.warning("Không tìm thấy nút 'Tiếp theo', tiếp tục...")

    def _check_success(self, page: Page) -> bool:
        """Kiểm tra xem đăng ký có thành công không."""
        success_indicators = [
            "text=Chào mừng",
            "text=Welcome",
            "myaccount.google.com",
            "text=Tài khoản của bạn đã được tạo",
        ]

        self._human_delay()

        # Kiểm tra URL
        current_url = page.url
        if "myaccount.google.com" in current_url or "welcome" in current_url.lower():
            return True

        # Kiểm tra text
        for sel in success_indicators:
            try:
                if sel.startswith("text="):
                    el = page.wait_for_selector(sel, timeout=5000)
                    if el:
                        return True
            except Exception:
                continue

        return False

    # ------------ Main Flow ------------

    def create_single_account(self, page: Page, account: AccountInfo, index: int) -> bool:
        """Thực hiện toàn bộ luồng tạo 1 tài khoản."""
        self.logger.info(
            f"[{index + 1}/{self.config.num_accounts}] "
            f"Tạo: {account.firstname} {account.lastname} | {account.email}"
        )

        try:
            self._step_open_signup(page)
            self._step_select_personal(page)
            self._step_fill_name(page, account)
            self._step_fill_birthday_gender(page, account)

            # Kiểm tra xác minh sau khi điền thông tin cơ bản
            self._step_handle_verification(page)

            self._step_choose_username(page, account)
            self._step_fill_password(page, account)

            # Kiểm tra xác minh sau khi tạo mật khẩu
            self._step_handle_verification(page)

            self._step_agree_terms(page)

            # Kiểm tra xác minh cuối cùng
            self._step_handle_verification(page)

            # Kiểm tra thành công
            if self._check_success(page):
                account.status = "success"
                account.created_at = datetime.now().isoformat()
                self.logger.info(f"[{index + 1}] ✅ Thành công! → {account.email}")
                self._screenshot(page, f"success_{index + 1}")
                return True
            else:
                account.status = "failed"
                account.error_message = "Không xác nhận được trạng thái đăng ký"
                self.logger.warning(f"[{index + 1}] ⚠️ Không rõ kết quả đăng ký.")
                self._screenshot(page, f"unclear_{index + 1}")
                return False

        except Exception as e:
            account.status = "failed"
            account.error_message = str(e)
            self.logger.error(f"[{index + 1}] ❌ Thất bại: {e}")
            self._screenshot(page, f"error_{index + 1}")
            return False

    def save_results(self):
        """Lưu kết quả ra file CSV."""
        if not self.results:
            self.logger.info("Không có kết quả để lưu.")
            return

        fieldnames = [
            "firstname", "lastname", "email", "username", "password",
            "birthday", "gender", "status", "error_message", "created_at",
        ]

        file_exists = os.path.exists(self.config.output_csv)

        with open(self.config.output_csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            for acc in self.results:
                writer.writerow(acc.to_dict())

        self.logger.info(f"📁 Kết quả đã lưu vào: {self.config.output_csv}")

    def print_summary(self):
        """In bảng tổng kết."""
        total = len(self.results)
        success = sum(1 for a in self.results if a.status == "success")
        failed = total - success

        self.logger.info("")
        self.logger.info("=" * 50)
        self.logger.info("📊  TỔNG KẾT")
        self.logger.info("=" * 50)
        self.logger.info(f"  Tổng số:    {total}")
        self.logger.info(f"  ✅ Thành công: {success}")
        self.logger.info(f"  ❌ Thất bại:   {failed}")
        self.logger.info("=" * 50)

        if success > 0:
            self.logger.info("")
            self.logger.info("📋  TÀI KHOẢN TẠO THÀNH CÔNG:")
            self.logger.info("-" * 50)
            for acc in self.results:
                if acc.status == "success":
                    self.logger.info(f"  📧 {acc.email} | 🔑 {acc.password}")
            self.logger.info("-" * 50)

    def run(self):
        """Chạy toàn bộ quy trình."""
        self.logger.info("🚀 Bắt đầu Auto Register Tool")
        self.logger.info(f"   Số tài khoản cần tạo: {self.config.num_accounts}")
        self.logger.info(f"   Headless: {self.config.headless}")
        self.logger.info(f"   Chờ xác minh thủ công: {self.config.wait_for_human_verification}")
        self.logger.info(f"   Browser profile: {self.config.user_data_dir}")
        self.logger.info("")

        # Tạo thư mục browser profile
        Path(self.config.user_data_dir).mkdir(parents=True, exist_ok=True)

        with sync_playwright() as p:
            # ===== DÙNG PERSISTENT CONTEXT =====
            # Giữ cookies, history, cache giữa các lần chạy
            # → Google tin tưởng hơn, ít yêu cầu xác minh hơn
            viewport = random.choice(self.config.viewports)
            user_agent = random.choice(self.config.user_agents)

            # Cấu hình proxy nếu có
            proxy_config = None
            if self.config.proxy_server:
                proxy_config = {"server": self.config.proxy_server}
                if self.config.proxy_username:
                    proxy_config["username"] = self.config.proxy_username
                    proxy_config["password"] = self.config.proxy_password
                self.logger.info(f"   🌐 Proxy: {self.config.proxy_server}")
            else:
                self.logger.info("   🌐 Proxy: Không (dùng IP trực tiếp)")

            context = p.chromium.launch_persistent_context(
                user_data_dir=self.config.user_data_dir,
                headless=self.config.headless,
                channel="chrome",  # ← DÙNG CHROME THẬT thay vì Chromium!
                viewport=viewport,
                user_agent=user_agent,
                locale="vi-VN",
                timezone_id="Asia/Ho_Chi_Minh",
                proxy=proxy_config,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-infobars",
                    "--disable-extensions",
                    "--disable-automation",
                    "--exclude-switches=enable-automation",
                    "--disable-component-extensions-with-background-pages",
                ],
                ignore_https_errors=True,
            )

            # Thêm stealth scripts
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                        { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                        { name: 'Native Client', filename: 'internal-nacl-plugin' },
                    ],
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['vi-VN', 'vi', 'en-US', 'en'],
                });
                window.chrome = { runtime: {}, loadTimes: function(){}, csi: function(){}, app: {} };
            """)

            # Làm ấm browser profile nếu chưa từng làm
            warmup_marker = os.path.join(self.config.user_data_dir, ".warmup_done")
            if not os.path.exists(warmup_marker):
                self.warmup_browser(context)
                with open(warmup_marker, "w") as f:
                    f.write(datetime.now().isoformat())
            else:
                self.logger.info("🌡️  Browser đã được làm ấm trước đó → bỏ qua.")
                self.logger.info("   (Xóa file browser_profile/.warmup_done để làm ấm lại)")
                self.logger.info("")

            for i in range(self.config.num_accounts):
                account = generate_account_info()
                success = False

                # Retry logic
                for attempt in range(self.config.max_retries + 1):
                    if attempt > 0:
                        self.logger.info(
                            f"[{i + 1}] 🔄 Retry lần {attempt}/{self.config.max_retries}..."
                        )
                        account = generate_account_info()

                    page = context.new_page()

                    try:
                        success = self.create_single_account(page, account, i)
                    finally:
                        page.close()

                    if success:
                        break

                    if attempt < self.config.max_retries:
                        retry_delay = random.uniform(5, 10)
                        self.logger.debug(f"Chờ {retry_delay:.1f}s trước khi retry...")
                        time.sleep(retry_delay)

                self.results.append(account)

                # Delay giữa các lần tạo
                if i < self.config.num_accounts - 1:
                    delay = random.uniform(*self.config.delay_between_accounts)
                    self.logger.info(f"Chờ {delay:.1f}s trước tài khoản tiếp...")
                    time.sleep(delay)

            context.close()

        # Lưu kết quả & tổng kết
        self.save_results()
        self.print_summary()


# ============================================================
# ▶️  ENTRY POINT
# ============================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Auto Register Google Account")
    parser.add_argument("--warmup", action="store_true",
                        help="Chỉ làm ấm browser profile (không tạo tài khoản)")
    parser.add_argument("--reset", action="store_true",
                        help="Xóa browser profile cũ và bắt đầu mới")
    parser.add_argument("--accounts", type=int, default=1,
                        help="Số tài khoản cần tạo (mặc định: 1)")
    parser.add_argument("--proxy", type=str, default="",
                        help="Proxy server (VD: http://host:port)")
    parser.add_argument("--proxy-user", type=str, default="",
                        help="Proxy username")
    parser.add_argument("--proxy-pass", type=str, default="",
                        help="Proxy password")
    args = parser.parse_args()

    config = Config(
        num_accounts=args.accounts,
        headless=False,
        wait_for_human_verification=True,
        verification_timeout=300,
        proxy_server=args.proxy,
        proxy_username=args.proxy_user,
        proxy_password=args.proxy_pass,
    )

    # Xóa profile cũ nếu --reset
    if args.reset:
        import shutil
        if os.path.exists(config.user_data_dir):
            shutil.rmtree(config.user_data_dir)
            print(f"🗑️  Đã xóa browser profile cũ: {config.user_data_dir}")
        if os.path.exists(config.screenshot_dir):
            shutil.rmtree(config.screenshot_dir)
        print("✅ Reset xong! Profile mới sẽ được tạo khi chạy.\n")

    tool = AutoRegister(config)

    if args.warmup:
        # Chỉ làm ấm, không tạo tài khoản
        Path(config.user_data_dir).mkdir(parents=True, exist_ok=True)
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=config.user_data_dir,
                headless=False,
                channel="chrome",
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-automation",
                ],
            )
            tool.warmup_browser(ctx)
            ctx.close()
        print("\n✅ Làm ấm xong! Giờ chạy lại không có --warmup để tạo tài khoản.")
    else:
        tool.run()

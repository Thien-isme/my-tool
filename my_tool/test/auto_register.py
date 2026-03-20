"""
Auto Register Tool - Playwright
================================
Cách dùng:
  1. Cài đặt: pip install playwright && playwright install chromium
  2. Chỉnh sửa phần CONFIG bên dưới
  3. Chạy: python auto_register.py

Chỉnh lại các selector (#id, .class, hoặc text) cho đúng với website của bạn.
"""

from playwright.sync_api import sync_playwright
import random
import string
import time

# ============================================================
# ⚙️  CONFIG - Chỉnh sửa tại đây
# ============================================================
BASE_URL = "https://accounts.google.com/v3/signin/identifier?continue=https%3A%2F%2Fmyaccount.google.com%2Fintro%2Fpersonal-info%3Fhl%3Dvi&dsh=S-1205284745%3A1774030175763681&ec=GAZAwAE&followup=https%3A%2F%2Fmyaccount.google.com%2Fintro%2Fpersonal-info%3Fhl%3Dvi&hl=vi&osid=1&passive=1209600&service=accountsettings&flowName=GlifWebSignIn&flowEntry=ServiceLogin&ifkv=ASfE1-omj5S_Jwujb-wdJGiGRWMPq65dbX9Zk0x9DTXgcgHjtxaiVxwFsP7chf4AbEYaRdAt_AiBaA"   # ← ĐỔI THÀNH URL WEBSITE CỦA BẠN (VD: https://abc.com)
NUM_ACCOUNTS = 5                         # Số tài khoản muốn tạo
HEADLESS = False                         # False = xem browser, True = chạy ngầm
DELAY_BETWEEN_ACCOUNTS = 1              # Giây chờ giữa các lần tạo
# ============================================================


def random_str(n=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=n))


FIRST_NAMES = ["Minh", "Anh", "Hoa", "Nam", "Linh", "Tuan", "Lan", "Hung", "Thu", "Duc",
               "Ha", "Khanh", "Phuong", "Bao", "Trang", "Long", "Mai", "Viet", "Ngan", "Thi"]
LAST_NAMES  = ["Nguyen", "Tran", "Le", "Pham", "Hoang", "Phan", "Vu", "Dang", "Bui", "Do",
               "Ho", "Ngo", "Duong", "Ly", "Dinh", "Cao", "Truong", "Vo", "Doan", "Luong"]

def random_firstname():
    return random.choice(FIRST_NAMES)

def random_lastname():
    return random.choice(LAST_NAMES)

def random_birthday():
    """Trả về (ngày, tháng, năm) ngẫu nhiên, tuổi từ 18-50"""
    year  = random.randint(1975, 2006)
    month = random.randint(1, 12)
    day   = random.randint(1, 28)   # dùng max 28 để tránh lỗi tháng 2
    return day, month, year

def random_gender():
    return random.choice(["male", "female"])

def random_email():
    return f"testuser_{random_str()}@gmail.com"


def random_password():
    return f"Test@{random_str(6)}"


def create_account(page, index: int):
    firstname      = random_firstname()
    lastname       = random_lastname()
    email          = random_email()
    password       = random_password()
    day, month, yr = random_birthday()
    gender         = random_gender()

    print(f"\n[{index + 1}] Tạo tài khoản: {firstname} {lastname} | {email}")

    try:
        # ----------------------------------------------------------------
        # BƯỚC 1: Vào trang đăng ký của website
        # ----------------------------------------------------------------
        page.goto(f"{BASE_URL}")
        page.wait_for_load_state("networkidle")

        # ----------------------------------------------------------------
        # BƯỚC 2: Click nút "Tạo tài khoản"
        # ----------------------------------------------------------------
        page.wait_for_selector("text=Tạo tài khoản")
        page.click("text=Tạo tài khoản")
        page.wait_for_load_state("networkidle")

        # ----------------------------------------------------------------
        # BƯỚC 3: Chọn mục đích "Cho mục đích cá nhân"
        # ← Nếu là dropdown thì dùng select_option, nếu là nút/link thì dùng click
        # ----------------------------------------------------------------
        page.wait_for_selector("text=Cho mục đích cá nhân")
        page.click("text=Cho mục đích cá nhân")
        page.wait_for_load_state("networkidle")

        # ----------------------------------------------------------------
        # BƯỚC 4: Điền 2 ô Họ và Tên
        # ← Chỉnh selector và giá trị cho đúng với website
        # ----------------------------------------------------------------
        page.wait_for_selector("[name='lastName']")          # ← đổi nếu selector khác
        page.fill("[name='lastName']", lastname)              # ô Last Name
        page.fill("[name='firstName']", firstname)            # ô First Name
        page.click("text=Tiếp theo")                          # ← đổi text nút cho đúng
        page.wait_for_load_state("networkidle")


        # ----------------------------------------------------------------
        # BƯỚC 3: Trang 2 - Ngày tháng năm sinh & Giới tính
        # ← Đây là cấu trúc Google thường dùng (select dropdown)
        # ----------------------------------------------------------------
        page.wait_for_selector("[name='month']")             # ← đổi nếu selector khác
        page.select_option("[name='month']", str(month))     # chọn tháng (1-12)
        page.select_option("[name='day']",   str(day))       # chọn ngày  (1-31)
        page.select_option("[name='year']",  str(yr))        # nhập năm

        # Giới tính - chọn radio hoặc dropdown
        # Cách 1: nếu là <select>
        page.select_option("[name='gender']", gender)        # "male" hoặc "female"
        # Cách 2: nếu là radio button (bỏ comment dòng dưới, comment dòng trên)
        # page.click(f"[value='{gender}']")                  # ← bỏ comment nếu cần

        page.click("text=Tiếp theo")                         # ← đổi text nút cho đúng
        page.wait_for_load_state("networkidle")

        # ----------------------------------------------------------------
        # BƯỚC CUỐI: Kiểm tra thành công
        # ----------------------------------------------------------------
        # Chọn 1 trong 2 cách kiểm tra:

        # Cách 1: Kiểm tra URL chuyển sang trang success
        # page.wait_for_url("**/success", timeout=10000)

        # Cách 2: Kiểm tra có text thông báo thành công
        # page.wait_for_selector("text=Đăng ký thành công", timeout=10000)

        print(f"[{index + 1}] ✅ Thành công!")
        return True

    except Exception as e:
        print(f"[{index + 1}] ❌ Thất bại: {e}")
        # Chụp ảnh màn hình khi lỗi để debug
        page.screenshot(path=f"error_{index + 1}.png")
        return False


def main():
    success = 0
    failed = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context()

        for i in range(NUM_ACCOUNTS):
            page = context.new_page()
            result = create_account(page, i)
            page.close()

            if result:
                success += 1
            else:
                failed += 1

            if i < NUM_ACCOUNTS - 1:
                time.sleep(DELAY_BETWEEN_ACCOUNTS)

        browser.close()

    print(f"\n{'='*40}")
    print(f"✅ Thành công: {success}/{NUM_ACCOUNTS}")
    print(f"❌ Thất bại:  {failed}/{NUM_ACCOUNTS}")
    print(f"{'='*40}")


if __name__ == "__main__":
    main()

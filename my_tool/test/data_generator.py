"""
Data Generator - Tạo thông tin tài khoản ngẫu nhiên
Sử dụng thư viện Faker để tạo tên, email, mật khẩu thực tế
"""
import random
import string
from faker import Faker

fake = Faker('en_US')


def generate_account_info():
    """Tạo thông tin tài khoản ngẫu nhiên"""
    first_name = fake.first_name()
    last_name = fake.last_name()

    # Tạo username từ tên + số ngẫu nhiên
    username_base = f"{first_name.lower()}{last_name.lower()}"
    # Loại bỏ ký tự đặc biệt
    username_base = ''.join(c for c in username_base if c.isalnum())
    username = f"{username_base}{random.randint(100, 99999)}"

    # Tạo mật khẩu mạnh
    password = generate_password()

    # Ngày sinh (tuổi 18-35)
    birth_year = random.randint(1990, 2007)
    birth_month = random.randint(1, 12)
    birth_day = random.randint(1, 28)  # Dùng 28 để tránh lỗi ngày không hợp lệ

    # Giới tính: 1=Nữ, 2=Nam, 3=Không muốn nói, 4=Tùy chỉnh
    gender = random.choice([1, 2, 3])

    return {
        'first_name': first_name,
        'last_name': last_name,
        'username': username,
        'password': password,
        'birth_year': str(birth_year),
        'birth_month': str(birth_month),
        'birth_day': str(birth_day),
        'gender': gender,
    }


def generate_password(length=14):
    """Tạo mật khẩu mạnh ngẫu nhiên"""
    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    digits = string.digits
    special = "!@#$%&*"

    # Đảm bảo có ít nhất 1 ký tự mỗi loại
    password = [
        random.choice(uppercase),
        random.choice(lowercase),
        random.choice(digits),
        random.choice(special),
    ]

    # Thêm ký tự ngẫu nhiên cho đủ độ dài
    all_chars = uppercase + lowercase + digits + special
    password += [random.choice(all_chars) for _ in range(length - 4)]

    # Xáo trộn
    random.shuffle(password)
    return ''.join(password)


def parse_proxy_string(proxy_str):
    """
    Parse proxy string thành dict cho Playwright.
    
    Hỗ trợ các format:
      - host:port:user:pass
      - host:port
      - user:pass@host:port
      - http://user:pass@host:port
    
    Returns:
        dict: {"server": "http://host:port", "username": "user", "password": "pass"}
        hoặc None nếu không parse được
    """
    proxy_str = proxy_str.strip()
    if not proxy_str:
        return None

    server = None
    username = None
    password = None

    try:
        # Format: http://user:pass@host:port
        if '://' in proxy_str:
            # Tách protocol
            protocol, rest = proxy_str.split('://', 1)
            if '@' in rest:
                auth, host_port = rest.rsplit('@', 1)
                username, password = auth.split(':', 1)
                server = f"{protocol}://{host_port}"
            else:
                server = proxy_str

        # Format: user:pass@host:port
        elif '@' in proxy_str:
            auth, host_port = proxy_str.rsplit('@', 1)
            username, password = auth.split(':', 1)
            server = f"http://{host_port}"

        # Format: host:port:user:pass
        elif proxy_str.count(':') == 3:
            parts = proxy_str.split(':')
            server = f"http://{parts[0]}:{parts[1]}"
            username = parts[2]
            password = parts[3]

        # Format: host:port
        elif proxy_str.count(':') == 1:
            server = f"http://{proxy_str}"

        else:
            return None

        result = {"server": server}
        if username and password:
            result["username"] = username
            result["password"] = password
        return result

    except Exception:
        return None


def load_proxies_from_file(file_path):
    """Đọc danh sách proxy từ file (mỗi dòng 1 proxy)"""
    proxies = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    proxy = parse_proxy_string(line)
                    if proxy:
                        proxies.append(proxy)
    except Exception as e:
        print(f"Lỗi đọc file proxy: {e}")
    return proxies

"""
Google Account Creator Tool - GUI Application
Giao diện đồ họa để tự động đăng ký tài khoản Google
Sử dụng CustomTkinter cho giao diện hiện đại
"""
import customtkinter as ctk
import threading
import queue
import csv
import os
import json
from datetime import datetime
from tkinter import filedialog, messagebox

from data_generator import generate_account_info, parse_proxy_string, load_proxies_from_file
from register_bot import GoogleRegisterBot


# ============ CẤU HÌNH GIAO DIỆN ============
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Màu sắc
COLORS = {
    'google_blue': '#4285F4',
    'google_red': '#EA4335',
    'google_yellow': '#FBBC05',
    'google_green': '#34A853',
    'success': '#2ecc71',
    'warning': '#f39c12',
    'error': '#e74c3c',
    'info': '#3498db',
    'bg_card': '#1e1e2e',
    'bg_dark': '#11111b',
    'text_dim': '#6c7086',
}

RESULT_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(RESULT_DIR, exist_ok=True)


class GoogleAccountCreatorApp(ctk.CTk):
    """Ứng dụng GUI tạo tài khoản Google tự động"""

    def __init__(self):
        super().__init__()

        # Cấu hình cửa sổ
        self.title("🔐 Google Account Creator Tool")
        self.geometry("1050x780")
        self.minsize(950, 700)

        # State
        self.log_queue = queue.Queue()
        self.results = []
        self.is_running = False
        self.bot_thread = None
        self.bot = None
        self.proxy_list = []

        # Tạo giao diện
        self._create_header()
        self._create_settings_panel()
        self._create_control_panel()
        self._create_log_panel()
        self._create_results_panel()

        # Cấu hình grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)  # Log panel mở rộng
        self.grid_rowconfigure(4, weight=1)  # Results panel mở rộng

        # Bắt đầu polling log queue
        self._poll_log_queue()

        # Xử lý đóng cửa sổ
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ============ TẠO GIAO DIỆN ============

    def _create_header(self):
        """Tạo header với tiêu đề và logo"""
        header = ctk.CTkFrame(self, fg_color="transparent", height=60)
        header.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="ew")

        # Tiêu đề
        title_label = ctk.CTkLabel(
            header,
            text="🔐  Google Account Creator",
            font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
            text_color=COLORS['google_blue']
        )
        title_label.pack(side="left")

        # Trạng thái
        self.status_label = ctk.CTkLabel(
            header,
            text="⏸ Sẵn sàng",
            font=ctk.CTkFont(size=14),
            text_color=COLORS['text_dim']
        )
        self.status_label.pack(side="right", padx=10)

    def _create_settings_panel(self):
        """Tạo panel cài đặt chính (Proxy + Account)"""
        settings_frame = ctk.CTkFrame(self, fg_color="transparent")
        settings_frame.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        settings_frame.grid_columnconfigure((0, 1), weight=1)

        # === CỘT TRÁI: Proxy Settings ===
        proxy_card = ctk.CTkFrame(settings_frame, corner_radius=12)
        proxy_card.grid(row=0, column=0, padx=(0, 8), pady=0, sticky="nsew")

        ctk.CTkLabel(
            proxy_card,
            text="🌐  Cài đặt Proxy",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS['google_blue']
        ).pack(pady=(12, 8), padx=15, anchor="w")

        # Proxy inputs
        proxy_input_frame = ctk.CTkFrame(proxy_card, fg_color="transparent")
        proxy_input_frame.pack(padx=15, pady=2, fill="x")

        # Row 1: Host + Port
        row1 = ctk.CTkFrame(proxy_input_frame, fg_color="transparent")
        row1.pack(fill="x", pady=2)
        row1.grid_columnconfigure(0, weight=3)
        row1.grid_columnconfigure(1, weight=1)

        self.proxy_host = ctk.CTkEntry(row1, placeholder_text="Host (vd: proxy.example.com)")
        self.proxy_host.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        self.proxy_port = ctk.CTkEntry(row1, placeholder_text="Port", width=80)
        self.proxy_port.grid(row=0, column=1, sticky="ew")

        # Row 2: Username + Password
        row2 = ctk.CTkFrame(proxy_input_frame, fg_color="transparent")
        row2.pack(fill="x", pady=2)
        row2.grid_columnconfigure((0, 1), weight=1)

        self.proxy_user = ctk.CTkEntry(row2, placeholder_text="Username")
        self.proxy_user.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        self.proxy_pass = ctk.CTkEntry(row2, placeholder_text="Password", show="•")
        self.proxy_pass.grid(row=0, column=1, sticky="ew")

        # Separator
        ctk.CTkLabel(proxy_card, text="── hoặc tải từ file ──",
                     font=ctk.CTkFont(size=11), text_color=COLORS['text_dim']
                     ).pack(pady=(8, 4))

        # Proxy file
        file_frame = ctk.CTkFrame(proxy_card, fg_color="transparent")
        file_frame.pack(padx=15, pady=(2, 12), fill="x")

        self.proxy_file_entry = ctk.CTkEntry(file_frame, placeholder_text="Đường dẫn file proxy...")
        self.proxy_file_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        ctk.CTkButton(
            file_frame, text="📁 Chọn", width=70,
            command=self._browse_proxy_file,
            fg_color=COLORS['google_blue'],
            hover_color="#3367D6"
        ).pack(side="right")

        # Proxy info label
        self.proxy_info_label = ctk.CTkLabel(
            proxy_card, text="", font=ctk.CTkFont(size=11),
            text_color=COLORS['google_green']
        )
        self.proxy_info_label.pack(pady=(0, 4))

        # Test proxy buttons
        test_btn_frame = ctk.CTkFrame(proxy_card, fg_color="transparent")
        test_btn_frame.pack(padx=15, pady=(0, 10), fill="x")

        self.test_proxy_btn = ctk.CTkButton(
            test_btn_frame, text="🧪 Test Proxy", width=120,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS['google_yellow'],
            text_color="#000000",
            hover_color="#e0a800",
            height=30,
            command=self._test_proxy
        )
        self.test_proxy_btn.pack(side="left", padx=(0, 5))

        self.test_no_proxy_btn = ctk.CTkButton(
            test_btn_frame, text="🔌 Test Không Proxy", width=140,
            font=ctk.CTkFont(size=12),
            fg_color="#6c7086",
            hover_color="#585b70",
            height=30,
            command=self._test_no_proxy
        )
        self.test_no_proxy_btn.pack(side="left")

        # === CỘT PHẢI: Account Settings ===
        account_card = ctk.CTkFrame(settings_frame, corner_radius=12)
        account_card.grid(row=0, column=1, padx=(8, 0), pady=0, sticky="nsew")

        ctk.CTkLabel(
            account_card,
            text="👤  Cài đặt Tài khoản",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS['google_green']
        ).pack(pady=(12, 8), padx=15, anchor="w")

        # Số lượng tài khoản
        num_frame = ctk.CTkFrame(account_card, fg_color="transparent")
        num_frame.pack(padx=15, pady=3, fill="x")
        ctk.CTkLabel(num_frame, text="Số tài khoản cần tạo:",
                     font=ctk.CTkFont(size=13)).pack(side="left")
        self.num_accounts_entry = ctk.CTkEntry(num_frame, width=70, justify="center")
        self.num_accounts_entry.pack(side="right")
        self.num_accounts_entry.insert(0, "1")

        # Delay giữa các tài khoản
        delay_frame = ctk.CTkFrame(account_card, fg_color="transparent")
        delay_frame.pack(padx=15, pady=3, fill="x")
        ctk.CTkLabel(delay_frame, text="Delay giữa mỗi tk (giây):",
                     font=ctk.CTkFont(size=13)).pack(side="left")
        self.delay_entry = ctk.CTkEntry(delay_frame, width=70, justify="center")
        self.delay_entry.pack(side="right")
        self.delay_entry.insert(0, "5")

        # Checkboxes
        self.headless_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            account_card, text="Chế độ ẩn (Headless)",
            variable=self.headless_var,
            font=ctk.CTkFont(size=13),
            checkbox_width=20, checkbox_height=20
        ).pack(padx=15, pady=3, anchor="w")

        self.auto_gen_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            account_card, text="Tự động tạo thông tin ngẫu nhiên",
            variable=self.auto_gen_var,
            font=ctk.CTkFont(size=13),
            checkbox_width=20, checkbox_height=20
        ).pack(padx=15, pady=3, anchor="w")

        self.screenshot_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            account_card, text="Chụp screenshot mỗi bước (debug)",
            variable=self.screenshot_var,
            font=ctk.CTkFont(size=13),
            checkbox_width=20, checkbox_height=20
        ).pack(padx=15, pady=(3, 12), anchor="w")

    def _create_control_panel(self):
        """Tạo panel điều khiển (nút Start/Stop/Export)"""
        control_frame = ctk.CTkFrame(self, fg_color="transparent")
        control_frame.grid(row=2, column=0, padx=20, pady=8, sticky="ew")

        # Nút Start
        self.start_btn = ctk.CTkButton(
            control_frame,
            text="▶  BẮT ĐẦU",
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=COLORS['google_green'],
            hover_color="#27ae60",
            height=42,
            width=180,
            command=self._start_registration
        )
        self.start_btn.pack(side="left", padx=(0, 10))

        # Nút Stop
        self.stop_btn = ctk.CTkButton(
            control_frame,
            text="⏹  DỪNG",
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=COLORS['google_red'],
            hover_color="#c0392b",
            height=42,
            width=140,
            state="disabled",
            command=self._stop_registration
        )
        self.stop_btn.pack(side="left", padx=(0, 10))

        # Nút Export
        self.export_btn = ctk.CTkButton(
            control_frame,
            text="📤  Xuất kết quả",
            font=ctk.CTkFont(size=13),
            fg_color=COLORS['google_blue'],
            hover_color="#3367D6",
            height=42,
            width=150,
            command=self._export_results
        )
        self.export_btn.pack(side="left", padx=(0, 10))

        # Nút Chạy Thử (Không Proxy) - mở browser
        self.quick_test_btn = ctk.CTkButton(
            control_frame,
            text="🚀  Chạy Thử (Không Proxy)",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS['google_yellow'],
            text_color="#000000",
            hover_color="#e0a800",
            height=42,
            width=200,
            command=self._quick_test_no_proxy
        )
        self.quick_test_btn.pack(side="left", padx=(0, 10))

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(control_frame, height=8)
        self.progress_bar.pack(side="right", fill="x", expand=True, padx=(15, 0))
        self.progress_bar.set(0)

    def _create_log_panel(self):
        """Tạo panel hiển thị log"""
        log_frame = ctk.CTkFrame(self, corner_radius=12)
        log_frame.grid(row=3, column=0, padx=20, pady=(5, 5), sticky="nsew")

        ctk.CTkLabel(
            log_frame,
            text="📝  Log hoạt động",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS['google_yellow']
        ).pack(pady=(8, 4), padx=12, anchor="w")

        self.log_textbox = ctk.CTkTextbox(
            log_frame,
            font=ctk.CTkFont(family="Consolas", size=12),
            corner_radius=8,
            wrap="word"
        )
        self.log_textbox.pack(padx=10, pady=(0, 10), fill="both", expand=True)

    def _create_results_panel(self):
        """Tạo panel hiển thị kết quả"""
        results_frame = ctk.CTkFrame(self, corner_radius=12)
        results_frame.grid(row=4, column=0, padx=20, pady=(5, 15), sticky="nsew")

        header_frame = ctk.CTkFrame(results_frame, fg_color="transparent")
        header_frame.pack(padx=12, pady=(8, 4), fill="x")

        ctk.CTkLabel(
            header_frame,
            text="✅  Kết quả đăng ký",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS['google_green']
        ).pack(side="left")

        self.result_count_label = ctk.CTkLabel(
            header_frame,
            text="0 tài khoản",
            font=ctk.CTkFont(size=12),
            text_color=COLORS['text_dim']
        )
        self.result_count_label.pack(side="right")

        self.results_textbox = ctk.CTkTextbox(
            results_frame,
            font=ctk.CTkFont(family="Consolas", size=12),
            corner_radius=8,
            height=120,
            wrap="none"
        )
        self.results_textbox.pack(padx=10, pady=(0, 10), fill="both", expand=True)

        # Header cho bảng kết quả
        header_text = f"{'STT':<5} {'Email':<35} {'Password':<20} {'Trạng thái':<20} {'Chi tiết'}"
        self.results_textbox.insert("end", header_text + "\n")
        self.results_textbox.insert("end", "─" * 110 + "\n")

    # ============ XỬ LÝ SỰ KIỆN ============

    def _browse_proxy_file(self):
        """Chọn file proxy"""
        file_path = filedialog.askopenfilename(
            title="Chọn file proxy",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            self.proxy_file_entry.delete(0, "end")
            self.proxy_file_entry.insert(0, file_path)
            proxies = load_proxies_from_file(file_path)
            self.proxy_list = proxies
            self.proxy_info_label.configure(
                text=f"✅ Đã tải {len(proxies)} proxy từ file",
                text_color=COLORS['google_green']
            )

    def _get_proxy_config(self, index=0):
        """Lấy cấu hình proxy (single hoặc từ list)"""
        # Ưu tiên proxy list từ file
        if self.proxy_list:
            proxy = self.proxy_list[index % len(self.proxy_list)]
            return proxy

        # Nếu không, dùng proxy nhập tay
        host = self.proxy_host.get().strip()
        port = self.proxy_port.get().strip()
        if host and port:
            proxy = {"server": f"http://{host}:{port}"}
            user = self.proxy_user.get().strip()
            passwd = self.proxy_pass.get().strip()
            if user and passwd:
                proxy["username"] = user
                proxy["password"] = passwd
            return proxy

        return None

    def _test_proxy(self):
        """Test proxy hiện tại có hoạt động không"""
        proxy = self._get_proxy_config()
        if not proxy:
            messagebox.showwarning("Cảnh báo", "Chưa cấu hình proxy! Hãy điền thông tin proxy trước.")
            return

        self.test_proxy_btn.configure(state="disabled", text="⏳ Đang test...")
        self._add_log("[SYSTEM] ═══ TEST PROXY ═══")

        def _run():
            bot = GoogleRegisterBot(
                headless=True,
                log_callback=self._add_log
            )
            try:
                success, msg = bot.test_proxy(proxy_config=proxy)
                if success:
                    self.proxy_info_label.configure(
                        text=f"✅ {msg}",
                        text_color=COLORS['google_green']
                    )
                else:
                    self.proxy_info_label.configure(
                        text=f"❌ {msg}",
                        text_color=COLORS['google_red']
                    )
            finally:
                bot.close()
                self.test_proxy_btn.configure(state="normal", text="🧪 Test Proxy")

        threading.Thread(target=_run, daemon=True).start()

    def _test_no_proxy(self):
        """Test kết nối trực tiếp (không proxy) để xác nhận tool hoạt động"""
        self.test_no_proxy_btn.configure(state="disabled", text="⏳ Đang test...")
        self._add_log("[SYSTEM] ═══ TEST KẾT NỐI TRỰC TIẾP (KHÔNG PROXY) ═══")

        def _run():
            bot = GoogleRegisterBot(
                headless=True,
                log_callback=self._add_log
            )
            try:
                success, msg = bot.test_proxy(proxy_config=None)
                if success:
                    self._add_log(f"[SYSTEM] ✅ Kết nối trực tiếp OK! → Lỗi là do PROXY")
                    self.proxy_info_label.configure(
                        text="✅ Mạng OK - Lỗi do proxy",
                        text_color=COLORS['google_yellow']
                    )
                else:
                    self._add_log(f"[SYSTEM] ❌ Kết nối trực tiếp cũng lỗi → Lỗi mạng")
            finally:
                bot.close()
                self.test_no_proxy_btn.configure(state="normal", text="🔌 Test Không Proxy")

        threading.Thread(target=_run, daemon=True).start()

    def _add_log(self, message):
        """Thêm message vào log queue (thread-safe)"""
        self.log_queue.put(message)

    def _poll_log_queue(self):
        """Kiểm tra và hiển thị log từ queue"""
        while not self.log_queue.empty():
            try:
                msg = self.log_queue.get_nowait()
                self.log_textbox.insert("end", msg + "\n")
                self.log_textbox.see("end")
            except queue.Empty:
                break
        self.after(100, self._poll_log_queue)

    def _add_result(self, result):
        """Thêm kết quả vào bảng"""
        self.results.append(result)
        idx = len(self.results)

        # Emoji trạng thái
        status_emoji = {
            'success': '✅',
            'possibly_success': '🟡',
            'username_taken': '🔄',
            'needs_verification': '⚠️',
            'error': '❌',
            'cancelled': '⏹',
            'unknown': '❓',
        }
        emoji = status_emoji.get(result.get('status', 'unknown'), '❓')

        line = f"{idx:<5} {result.get('email', 'N/A'):<35} {result.get('password', 'N/A'):<20} {emoji} {result.get('status', 'unknown'):<15} {result.get('detail', '')}"
        self.results_textbox.insert("end", line + "\n")
        self.results_textbox.see("end")

        self.result_count_label.configure(text=f"{idx} tài khoản")

    def _start_registration(self):
        """Bắt đầu quá trình đăng ký"""
        if self.is_running:
            return

        # Validate
        try:
            num_accounts = int(self.num_accounts_entry.get())
            if num_accounts < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("Lỗi", "Số tài khoản phải là số nguyên dương!")
            return

        try:
            delay = float(self.delay_entry.get())
            if delay < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Lỗi", "Delay phải là số không âm!")
            return

        # Kiểm tra proxy
        proxy = self._get_proxy_config()
        if not proxy and not self.proxy_list:
            if not messagebox.askyesno(
                "Không có proxy",
                "Bạn chưa cấu hình proxy. Tiếp tục mà không có proxy?\n\n"
                "⚠️ Google có thể chặn nếu không dùng proxy residential."
            ):
                return

        # Cập nhật UI
        self.is_running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.status_label.configure(
            text="🔄 Đang chạy...",
            text_color=COLORS['google_green']
        )
        self.progress_bar.set(0)

        self._add_log("[SYSTEM] ═══════════════════════════════════════")
        self._add_log("[SYSTEM] 🚀 Bắt đầu đăng ký tài khoản Google")
        self._add_log(f"[SYSTEM] Số lượng: {num_accounts} | Delay: {delay}s")
        self._add_log(f"[SYSTEM] Headless: {self.headless_var.get()} | Auto-gen: {self.auto_gen_var.get()}")
        if proxy:
            self._add_log(f"[SYSTEM] Proxy: {proxy['server']}")
        self._add_log("[SYSTEM] ═══════════════════════════════════════")

        # Chạy bot trong thread riêng
        self.bot_thread = threading.Thread(
            target=self._run_bot_thread,
            args=(num_accounts, delay),
            daemon=True
        )
        self.bot_thread.start()

    def _run_bot_thread(self, num_accounts, delay):
        """Thread chạy bot (không chạy trên main thread)"""
        screenshot_dir = os.path.join(RESULT_DIR, "screenshots") if self.screenshot_var.get() else None

        self.bot = GoogleRegisterBot(
            headless=self.headless_var.get(),
            log_callback=self._add_log,
            screenshot_dir=screenshot_dir
        )

        try:
            self.bot.start_browser()

            for i in range(num_accounts):
                if not self.bot.is_running():
                    self._add_log(f"[SYSTEM] ⏹ Đã dừng sau {i} tài khoản")
                    break

                self._add_log(f"\n[SYSTEM] ━━━ Tài khoản {i + 1}/{num_accounts} ━━━")

                # Tạo thông tin tài khoản
                if self.auto_gen_var.get():
                    account_info = generate_account_info()
                    self._add_log(f"[SYSTEM] Auto-gen: {account_info['first_name']} {account_info['last_name']} | {account_info['username']}")
                else:
                    account_info = generate_account_info()

                # Lấy proxy cho tài khoản này
                proxy = self._get_proxy_config(index=i)

                # Đăng ký
                result = self.bot.register_one(account_info, proxy_config=proxy)

                if result:
                    # Cập nhật kết quả trên UI (thread-safe via queue)
                    self.log_queue.put(("__RESULT__", result))

                    # Cập nhật progress
                    progress = (i + 1) / num_accounts
                    self.log_queue.put(("__PROGRESS__", progress))

                # Delay giữa các tài khoản
                if i < num_accounts - 1 and self.bot.is_running():
                    self._add_log(f"[SYSTEM] ⏳ Chờ {delay}s trước tài khoản tiếp theo...")
                    import time
                    time.sleep(delay)

        except Exception as e:
            self._add_log(f"[SYSTEM] ❌ Lỗi nghiêm trọng: {str(e)}")
        finally:
            if self.bot:
                self.bot.close()
            self._add_log("[SYSTEM] ═══════════════════════════════════════")
            self._add_log("[SYSTEM] ✅ Hoàn tất quá trình đăng ký")
            self._add_log("[SYSTEM] ═══════════════════════════════════════")

            # Auto-save kết quả
            self._auto_save_results()

            # Reset UI state (schedule on main thread)
            self.log_queue.put(("__DONE__", None))

    def _quick_test_no_proxy(self):
        """Chạy thử 1 tài khoản không proxy, mở browser để xem"""
        if self.is_running:
            messagebox.showwarning("Cảnh báo", "Bot đang chạy! Hãy dừng trước.")
            return

        # Cập nhật UI
        self.is_running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.quick_test_btn.configure(state="disabled")
        self.status_label.configure(
            text="🚀 Đang chạy thử (không proxy)...",
            text_color=COLORS['google_yellow']
        )
        self.progress_bar.set(0)

        self._add_log("[SYSTEM] ═════════════════════════════════════════")
        self._add_log("[SYSTEM] 🚀 CHẠY THỬ - KHÔNG PROXY - MỞ BROWSER")
        self._add_log("[SYSTEM] ═════════════════════════════════════════")

        def _run():
            screenshot_dir = os.path.join(RESULT_DIR, "screenshots")
            bot = GoogleRegisterBot(
                headless=False,  # Mở browser để xem
                log_callback=self._add_log,
                screenshot_dir=screenshot_dir
            )
            self.bot = bot
            try:
                bot.start_browser()

                # Tạo thông tin ngẫu nhiên
                account_info = generate_account_info()
                self._add_log(f"[SYSTEM] Auto-gen: {account_info['first_name']} {account_info['last_name']} | {account_info['username']}")
                self._add_log(f"[SYSTEM] Password: {account_info['password']}")
                self._add_log("[SYSTEM] Proxy: KHÔNG (kết nối trực tiếp)")
                self._add_log("[SYSTEM] Browser: MỞ (headless=False)")

                # Đăng ký không proxy
                result = bot.register_one(account_info, proxy_config=None)

                if result:
                    self.log_queue.put(("__RESULT__", result))
                    self.log_queue.put(("__PROGRESS__", 1.0))

            except Exception as e:
                self._add_log(f"[SYSTEM] ❌ Lỗi: {str(e)}")
            finally:
                if bot:
                    bot.close()
                self._add_log("[SYSTEM] ═══ Hoàn tất chạy thử ═══")
                self._auto_save_results()
                self.log_queue.put(("__DONE__", None))
                # Reset nút
                self.quick_test_btn.configure(state="normal")

        threading.Thread(target=_run, daemon=True).start()

    def _stop_registration(self):
        """Dừng quá trình đăng ký"""
        if self.bot:
            self.bot.stop()
        self.is_running = False
        self.status_label.configure(
            text="⏹ Đang dừng...",
            text_color=COLORS['google_yellow']
        )
        self._add_log("[SYSTEM] ⏹ Đang dừng... vui lòng chờ bước hiện tại hoàn thành")

    def _export_results(self):
        """Xuất kết quả ra file CSV"""
        if not self.results:
            messagebox.showinfo("Thông báo", "Chưa có kết quả để xuất!")
            return

        file_path = filedialog.asksaveasfilename(
            title="Xuất kết quả",
            defaultextension=".csv",
            initialfile=f"accounts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            filetypes=[("CSV files", "*.csv"), ("Text files", "*.txt"), ("All files", "*.*")]
        )

        if file_path:
            try:
                with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=['email', 'password', 'first_name', 'last_name', 'status', 'detail'])
                    writer.writeheader()
                    writer.writerows(self.results)
                messagebox.showinfo("Thành công", f"Đã xuất {len(self.results)} kết quả ra:\n{file_path}")
                self._add_log(f"[SYSTEM] 📤 Đã xuất kết quả: {file_path}")
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể xuất file: {e}")

    def _auto_save_results(self):
        """Tự động lưu kết quả sau khi hoàn tất"""
        if not self.results:
            return

        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            # Lưu CSV
            csv_path = os.path.join(RESULT_DIR, f"accounts_{timestamp}.csv")
            with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=['email', 'password', 'first_name', 'last_name', 'status', 'detail'])
                writer.writeheader()
                writer.writerows(self.results)

            # Lưu TXT format đơn giản (email:password)
            txt_path = os.path.join(RESULT_DIR, f"accounts_{timestamp}.txt")
            with open(txt_path, 'w', encoding='utf-8') as f:
                for r in self.results:
                    if r.get('status') in ('success', 'possibly_success'):
                        f.write(f"{r['email']}:{r['password']}\n")

            self._add_log(f"[SYSTEM] 💾 Tự động lưu: {csv_path}")

        except Exception as e:
            self._add_log(f"[SYSTEM] ⚠️ Không thể auto-save: {e}")

    def _poll_log_queue(self):
        """Xử lý log queue - chạy trên main thread"""
        while not self.log_queue.empty():
            try:
                item = self.log_queue.get_nowait()

                # Xử lý các message đặc biệt
                if isinstance(item, tuple):
                    msg_type, data = item

                    if msg_type == "__RESULT__":
                        self._add_result(data)
                        continue

                    elif msg_type == "__PROGRESS__":
                        self.progress_bar.set(data)
                        continue

                    elif msg_type == "__DONE__":
                        self._on_bot_done()
                        continue

                # Message log bình thường
                self.log_textbox.insert("end", str(item) + "\n")
                self.log_textbox.see("end")

            except queue.Empty:
                break

        self.after(100, self._poll_log_queue)

    def _on_bot_done(self):
        """Xử lý khi bot hoàn tất"""
        self.is_running = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

        # Đếm thành công
        success_count = sum(1 for r in self.results if r.get('status') in ('success', 'possibly_success'))
        total = len(self.results)

        self.status_label.configure(
            text=f"✅ Hoàn tất ({success_count}/{total} thành công)",
            text_color=COLORS['google_green'] if success_count > 0 else COLORS['google_red']
        )

    def _on_close(self):
        """Xử lý đóng ứng dụng"""
        if self.is_running:
            if messagebox.askyesno("Xác nhận", "Bot đang chạy. Bạn có muốn dừng và thoát?"):
                self._stop_registration()
                self.after(1000, self.destroy)
            return
        self.destroy()


# ============ CHẠY ỨNG DỤNG ============
if __name__ == "__main__":
    app = GoogleAccountCreatorApp()
    app.mainloop()

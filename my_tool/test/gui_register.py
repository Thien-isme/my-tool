"""
Tool Reg Gmail - GUI Version
==============================
Giao diện đồ họa để tạo tài khoản Gmail tự động.

Cách dùng:
  pip install playwright
  playwright install chromium
  python gui_register.py
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import requests
import time
import os
import random
from pathlib import Path

# Import từ script chính
from auto_register import (
    Config, AutoRegister, generate_account_info, setup_logger
)


class ProxyChecker:
    """Kiểm tra proxy có hoạt động không."""

    @staticmethod
    def check_single(proxy_url: str, timeout: int = 10) -> bool:
        """Kiểm tra 1 proxy."""
        try:
            proxies = {"http": proxy_url, "https": proxy_url}
            resp = requests.get(
                "https://httpbin.org/ip",
                proxies=proxies,
                timeout=timeout,
            )
            return resp.status_code == 200
        except Exception:
            return False

    @staticmethod
    def parse_proxy_line(line: str) -> dict:
        """Parse dòng proxy thành dict config cho Playwright.

        Hỗ trợ format:
          - http://host:port
          - http://user:pass@host:port
          - host:port (mặc định http)
        """
        line = line.strip()
        if not line or line.startswith("#"):
            return None

        # Thêm http:// nếu chưa có
        if not line.startswith("http://") and not line.startswith("socks"):
            line = f"http://{line}"

        # Parse username:password nếu có
        result = {"server": line}

        if "@" in line:
            # http://user:pass@host:port
            protocol = line.split("://")[0]
            rest = line.split("://")[1]
            auth, hostport = rest.rsplit("@", 1)
            if ":" in auth:
                user, passwd = auth.split(":", 1)
                result["server"] = f"{protocol}://{hostport}"
                result["username"] = user
                result["password"] = passwd

        return result


class ToolRegGmail(tk.Tk):
    """Giao diện chính của Tool Reg Gmail."""

    def __init__(self):
        super().__init__()

        self.title("Tool Reg Gmail")
        self.geometry("750x680")
        self.resizable(True, True)
        self.configure(bg="#f0f0f0")

        # State
        self.proxy_list = []
        self.proxy_status = {}  # proxy -> "active" / "dead"
        self.proxy_index = 0
        self.is_running = False
        self.worker_thread = None

        self._build_ui()

    def _build_ui(self):
        """Xây dựng giao diện."""
        # Title
        title = tk.Label(
            self, text="Tool Reg Gmail",
            font=("Segoe UI", 18, "bold"), bg="#f0f0f0", fg="#333"
        )
        title.pack(pady=(10, 5))

        # Tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)

        # Tab 1: Tạo tài khoản
        self.tab_create = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_create, text="  Tạo Tài Khoản  ")

        # Tab 2: Cấu hình Proxy
        self.tab_proxy = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_proxy, text="  Cấu Hình Proxy  ")

        # Tab 3: Kết quả
        self.tab_results = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_results, text="  Kết Quả  ")

        self._build_create_tab()
        self._build_proxy_tab()
        self._build_results_tab()

    # ==================== TAB TẠO TÀI KHOẢN ====================

    def _build_create_tab(self):
        tab = self.tab_create

        # --- Cấu hình ---
        config_frame = ttk.LabelFrame(tab, text="Cấu Hình", padding=10)
        config_frame.pack(fill="x", padx=10, pady=5)

        # Số tài khoản
        row1 = ttk.Frame(config_frame)
        row1.pack(fill="x", pady=3)
        ttk.Label(row1, text="Số tài khoản:").pack(side="left")
        self.var_num_accounts = tk.StringVar(value="1")
        ttk.Entry(row1, textvariable=self.var_num_accounts, width=8).pack(side="left", padx=5)

        # Timeout xác minh
        ttk.Label(row1, text="   Timeout xác minh (giây):").pack(side="left")
        self.var_timeout = tk.StringVar(value="300")
        ttk.Entry(row1, textvariable=self.var_timeout, width=8).pack(side="left", padx=5)

        # Chế độ
        row2 = ttk.Frame(config_frame)
        row2.pack(fill="x", pady=3)

        self.var_use_proxy = tk.BooleanVar(value=False)
        ttk.Checkbutton(row2, text="Sử Dụng Proxy", variable=self.var_use_proxy).pack(side="left")

        self.var_rotate_proxy = tk.BooleanVar(value=True)
        ttk.Checkbutton(row2, text="Xoay Proxy Tự Động (mỗi tài khoản dùng 1 proxy)", variable=self.var_rotate_proxy).pack(side="left", padx=15)

        row3 = ttk.Frame(config_frame)
        row3.pack(fill="x", pady=3)

        self.var_warmup = tk.BooleanVar(value=True)
        ttk.Checkbutton(row3, text="Làm ấm browser trước khi tạo", variable=self.var_warmup).pack(side="left")

        self.var_wait_verify = tk.BooleanVar(value=True)
        ttk.Checkbutton(row3, text="Chờ xác minh thủ công (QR/SMS)", variable=self.var_wait_verify).pack(side="left", padx=15)

        # Buttons
        btn_frame = ttk.Frame(config_frame)
        btn_frame.pack(fill="x", pady=5)

        self.btn_start = ttk.Button(btn_frame, text="▶  BẮT ĐẦU TẠO", command=self._start_create)
        self.btn_start.pack(side="left", padx=5)

        self.btn_stop = ttk.Button(btn_frame, text="⏹  DỪNG", command=self._stop_create, state="disabled")
        self.btn_stop.pack(side="left", padx=5)

        ttk.Button(btn_frame, text="🔄 Reset Profile", command=self._reset_profile).pack(side="left", padx=5)

        # --- Log ---
        log_frame = ttk.LabelFrame(tab, text="Log", padding=5)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=15, font=("Consolas", 9),
            bg="#1e1e1e", fg="#d4d4d4", insertbackground="white",
        )
        self.log_text.pack(fill="both", expand=True)

        # Status bar
        self.status_var = tk.StringVar(value="Sẵn sàng")
        status = ttk.Label(tab, textvariable=self.status_var, relief="sunken", anchor="w")
        status.pack(fill="x", padx=10, pady=(0, 5))

    # ==================== TAB CẤU HÌNH PROXY ====================

    def _build_proxy_tab(self):
        tab = self.tab_proxy

        # --- Thêm proxy thủ công ---
        add_frame = ttk.LabelFrame(tab, text="Thêm Proxy", padding=10)
        add_frame.pack(fill="x", padx=10, pady=5)

        row1 = ttk.Frame(add_frame)
        row1.pack(fill="x", pady=3)

        ttk.Label(row1, text="Loại Proxy:").pack(side="left")
        self.var_proxy_type = tk.StringVar(value="http")
        proxy_type_combo = ttk.Combobox(
            row1, textvariable=self.var_proxy_type,
            values=["http", "socks5"], width=8, state="readonly"
        )
        proxy_type_combo.pack(side="left", padx=5)

        ttk.Label(row1, text="   Proxy (IP:Port):").pack(side="left")
        self.var_proxy_addr = tk.StringVar()
        ttk.Entry(row1, textvariable=self.var_proxy_addr, width=25).pack(side="left", padx=5)

        row2 = ttk.Frame(add_frame)
        row2.pack(fill="x", pady=3)

        ttk.Label(row2, text="Username:").pack(side="left")
        self.var_proxy_user = tk.StringVar()
        ttk.Entry(row2, textvariable=self.var_proxy_user, width=15).pack(side="left", padx=5)

        ttk.Label(row2, text="   Password:").pack(side="left")
        self.var_proxy_pass = tk.StringVar()
        ttk.Entry(row2, textvariable=self.var_proxy_pass, width=15, show="*").pack(side="left", padx=5)

        ttk.Button(row2, text="➕ Thêm", command=self._add_proxy).pack(side="left", padx=10)

        # --- Danh sách proxy ---
        list_frame = ttk.LabelFrame(tab, text="Danh Sách Proxy", padding=5)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.proxy_listbox = tk.Listbox(
            list_frame, height=8, font=("Consolas", 10),
            selectmode="extended",
        )
        self.proxy_listbox.pack(fill="both", expand=True, side="left")

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.proxy_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.proxy_listbox.config(yscrollcommand=scrollbar.set)

        # Buttons dưới list
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(btn_frame, text="🔍 Kiểm Tra Proxy", command=self._check_proxies).pack(side="left", padx=3)
        ttk.Button(btn_frame, text="📂 Tải từ file", command=self._load_proxies_file).pack(side="left", padx=3)
        ttk.Button(btn_frame, text="🗑️ Xóa đã chọn", command=self._remove_selected_proxy).pack(side="left", padx=3)
        ttk.Button(btn_frame, text="🧹 Xóa tất cả", command=self._clear_proxies).pack(side="left", padx=3)

        # --- Thống kê ---
        stats_frame = ttk.LabelFrame(tab, text="Thống Kê Proxy", padding=10)
        stats_frame.pack(fill="x", padx=10, pady=5)

        self.proxy_stats_var = tk.StringVar(value="Tổng số proxy: 0  |  Hoạt động: 0  |  Đã sử dụng: 0/0")
        ttk.Label(stats_frame, textvariable=self.proxy_stats_var, font=("Segoe UI", 10)).pack()

    # ==================== TAB KẾT QUẢ ====================

    def _build_results_tab(self):
        tab = self.tab_results

        # Treeview hiển thị tài khoản đã tạo
        columns = ("email", "password", "status")
        self.results_tree = ttk.Treeview(tab, columns=columns, show="headings", height=15)
        self.results_tree.heading("email", text="Email")
        self.results_tree.heading("password", text="Mật khẩu")
        self.results_tree.heading("status", text="Trạng thái")
        self.results_tree.column("email", width=250)
        self.results_tree.column("password", width=200)
        self.results_tree.column("status", width=120)
        self.results_tree.pack(fill="both", expand=True, padx=10, pady=10)

        # Buttons
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(btn_frame, text="📋 Copy tất cả", command=self._copy_results).pack(side="left", padx=3)
        ttk.Button(btn_frame, text="💾 Xuất CSV", command=self._export_csv).pack(side="left", padx=3)
        ttk.Button(btn_frame, text="🧹 Xóa kết quả", command=self._clear_results).pack(side="left", padx=3)

    # ==================== PROXY ACTIONS ====================

    def _add_proxy(self):
        addr = self.var_proxy_addr.get().strip()
        if not addr:
            messagebox.showwarning("Lỗi", "Vui lòng nhập địa chỉ proxy (IP:Port)")
            return

        ptype = self.var_proxy_type.get()
        user = self.var_proxy_user.get().strip()
        passwd = self.var_proxy_pass.get().strip()

        if user and passwd:
            proxy_str = f"{ptype}://{user}:{passwd}@{addr}"
        else:
            proxy_str = f"{ptype}://{addr}"

        self.proxy_list.append(proxy_str)
        self.proxy_listbox.insert("end", proxy_str)
        self.var_proxy_addr.set("")
        self.var_proxy_user.set("")
        self.var_proxy_pass.set("")
        self._update_proxy_stats()

    def _load_proxies_file(self):
        filepath = filedialog.askopenfilename(
            title="Chọn file proxy",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not filepath:
            return

        with open(filepath, "r") as f:
            lines = f.readlines()

        count = 0
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                if not line.startswith("http://") and not line.startswith("socks"):
                    line = f"http://{line}"
                self.proxy_list.append(line)
                self.proxy_listbox.insert("end", line)
                count += 1

        self._update_proxy_stats()
        messagebox.showinfo("Thành công", f"Đã tải {count} proxy từ file.")

    def _remove_selected_proxy(self):
        selected = list(self.proxy_listbox.curselection())
        for i in reversed(selected):
            self.proxy_list.pop(i)
            self.proxy_listbox.delete(i)
        self._update_proxy_stats()

    def _clear_proxies(self):
        self.proxy_list.clear()
        self.proxy_listbox.delete(0, "end")
        self.proxy_status.clear()
        self._update_proxy_stats()

    def _check_proxies(self):
        if not self.proxy_list:
            messagebox.showwarning("Lỗi", "Chưa có proxy nào để kiểm tra!")
            return

        self._log("🔍 Đang kiểm tra proxy...")
        self.status_var.set("Đang kiểm tra proxy...")

        def check_thread():
            active = 0
            for i, proxy in enumerate(self.proxy_list):
                ok = ProxyChecker.check_single(proxy, timeout=8)
                self.proxy_status[proxy] = "active" if ok else "dead"

                status_icon = "✅" if ok else "❌"
                self._log(f"  {status_icon} {proxy}")

                # Cập nhật màu trong listbox
                self.proxy_listbox.itemconfig(i, fg="green" if ok else "red")

                if ok:
                    active += 1

            self._update_proxy_stats()
            self._log(f"📊 Kết quả: {active}/{len(self.proxy_list)} proxy hoạt động.")
            self.status_var.set(f"Kiểm tra xong: {active}/{len(self.proxy_list)} hoạt động")

        threading.Thread(target=check_thread, daemon=True).start()

    def _update_proxy_stats(self):
        total = len(self.proxy_list)
        active = sum(1 for p in self.proxy_list if self.proxy_status.get(p) == "active")
        used = getattr(self, "_proxies_used", 0)
        self.proxy_stats_var.set(f"Tổng số proxy: {total}  |  Hoạt động: {active}  |  Đã sử dụng: {used}/{total}")

    def _get_next_proxy(self) -> dict:
        """Lấy proxy tiếp theo (xoay vòng)."""
        if not self.proxy_list:
            return None

        # Lọc proxy active
        active_proxies = [p for p in self.proxy_list if self.proxy_status.get(p) != "dead"]
        if not active_proxies:
            active_proxies = self.proxy_list  # Nếu chưa check thì dùng tất cả

        proxy_str = active_proxies[self.proxy_index % len(active_proxies)]
        self.proxy_index += 1
        self._proxies_used = self.proxy_index

        return ProxyChecker.parse_proxy_line(proxy_str)

    # ==================== CREATE ACTIONS ====================

    def _start_create(self):
        if self.is_running:
            return

        num = int(self.var_num_accounts.get() or "1")
        timeout = int(self.var_timeout.get() or "300")

        self.is_running = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.status_var.set("Đang tạo tài khoản...")
        self.proxy_index = 0
        self._proxies_used = 0

        def worker():
            try:
                for i in range(num):
                    if not self.is_running:
                        self._log("⏹ Đã dừng bởi người dùng.")
                        break

                    # Lấy proxy nếu bật
                    proxy_server = ""
                    proxy_user = ""
                    proxy_pass = ""

                    if self.var_use_proxy.get() and self.proxy_list:
                        proxy_config = self._get_next_proxy()
                        if proxy_config:
                            proxy_server = proxy_config.get("server", "")
                            proxy_user = proxy_config.get("username", "")
                            proxy_pass = proxy_config.get("password", "")
                            self._log(f"🌐 Proxy: {proxy_server}")
                        self._update_proxy_stats()

                    config = Config(
                        num_accounts=1,
                        headless=False,
                        wait_for_human_verification=self.var_wait_verify.get(),
                        verification_timeout=timeout,
                        proxy_server=proxy_server,
                        proxy_username=proxy_user,
                        proxy_password=proxy_pass,
                    )

                    self._log(f"\n{'='*50}")
                    self._log(f"[{i+1}/{num}] Bắt đầu tạo tài khoản...")
                    self.status_var.set(f"Đang tạo tài khoản {i+1}/{num}...")

                    tool = AutoRegister(config)

                    # Override logger để ghi vào GUI
                    original_info = tool.logger.info
                    original_warning = tool.logger.warning
                    original_error = tool.logger.error

                    def gui_info(msg, _orig=original_info):
                        _orig(msg)
                        self._log(f"  {msg}")

                    def gui_warning(msg, _orig=original_warning):
                        _orig(msg)
                        self._log(f"⚠ {msg}")

                    def gui_error(msg, _orig=original_error):
                        _orig(msg)
                        self._log(f"❌ {msg}")

                    tool.logger.info = gui_info
                    tool.logger.warning = gui_warning
                    tool.logger.error = gui_error

                    tool.run()

                    # Thêm kết quả vào tab Kết Quả
                    for acc in tool.results:
                        self.results_tree.insert("", "end", values=(
                            acc.email, acc.password,
                            "✅ Thành công" if acc.status == "success" else "❌ Thất bại"
                        ))

                    # Delay giữa các tài khoản
                    if i < num - 1 and self.is_running:
                        delay = random.uniform(3, 7)
                        self._log(f"\n⏳ Chờ {delay:.0f}s trước tài khoản tiếp...")
                        time.sleep(delay)

                        # Đổi IP nếu cần (nhắc nhở)
                        if self.var_rotate_proxy.get() and not self.proxy_list:
                            self._log("💡 Mẹo: Bật/tắt chế độ máy bay trên điện thoại để đổi IP!")

            except Exception as e:
                self._log(f"❌ Lỗi: {e}")
            finally:
                self.is_running = False
                self.btn_start.config(state="normal")
                self.btn_stop.config(state="disabled")
                self.status_var.set("Hoàn tất!")
                self._log("\n✅ Hoàn tất tất cả!")

        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()

    def _stop_create(self):
        self.is_running = False
        self.status_var.set("Đang dừng...")

    def _reset_profile(self):
        import shutil
        profile_dir = "browser_profile"
        if os.path.exists(profile_dir):
            shutil.rmtree(profile_dir)
        screenshot_dir = "screenshots"
        if os.path.exists(screenshot_dir):
            shutil.rmtree(screenshot_dir)
        warmup_marker = os.path.join(profile_dir, ".warmup_done")
        self._log("🗑️ Đã reset browser profile!")
        messagebox.showinfo("Reset", "Đã xóa browser profile cũ. Profile mới sẽ được tạo khi chạy.")

    # ==================== RESULTS ACTIONS ====================

    def _copy_results(self):
        lines = []
        for item in self.results_tree.get_children():
            values = self.results_tree.item(item, "values")
            lines.append(f"{values[0]} | {values[1]} | {values[2]}")
        if lines:
            self.clipboard_clear()
            self.clipboard_append("\n".join(lines))
            messagebox.showinfo("Copy", f"Đã copy {len(lines)} tài khoản!")
        else:
            messagebox.showinfo("Copy", "Chưa có kết quả nào.")

    def _export_csv(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV file", "*.csv")],
            initialfile="accounts.csv"
        )
        if not filepath:
            return

        import csv
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Email", "Password", "Status"])
            for item in self.results_tree.get_children():
                writer.writerow(self.results_tree.item(item, "values"))

        messagebox.showinfo("Xuất CSV", f"Đã lưu vào {filepath}")

    def _clear_results(self):
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)

    # ==================== HELPERS ====================

    def _log(self, msg: str):
        """Ghi log lên GUI (thread-safe)."""
        def _append():
            self.log_text.insert("end", msg + "\n")
            self.log_text.see("end")
        self.after(0, _append)


# ============================================================
# ▶️  ENTRY POINT
# ============================================================
if __name__ == "__main__":
    app = ToolRegGmail()
    app.mainloop()

import time
import os
import pandas as pd
import urllib.parse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

def scrape_duckduckgo_images(keyword, max_images):
    print(f"[*] Bắt đầu tìm kiếm {max_images} ảnh cho từ khóa: '{keyword}' qua DuckDuckGo...")
    
    # Cấu hình dùng trình duyệt Google Chrome chuẩn mượt mà
    options = Options()
    options.add_argument("--disable-notifications")
    
    # Tắt các dòng thông báo dễ bị phát hiện bot
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    try:
        driver = webdriver.Chrome(options=options)
    except Exception as e:
        print("[-] Lỗi khởi tạo trình duyệt Chrome.")
        print("Lỗi chi tiết:", e)
        return
        
    try:
        # Mã hóa keyword để tránh lỗi với các kí tự tiếng Việt hoặc dấu cách
        encoded_keyword = urllib.parse.quote(keyword)
        driver.get(f"https://duckduckgo.com/?q={encoded_keyword}&iax=images&ia=images")
        time.sleep(5) # Đợi trang hình ảnh tải đầy đủ
        
        print("[*] Đang tải các hình ảnh...")
        image_urls = set()
        
        while len(image_urls) < max_images:
            # DuckDuckGo đã thay đổi các class, dùng selector cấu trúc 'figure img' cho ổn định
            images = driver.find_elements(By.CSS_SELECTOR, "figure img")
            
            if not images:
                print("[-] Không tìm thấy ảnh nào. Đang thử cuộn trang và đợi lại...")
                driver.execute_script("window.scrollTo(0, 1000);")
                time.sleep(3)
                images = driver.find_elements(By.CSS_SELECTOR, "figure img")
                if not images:
                    break

            for img in images:
                if len(image_urls) >= max_images:
                    break
                    
                src = img.get_attribute("src")
                if not src or "http" not in src:
                    src = img.get_attribute("data-src")
                    
                # DuckDuckGo uses a proxy URL starting with https://external-content.duckduckgo.com/iu/?u=
                # The actual URL is encoded in the 'u' parameter.
                if src and "external-content.duckduckgo.com" in src and "u=" in src:
                    try:
                        actual_url_encoded = src.split("u=")[1].split("&")[0]
                        src = urllib.parse.unquote(actual_url_encoded)
                    except Exception:
                        pass # Keep the proxy URL if decoding fails
                            
                if src and "http" in src:
                    # Filter out DDG proxy or tracking links that might have slipped through
                    if "duckduckgo.com" not in src:
                        if src not in image_urls:
                            image_urls.add(src)
                            print(f"[{len(image_urls)}/{max_images}] Đã lưu: {src[:70]}...")
            
            if len(image_urls) < max_images:
                 driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                 time.sleep(2)
                 
    finally:
        driver.quit()
        
    if image_urls:
         print("\n[*] Đang lưu các link kết quả vào file Excel...")
         df = pd.DataFrame(list(image_urls), columns=['Link Ảnh'])
         safe_keyword = "".join([c for c in keyword if c.isalnum() or c==' ']).rstrip()
         filename = f"ket_qua_{safe_keyword.replace(' ', '_')}.xlsx"
         df.to_excel(filename, index=False)
         print(f"[+] Tuyệt vời! Bạn đã lấy thành công {len(image_urls)} link ảnh vào file: {os.path.abspath(filename)}")
    else:
         print("[-] Lấy ảnh thất bại. Có thể mạng chậm hoặc lỗi load ảnh.")

if __name__ == "__main__":
    kw = input(">> Nhập từ khóa bạn muốn tìm (vd: 'gái xinh', 'phong cảnh'): ")
    try:
        limit = int(input(">> Nhập số lượng ảnh cần lấy: "))
    except ValueError:
        limit = 5
        print("Nhập sai định dạng, mặc định sẽ lấy 5 ảnh.")
        
    scrape_duckduckgo_images(kw, limit)

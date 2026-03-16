import time
import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

def scrape_duckduckgo_images(keyword, max_images):
    print(f"[*] Bắt đầu tìm kiếm {max_images} ảnh cho từ khóa: '{keyword}' qua DuckDuckGo...")
    
    # Cấu hình dùng trình duyệt Opera GX
    options = Options()
    
    # TRỎ ĐƯỜNG DẪN ĐẾN FILE CHẠY OPERA GX CỦA BẠN
    # Đường dẫn cài đặt gốc trên máy bạn (đã được tìm thấy)
    opera_gx_path = r"C:\Users\thien\AppData\Local\Programs\Opera GX\opera.exe"
    options.binary_location = opera_gx_path
    
    options.add_argument("--disable-notifications")
    
    # Tắt các flag dễ bị phát hiện bot
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    try:
        # Quan trọng: Opera vẫn dùng engine Chromium nên ta dùng luôn webdriver.Chrome
        driver = webdriver.Chrome(options=options)
    except Exception as e:
        print("[-] Lỗi khởi tạo trình duyệt Opera GX.")
        print("Bạn có thể cần tải ChromeDriver bản mới nhất tương thích với nhân Chromium của Opera GX.")
        print("Lỗi chi tiết:", e)
        return
        
    try:
        # Vào trang hình ảnh của DuckDuckGo
        driver.get(f"https://duckduckgo.com/?q={keyword}&iax=images&ia=images")
        time.sleep(3) # Đợi trang hình ảnh tải đầy đủ
        
        print("[*] Đang tải các hình ảnh...")
        image_urls = set()
        
        # DuckDuckGo Hình ảnh chứa ảnh trực tiếp trong class 'tile--img__img'
        
        while len(image_urls) < max_images:
            # Lấy tất cả ảnh hiện có trên trang
            images = driver.find_elements(By.CSS_SELECTOR, "img.tile--img__img")
            
            if not images:
                print("[-] Không tìm thấy ảnh nào. Đang thử lại...")
                time.sleep(2)
                images = driver.find_elements(By.CSS_SELECTOR, "img.tile--img__img")
                if not images:
                    break

            for img in images:
                if len(image_urls) >= max_images:
                    break
                    
                src = img.get_attribute("src")
                if src and "http" in src:
                    if src not in image_urls:
                        image_urls.add(src)
                        print(f"[{len(image_urls)}/{max_images}] Đã lưu: {src[:70]}...")
            
            # Cuộn trang nếu vẫn chưa đủ số lượng
            if len(image_urls) < max_images:
                 driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                 time.sleep(2)
                 
    finally:
        driver.quit()
        
    # Lưu vào Excel
    if image_urls:
         print("\n[*] Đang lưu các link kết quả vào file Excel...")
         df = pd.DataFrame(list(image_urls), columns=['Link Ảnh'])
         
         safe_keyword = "".join([c for c in keyword if c.isalnum() or c==' ']).rstrip()
         filename = f"ket_qua_{safe_keyword.replace(' ', '_')}.xlsx"
         
         df.to_excel(filename, index=False)
         print(f"[+] Tuyệt vời! Bạn đã lấy thành công {len(image_urls)} link ảnh vào file: {os.path.abspath(filename)}")
    else:
         print("[-] Lấy ảnh thất bại. Có thể mạng chậm hoặc trình duyệt bị lỗi.")

if __name__ == "__main__":
    kw = input(">> Nhập từ khóa bạn muốn tìm (vd: 'gái xinh', 'phong cảnh'): ")
    try:
        limit = int(input(">> Nhập số lượng ảnh cần lấy: "))
    except ValueError:
        limit = 5
        print("Nhập sai định dạng, mặc định sẽ lấy 5 ảnh.")
        
    scrape_duckduckgo_images(kw, limit)

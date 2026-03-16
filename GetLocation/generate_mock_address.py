import os
import requests
import random
import pandas as pd
from faker import Faker
import argparse
import sys
import urllib.parse
import time
import unidecode

def normalize_string(s):
    return unidecode.unidecode(s.lower()).strip()

def search_location(query, data):
    target = normalize_string(query)
    
    # 1. Tìm trùng ở cấp Tỉnh/Thành phố
    for province in data:
        if target in normalize_string(province['name']):
            return province['name'], province.get('districts', [])
            
    # 2. Tìm trùng ở cấp Quận/Huyện
    for province in data:
        for district in province.get('districts', []):
            if target in normalize_string(district['name']):
                return province['name'], [district]
                
    # 3. Tìm trùng ở cấp Phường/Xã
    for province in data:
        for district in province.get('districts', []):
            for ward in district.get('wards', []):
                if target in normalize_string(ward['name']):
                    # Dù tìm thấy Phường, ta vẫn lấy cấp Quận làm list để code random tiếp tục chạy
                    # Nhưng lọc list districts chỉ còn Quận này, và list wards của Quận này ưu tiên Phường tìm thấy
                    modified_district = dict(district)
                    modified_district['wards'] = [ward]
                    return province['name'], [modified_district]
                    
    return None, None

def get_unique_filename(base_filename):
    if not os.path.exists(base_filename):
        return base_filename
        
    name, ext = os.path.splitext(base_filename)
    counter = 1
    
    while True:
        new_filename = f"{name}_{counter}{ext}"
        if not os.path.exists(new_filename):
            return new_filename
        counter += 1

PROVINCE_BBOX = {
    # name_fragment: (min_lat, min_lon, max_lat, max_lon)
    "ho chi minh": (10.60, 106.50, 11.10, 107.00),
    "ha noi"     : (20.80, 105.60, 21.40, 106.00),
    "da nang"    : (15.95, 107.95, 16.20, 108.30),
    "can tho"    : (9.95,  105.60, 10.25, 105.90),
    "hai phong"  : (20.70, 106.50, 20.95, 106.90),
    "hue"        : (16.30, 107.50, 16.60, 107.85),
    "nha trang"  : (12.20, 109.10, 12.30, 109.25),
    "da lat"     : (11.90, 108.35, 12.00, 108.50),
    "bien hoa"   : (10.90, 106.85, 11.05, 107.00),
    "vung tau"   : (10.30, 107.00, 10.45, 107.20),
    "quy nhon"   : (13.70, 109.15, 13.85, 109.30),
    "vinh"       : (18.60, 105.60, 18.75, 105.75),
    "buon ma thuot": (12.60, 107.97, 12.72, 108.10),
    "long xuyen" : (10.35, 105.38, 10.45, 105.50),
    "ca mau"     : (9.15,  105.10, 9.30,  105.25),
    "bac ninh"   : (21.15, 106.00, 21.25, 106.15),
    "thai nguyen": (21.55, 105.80, 21.70, 105.95),
    "nam dinh"   : (20.38, 106.10, 20.50, 106.25),
}

def load_province_amenities(province_name):
    """Tải toàn bộ tiện ích của tỉnh/thành phố bằng bounding box (nhanh, tin cậy)."""
    import unidecode
    print(f"Đang tải tiện ích xung quanh từ OpenStreetMap...")
    
    province_key = unidecode.unidecode(province_name.lower())
    bbox = None
    for key, coords in PROVINCE_BBOX.items():
        if key in province_key or province_key in key:
            bbox = coords
            break
    
    if not bbox:
        # Fallback: dùng tọa độ trung tâm TP.HCM nếu không tìm thấy
        print(f"Không có tọa độ cho '{province_name}', dùng vùng TP.HCM làm mặc định.")
        bbox = (10.60, 106.50, 11.10, 107.00)
    
    min_lat, min_lon, max_lat, max_lon = bbox
    
    query = f"""
[out:json][timeout:25];
(
  node["amenity"~"cinema|hospital|marketplace"](around:10000,{(min_lat+max_lat)/2},{(min_lon+max_lon)/2});
  node["shop"~"supermarket|shopping_mall"](around:10000,{(min_lat+max_lat)/2},{(min_lon+max_lon)/2});
  node["leisure"="park"](around:10000,{(min_lat+max_lat)/2},{(min_lon+max_lon)/2});
  node["name"~"Bách Hóa Xanh|Vincom|Coopmart|Big C|Lotte|Aeon|Gigamall|Landmark"](around:10000,{(min_lat+max_lat)/2},{(min_lon+max_lon)/2});
);
out tags qt 200;
"""
    
    url = "https://overpass-api.de/api/interpreter"
    try:
        response = requests.post(url, data={'data': query}, timeout=30)
        if response.status_code == 200:
            data = response.json()
            elements = data.get('elements', [])
            amenities = list({tags['name'] for el in elements if (tags := el.get('tags', {})) and (name := tags.get('name')) and len(name) > 2})
            print(f"Tìm thấy {len(amenities)} tiện ích trong khu vực.")
            return amenities
        else:
            print(f"Overpass API HTTP {response.status_code}. Sẽ dùng mô tả mặc định.")
    except Exception as e:
        print(f"Không thể kết nối Overpass API: {e}")
    
    return []


def pick_nearby_amenities(province_amenities):
    """Lấy ngẫu nhiên 3-4 tiện ích từ danh sách của tỉnh."""
    if not province_amenities:
        return "Khu vực thuận tiện, gần chợ và tiện ích cơ bản."
    selected = random.sample(province_amenities, min(4, len(province_amenities)))
    return "Gần các địa điểm:\n- " + "\n- ".join(selected)

def generate_mock_data(search_term, num_records, base_output_file):
    print("Đang tải danh sách dữ liệu hành chính từ API...")
    try:
        response = requests.get("https://provinces.open-api.vn/api/?depth=3")
        response.raise_for_status()
        provinces = response.json()
    except Exception as e:
        print(f"Lỗi khi lấy dữ liệu: {e}")
        sys.exit(1)
        
    province_name, districts = search_location(search_term, provinces)
    if not province_name or not districts:
        print(f"Không tìm thấy dữ liệu địa lý cho từ khóa: '{search_term}'. Vui lòng thử lại tên khác.")
        sys.exit(1)
        
    print(f"Đã tìm thấy khu vực trong: {province_name}")
        
    output_file = get_unique_filename(base_output_file)
    
    try:
        fake = Faker('vi_VN')
    except Exception as e:
        print("Lỗi khởi tạo Faker vi_VN, sử dụng tiếng Việt tiêu chuẩn:", e)
        fake = Faker()
        
    # Tải tiện ích toàn tỉnh 1 lần duy nhất
    province_amenities = load_province_amenities(province_name)
        
    records = []
    
    VIETNAM_STREETS = [
        "Nguyễn Huệ", "Lê Lợi", "Trần Hưng Đạo", "Điện Biên Phủ", "Nguyễn Thị Minh Khai",
        "Lý Thường Kiệt", "Hai Bà Trưng", "Phan Chu Trinh", "Hùng Vương", "Lê Duẩn",
        "Nguyễn Văn Linh", "Phạm Văn Đồng", "Trường Chinh", "Hoàng Văn Thụ", "Cống Quỳnh",
        "Bùi Viện", "Đề Thám", "Phạm Ngũ Lão", "Nguyễn Trãi", "Lê Văn Sỹ",
        "Cách Mạng Tháng 8", "Nam Kỳ Khởi Nghĩa", "Đinh Tiên Hoàng", "Võ Văn Tần",
        "Phan Đình Phùng", "Trần Phú", "Pasteur", "Alexandre de Rhodes", "Đồng Khởi",
        "Ngô Đức Kế", "Hoàng Diệu", "Bến Chương Dương", "Nguyễn Đình Chiểu", "Hồ Xuân Hương",
        "Lê Quý Đôn", "Cao Thắng", "Nguyễn Thiện Thuật", "Bắc Hải", "Lý Chính Thắng",
        "Võ Thị Sáu", "Phạm Viết Chánh", "Nguyễn Công Trứ", "Nguyễn Đức Cảnh", "Trần Văn Kiểu",
        "Bình Thới", "An Dương Vương", "Lạc Long Quân", "Tô Hiến Thành", "Sư Vạn Hạnh",
        "Lý Nam Đế", "Trần Nhật Duật", "Nguyễn Lương Bằng", "Hoàng Sa", "Trường Sa",
        "Châu Văn Liêm", "Phú Lâm", "Bình Long", "Âu Cơ", "Đặng Văn Bi",
    ]
    
    print(f"Đang sinh ngẫu nhiên {num_records} địa chỉ...")
    for _ in range(num_records):
        district = random.choice(districts)
        wards = district.get('wards', [])
        
        ward_name = ""
        if wards:
            ward = random.choice(wards)
            ward_name = ward.get('name', '')
            
        # Address format: Số nhà, Tên đường, Phường/Xã, Quận/Huyện, Tỉnh/Thành phố
        street_name = random.choice(VIETNAM_STREETS)
        building_num = str(random.randint(1, 300))
        
        full_address_parts = [f"{building_num} {street_name}"]
        if ward_name:
            full_address_parts.append(ward_name)
        full_address_parts.append(district['name'])
        full_address_parts.append(province_name)
        full_address = ", ".join(full_address_parts)
        
        property_types = ['Apartment', 'House', 'Studio', 'Room']
        statuses = ['Pending', 'Approved', 'Available', 'Rented', 'Unavailable', 'Rejected', 'Blocked']
        amenities_list = ['Wifi, Máy lạnh, Tủ lạnh', 'Ban công, Bếp, Chỗ để xe máy', 'Thang máy, Bảo vệ 24/7', 'Nội thất cơ bản', 'Đầy đủ nội thất']
        
        prop_type = random.choice(property_types)
        
        # Mapping to Vietnamese for Title and Description
        prop_type_vn = "Căn hộ chung cư"
        if prop_type == "House":
            prop_type_vn = "Nhà nguyên căn"
        elif prop_type == "Studio":
            prop_type_vn = "Căn hộ Studio"
        elif prop_type == "Room":
            prop_type_vn = "Phòng trọ"
        
        bedrooms = random.randint(1, 5)
        bathrooms = random.randint(1, 4)
        area = round(random.uniform(20.0, 150.0), 1)
        monthly_rent = random.randint(3000000, 30000000)
        
        # Lấy tiện ích từ danh sách đã cache
        nearby = pick_nearby_amenities(province_amenities)
        
        # Mô tả tiện ích bên trong (nội khu)
        internal_amenities = random.choice(amenities_list)
        
        # Xây dựng câu mô tả hoàn chỉnh
        pet_friendly = "Có" if random.choice([True, False]) else "Không"
        smoking = "Cho phép hút thuốc." if random.choice([True, False]) else "Môi trường không khói thuốc."
        
        desc = (f"Phòng thoáng mát, khu vực an ninh.\n"
                f"Tình trạng nội thất: {internal_amenities}.\n"
                f"Nuôi thú cưng: {pet_friendly}.\n"
                f"{nearby}")

        records.append({
            "Title": f"Cho thuê {prop_type_vn.lower()} diện tích {area}m2 tại {district['name']}",
            "Description": desc,
            "PropertyType": prop_type,
            "Status": random.choice(statuses),
            "AddressDetails": full_address,
            "City": province_name,
            "District": district['name'],
            "Ward": ward_name,
            "Area": area,
            "Bedrooms": bedrooms,
            "Bathrooms": bathrooms,
            "MonthlyRent": monthly_rent,
            "DepositAmount": monthly_rent * random.randint(1, 3), # Deposit 1-3 months
            "Amenities": internal_amenities,
            "AllowPets": "Có" in pet_friendly,
            "AllowSmoking": "Cho phép hút thuốc" in smoking,
            "IsAvailable": random.choice([True, False]),
            "LandlordId": fake.uuid4(),
            "CreatedAt": fake.date_time_between(start_date="-1y", end_date="now").strftime("%Y-%m-%d %H:%M:%S")
        })
        
    df = pd.DataFrame(records)
    try:
        from openpyxl.styles import Alignment
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Mock Data')
            workbook = writer.book
            worksheet = writer.sheets['Mock Data']
            
            # Auto-wrap text on the Description column
            desc_col_idx = df.columns.get_loc('Description') + 1 # 1-based index in openpyxl
            
            for row in range(2, len(df) + 2):
                cell = worksheet.cell(row=row, column=desc_col_idx)
                cell.alignment = Alignment(wrap_text=True)
                
        print(f"Đã lưu thành công {num_records} địa chỉ vào file: {output_file}")
    except Exception as e:
        print(f"Lỗi khi lưu ra file Excel: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Công cụ tạo Mock Data Địa chỉ tại một Tỉnh/Thành phố ngẫu nhiên.")
    parser.add_argument("--city", type=str, required=True, help="Tên Tỉnh/Thành phố (VD: 'Hà Nội', 'Hồ Chí Minh', 'Đà Nẵng')")
    parser.add_argument("--count", type=int, default=100, help="Số lượng địa chỉ cần tạo (mặc định: 100)")
    parser.add_argument("--output", type=str, default="mock_addresses.xlsx", help="Tên file Excel đầu ra (mặc định: mock_addresses.xlsx)")
    
    args = parser.parse_args()
    generate_mock_data(args.city, args.count, args.output)

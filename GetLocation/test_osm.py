import requests
import urllib.parse
import json

headers = {'User-Agent': 'MockDataGenerator/1.0 (contact@example.com)'}

# Step 1: Test Nominatim geocoding 
ward = "Phường 1"
district = "Quận 4"
province = "Thành phố Hồ Chí Minh"

query = f"{ward}, {district}, {province}, Vietnam"
url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(query)}&format=json&limit=1"

print(f"[1] Nominatim URL: {url}")
res = requests.get(url, headers=headers, timeout=10)
print(f"    Status: {res.status_code}")
data = res.json()
print(f"    Result: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")

if data:
    lat = data[0]['lat']
    lon = data[0]['lon']
    print(f"\n[2] Coordinates: lat={lat}, lon={lon}")

    # Step 2: Test Overpass query around the coordinate
    overpass_query = f"""
    [out:json][timeout:25];
    (
      node["amenity"~"cinema|marketplace|hospital"](around:2000,{lat},{lon});
      node["shop"~"supermarket|mall"](around:2000,{lat},{lon});
      node["leisure"~"park"](around:2000,{lat},{lon});
      node["name"~"Bách Hóa Xanh|Vincom|Coopmart|Big C"](around:2000,{lat},{lon});
    );
    out center 10;
    """

    overpass_url = "https://overpass-api.de/api/interpreter"
    print(f"\n[3] Calling Overpass API...")
    try:
        r = requests.post(overpass_url, data={'data': overpass_query}, timeout=30)
        print(f"    Status: {r.status_code}")
        result = r.json()
        elements = result.get('elements', [])
        print(f"    Elements found: {len(elements)}")
        for el in elements[:5]:
            name = el.get('tags', {}).get('name', 'no-name')
            print(f"    - {name}")
    except Exception as e:
        print(f"    Overpass error: {e}")
else:
    print("    [ERROR] No geocoding result!")

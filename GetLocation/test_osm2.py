import requests
import json

# Test 1: Simple Overpass query with timeout=15 to check basic connectivity
print("=== Test 1: Simple Overpass test ===")
q1 = """
[out:json][timeout:10];
node["name"="Vincom Center Đồng Khởi"];
out 3;
"""
try:
    r = requests.post("https://overpass-api.de/api/interpreter", data={'data': q1}, timeout=12)
    print(f"Status: {r.status_code}")
    data = r.json()
    print(f"Elements: {len(data.get('elements', []))}")
    for el in data.get('elements', [])[:3]:
        print(f"  - {el.get('tags', {}).get('name', 'N/A')}")
except Exception as e:
    print(f"ERROR: {e}")

print()
# Test 2: Using geocodeArea with Hồ Chí Minh
print("=== Test 2: geocodeArea(Hồ Chí Minh) - node search ===")
q2 = """
[out:json][timeout:15];
area["name"="Hồ Chí Minh"]["boundary"="administrative"]->.city;
node["amenity"="cinema"](area.city);
out 5;
"""
try:
    r = requests.post("https://overpass-api.de/api/interpreter", data={'data': q2}, timeout=18)
    print(f"Status: {r.status_code}")
    data = r.json()
    print(f"Elements: {len(data.get('elements', []))}")
    for el in data.get('elements', [])[:5]:
        print(f"  - {el.get('tags', {}).get('name', 'N/A')}")
except Exception as e:
    print(f"ERROR: {e}")

print()
# Test 3: Use vi name  
print("=== Test 3: geodesic Hồ Chí Minh query ===")
q3 = """
[out:json][timeout:15];
(
  node["name"~"Vincom|Bách Hóa Xanh|Lotte|Big C|Coopmart"](10.6,106.5,11.2,107.0);
);
out 10;
"""
try:
    r = requests.post("https://overpass-api.de/api/interpreter", data={'data': q3}, timeout=18)
    print(f"Status: {r.status_code}")
    data = r.json()
    print(f"Elements: {len(data.get('elements', []))}")
    for el in data.get('elements', [])[:10]:
        print(f"  - {el.get('tags', {}).get('name', 'N/A')}")
except Exception as e:
    print(f"ERROR: {e}")

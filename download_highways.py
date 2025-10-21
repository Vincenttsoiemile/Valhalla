#!/usr/bin/env python3
"""下載大溫哥華地區高速公路數據"""

import requests
import json
import time

# Overpass API 端點
OVERPASS_URL = "http://overpass-api.de/api/interpreter"

# 大溫哥華地區邊界（擴大範圍）
BBOX = {
    'south': 49.0,
    'west': -123.3,
    'north': 49.4,
    'east': -122.5
}

# Overpass 查詢（motorway + trunk 主要幹道）
query = f"""
[out:json][timeout:300];
(
  way["highway"="motorway"]({BBOX['south']},{BBOX['west']},{BBOX['north']},{BBOX['east']});
  way["highway"="trunk"]({BBOX['south']},{BBOX['west']},{BBOX['north']},{BBOX['east']});
  way["highway"="motorway_link"]({BBOX['south']},{BBOX['west']},{BBOX['north']},{BBOX['east']});
);
out body;
>;
out skel qt;
"""

print("🛣️  下載大溫哥華地區高速公路數據...")
print(f"範圍: {BBOX}")
print(f"類型: motorway, trunk, motorway_link")
print("")

try:
    print("發送請求到 Overpass API...")
    response = requests.post(OVERPASS_URL, data={'data': query}, timeout=600)
    
    if response.status_code == 200:
        data = response.json()
        
        # 統計
        nodes_count = sum(1 for e in data['elements'] if e['type'] == 'node')
        ways_count = sum(1 for e in data['elements'] if e['type'] == 'way')
        
        print(f"✅ 下載成功！")
        print(f"   節點數: {nodes_count:,}")
        print(f"   道路段數: {ways_count:,}")
        
        # 保存到文件
        output_file = 'highways_data.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        
        print(f"💾 已保存到: {output_file}")
        print(f"   檔案大小: {len(json.dumps(data)) / 1024 / 1024:.2f} MB")
        
    else:
        print(f"❌ 請求失敗: HTTP {response.status_code}")
        print(response.text)
        
except requests.exceptions.Timeout:
    print("❌ 請求超時，請稍後再試")
except Exception as e:
    print(f"❌ 錯誤: {e}")


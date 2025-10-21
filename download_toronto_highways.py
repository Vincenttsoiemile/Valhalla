#!/usr/bin/env python3
"""下載多倫多地區高速公路數據"""

import requests
import json
import time

# Overpass API 端點
OVERPASS_URL = "http://overpass-api.de/api/interpreter"

# 多倫多地區邊界（擴大範圍，包含 GTA）
BBOX = {
    'south': 43.4,   # 南至 Lake Ontario
    'west': -79.8,   # 西至 Mississauga
    'north': 44.0,   # 北至 Vaughan/Markham
    'east': -79.0    # 東至 Scarborough/Pickering
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

print("🛣️  下載多倫多地區（GTA）高速公路數據...")
print(f"範圍: {BBOX}")
print(f"類型: motorway, trunk, motorway_link")
print(f"主要高速公路: 401, 404, 400, DVP, Gardiner, QEW")
print("")

try:
    print("發送請求到 Overpass API（可能需要 1-2 分鐘）...")
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
        output_file = 'highways_data_toronto.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)

        print(f"💾 已保存到: {output_file}")
        print(f"   檔案大小: {len(json.dumps(data)) / 1024 / 1024:.2f} MB")

        # 提示下一步
        print("")
        print("📝 下一步:")
        print("   1. 將 'highways_data_toronto.json' 重命名為 'highways_data.json'")
        print("      或修改 river_detection.py 使用新檔案名")
        print("   2. 重啟 Flask 應用")

    else:
        print(f"❌ 請求失敗: HTTP {response.status_code}")
        print(response.text)

except requests.exceptions.Timeout:
    print("❌ 請求超時，請稍後再試")
except Exception as e:
    print(f"❌ 錯誤: {e}")

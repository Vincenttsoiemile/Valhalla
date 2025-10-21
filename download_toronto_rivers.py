#!/usr/bin/env python3
"""下載多倫多地區河流數據"""

import requests
import json
import time

# Overpass API 端點
OVERPASS_URL = "http://overpass-api.de/api/interpreter"

# 多倫多地區邊界（擴大範圍，包含 GTA - Greater Toronto Area）
BBOX = {
    'south': 43.4,   # 南至 Lake Ontario
    'west': -79.8,   # 西至 Mississauga
    'north': 44.0,   # 北至 Vaughan/Markham
    'east': -79.0    # 東至 Scarborough/Pickering
}

# Overpass 查詢（河流 waterway）
query = f"""
[out:json][timeout:300];
(
  way["waterway"="river"]({BBOX['south']},{BBOX['west']},{BBOX['north']},{BBOX['east']});
  way["waterway"="stream"]({BBOX['south']},{BBOX['west']},{BBOX['north']},{BBOX['east']});
  way["waterway"="canal"]({BBOX['south']},{BBOX['west']},{BBOX['north']},{BBOX['east']});
  relation["waterway"="river"]({BBOX['south']},{BBOX['west']},{BBOX['north']},{BBOX['east']});
);
out body;
>;
out skel qt;
"""

print("🌊 下載多倫多地區（GTA）河流數據...")
print(f"範圍: {BBOX}")
print(f"類型: river, stream, canal")
print("")

try:
    print("發送請求到 Overpass API（可能需要 1-3 分鐘）...")
    response = requests.post(OVERPASS_URL, data={'data': query}, timeout=600)

    if response.status_code == 200:
        data = response.json()

        # 統計
        nodes_count = sum(1 for e in data['elements'] if e['type'] == 'node')
        ways_count = sum(1 for e in data['elements'] if e['type'] == 'way')
        relations_count = sum(1 for e in data['elements'] if e['type'] == 'relation')

        print(f"✅ 下載成功！")
        print(f"   節點數: {nodes_count:,}")
        print(f"   河流段數: {ways_count:,}")
        print(f"   關係數: {relations_count:,}")

        # 保存到文件
        output_file = 'rivers_data_toronto.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)

        print(f"💾 已保存到: {output_file}")
        print(f"   檔案大小: {len(json.dumps(data)) / 1024 / 1024:.2f} MB")

        # 提示下一步
        print("")
        print("📝 下一步:")
        print("   1. 將 'rivers_data_toronto.json' 重命名為 'rivers_data.json'")
        print("      或修改 river_detection.py 使用新檔案名")
        print("   2. 重啟 Flask 應用")

    else:
        print(f"❌ 請求失敗: HTTP {response.status_code}")
        print(response.text)

except requests.exceptions.Timeout:
    print("❌ 請求超時，請稍後再試")
except Exception as e:
    print(f"❌ 錯誤: {e}")

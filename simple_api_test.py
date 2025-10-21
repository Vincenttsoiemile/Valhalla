#!/usr/bin/env python3
"""簡單的 Valhalla API 測試"""

import json
import requests

# 使用 Valhalla Demo Server
url = "https://valhalla1.openstreetmap.de/route"

# 測試路徑規劃：柏林布蘭登堡門 -> 柏林電視塔
request = {
    "locations": [
        {"lat": 52.5200, "lon": 13.4050},  # 布蘭登堡門
        {"lat": 52.5244, "lon": 13.4105}   # 柏林電視塔
    ],
    "costing": "auto",
    "directions_options": {"language": "zh-TW"}
}

response = requests.post(url, json=request)
data = response.json()

print(json.dumps(data, indent=2, ensure_ascii=False))

if "trip" in data:
    summary = data["trip"]["summary"]
    print(f"\n✅ 路徑規劃成功！")
    print(f"距離: {summary['length']:.2f} km")
    print(f"時間: {summary['time'] / 60:.1f} 分鐘")


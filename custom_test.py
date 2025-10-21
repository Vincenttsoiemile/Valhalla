#!/usr/bin/env python3
"""自訂參數測試 - 不同交通模式"""

import json
import requests

BASE_URL = "https://valhalla1.openstreetmap.de/route"

# 測試地點：柏林布蘭登堡門 -> 柏林電視塔
locations = [
    {"lat": 52.5200, "lon": 13.4050},  # 布蘭登堡門
    {"lat": 52.5244, "lon": 13.4105}   # 柏林電視塔
]

# 測試不同的交通模式
costing_modes = {
    "auto": "🚗 汽車",
    "pedestrian": "🚶 步行",
    "bicycle": "🚴 自行車",
    "bus": "🚌 公車"
}

print("=" * 60)
print("測試不同交通模式的路徑規劃")
print("=" * 60)

for mode, icon in costing_modes.items():
    print(f"\n{icon} {mode.upper()}")
    print("-" * 40)
    
    request = {
        "locations": locations,
        "costing": mode,
        "directions_options": {"language": "zh-TW"}
    }
    
    try:
        response = requests.post(BASE_URL, json=request)
        data = response.json()
        
        if "trip" in data:
            summary = data["trip"]["summary"]
            distance = summary["length"]
            time_min = summary["time"] / 60
            
            print(f"距離: {distance:.2f} km")
            print(f"時間: {time_min:.1f} 分鐘")
            
            # 計算平均速度
            if time_min > 0:
                speed = (distance / time_min) * 60
                print(f"平均速度: {speed:.1f} km/h")
            
            print("✅ 成功")
        else:
            print(f"❌ 錯誤: {data.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ 失敗: {e}")

print("\n" + "=" * 60)
print("測試完成")
print("=" * 60)


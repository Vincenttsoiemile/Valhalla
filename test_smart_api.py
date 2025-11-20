#!/usr/bin/env python3
"""測試 Smart Route Planner API"""

import requests
import json

# API 端點
API_URL = "http://localhost:8080/api/optimize-route-smart"

# 測試資料
test_data = {
    "start": {
        "lat": 43.681878,
        "lon": -79.713353
    },
    "order_group": "Group202511131925010114",  # 使用真實的 order_group
    "maxGroupSize": 15,
    "clusterRadius": 0.8
}

print("=" * 60)
print("測試 Smart Route Planner API")
print("=" * 60)
print(f"\n請求 URL: {API_URL}")
print(f"請求資料: {json.dumps(test_data, indent=2, ensure_ascii=False)}")
print("\n發送請求中...")

try:
    response = requests.post(API_URL, json=test_data, timeout=30)

    print(f"\n狀態碼: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print("\n✅ 成功！")
        print(f"\n總訂單數: {result.get('total_orders')}")
        print(f"總組數: {result.get('total_groups')}")
        print(f"總距離: {result.get('total_distance', 0):.2f}")
        print(f"\n各組訂單數:")
        for group, count in result.get('groups', {}).items():
            print(f"  {group} 組: {count} 個訂單")

        # 顯示前 5 個訂單
        print(f"\n前 5 個訂單:")
        for order in result.get('orders', [])[:5]:
            print(f"  {order['sequence']}. {order['group_sequence']} - {order['tracking_number']}")
    else:
        print(f"\n❌ 錯誤！")
        print(f"回應: {response.text}")

except requests.exceptions.Timeout:
    print("\n❌ 請求超時！")
except requests.exceptions.ConnectionError:
    print("\n❌ 連接失敗！請確保 Flask 服務正在運行")
except Exception as e:
    print(f"\n❌ 發生錯誤: {str(e)}")

print("\n" + "=" * 60)

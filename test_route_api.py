#!/usr/bin/env python3
"""測試路線優化 API 並分析結果"""

import requests
import json
import time

API_URL = "http://localhost:8080/api/route"

# 測試配置
config = {
    "start": {"lat": 43.434800, "lon": -79.775666},
    "order_group": "Group202510172101060201",
    "max_group_size": 30,
    "cluster_radius": 1.0,
    "min_samples": 3,
    "metric": "euclidean",
    "group_order_method": "greedy",
    "inner_order_method": "nearest",
    "random_state": 42,
    "n_init": 10,
    "verification": "geometry",
    "check_highways": True,
    "group_penalty": 2.0,
    "inner_penalty": 1.5,
    "end_point_mode": "last_order"
}

print("=" * 70)
print("測試路線優化 API - 含空間索引幾何檢測")
print("=" * 70)

print("\n📋 配置:")
print(f"  訂單組: {config['order_group']}")
print(f"  起點: ({config['start']['lat']}, {config['start']['lon']})")
print(f"  群組大小: {config['max_group_size']}")
print(f"  驗證方法: {config['verification']}")
print(f"  檢查高速公路: {config['check_highways']}")
print(f"  群組懲罰係數: {config['group_penalty']}")
print(f"  組內懲罰係數: {config['inner_penalty']}")

print("\n🚀 發送請求...")
start_time = time.time()

try:
    response = requests.post(API_URL, json=config, timeout=60)
    request_time = time.time() - start_time

    print(f"✓ 請求完成，耗時: {request_time:.2f} 秒")
    print(f"  HTTP 狀態: {response.status_code}")

    if response.status_code == 200:
        data = response.json()

        print("\n📊 結果統計:")
        print(f"  總訂單數: {data.get('total_orders', 0)}")
        print(f"  群組數: {data.get('num_groups', 0)}")

        if 'river_crossings' in data:
            print(f"\n🌊 跨河檢測:")
            crossings = data['river_crossings']
            print(f"  跨河連接數: {len(crossings)}")

            # 統計跨河和跨高速公路
            river_count = sum(1 for c in crossings if c.get('crosses_river'))
            highway_count = sum(1 for c in crossings if c.get('crosses_highway'))

            print(f"  - 跨河流: {river_count}")
            print(f"  - 跨高速公路: {highway_count}")

            if len(crossings) > 0:
                print(f"\n  前 5 個跨越:")
                for i, crossing in enumerate(crossings[:5]):
                    print(f"    {i+1}. {crossing['from']} → {crossing['to']}")
                    print(f"       跨河: {crossing.get('crosses_river', False)}, "
                          f"跨高速: {crossing.get('crosses_highway', False)}")

        print(f"\n✅ 驗證方法: {data.get('verification_method', 'N/A')}")

        # 顯示群組信息
        if 'groups' in data:
            print(f"\n📦 群組詳情:")
            for group_name, orders in data['groups'].items():
                print(f"  {group_name}: {len(orders)} 個訂單")

        # 保存完整結果
        with open('test_route_result.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n💾 完整結果已保存到: test_route_result.json")

    else:
        print(f"\n❌ 請求失敗:")
        print(f"  狀態碼: {response.status_code}")
        print(f"  錯誤: {response.text[:500]}")

except requests.Timeout:
    print(f"\n❌ 請求超時 (>60秒)")
except Exception as e:
    print(f"\n❌ 錯誤: {e}")

print("\n" + "=" * 70)

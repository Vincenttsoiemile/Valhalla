#!/usr/bin/env python3
"""測試 Smart 模式是否形成閉環"""

import requests
import json
import numpy as np

API_URL = "http://localhost:8080/api/optimize-route-smart"

# 使用用戶提供的配置
test_data = {
    "start": {
        "lat": 43.734577,
        "lon": -79.707828
    },
    "order_group": "Group202511151924060106",
    "maxGroupSize": 30,
    "clusterRadius": 1.0
}

print("=" * 80)
print("測試 Smart 模式是否形成閉環")
print("=" * 80)

def calculate_distance(p1, p2):
    """計算兩點之間的距離"""
    return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

try:
    response = requests.post(API_URL, json=test_data, timeout=30)

    if response.status_code == 200:
        result = response.json()
        orders = result.get('orders', [])

        if not orders:
            print("❌ 沒有訂單數據")
            exit(1)

        print(f"\n起始點: ({test_data['start']['lat']}, {test_data['start']['lon']})")
        print(f"總訂單數: {len(orders)}")
        print(f"總組數: {result.get('total_groups')}")

        # 獲取組別列表
        groups = {}
        for order in orders:
            group = order['group_label']
            if group not in groups:
                groups[group] = []
            groups[group].append(order)

        print(f"\n組別順序: {' → '.join(sorted(groups.keys()))}")

        # 分析每組的中心點
        print("\n" + "=" * 80)
        print("組別中心點分析：")
        print("=" * 80)

        start_point = np.array([test_data['start']['lat'], test_data['start']['lon']])
        group_centers = {}

        for group_label in sorted(groups.keys()):
            group_orders = groups[group_label]
            lats = [o['lat'] for o in group_orders]
            lons = [o['lon'] for o in group_orders]
            center = np.array([np.mean(lats), np.mean(lons)])
            group_centers[group_label] = center

            dist_to_start = calculate_distance(start_point, center)
            print(f"{group_label} 組: 中心點 ({center[0]:.6f}, {center[1]:.6f}), 距起點 {dist_to_start:.6f}")

        # 檢查是否形成閉環
        print("\n" + "=" * 80)
        print("閉環檢測：")
        print("=" * 80)

        group_labels = sorted(groups.keys())
        first_group = group_labels[0]
        last_group = group_labels[-1]

        first_center = group_centers[first_group]
        last_center = group_centers[last_group]

        dist_start_to_first = calculate_distance(start_point, first_center)
        dist_start_to_last = calculate_distance(start_point, last_center)
        dist_last_to_first = calculate_distance(last_center, first_center)

        print(f"\n起點 → {first_group} 組中心: {dist_start_to_first:.6f}")
        print(f"起點 → {last_group} 組中心: {dist_start_to_last:.6f}")
        print(f"{last_group} 組中心 → {first_group} 組中心: {dist_last_to_first:.6f}")

        # 判斷是否閉環
        # 如果最後一組離起點的距離比第一組還近，或者非常接近，可能形成閉環
        ratio = dist_start_to_last / dist_start_to_first if dist_start_to_first > 0 else float('inf')

        print(f"\n最後組距起點 / 第一組距起點 = {ratio:.2f}")

        if ratio < 0.5:
            print(f"\n⚠️  可能形成閉環！最後一組({last_group})離起點比第一組({first_group})還近")
        elif ratio < 1.0:
            print(f"\n⚠️  可能部分閉環，最後一組({last_group})離起點較近")
        else:
            print(f"\n✅ 開放式路徑，最後一組({last_group})離起點較遠")

        # 檢查組別順序的合理性
        print("\n" + "=" * 80)
        print("組別順序合理性分析：")
        print("=" * 80)

        prev_center = start_point
        total_group_distance = 0

        for i, group_label in enumerate(group_labels):
            center = group_centers[group_label]
            dist = calculate_distance(prev_center, center)
            total_group_distance += dist

            if i == 0:
                print(f"起點 → {group_label}: {dist:.6f}")
            else:
                prev_label = group_labels[i-1]
                print(f"{prev_label} → {group_label}: {dist:.6f}")

            prev_center = center

        print(f"\n組間總距離（中心點到中心點）: {total_group_distance:.6f}")

        # 計算如果形成閉環的額外距離
        closing_distance = calculate_distance(last_center, first_center)
        print(f"如果閉環（{last_group} → {first_group}）: +{closing_distance:.6f}")
        print(f"閉環總距離: {total_group_distance + closing_distance:.6f}")

        # 顯示實際路徑的前5個和後5個訂單
        print("\n" + "=" * 80)
        print("實際訂單順序（前5個和後5個）：")
        print("=" * 80)

        print("\n前5個訂單：")
        for order in orders[:5]:
            dist = calculate_distance(start_point, [order['lat'], order['lon']])
            print(f"  {order['group_sequence']}: ({order['lat']:.6f}, {order['lon']:.6f}), 距起點 {dist:.6f}")

        print(f"\n... (共 {len(orders)} 個訂單) ...\n")

        print("後5個訂單：")
        for order in orders[-5:]:
            dist = calculate_distance(start_point, [order['lat'], order['lon']])
            print(f"  {order['group_sequence']}: ({order['lat']:.6f}, {order['lon']:.6f}), 距起點 {dist:.6f}")

        # 最後訂單距離起點的距離
        last_order = orders[-1]
        last_order_point = np.array([last_order['lat'], last_order['lon']])
        dist_last_to_start = calculate_distance(last_order_point, start_point)

        print(f"\n最後訂單 {last_order['group_sequence']} 距起點: {dist_last_to_start:.6f}")

    else:
        print(f"\n❌ API 錯誤: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"\n❌ 發生錯誤: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)

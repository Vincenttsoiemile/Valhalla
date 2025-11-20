#!/usr/bin/env python3
"""測試新的單向性約束功能（組內路徑方向性）"""

import requests
import json
import numpy as np

API_URL = "http://localhost:8080/api/optimize-route-smart"

# 使用用戶提供的配置
test_data_base = {
    "start": {
        "lat": 43.733895,
        "lon": -79.704437
    },
    "order_group": "Group202511151924060106",
    "maxGroupSize": 30,
    "clusterRadius": 1.0,
    "nextGroupLinkage": "none"  # 不使用 linkage，純測試 directional constraint
}

def calculate_distance(p1, p2):
    """計算兩點之間的距離"""
    return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def analyze_directional_trend(orders, groups):
    """分析組內路徑的方向性趨勢"""
    group_labels = sorted(groups.keys())

    print("\n組內方向性分析：")
    print("="*80)

    for i, group_label in enumerate(group_labels):
        group_orders = groups[group_label]

        if len(group_orders) < 3:
            continue

        # 如果不是最後一組，計算到下一組中心的距離趨勢
        if i < len(group_labels) - 1:
            next_group_label = group_labels[i + 1]
            next_group_orders = groups[next_group_label]

            # 計算下一組中心點
            next_lats = [o['lat'] for o in next_group_orders]
            next_lons = [o['lon'] for o in next_group_orders]
            next_center = np.array([np.mean(next_lats), np.mean(next_lons)])

            # 計算該組每個訂單到下一組中心的距離
            distances_to_next = []
            for order in group_orders:
                point = np.array([order['lat'], order['lon']])
                dist = calculate_distance(point, next_center)
                distances_to_next.append(dist)

            # 計算前半段和後半段的平均距離
            mid = len(distances_to_next) // 2
            first_half_avg = np.mean(distances_to_next[:mid])
            second_half_avg = np.mean(distances_to_next[mid:])

            # 計算距離變化趨勢
            distance_trend = second_half_avg - first_half_avg

            print(f"\n{group_label} 組 → {next_group_label} 組:")
            print(f"  組內訂單數: {len(group_orders)}")
            print(f"  前半段平均距離到下一組: {first_half_avg:.6f}")
            print(f"  後半段平均距離到下一組: {second_half_avg:.6f}")
            print(f"  方向性趨勢: {distance_trend:.6f}", end="")

            if distance_trend < 0:
                print(f" ✅ (後半段更靠近下一組，有方向性)")
            else:
                print(f" ⚠️  (後半段更遠，無明顯方向性)")

            # 顯示距離序列
            print(f"  距離序列（前5個 & 後5個）:")
            if len(distances_to_next) > 10:
                print(f"    前5: {[f'{d:.4f}' for d in distances_to_next[:5]]}")
                print(f"    後5: {[f'{d:.4f}' for d in distances_to_next[-5:]]}")
            else:
                print(f"    全部: {[f'{d:.4f}' for d in distances_to_next]}")

def test_directional_constraint(enable_constraint):
    """測試指定的單向性約束設置"""
    constraint_name = "啟用" if enable_constraint else "停用"

    print(f"\n{'='*80}")
    print(f"測試方案: 單向性約束 {constraint_name}")
    print(f"{'='*80}")

    test_data = test_data_base.copy()
    test_data['directionalConstraint'] = enable_constraint

    response = requests.post(API_URL, json=test_data, timeout=60)

    if response.status_code != 200:
        print(f"❌ API 錯誤: {response.status_code}")
        print(response.text)
        return None

    result = response.json()
    orders = result.get('orders', [])

    # 提取組別
    groups = {}
    for order in orders:
        group = order['group_label']
        if group not in groups:
            groups[group] = []
        groups[group].append(order)

    print(f"\n總訂單數: {len(orders)}")
    print(f"總組數: {len(groups)}")
    print(f"總距離: {result.get('total_distance', 0):.6f}")

    # 分析方向性趨勢
    analyze_directional_trend(orders, groups)

    return {
        'constraint': constraint_name,
        'total_distance': result.get('total_distance', 0),
        'num_groups': len(groups),
        'num_orders': len(orders),
        'orders': orders,
        'groups': groups
    }

print("="*80)
print("單向性約束功能測試 - 組內路徑方向性")
print("="*80)

# 測試兩種方案
results = []

# 方案 1: 停用單向性約束
result_off = test_directional_constraint(False)
if result_off:
    results.append(result_off)

# 方案 2: 啟用單向性約束
result_on = test_directional_constraint(True)
if result_on:
    results.append(result_on)

# 對比分析
if len(results) >= 2:
    print(f"\n{'='*80}")
    print("對比分析")
    print(f"{'='*80}")

    print(f"\n{'方案':<20} {'總距離':<12} {'組數':<8} {'訂單數':<8} {'差異 %':<10}")
    print("-" * 80)

    baseline = results[0]
    for result in results:
        diff_pct = ((result['total_distance'] - baseline['total_distance']) / baseline['total_distance'] * 100) if baseline['total_distance'] > 0 else 0

        print(f"{result['constraint']:<20} "
              f"{result['total_distance']:<12.6f} "
              f"{result['num_groups']:<8} "
              f"{result['num_orders']:<8} "
              f"{diff_pct:+.2f}%")

    print(f"\n分析：")
    if results[1]['total_distance'] < results[0]['total_distance']:
        improvement = (results[0]['total_distance'] - results[1]['total_distance']) / results[0]['total_distance'] * 100
        print(f"  ✅ 啟用單向性約束後，總距離改善了 {improvement:.2f}%")
    elif results[1]['total_distance'] > results[0]['total_distance']:
        degradation = (results[1]['total_distance'] - results[0]['total_distance']) / results[0]['total_distance'] * 100
        print(f"  ⚠️  啟用單向性約束後，總距離增加了 {degradation:.2f}%")
        print(f"  （這是正常的，因為方向性約束可能會犧牲部分距離來獲得更好的方向性）")
    else:
        print(f"  ✅ 兩種方案總距離相同")

print(f"\n{'='*80}")

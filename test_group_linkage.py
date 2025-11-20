#!/usr/bin/env python3
"""測試組間銜接功能的三種方案"""

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
    "directionalConstraint": False  # 不使用單向性約束，以更好觀察銜接效果
}

def calculate_distance(p1, p2):
    """計算兩點之間的距離"""
    return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def test_linkage_method(linkage_method, linkage_weight=0.5):
    """測試指定的銜接方法"""
    method_names = {
        'none': '無銜接（標準 2-opt）',
        'weighted': f'權重式銜接 (weight={linkage_weight})',
        'virtual_endpoint': '虛擬終點法'
    }
    method_name = method_names.get(linkage_method, linkage_method)

    print(f"\n{'='*80}")
    print(f"測試方案: {method_name}")
    print(f"{'='*80}")

    test_data = test_data_base.copy()
    test_data['nextGroupLinkage'] = linkage_method
    test_data['linkageWeight'] = linkage_weight

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

    start_point = np.array([test_data_base['start']['lat'], test_data_base['start']['lon']])

    # 計算組別中心點
    group_centers = {}
    group_labels_list = sorted(groups.keys())

    for group_label in group_labels_list:
        group_orders = groups[group_label]
        lats = [o['lat'] for o in group_orders]
        lons = [o['lon'] for o in group_orders]
        group_centers[group_label] = np.array([np.mean(lats), np.mean(lons)])

    print(f"\n總訂單數: {len(orders)}")
    print(f"總組數: {len(groups)}")
    print(f"總距離: {result.get('total_distance', 0):.6f}")

    # 分析組間銜接
    print(f"\n組間銜接分析：")
    total_linkage_distance = 0
    total_internal_distance = 0

    for i, group_label in enumerate(group_labels_list):
        group_orders_list = groups[group_label]

        # 組內距離
        group_internal_dist = 0
        for j in range(len(group_orders_list) - 1):
            p1 = np.array([group_orders_list[j]['lat'], group_orders_list[j]['lon']])
            p2 = np.array([group_orders_list[j+1]['lat'], group_orders_list[j+1]['lon']])
            group_internal_dist += calculate_distance(p1, p2)

        total_internal_distance += group_internal_dist

        # 組間銜接距離
        if i < len(group_labels_list) - 1:
            last_order = group_orders_list[-1]
            last_point = np.array([last_order['lat'], last_order['lon']])

            next_group_label = group_labels_list[i + 1]
            next_center = group_centers[next_group_label]
            next_first_order = groups[next_group_label][0]
            next_first_point = np.array([next_first_order['lat'], next_first_order['lon']])

            # 銜接距離（從當前組最後訂單到下一組第一個訂單）
            linkage_dist = calculate_distance(last_point, next_first_point)
            total_linkage_distance += linkage_dist

            # 最後訂單到下一組中心的距離
            dist_to_next_center = calculate_distance(last_point, next_center)

            print(f"  {group_label} → {next_group_label}:")
            print(f"    銜接距離: {linkage_dist:.6f}")
            print(f"    {group_label}最後訂單 到 {next_group_label}中心: {dist_to_next_center:.6f}")

    print(f"\n組內總距離: {total_internal_distance:.6f}")
    print(f"組間總距離: {total_linkage_distance:.6f}")
    print(f"總距離: {total_internal_distance + total_linkage_distance:.6f}")

    return {
        'method': method_name,
        'total_distance': result.get('total_distance', 0),
        'internal_distance': total_internal_distance,
        'linkage_distance': total_linkage_distance,
        'num_groups': len(groups),
        'num_orders': len(orders)
    }

print("="*80)
print("組間銜接功能測試 - 三種方案對比")
print("="*80)

# 測試三種方案
results = []

# 方案 1: 無銜接
result_none = test_linkage_method('none')
if result_none:
    results.append(result_none)

# 方案 2: 權重式銜接
result_weighted = test_linkage_method('weighted', linkage_weight=0.5)
if result_weighted:
    results.append(result_weighted)

# 方案 3: 虛擬終點法
result_virtual = test_linkage_method('virtual_endpoint')
if result_virtual:
    results.append(result_virtual)

# 對比分析
if len(results) >= 2:
    print(f"\n{'='*80}")
    print("對比分析")
    print(f"{'='*80}")

    print(f"\n{'方案':<30} {'總距離':<12} {'組內距離':<12} {'組間距離':<12} {'差異 %':<10}")
    print("-" * 80)

    baseline = results[0]  # 使用無銜接作為基準
    for result in results:
        diff_pct = ((result['total_distance'] - baseline['total_distance']) / baseline['total_distance'] * 100) if baseline['total_distance'] > 0 else 0

        print(f"{result['method']:<30} "
              f"{result['total_distance']:<12.6f} "
              f"{result['internal_distance']:<12.6f} "
              f"{result['linkage_distance']:<12.6f} "
              f"{diff_pct:+.2f}%")

    # 詳細分析
    print(f"\n詳細對比：")

    if len(results) >= 2:
        # 權重式 vs 無銜接
        linkage_reduction_weighted = results[0]['linkage_distance'] - results[1]['linkage_distance']
        linkage_reduction_pct_weighted = (linkage_reduction_weighted / results[0]['linkage_distance'] * 100) if results[0]['linkage_distance'] > 0 else 0

        print(f"\n權重式銜接:")
        print(f"  - 組間距離減少: {linkage_reduction_weighted:.6f} ({linkage_reduction_pct_weighted:.2f}%)")
        print(f"  - 組內距離變化: {results[1]['internal_distance'] - results[0]['internal_distance']:+.6f}")

    if len(results) >= 3:
        # 虛擬終點 vs 無銜接
        linkage_reduction_virtual = results[0]['linkage_distance'] - results[2]['linkage_distance']
        linkage_reduction_pct_virtual = (linkage_reduction_virtual / results[0]['linkage_distance'] * 100) if results[0]['linkage_distance'] > 0 else 0

        print(f"\n虛擬終點法:")
        print(f"  - 組間距離減少: {linkage_reduction_virtual:.6f} ({linkage_reduction_pct_virtual:.2f}%)")
        print(f"  - 組內距離變化: {results[2]['internal_distance'] - results[0]['internal_distance']:+.6f}")

    # 建議
    print(f"\n建議:")

    best_linkage = min(results[1:], key=lambda x: x['linkage_distance'])
    best_total = min(results, key=lambda x: x['total_distance'])

    print(f"  - 最佳組間銜接: {best_linkage['method']} (組間距離 {best_linkage['linkage_distance']:.6f})")
    print(f"  - 最佳總距離: {best_total['method']} (總距離 {best_total['total_distance']:.6f})")

    if best_total == results[0]:
        print(f"  ⚠️  無銜接方案總距離最短，銜接優化未能改善整體路徑")
    else:
        improvement = (results[0]['total_distance'] - best_total['total_distance']) / results[0]['total_distance'] * 100
        print(f"  ✅ {best_total['method']} 相比無銜接改善了 {improvement:.2f}%")

print(f"\n{'='*80}")

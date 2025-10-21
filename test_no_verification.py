#!/usr/bin/env python3
"""測試不檢測 vs 幾何檢測的差異"""

import requests
import json
import time

API_URL = "http://localhost:8080/api/route"

# 基礎配置
base_config = {
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
    "group_penalty": 2.0,
    "inner_penalty": 1.5,
    "end_point_mode": "last_order"
}

print("=" * 80)
print("比較：不檢測 vs 幾何數據檢測")
print("=" * 80)

results = {}

# 測試 1: 不檢測
print("\n【測試 1】不檢測 (verification: none)")
config1 = base_config.copy()
config1["verification"] = "none"
config1["check_highways"] = False

start = time.time()
resp1 = requests.post(API_URL, json=config1, timeout=60)
time1 = time.time() - start

if resp1.status_code == 200:
    data1 = resp1.json()
    results['none'] = data1
    print(f"  ✓ 完成，耗時: {time1:.2f} 秒")
    print(f"  訂單數: {data1.get('total_orders', 0)}")
    print(f"  跨河檢測: {len(data1.get('crossings', []))} 個")

    # 保存序列
    with open('sequence_none.json', 'w') as f:
        json.dump(data1.get('optimized_orders', []), f, indent=2)
else:
    print(f"  ✗ 失敗: {resp1.status_code}")

# 測試 2: 幾何檢測
print("\n【測試 2】幾何數據檢測 (verification: geometry + checkHighways)")
config2 = base_config.copy()
config2["verification"] = "geometry"
config2["check_highways"] = True

start = time.time()
resp2 = requests.post(API_URL, json=config2, timeout=60)
time2 = time.time() - start

if resp2.status_code == 200:
    data2 = resp2.json()
    results['geometry'] = data2
    print(f"  ✓ 完成，耗時: {time2:.2f} 秒")
    print(f"  訂單數: {data2.get('total_orders', 0)}")
    print(f"  跨河檢測: {len(data2.get('crossings', []))} 個")

    # 統計
    crossings = data2.get('crossings', [])
    river_count = sum(1 for c in crossings if c.get('crosses_river'))
    highway_count = sum(1 for c in crossings if c.get('crosses_highway'))

    print(f"    - 跨河流: {river_count}")
    print(f"    - 跨高速公路: {highway_count}")

    # 保存序列
    with open('sequence_geometry.json', 'w') as f:
        json.dump(data2.get('optimized_orders', []), f, indent=2)
else:
    print(f"  ✗ 失敗: {resp2.status_code}")

# 比較差異
if 'none' in results and 'geometry' in results:
    print("\n" + "=" * 80)
    print("比較分析")
    print("=" * 80)

    print(f"\n⏱ 性能對比:")
    print(f"  不檢測耗時: {time1:.2f} 秒")
    print(f"  幾何檢測耗時: {time2:.2f} 秒")
    print(f"  額外耗時: {time2 - time1:.2f} 秒 ({(time2/time1 - 1) * 100:.1f}%)")

    # 比較序列差異
    orders1 = results['none'].get('optimized_orders', [])
    orders2 = results['geometry'].get('optimized_orders', [])

    if len(orders1) == len(orders2) and len(orders1) > 0:
        seq1 = [o['tracking_number'] for o in orders1]
        seq2 = [o['tracking_number'] for o in orders2]

        diff_count = sum(1 for i in range(len(seq1)) if seq1[i] != seq2[i])
        same_percent = (1 - diff_count / len(seq1)) * 100 if len(seq1) > 0 else 0

        print(f"\n📊 序列對比:")
        print(f"  總訂單數: {len(seq1)}")
        print(f"  相同位置: {len(seq1) - diff_count} ({same_percent:.1f}%)")
        print(f"  不同位置: {diff_count} ({100 - same_percent:.1f}%)")

        if diff_count > 0:
            print(f"\n  前 10 個不同位置:")
            shown = 0
            for i in range(len(seq1)):
                if seq1[i] != seq2[i]:
                    print(f"    位置 {i+1}: {seq1[i]} → {seq2[i]}")
                    shown += 1
                    if shown >= 10:
                        break

    print(f"\n💡 結論:")
    if diff_count == 0:
        print("  序列完全相同 - 幾何檢測未改變路線順序")
    elif diff_count < len(seq1) * 0.1:
        print(f"  序列微調 - 幾何檢測僅影響 {diff_count} 個位置({100-same_percent:.1f}%)")
    else:
        print(f"  序列優化 - 幾何檢測顯著改變了路線以避免跨河/高速公路")

print("\n" + "=" * 80)

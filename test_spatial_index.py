#!/usr/bin/env python3
"""測試空間索引性能"""

import time
from river_detection import ObstacleDetector

print("=" * 60)
print("測試空間索引性能")
print("=" * 60)

# 初始化檢測器
print("\n1. 初始化 ObstacleDetector...")
start = time.time()
detector = ObstacleDetector.get_instance()
init_time = time.time() - start
print(f"   初始化耗時: {init_time:.2f} 秒")

# 測試數據
test_coords = [
    (43.438711, -79.771214),  # 起點
    (43.436248, -79.683193),  # 訂單 1
    (43.445905, -79.665735),  # 訂單 2
    (43.383193, -79.725656),  # 訂單 3
    (43.445817, -79.717065),  # 訂單 4
]

print(f"\n2. 測試 {len(test_coords) - 1} 對訂單連接...")
print(f"   河流數據: {len(detector.rivers):,} 條線段")
print(f"   高速公路數據: {len(detector.highways):,} 條線段")
print(f"   空間索引狀態:")
print(f"     - 河流索引: {'✓ 已建立' if detector.rivers_tree else '✗ 未建立'}")
print(f"     - 高速公路索引: {'✓ 已建立' if detector.highways_tree else '✗ 未建立'}")

# 執行檢測
print("\n3. 執行幾何檢測...")
start = time.time()
crossings = 0

for i in range(len(test_coords) - 1):
    lat1, lon1 = test_coords[i]
    lat2, lon2 = test_coords[i + 1]

    result = detector.check_obstacle_crossing(
        lat1, lon1, lat2, lon2,
        check_rivers=True,
        check_highways=True
    )

    if result['crosses_any']:
        crossings += 1
        print(f"   發現跨越: {i} -> {i+1}")
        print(f"     - 跨河: {result['crosses_river']}")
        print(f"     - 跨高速公路: {result['crosses_highway']}")

check_time = time.time() - start

print(f"\n4. 性能統計:")
print(f"   總檢測時間: {check_time:.4f} 秒")
print(f"   平均每對: {check_time / (len(test_coords) - 1) * 1000:.2f} 毫秒")
print(f"   發現跨越: {crossings} 對")

# 估算大量訂單性能
estimated_190 = (check_time / (len(test_coords) - 1)) * 189
print(f"\n5. 估算 190 個訂單 (189 對):")
print(f"   預估耗時: {estimated_190:.2f} 秒")

if estimated_190 < 30:
    print(f"   性能評級: ✓ 優秀（遠低於 30 秒超時限制）")
elif estimated_190 < 60:
    print(f"   性能評級: ○ 可接受（在合理範圍內）")
else:
    print(f"   性能評級: ✗ 需要優化（可能超時）")

print("\n" + "=" * 60)

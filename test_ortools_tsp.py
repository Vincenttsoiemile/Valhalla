#!/usr/bin/env python3
"""測試 OR-Tools TSP 功能"""

from tsp_solver import solve_tsp

# 測試數據：5個點
test_coords = [
    (43.6532, -79.3832),  # 起點
    (43.6545, -79.3850),
    (43.6520, -79.3800),
    (43.6700, -79.4000),
    (43.6710, -79.4020),
]

print("測試 OR-Tools TSP...")
print(f"測試座標: {len(test_coords)} 個點")

try:
    result = solve_tsp(test_coords, method='ortools', start_index=0)
    print(f"✓ 成功！路徑: {result}")
except Exception as e:
    print(f"✗ 失敗：{e}")
    import traceback
    traceback.print_exc()


#!/usr/bin/env python3
"""測試 app.py 中的 OR-Tools TSP 調用"""

import math
from tsp_solver import solve_tsp

# 模擬 app.py 中的場景
def calculate_distance(lat1, lon1, lat2, lon2):
    return math.sqrt((lat2 - lat1)**2 + (lon2 - lon1)**2)

# 測試數據
group_orders = [
    {'tracking_number': 'T001', 'lat': 43.6545, 'lon': -79.3850},
    {'tracking_number': 'T002', 'lat': 43.6520, 'lon': -79.3800},
    {'tracking_number': 'T003', 'lat': 43.6700, 'lon': -79.4000},
    {'tracking_number': 'T004', 'lat': 43.6710, 'lon': -79.4020},
    {'tracking_number': 'T005', 'lat': 43.6550, 'lon': -79.3860},
]

current_pos = (43.6532, -79.3832)  # 起點
inner_order_method = 'ortools'
river_detector = None  # 不啟用障礙檢測

print(f"測試群組內排序，方法: {inner_order_method}")
print(f"起點: {current_pos}")
print(f"訂單數: {len(group_orders)}")

# 模擬 app.py 的代碼
if inner_order_method in ['ortools', '2opt-inner', 'lkh']:
    coords_with_start = [current_pos] + [(o['lat'], o['lon']) for o in group_orders]
    
    def obstacle_aware_distance(i, j, coords):
        lat1, lon1 = coords[i]
        lat2, lon2 = coords[j]
        dist = calculate_distance(lat1, lon1, lat2, lon2)
        
        if river_detector:
            # 障礙檢測邏輯（這裡跳過）
            pass
        
        return dist
    
    try:
        print(f"\n調用 solve_tsp...")
        route_indices = solve_tsp(
            coords_with_start, 
            method=inner_order_method, 
            start_index=0,
            distance_func=obstacle_aware_distance if river_detector else None
        )
        
        print(f"✓ 成功！返回路徑索引: {route_indices}")
        
        # 移除起點索引
        route_indices = [i - 1 for i in route_indices if i > 0]
        print(f"移除起點後: {route_indices}")
        
        # 按順序排列
        group_sequence = [group_orders[i] for i in route_indices]
        
        print(f"\n最終順序:")
        for i, order in enumerate(group_sequence, 1):
            print(f"  {i}. {order['tracking_number']} ({order['lat']:.4f}, {order['lon']:.4f})")
        
    except Exception as e:
        print(f"✗ 失敗：{e}")
        import traceback
        traceback.print_exc()

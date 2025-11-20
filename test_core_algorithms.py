#!/usr/bin/env python3
"""
测试核心算法模块 - 验证独立运行
"""

from core_routing_algorithms import (
    plan_route, 
    analyze_order_distribution,
    hybrid_clustering,
    order_clusters_greedy,
    solve_tsp
)

print("="*80)
print("核心算法模块测试")
print("="*80)

# 创建测试订单（多伦多地区）
test_orders = [
    {'tracking_number': 'TEST001', 'lat': 43.6532, 'lon': -79.3832},
    {'tracking_number': 'TEST002', 'lat': 43.6545, 'lon': -79.3850},
    {'tracking_number': 'TEST003', 'lat': 43.6520, 'lon': -79.3800},
    {'tracking_number': 'TEST004', 'lat': 43.6700, 'lon': -79.4000},
    {'tracking_number': 'TEST005', 'lat': 43.6710, 'lon': -79.4020},
    {'tracking_number': 'TEST006', 'lat': 43.6680, 'lon': -79.3950},
    {'tracking_number': 'TEST007', 'lat': 43.6550, 'lon': -79.3820},
    {'tracking_number': 'TEST008', 'lat': 43.6560, 'lon': -79.3840},
]

start_position = (43.6532, -79.3832)

print(f"\n测试订单数量: {len(test_orders)}")
print(f"起点: {start_position}")
print()

# 测试 1: 分析订单分布
print("测试 1: 分析订单分布")
print("-" * 80)
analysis = analyze_order_distribution(test_orders)
print(f"✅ 分析完成")
print()

# 测试 2: 混合聚类
print("测试 2: 混合聚类")
print("-" * 80)
clusters = hybrid_clustering(
    orders=test_orders,
    cluster_radius=1.0,
    min_samples=2,
    max_group_size=5
)
print(f"✅ 聚类完成: {len(clusters)} 个群组")
print()

# 测试 3: 群组排序
print("测试 3: 群组排序")
print("-" * 80)
cluster_order = order_clusters_greedy(clusters, start_position)
print(f"✅ 排序完成: {cluster_order}")
print()

# 测试 4: TSP 求解
print("测试 4: TSP 求解（贪心算法）")
print("-" * 80)
coords = [(o['lat'], o['lon']) for o in test_orders[:5]]
route = solve_tsp(coords, method='nearest', start_index=0)
print(f"✅ TSP 完成: {route}")
print()

# 测试 5: 完整路径规划
print("测试 5: 完整路径规划")
print("-" * 80)
result = plan_route(
    orders=test_orders,
    start_pos=start_position,
    cluster_params={
        'cluster_radius': 1.0,
        'min_samples': 2,
        'max_group_size': 5
    },
    group_order_method='greedy',
    inner_order_method='nearest'
)
print(f"✅ 规划完成: {len(result)} 个订单")
print()

# 显示结果
print("="*80)
print("最终路径结果:")
print("="*80)
print(f"{'序号':<6} {'组内编号':<10} {'Tracking Number':<15} {'座标'}")
print("-" * 80)
for order in result:
    print(f"{order['sequence']:<6} {order['group_sequence']:<10} {order['tracking_number']:<15} "
          f"({order['lat']:.4f}, {order['lon']:.4f})")

print()
print("="*80)
print("✅ 所有测试通过！核心算法模块可以独立运行")
print("="*80)
print()
print("依赖包:")
print("  - numpy")
print("  - scikit-learn")
print("  - scipy")
print("  - ortools (可选)")
print()
print("安装命令:")
print("  pip install -r core_algorithms_requirements.txt")



#!/usr/bin/env python3
"""可視化 Smart 模式路徑"""

import requests
import matplotlib.pyplot as plt
import numpy as np

API_URL = "http://localhost:8080/api/optimize-route-smart"

test_data = {
    "start": {
        "lat": 43.734577,
        "lon": -79.707828
    },
    "order_group": "Group202511151924060106",
    "maxGroupSize": 30,
    "clusterRadius": 1.0
}

response = requests.post(API_URL, json=test_data, timeout=30)

if response.status_code == 200:
    result = response.json()
    orders = result.get('orders', [])

    # 提取組別
    groups = {}
    for order in orders:
        group = order['group_label']
        if group not in groups:
            groups[group] = []
        groups[group].append(order)

    # 創建圖表
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

    # 左圖：顯示所有訂單和組別
    colors = plt.cm.tab10(np.linspace(0, 1, len(groups)))

    start_lat = test_data['start']['lat']
    start_lon = test_data['start']['lon']

    # 繪製起點
    ax1.plot(start_lon, start_lat, 'r*', markersize=20, label='起點', zorder=10)

    # 繪製每組的訂單
    for i, (group_label, group_orders) in enumerate(sorted(groups.items())):
        lats = [o['lat'] for o in group_orders]
        lons = [o['lon'] for o in group_orders]
        ax1.scatter(lons, lats, c=[colors[i]], label=f'{group_label} 組', s=50, alpha=0.6)

        # 計算並繪製中心點
        center_lat = np.mean(lats)
        center_lon = np.mean(lons)
        ax1.plot(center_lon, center_lat, 'o', color=colors[i], markersize=15,
                markeredgecolor='black', markeredgewidth=2, zorder=5)
        ax1.text(center_lon, center_lat, group_label, fontsize=12, fontweight='bold',
                ha='center', va='center', color='white', zorder=6)

    ax1.set_xlabel('Longitude')
    ax1.set_ylabel('Latitude')
    ax1.set_title('所有訂單和組別分布')
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)

    # 右圖：顯示組別順序（中心點連線）
    ax2.plot(start_lon, start_lat, 'r*', markersize=20, label='起點', zorder=10)

    # 計算組別中心點
    group_centers = []
    group_labels_list = []
    for group_label in sorted(groups.keys()):
        group_orders = groups[group_label]
        lats = [o['lat'] for o in group_orders]
        lons = [o['lon'] for o in group_orders]
        center_lat = np.mean(lats)
        center_lon = np.mean(lons)
        group_centers.append((center_lon, center_lat))
        group_labels_list.append(group_label)

    # 繪製組別中心點
    for i, ((lon, lat), label) in enumerate(zip(group_centers, group_labels_list)):
        ax2.plot(lon, lat, 'o', color=colors[i], markersize=15,
                markeredgecolor='black', markeredgewidth=2, zorder=5)
        ax2.text(lon, lat, label, fontsize=12, fontweight='bold',
                ha='center', va='center', color='white', zorder=6)

    # 繪製從起點到第一組的線
    ax2.plot([start_lon, group_centers[0][0]],
            [start_lat, group_centers[0][1]],
            'b-', linewidth=2, alpha=0.7, label='實際路徑')

    # 繪製組別之間的連線
    for i in range(len(group_centers) - 1):
        ax2.plot([group_centers[i][0], group_centers[i+1][0]],
                [group_centers[i][1], group_centers[i+1][1]],
                'b-', linewidth=2, alpha=0.7)

    # 繪製從最後一組回到起點的虛線（如果是閉環的話）
    ax2.plot([group_centers[-1][0], start_lon],
            [group_centers[-1][1], start_lat],
            'r--', linewidth=2, alpha=0.5, label='如果閉環（不存在）')

    # 標註距離
    dist_to_first = np.sqrt((start_lon - group_centers[0][0])**2 +
                            (start_lat - group_centers[0][1])**2)
    dist_to_last = np.sqrt((start_lon - group_centers[-1][0])**2 +
                           (start_lat - group_centers[-1][1])**2)

    ax2.text(0.02, 0.98, f'起點 → {group_labels_list[0]}: {dist_to_first:.6f}\n'
                          f'起點 → {group_labels_list[-1]}: {dist_to_last:.6f}\n'
                          f'比例: {dist_to_last/dist_to_first:.2f}x',
            transform=ax2.transAxes, fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    ax2.set_xlabel('Longitude')
    ax2.set_ylabel('Latitude')
    ax2.set_title('組別順序路徑（中心點連線）')
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('smart_path_visualization.png', dpi=150, bbox_inches='tight')
    print("✅ 可視化圖表已保存為 smart_path_visualization.png")
    print(f"\n組別順序: {' → '.join(group_labels_list)}")
    print(f"是否閉環: 否（最後組距起點是第一組的 {dist_to_last/dist_to_first:.2f} 倍）")
else:
    print(f"❌ API 錯誤: {response.status_code}")

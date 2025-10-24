#!/usr/bin/env python3
"""
分析特定訂單的聚類決策過程
重點：為什麼 B-35 和 B-36 屬於群組 B 而不是群組 A
"""

import pymysql
import numpy as np
from sklearn.cluster import DBSCAN, KMeans
import math

# 資料庫配置
DB_CONFIG = {
    'host': '15.156.112.57',
    'port': 33306,
    'user': 'select-user',
    'password': 'emile2024',
    'database': 'bonddb',
    'charset': 'utf8mb4'
}

ORDER_GROUP = "Group202510172101060201"

def get_db_connection():
    return pymysql.connect(**DB_CONFIG)


def calculate_distance(lat1, lon1, lat2, lon2):
    """計算兩點之間的歐幾里得距離"""
    return math.sqrt((lat2 - lat1)**2 + (lon2 - lon1)**2)


def fetch_orders():
    """獲取訂單"""
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    query = """
        SELECT tracking_number, latitude, longitude 
        FROM ordersjb 
        WHERE order_group = %s 
        AND latitude IS NOT NULL 
        AND longitude IS NOT NULL
        ORDER BY tracking_number
    """
    
    cursor.execute(query, (ORDER_GROUP,))
    orders = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    # 轉換座標
    valid_orders = []
    for order in orders:
        lat_raw = float(order['latitude'])
        lon_raw = float(order['longitude'])
        lat = lat_raw / 10000000000.0 if abs(lat_raw) > 1000 else lat_raw
        lon = lon_raw / 10000000000.0 if abs(lon_raw) > 1000 else lon_raw
        
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            if abs(lat) > 0.001 and abs(lon) > 0.001:
                valid_orders.append({
                    'tracking_number': order['tracking_number'],
                    'lat': lat,
                    'lon': lon
                })
    
    return valid_orders


def perform_clustering(valid_orders, cluster_radius=1.5, min_samples=3, max_group_size=40):
    """執行聚類並返回詳細信息"""
    
    print("="*80)
    print("步驟 1：DBSCAN 聚類")
    print("="*80)
    
    coords = np.array([[o['lat'], o['lon']] for o in valid_orders])
    
    # DBSCAN
    eps_distance = cluster_radius / 111.0
    dbscan = DBSCAN(eps=eps_distance, min_samples=min_samples, metric='euclidean')
    cluster_labels = dbscan.fit_predict(coords)
    
    print(f"\nDBSCAN 參數:")
    print(f"  - eps: {eps_distance:.6f} 度 ({cluster_radius} km)")
    print(f"  - min_samples: {min_samples}")
    print(f"  - metric: euclidean")
    
    # 處理噪聲點
    noise_indices = np.where(cluster_labels == -1)[0]
    if len(noise_indices) > 0:
        print(f"\n處理 {len(noise_indices)} 個孤立點...")
        for idx in noise_indices:
            point = coords[idx]
            valid_clusters = cluster_labels[cluster_labels != -1]
            if len(valid_clusters) > 0:
                distances = [calculate_distance(point[0], point[1], coords[i][0], coords[i][1]) 
                           for i in range(len(coords)) if cluster_labels[i] != -1]
                if distances:
                    nearest_idx = [i for i in range(len(coords)) if cluster_labels[i] != -1][np.argmin(distances)]
                    cluster_labels[idx] = cluster_labels[nearest_idx]
            else:
                cluster_labels[idx] = 0
    
    # 統計初始群組
    initial_clusters = {}
    for idx, label in enumerate(cluster_labels):
        if label not in initial_clusters:
            initial_clusters[label] = []
        initial_clusters[label].append({
            'index': idx,
            'order': valid_orders[idx]
        })
    
    print(f"\nDBSCAN 結果：{len(initial_clusters)} 個初始群組")
    for label in sorted(initial_clusters.keys()):
        print(f"  群組 {label}: {len(initial_clusters[label])} 個訂單")
    
    print("\n" + "="*80)
    print("步驟 2：K-means 細分大群組")
    print("="*80)
    
    # K-means 細分
    final_clusters = {}
    cluster_id = 0
    cluster_mapping = {}  # 記錄每個訂單從 DBSCAN label 到最終 cluster_id 的映射
    
    for label, items in initial_clusters.items():
        orders = [item['order'] for item in items]
        indices = [item['index'] for item in items]
        
        if len(orders) <= max_group_size:
            # 不需要細分
            final_clusters[cluster_id] = {
                'orders': orders,
                'indices': indices,
                'dbscan_label': label,
                'subdivided': False
            }
            for idx in indices:
                cluster_mapping[idx] = cluster_id
            print(f"\n群組 {label} → Cluster {cluster_id}: {len(orders)} 個訂單（保持不變）")
            cluster_id += 1
        else:
            # 需要細分
            n_sub_clusters = (len(orders) + max_group_size - 1) // max_group_size
            print(f"\n群組 {label}: {len(orders)} 個訂單 → 細分成 {n_sub_clusters} 個子群組")
            
            sub_coords = np.array([[o['lat'], o['lon']] for o in orders])
            kmeans = KMeans(n_clusters=n_sub_clusters, random_state=42, n_init=10)
            sub_labels = kmeans.fit_predict(sub_coords)
            
            for sub_label in range(n_sub_clusters):
                sub_orders = [orders[i] for i in range(len(orders)) if sub_labels[i] == sub_label]
                sub_indices = [indices[i] for i in range(len(orders)) if sub_labels[i] == sub_label]
                
                final_clusters[cluster_id] = {
                    'orders': sub_orders,
                    'indices': sub_indices,
                    'dbscan_label': label,
                    'kmeans_sublabel': sub_label,
                    'subdivided': True
                }
                for idx in sub_indices:
                    cluster_mapping[idx] = cluster_id
                
                print(f"  子群組 {sub_label} → Cluster {cluster_id}: {len(sub_orders)} 個訂單")
                cluster_id += 1
    
    return cluster_labels, final_clusters, cluster_mapping, coords


def analyze_specific_orders(valid_orders, cluster_labels, final_clusters, cluster_mapping, coords):
    """分析特定訂單的聚類決策"""
    
    # 找到 B-35 和 B-36 對應的訂單
    # 從報告中我們知道：
    # B-35: EM200003259335CA (待確認)
    # B-36: EM500029551897CA (待確認)
    
    # 先找出群組 B 的所有訂單
    print("\n" + "="*80)
    print("步驟 3：分析 B-35 和 B-36 的聚類決策")
    print("="*80)
    
    # 實際上我們需要先運行完整的群組排序才能知道哪些訂單對應 B-35, B-36
    # 這裡我們先分析所有 cluster 的特徵
    
    print("\n所有 Cluster 的中心點：")
    for cluster_id, cluster_info in final_clusters.items():
        orders = cluster_info['orders']
        avg_lat = sum(o['lat'] for o in orders) / len(orders)
        avg_lon = sum(o['lon'] for o in orders) / len(orders)
        print(f"\nCluster {cluster_id}:")
        print(f"  訂單數: {len(orders)}")
        print(f"  中心點: ({avg_lat:.6f}, {avg_lon:.6f})")
        print(f"  DBSCAN Label: {cluster_info['dbscan_label']}")
        if cluster_info['subdivided']:
            print(f"  K-means 子標籤: {cluster_info['kmeans_sublabel']}")
        
        # 顯示前 3 個訂單
        print(f"  前 3 個訂單:")
        for i, order in enumerate(orders[:3], 1):
            print(f"    {i}. {order['tracking_number']} ({order['lat']:.6f}, {order['lon']:.6f})")
    
    # 分析特定訂單的鄰居
    print("\n" + "="*80)
    print("步驟 4：分析訂單的鄰近關係")
    print("="*80)
    
    # 找出一些關鍵訂單並分析它們的鄰居
    sample_tracking_numbers = [
        'EM200003259335CA',  # 可能是 B-35
        'EM500029551897CA',  # 可能是 B-36
        'EM200003159110CA',  # A-01
        'EM200003202354CA',  # A-02
    ]
    
    for target_tracking in sample_tracking_numbers:
        # 找到目標訂單
        target_idx = None
        for idx, order in enumerate(valid_orders):
            if order['tracking_number'] == target_tracking:
                target_idx = idx
                break
        
        if target_idx is None:
            continue
        
        target_order = valid_orders[target_idx]
        target_coord = coords[target_idx]
        target_cluster = cluster_mapping[target_idx]
        
        print(f"\n分析訂單: {target_tracking}")
        print(f"  座標: ({target_coord[0]:.6f}, {target_coord[1]:.6f})")
        print(f"  DBSCAN Label: {cluster_labels[target_idx]}")
        print(f"  最終 Cluster ID: {target_cluster}")
        
        # 找出距離最近的 10 個訂單
        distances = []
        for idx in range(len(coords)):
            if idx != target_idx:
                dist = calculate_distance(
                    target_coord[0], target_coord[1],
                    coords[idx][0], coords[idx][1]
                )
                distances.append({
                    'index': idx,
                    'distance': dist,
                    'order': valid_orders[idx],
                    'dbscan_label': cluster_labels[idx],
                    'cluster_id': cluster_mapping[idx]
                })
        
        distances.sort(key=lambda x: x['distance'])
        
        print(f"\n  最近的 10 個鄰居:")
        for i, neighbor in enumerate(distances[:10], 1):
            same_dbscan = "✓" if neighbor['dbscan_label'] == cluster_labels[target_idx] else "✗"
            same_cluster = "✓" if neighbor['cluster_id'] == target_cluster else "✗"
            print(f"    {i}. {neighbor['order']['tracking_number']}")
            print(f"       距離: {neighbor['distance']:.6f} 度 ({neighbor['distance']*111:.2f} km)")
            print(f"       DBSCAN: {neighbor['dbscan_label']} {same_dbscan} | Cluster: {neighbor['cluster_id']} {same_cluster}")


def main():
    """主函數"""
    print(f"\n分析 {ORDER_GROUP} 的聚類決策")
    print("重點：B-35 和 B-36 為什麼屬於群組 B？\n")
    
    # 獲取訂單
    valid_orders = fetch_orders()
    print(f"總訂單數: {len(valid_orders)}\n")
    
    # 執行聚類（使用與測試相同的參數）
    cluster_labels, final_clusters, cluster_mapping, coords = perform_clustering(
        valid_orders,
        cluster_radius=1.5,
        min_samples=3,
        max_group_size=40
    )
    
    # 分析特定訂單
    analyze_specific_orders(valid_orders, cluster_labels, final_clusters, cluster_mapping, coords)
    
    print("\n" + "="*80)
    print("總結")
    print("="*80)
    print("\nDBSCAN 聚類決策基於：")
    print("  1. 密度：每個點的 ε-鄰域（1.5km）內至少有 3 個點")
    print("  2. 連通性：相鄰的密集點會被歸為同一群組")
    print("  3. 地理邊界：自然分隔（如河流）會導致不同群組")
    print("\nK-means 細分決策基於：")
    print("  1. 距離：將大群組分成多個距離較近的子群組")
    print("  2. 平衡：確保每個子群組訂單數 ≤ 40")
    print("\n群組字母分配（A, B, C...）由訪問順序決定，不是聚類決策")


if __name__ == '__main__':
    main()


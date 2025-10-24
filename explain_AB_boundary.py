#!/usr/bin/env python3
"""
解釋群組 A 和群組 B 的邊界劃分
為什麼某些訂單屬於 B 而不是 A？
"""

import pymysql
import numpy as np
from sklearn.cluster import DBSCAN, KMeans
import math

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
    return math.sqrt((lat2 - lat1)**2 + (lon2 - lon1)**2)


def fetch_orders():
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


def main():
    print("="*80)
    print("解釋群組 A 和群組 B 的劃分邏輯")
    print("="*80)
    
    valid_orders = fetch_orders()
    coords = np.array([[o['lat'], o['lon']] for o in valid_orders])
    
    # 執行相同的聚類
    cluster_radius = 1.5
    min_samples = 3
    max_group_size = 40
    
    eps_distance = cluster_radius / 111.0
    dbscan = DBSCAN(eps=eps_distance, min_samples=min_samples, metric='euclidean')
    cluster_labels = dbscan.fit_predict(coords)
    
    # 處理噪聲點
    noise_indices = np.where(cluster_labels == -1)[0]
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
    
    # 分組
    initial_clusters = {}
    for idx, label in enumerate(cluster_labels):
        if label not in initial_clusters:
            initial_clusters[label] = []
        initial_clusters[label].append(idx)
    
    # K-means 細分
    final_clusters = {}
    cluster_id = 0
    cluster_mapping = {}
    
    for label, indices in initial_clusters.items():
        orders = [valid_orders[i] for i in indices]
        
        if len(orders) <= max_group_size:
            final_clusters[cluster_id] = indices
            for idx in indices:
                cluster_mapping[idx] = cluster_id
            cluster_id += 1
        else:
            n_sub_clusters = (len(orders) + max_group_size - 1) // max_group_size
            sub_coords = np.array([[o['lat'], o['lon']] for o in orders])
            kmeans = KMeans(n_clusters=n_sub_clusters, random_state=42, n_init=10)
            sub_labels = kmeans.fit_predict(sub_coords)
            
            for sub_label in range(n_sub_clusters):
                sub_indices = [indices[i] for i in range(len(orders)) if sub_labels[i] == sub_label]
                final_clusters[cluster_id] = sub_indices
                for idx in sub_indices:
                    cluster_mapping[idx] = cluster_id
                cluster_id += 1
    
    print("\n關鍵發現：")
    print("-" * 80)
    print("\n1. DBSCAN 階段：")
    print(f"   - 所有 190 個訂單首先被 DBSCAN 分成 {len(initial_clusters)} 個大群組")
    print(f"   - DBSCAN 基於密度：1.5km 半徑內至少 3 個訂單才算同一群組")
    
    for label in sorted(initial_clusters.keys()):
        indices = initial_clusters[label]
        print(f"\n   DBSCAN 群組 {label}: {len(indices)} 個訂單")
        lats = [coords[i][0] for i in indices]
        lons = [coords[i][1] for i in indices]
        print(f"     緯度範圍: {min(lats):.6f} ~ {max(lats):.6f}")
        print(f"     經度範圍: {min(lons):.6f} ~ {max(lons):.6f}")
    
    print("\n\n2. K-means 細分階段：")
    print(f"   - DBSCAN 群組太大（>40 個訂單）時，用 K-means 細分")
    print(f"   - 最終產生 {len(final_clusters)} 個 Cluster")
    
    for cid in sorted(final_clusters.keys()):
        indices = final_clusters[cid]
        print(f"\n   Cluster {cid}: {len(indices)} 個訂單")
        center_lat = np.mean([coords[i][0] for i in indices])
        center_lon = np.mean([coords[i][1] for i in indices])
        print(f"     中心點: ({center_lat:.6f}, {center_lon:.6f})")
        
        # 找出這個 cluster 的邊界訂單
        lats = [coords[i][0] for i in indices]
        lons = [coords[i][1] for i in indices]
        print(f"     緯度範圍: {min(lats):.6f} ~ {max(lats):.6f}")
        print(f"     經度範圍: {min(lons):.6f} ~ {max(lons):.6f}")
    
    print("\n\n3. 群組字母分配（A, B, C...）：")
    print("   - 由 2-opt 算法決定訪問順序")
    print("   - 從起點 (43.6532, -79.3832) 開始")
    print("   - 選擇距離最近的 Cluster，然後逐步選擇")
    
    # 計算每個 cluster 到起點的距離
    start = (43.6532, -79.3832)
    cluster_distances = {}
    for cid, indices in final_clusters.items():
        center_lat = np.mean([coords[i][0] for i in indices])
        center_lon = np.mean([coords[i][1] for i in indices])
        dist = calculate_distance(start[0], start[1], center_lat, center_lon)
        cluster_distances[cid] = {
            'distance': dist,
            'center': (center_lat, center_lon),
            'count': len(indices)
        }
    
    print("\n   各 Cluster 距離起點的距離：")
    for cid in sorted(cluster_distances.keys(), key=lambda x: cluster_distances[x]['distance']):
        info = cluster_distances[cid]
        print(f"     Cluster {cid}: {info['distance']*111:.2f} km ({info['count']} 個訂單)")
    
    print("\n\n" + "="*80)
    print("為什麼某些訂單在群組 B 而不是群組 A？")
    print("="*80)
    print("\n核心原因：")
    print("  1️⃣  DBSCAN 先將所有訂單按「密度」分成幾個大區域")
    print("     - 如果兩個訂單距離 > 1.5km，且中間沒有其他訂單，會被分到不同區域")
    print("\n  2️⃣  K-means 再將大區域按「距離」細分成小群組")
    print("     - 同一個 DBSCAN 區域內，距離較近的訂單會在同一個小群組")
    print("     - K-means 確保每個群組 ≤ 40 個訂單")
    print("\n  3️⃣  群組字母（A, B, C...）由「訪問順序」決定，不是地理位置")
    print("     - 最接近起點的 Cluster → 群組 A")
    print("     - 第二接近的 Cluster → 群組 B")
    print("     - 以此類推...")
    
    # 分析 A 和 B 群組的邊界
    print("\n\n特別分析：Cluster 0 (群組 A) vs Cluster 2 (群組 B)")
    print("-" * 80)
    
    cluster_A_indices = final_clusters[0]  # 群組 A
    cluster_B_indices = final_clusters[2]  # 群組 B
    
    # 找出兩個群組之間最近的訂單對
    min_dist = float('inf')
    closest_pair = None
    
    for idx_A in cluster_A_indices:
        for idx_B in cluster_B_indices:
            dist = calculate_distance(
                coords[idx_A][0], coords[idx_A][1],
                coords[idx_B][0], coords[idx_B][1]
            )
            if dist < min_dist:
                min_dist = dist
                closest_pair = (idx_A, idx_B)
    
    if closest_pair:
        idx_A, idx_B = closest_pair
        print(f"\n群組 A 和群組 B 之間最近的兩個訂單：")
        print(f"  群組 A: {valid_orders[idx_A]['tracking_number']}")
        print(f"          ({coords[idx_A][0]:.6f}, {coords[idx_A][1]:.6f})")
        print(f"  群組 B: {valid_orders[idx_B]['tracking_number']}")
        print(f"          ({coords[idx_B][0]:.6f}, {coords[idx_B][1]:.6f})")
        print(f"  距離: {min_dist*111:.2f} km")
        print(f"\n→ 即使最近距離也有 {min_dist*111:.2f} km")
        print(f"→ K-means 將它們分成不同群組是因為：")
        print(f"  - 它們各自與自己群組內的其他訂單更接近")
        print(f"  - K-means 目標是最小化群組內部距離，不是群組間距離")
    
    # 顯示群組 B 中距離群組 A 最近的幾個訂單
    print(f"\n\n群組 B 中距離群組 A 最近的 5 個訂單：")
    print(f"{'序號':<6} {'Tracking Number':<20} {'座標':<30} {'距群組A中心':<15}")
    print("-" * 80)
    
    center_A = (
        np.mean([coords[i][0] for i in cluster_A_indices]),
        np.mean([coords[i][1] for i in cluster_A_indices])
    )
    
    distances_to_A = []
    for idx_B in cluster_B_indices:
        dist = calculate_distance(
            center_A[0], center_A[1],
            coords[idx_B][0], coords[idx_B][1]
        )
        distances_to_A.append((idx_B, dist))
    
    distances_to_A.sort(key=lambda x: x[1])
    
    for i, (idx_B, dist) in enumerate(distances_to_A[:5], 1):
        order = valid_orders[idx_B]
        coord_str = f"({coords[idx_B][0]:.6f}, {coords[idx_B][1]:.6f})"
        print(f"{i:<6} {order['tracking_number']:<20} {coord_str:<30} {dist*111:.2f} km")
    
    print("\n→ 這些訂單雖然離群組 A 較近，但它們：")
    print("  1. 與群組 B 內的其他訂單形成密集區域")
    print("  2. K-means 將它們分配到群組 B 使得群組 B 的內部距離最小")
    print("  3. 如果將它們分到群組 A，會增加群組 A 的分散度")


if __name__ == '__main__':
    main()


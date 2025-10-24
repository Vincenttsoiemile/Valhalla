#!/usr/bin/env python3
"""
分析特定訂單：B-35 和 B-36 的聚類決策
EM200003227018CA 和 EM200003173839CA
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
TARGET_ORDERS = ['EM200003227018CA', 'EM200003173839CA']

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
    print("分析特定訂單：B-35 和 B-36")
    print("="*80)
    
    valid_orders = fetch_orders()
    coords = np.array([[o['lat'], o['lon']] for o in valid_orders])
    
    # 找到目標訂單的索引
    target_indices = {}
    for tracking_num in TARGET_ORDERS:
        for idx, order in enumerate(valid_orders):
            if order['tracking_number'] == tracking_num:
                target_indices[tracking_num] = idx
                break
    
    if len(target_indices) != 2:
        print(f"❌ 找不到目標訂單！")
        print(f"找到的訂單: {list(target_indices.keys())}")
        return
    
    print(f"\n✅ 找到目標訂單：")
    for tracking_num, idx in target_indices.items():
        order = valid_orders[idx]
        print(f"  {tracking_num}")
        print(f"    索引: {idx}")
        print(f"    座標: ({order['lat']:.6f}, {order['lon']:.6f})")
    
    # 執行 DBSCAN
    print("\n" + "="*80)
    print("步驟 1：DBSCAN 聚類")
    print("="*80)
    
    cluster_radius = 1.5
    min_samples = 3
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
    
    print(f"\nDBSCAN 參數: eps={eps_distance:.6f} 度 ({cluster_radius} km), min_samples={min_samples}")
    print(f"DBSCAN 結果：{len(set(cluster_labels))} 個群組")
    
    for tracking_num, idx in target_indices.items():
        print(f"\n  {tracking_num}:")
        print(f"    DBSCAN Label: {cluster_labels[idx]}")
    
    # 分析兩個訂單是否在同一個 DBSCAN 群組
    labels = [cluster_labels[idx] for idx in target_indices.values()]
    if labels[0] == labels[1]:
        print(f"\n✅ 兩個訂單在同一個 DBSCAN 群組（Label {labels[0]}）")
    else:
        print(f"\n❌ 兩個訂單在不同的 DBSCAN 群組（Labels {labels[0]} 和 {labels[1]}）")
    
    # 執行 K-means 細分
    print("\n" + "="*80)
    print("步驟 2：K-means 細分")
    print("="*80)
    
    max_group_size = 40
    
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
            print(f"\nDBSCAN 群組 {label}: {len(orders)} 個訂單 → Cluster {cluster_id}（不需細分）")
            cluster_id += 1
        else:
            n_sub_clusters = (len(orders) + max_group_size - 1) // max_group_size
            print(f"\nDBSCAN 群組 {label}: {len(orders)} 個訂單 → 細分成 {n_sub_clusters} 個 Cluster")
            
            sub_coords = np.array([[o['lat'], o['lon']] for o in orders])
            kmeans = KMeans(n_clusters=n_sub_clusters, random_state=42, n_init=10)
            sub_labels = kmeans.fit_predict(sub_coords)
            
            for sub_label in range(n_sub_clusters):
                sub_indices = [indices[i] for i in range(len(orders)) if sub_labels[i] == sub_label]
                final_clusters[cluster_id] = sub_indices
                for idx in sub_indices:
                    cluster_mapping[idx] = cluster_id
                print(f"  子群組 {sub_label} → Cluster {cluster_id}: {len(sub_indices)} 個訂單")
                cluster_id += 1
    
    print("\n目標訂單的 Cluster 分配：")
    for tracking_num, idx in target_indices.items():
        cid = cluster_mapping[idx]
        print(f"  {tracking_num}: Cluster {cid}")
    
    # 分析兩個訂單是否在同一個最終 Cluster
    cluster_ids = [cluster_mapping[idx] for idx in target_indices.values()]
    if cluster_ids[0] == cluster_ids[1]:
        print(f"\n✅ 兩個訂單在同一個最終 Cluster（Cluster {cluster_ids[0]}）")
    else:
        print(f"\n❌ 兩個訂單在不同的最終 Cluster（Clusters {cluster_ids[0]} 和 {cluster_ids[1]}）")
    
    # 計算兩個訂單之間的距離
    print("\n" + "="*80)
    print("步驟 3：訂單間距離分析")
    print("="*80)
    
    idx1, idx2 = list(target_indices.values())
    coord1, coord2 = coords[idx1], coords[idx2]
    
    distance = calculate_distance(coord1[0], coord1[1], coord2[0], coord2[1])
    
    print(f"\n訂單 1: {TARGET_ORDERS[0]}")
    print(f"  座標: ({coord1[0]:.6f}, {coord1[1]:.6f})")
    
    print(f"\n訂單 2: {TARGET_ORDERS[1]}")
    print(f"  座標: ({coord2[0]:.6f}, {coord2[1]:.6f})")
    
    print(f"\n兩訂單之間的距離: {distance*111:.2f} km ({distance:.6f} 度)")
    
    if distance * 111 < cluster_radius:
        print(f"✅ 距離 < {cluster_radius} km，DBSCAN 會認為它們可能在同一群組（如果周圍有足夠密度）")
    else:
        print(f"❌ 距離 > {cluster_radius} km，DBSCAN 可能將它們分到不同群組")
    
    # 分析每個訂單的鄰居
    print("\n" + "="*80)
    print("步驟 4：鄰居分析")
    print("="*80)
    
    for tracking_num, target_idx in target_indices.items():
        target_coord = coords[target_idx]
        target_cluster = cluster_mapping[target_idx]
        
        print(f"\n{tracking_num} 的最近 10 個鄰居：")
        print(f"{'排名':<4} {'Tracking Number':<20} {'距離(km)':<10} {'同Cluster?':<12} {'Cluster ID'}")
        print("-" * 80)
        
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
                    'cluster_id': cluster_mapping[idx]
                })
        
        distances.sort(key=lambda x: x['distance'])
        
        for i, neighbor in enumerate(distances[:10], 1):
            same_cluster = "✓ 是" if neighbor['cluster_id'] == target_cluster else "✗ 否"
            print(f"{i:<4} {neighbor['order']['tracking_number']:<20} {neighbor['distance']*111:<10.2f} {same_cluster:<12} {neighbor['cluster_id']}")
    
    # 分析為什麼在同一個或不同的 Cluster
    print("\n" + "="*80)
    print("總結：為什麼這兩個訂單的分組結果？")
    print("="*80)
    
    if cluster_ids[0] == cluster_ids[1]:
        print(f"\n✅ 這兩個訂單在同一個 Cluster（Cluster {cluster_ids[0]}）")
        print("\n原因：")
        print(f"  1. 它們的距離 ({distance*111:.2f} km) 足夠近")
        print(f"  2. DBSCAN 將它們歸為同一密集區域")
        print(f"  3. K-means 細分時，它們被分配到同一子群組")
        print(f"  4. 它們與該 Cluster 內的其他訂單距離更近")
    else:
        print(f"\n❌ 這兩個訂單在不同的 Cluster（Clusters {cluster_ids[0]} 和 {cluster_ids[1]}）")
        print("\n可能原因：")
        if labels[0] != labels[1]:
            print(f"  1. DBSCAN 階段已將它們分到不同群組（密度不連續）")
            print(f"     - 訂單 1 在 DBSCAN 群組 {labels[0]}")
            print(f"     - 訂單 2 在 DBSCAN 群組 {labels[1]}")
        else:
            print(f"  1. DBSCAN 階段它們在同一群組（群組 {labels[0]}）")
            print(f"  2. K-means 細分時被分配到不同子群組")
            print(f"  3. 每個訂單與各自子群組內的其他訂單更接近")
        print(f"  4. 它們的距離 ({distance*111:.2f} km) 相對較遠")
    
    # 計算兩個訂單到各自 Cluster 中心的距離
    print("\n" + "="*80)
    print("距離 Cluster 中心的距離")
    print("="*80)
    
    for tracking_num, idx in target_indices.items():
        cid = cluster_mapping[idx]
        cluster_indices = final_clusters[cid]
        
        center_lat = np.mean([coords[i][0] for i in cluster_indices])
        center_lon = np.mean([coords[i][1] for i in cluster_indices])
        
        dist_to_center = calculate_distance(coords[idx][0], coords[idx][1], center_lat, center_lon)
        
        print(f"\n{tracking_num}:")
        print(f"  所屬 Cluster: {cid} ({len(cluster_indices)} 個訂單)")
        print(f"  Cluster 中心: ({center_lat:.6f}, {center_lon:.6f})")
        print(f"  距離中心: {dist_to_center*111:.2f} km")


if __name__ == '__main__':
    main()


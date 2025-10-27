#!/usr/bin/env python3
"""Valhalla 訂單路徑規劃系統 - Flask 後端"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import pymysql
import requests
import os
from river_detection import verify_route_crossings, RiverDetector
from tsp_solver import solve_tsp

app = Flask(__name__, static_folder='static')
CORS(app)

# MySQL 配置
DB_CONFIG = {
    'host': '15.156.112.57',
    'port': 33306,
    'user': 'select-user',
    'password': 'emile2024',
    'database': 'bonddb',
    'charset': 'utf8mb4'
}

# Valhalla API
VALHALLA_URL = "https://valhalla1.openstreetmap.de"


def get_db_connection():
    """建立資料庫連接"""
    return pymysql.connect(**DB_CONFIG)


@app.route('/')
def index():
    """首頁"""
    response = send_from_directory('static', 'index.html')
    # 禁用緩存以確保部署時立即更新
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/static/<path:filename>')
def serve_static(filename):
    """服務靜態文件（禁用緩存）"""
    response = send_from_directory('static', filename)
    # 禁用緩存以確保部署時立即更新
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/api/orders', methods=['GET'])
def get_orders():
    """取得指定 order_group 的所有訂單"""
    order_group = request.args.get('order_group')
    
    if not order_group:
        return jsonify({'error': 'order_group 參數必填'}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # 查詢該 order_group 的所有訂單
        query = """
            SELECT tracking_number, latitude, longitude 
            FROM ordersjb 
            WHERE order_group = %s 
            AND latitude IS NOT NULL 
            AND longitude IS NOT NULL
            ORDER BY tracking_number
        """
        
        cursor.execute(query, (order_group,))
        orders = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if not orders:
            return jsonify({'error': f'找不到 order_group: {order_group} 的訂單'}), 404
        
        # 轉換格式：資料庫整數除以 10^10
        result = []
        for order in orders:
            try:
                lat_raw = float(order['latitude'])
                lon_raw = float(order['longitude'])
                
                # 轉換格式
                lat = lat_raw / 10000000000.0 if abs(lat_raw) > 1000 else lat_raw
                lon = lon_raw / 10000000000.0 if abs(lon_raw) > 1000 else lon_raw
                
                # 驗證有效性
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    if abs(lat) > 0.001 and abs(lon) > 0.001:
                        result.append({
                            'tracking_number': order['tracking_number'],
                            'lat': lat,
                            'lon': lon
                        })
            except (ValueError, TypeError):
                continue
        
        return jsonify({
            'order_group': order_group,
            'count': len(result),
            'orders': result
        })
        
    except Exception as e:
        return jsonify({'error': f'資料庫錯誤: {str(e)}'}), 500


@app.route('/api/route', methods=['POST'])
def calculate_route():
    """計算優化路徑"""
    data = request.json
    
    # 驗證輸入
    if not data.get('start'):
        return jsonify({'error': '起點必填'}), 400
    if not data.get('order_group'):
        return jsonify({'error': 'order_group 必填'}), 400
    
    start = data['start']
    order_group = data['order_group']
    costing = data.get('costing', 'auto')
    max_orders = data.get('max_orders', 5000)  # 用戶指定的最大訂單數
    max_group_size = data.get('max_group_size', 30)  # 每組最多訂單數
    cluster_radius = data.get('cluster_radius', 1.0)  # 鄰域半徑 (km)
    min_samples = data.get('min_samples', 3)  # DBSCAN 最小樣本數
    metric = data.get('metric', 'euclidean')  # 距離計算方式
    random_state = data.get('random_state', 42)  # K-means 隨機種子
    n_init = data.get('n_init', 10)  # K-means 初始化次數
    verification = data.get('verification', 'none')  # 跨河檢測方式
    group_penalty = data.get('group_penalty', 2.0)  # 群組間跨河懲罰
    inner_penalty = data.get('inner_penalty', 1.5)  # 組內跨河懲罰
    check_highways = data.get('check_highways', False)  # 是否檢測高速公路
    group_order_method = data.get('group_order_method', 'greedy')  # 群組排序方法
    inner_order_method = data.get('inner_order_method', 'nearest')  # 組內排序方法
    end_point_mode = data.get('end_point_mode', 'last_order')  # 終點模式
    end_point = data.get('end_point')  # 終點座標（手動模式）
    
    print(f"[DEBUG] 計算路徑請求: order_group={order_group}, costing={costing}, max_orders={max_orders}, start={start}, end_point_mode={end_point_mode}")
    
    try:
        # 從資料庫取得訂單座標
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
        
        cursor.execute(query, (order_group,))
        orders = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if not orders:
            return jsonify({'error': f'找不到 order_group: {order_group} 的訂單'}), 404
        
        print(f"[DEBUG] 找到 {len(orders)} 個訂單")
        
        # 驗證並過濾有效的經緯度
        valid_orders = []
        for order in orders:
            try:
                # 資料庫格式：整數需除以 10^10 轉換為正確的經緯度
                lat_raw = float(order['latitude'])
                lon_raw = float(order['longitude'])
                
                # 轉換格式：如果數值很大，除以 10^10
                if abs(lat_raw) > 1000:
                    lat = lat_raw / 10000000000.0
                else:
                    lat = lat_raw
                    
                if abs(lon_raw) > 1000:
                    lon = lon_raw / 10000000000.0
                else:
                    lon = lon_raw
                
                # 驗證經緯度範圍
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    if abs(lat) > 0.001 and abs(lon) > 0.001:  # 排除 0,0
                        valid_orders.append({
                            'tracking_number': order['tracking_number'],
                            'lat': lat,
                            'lon': lon
                        })
                        print(f"[DEBUG] 訂單 {order['tracking_number']}: ({lat:.6f}, {lon:.6f})")
            except (ValueError, TypeError) as e:
                print(f"[WARN] 跳過無效座標: {order.get('tracking_number')} - {e}")
                continue
        
        if not valid_orders:
            return jsonify({'error': '沒有有效的訂單座標'}), 404
        
        # 限制訂單數量（用戶指定或默認 5000）
        max_allowed = min(max_orders, 5000)  # 最多 5000 個
        if len(valid_orders) > max_allowed:
            print(f"[INFO] 訂單數量 {len(valid_orders)}，取前 {max_allowed} 個計算")
            valid_orders = valid_orders[:max_allowed]
        
        print(f"[DEBUG] 有效訂單: {len(valid_orders)} 個")
        
        # 使用 DBSCAN + K-means 混合聚類
        from sklearn.cluster import DBSCAN, KMeans
        import numpy as np
        import math
        import time
        
        # 初始化演算法步驟記錄
        algorithm_steps = []
        step_counter = 0
        
        def calculate_distance(lat1, lon1, lat2, lon2):
            """計算兩點之間的歐幾里得距離"""
            return math.sqrt((lat2 - lat1)**2 + (lon2 - lon1)**2)
        
        # 步驟 1: DBSCAN 聚類（粗分）
        n_orders = len(valid_orders)
        
        print(f"[INFO] 使用混合聚類對 {n_orders} 個訂單分組（每組最多 {max_group_size} 個，半徑 {cluster_radius} km）...")
        
        # 準備數據
        coords = np.array([[o['lat'], o['lon']] for o in valid_orders])
        
        # 記錄步驟 0：初始狀態
        step_counter += 1
        algorithm_steps.append({
            'step': step_counter,
            'name': '初始化',
            'description': f'載入 {n_orders} 個訂單座標',
            'timestamp': float(time.time()),
            'affected_by': ['order_group'],
            'data': {
                'orders': [{'lat': float(o['lat']), 'lon': float(o['lon']), 'tracking_number': o['tracking_number']} for o in valid_orders],
                'total_orders': int(n_orders)
            }
        })
        
        # DBSCAN 參數（根據 metric 選擇不同的處理方式）
        step_counter += 1
        if metric == 'haversine':
            # Haversine 需要弧度並使用地球半徑
            coords_rad = np.radians(coords)
            eps_distance = cluster_radius / 6371.0  # 地球半徑 6371 km
            dbscan = DBSCAN(eps=eps_distance, min_samples=min_samples, metric='haversine')
            cluster_labels = dbscan.fit_predict(coords_rad)
            print(f"[INFO] 使用 Haversine 距離，eps={eps_distance:.6f} 弧度")
        else:
            # Euclidean 或 Manhattan：1 度 ≈ 111 km
            eps_distance = cluster_radius / 111.0
            dbscan = DBSCAN(eps=eps_distance, min_samples=min_samples, metric=metric)
            cluster_labels = dbscan.fit_predict(coords)
            print(f"[INFO] 使用 {metric} 距離，eps={eps_distance:.6f} 度")
        
        # 記錄步驟 1：DBSCAN 聚類完成
        unique_labels = set(cluster_labels)
        n_clusters = len(unique_labels) - (1 if -1 in unique_labels else 0)
        n_noise = list(cluster_labels).count(-1)
        
        # 建立初步群組資料並計算中心點
        dbscan_clusters = {}
        dbscan_centers = {}
        for idx, label in enumerate(cluster_labels):
            label_key = str(int(label))  # 轉換為字符串
            if label_key not in dbscan_clusters:
                dbscan_clusters[label_key] = []
            dbscan_clusters[label_key].append({
                'index': int(idx),
                'lat': float(valid_orders[idx]['lat']),
                'lon': float(valid_orders[idx]['lon']),
                'tracking_number': valid_orders[idx]['tracking_number']
            })
        
        # 計算每個 DBSCAN 群組的中心點
        for label_key, orders in dbscan_clusters.items():
            center_lat = sum(o['lat'] for o in orders) / len(orders)
            center_lon = sum(o['lon'] for o in orders) / len(orders)
            dbscan_centers[label_key] = {
                'lat': float(center_lat),
                'lon': float(center_lon),
                'count': len(orders)
            }
        
        # 生成包含中心點的描述
        cluster_centers_desc = []
        for label_key, center in sorted(dbscan_centers.items(), key=lambda x: int(x[0]) if x[0] != '-1' else -999):
            if label_key != '-1':  # 排除噪聲點
                cluster_centers_desc.append(f"群組{label_key}: ({center['lat']:.5f}, {center['lon']:.5f}), {center['count']}點")
        
        centers_text = " | ".join(cluster_centers_desc[:3])  # 只顯示前3個群組避免太長
        if len(cluster_centers_desc) > 3:
            centers_text += f" | ...共{len(cluster_centers_desc)}組"
        
        algorithm_steps.append({
            'step': step_counter,
            'name': 'DBSCAN 密度聚類',
            'description': f'找到 {n_clusters} 組，{n_noise} 噪聲點 | 中心點: {centers_text}',
            'timestamp': float(time.time()),
            'affected_by': ['cluster_radius', 'min_samples', 'metric'],
            'data': {
                'method': 'DBSCAN',
                'parameters': {
                    'eps': eps_distance,
                    'min_samples': min_samples,
                    'metric': metric,
                    'radius_km': cluster_radius
                },
                'result': {
                    'n_clusters': int(n_clusters),
                    'n_noise': int(n_noise),
                    'clusters': dbscan_clusters,
                    'centers': dbscan_centers
                },
                'stats': {
                    'total_groups': int(n_clusters),
                    'noise_points': int(n_noise),
                    'clustered_points': int(n_orders - n_noise)
                }
            }
        })
        
        # 處理噪聲點（label = -1）：將它們分配到最近的群組
        noise_indices = np.where(cluster_labels == -1)[0]
        noise_reassignments = []
        
        if len(noise_indices) > 0:
            print(f"[INFO] 發現 {len(noise_indices)} 個孤立點，分配到最近的群組...")
            step_counter += 1
            
            for idx in noise_indices:
                point = coords[idx]
                # 找到最近的非噪聲點
                valid_clusters = cluster_labels[cluster_labels != -1]
                if len(valid_clusters) > 0:
                    distances = [calculate_distance(point[0], point[1], coords[i][0], coords[i][1]) 
                               for i in range(len(coords)) if cluster_labels[i] != -1]
                    if distances:
                        nearest_idx = [i for i in range(len(coords)) if cluster_labels[i] != -1][np.argmin(distances)]
                        old_label = cluster_labels[idx]
                        new_label = cluster_labels[nearest_idx]
                        cluster_labels[idx] = new_label
                        
                        # 計算目標群組的中心點
                        target_cluster_points = [(valid_orders[i]['lat'], valid_orders[i]['lon']) 
                                               for i in range(len(cluster_labels)) if cluster_labels[i] == new_label]
                        target_center_lat = sum(p[0] for p in target_cluster_points) / len(target_cluster_points)
                        target_center_lon = sum(p[1] for p in target_cluster_points) / len(target_cluster_points)
                        
                        noise_reassignments.append({
                            'order_index': int(idx),
                            'tracking_number': valid_orders[idx]['tracking_number'],
                            'lat': float(valid_orders[idx]['lat']),
                            'lon': float(valid_orders[idx]['lon']),
                            'old_label': int(old_label),
                            'new_label': int(new_label),
                            'distance_to_cluster': float(min(distances)),
                            'target_center': {
                                'lat': float(target_center_lat),
                                'lon': float(target_center_lon)
                            }
                        })
                else:
                    cluster_labels[idx] = 0  # 如果沒有其他群組，創建新群組
            
            # 記錄步驟 2：噪聲點重新分配
            # 生成分配目標摘要
            reassignment_summary = {}
            for ra in noise_reassignments:
                target_label = ra['new_label']
                if target_label not in reassignment_summary:
                    reassignment_summary[target_label] = {
                        'count': 0,
                        'center': ra['target_center']
                    }
                reassignment_summary[target_label]['count'] += 1
            
            summary_text = " | ".join([
                f"群組{label}: ({info['center']['lat']:.5f}, {info['center']['lon']:.5f}), {info['count']}點"
                for label, info in list(reassignment_summary.items())[:2]
            ])
            if len(reassignment_summary) > 2:
                summary_text += f" | ...共分配到{len(reassignment_summary)}個群組"
            
            algorithm_steps.append({
                'step': step_counter,
                'name': '噪聲點處理',
                'description': f'{len(noise_indices)} 孤立點 → {summary_text}',
                'timestamp': float(time.time()),
                'affected_by': ['cluster_radius', 'min_samples'],
                'data': {
                    'noise_count': int(len(noise_indices)),
                    'reassignments': noise_reassignments,
                    'summary': reassignment_summary
                }
            })
        
        # 將訂單按群組分類
        initial_clusters = {}
        for idx, label in enumerate(cluster_labels):
            if label not in initial_clusters:
                initial_clusters[label] = []
            initial_clusters[label].append(valid_orders[idx])
        
        print(f"[INFO] DBSCAN 完成，初步分成 {len(initial_clusters)} 組")
        
        # 步驟 3: 對大群組進行二次分割（用 K-means）
        step_counter += 1
        clusters = {}
        cluster_id = 0
        kmeans_operations = []
        
        for label, orders in initial_clusters.items():
            if len(orders) <= max_group_size:
                # 群組夠小，直接使用
                clusters[cluster_id] = orders
                print(f"  群組 {cluster_id}: {len(orders)} 個訂單（保持）")
                
                # 計算中心點
                center_lat = sum(o['lat'] for o in orders) / len(orders)
                center_lon = sum(o['lon'] for o in orders) / len(orders)
                
                kmeans_operations.append({
                    'original_label': int(label),
                    'action': 'keep',
                    'size': int(len(orders)),
                    'final_cluster_id': int(cluster_id),
                    'center': {
                        'lat': float(center_lat),
                        'lon': float(center_lon)
                    }
                })
                cluster_id += 1
            else:
                # 群組太大，用 K-means 細分
                n_sub_clusters = (len(orders) + max_group_size - 1) // max_group_size  # 向上取整
                print(f"  群組 {label} 有 {len(orders)} 個訂單，細分成 {n_sub_clusters} 個子群組...")
                
                # 計算原始群組中心點
                orig_center_lat = sum(o['lat'] for o in orders) / len(orders)
                orig_center_lon = sum(o['lon'] for o in orders) / len(orders)
                
                sub_coords = np.array([[o['lat'], o['lon']] for o in orders])
                kmeans = KMeans(n_clusters=n_sub_clusters, random_state=random_state, n_init=n_init)
                sub_labels = kmeans.fit_predict(sub_coords)
                
                split_info = {
                    'original_label': int(label),
                    'action': 'split',
                    'original_size': int(len(orders)),
                    'original_center': {
                        'lat': float(orig_center_lat),
                        'lon': float(orig_center_lon)
                    },
                    'n_sub_clusters': int(n_sub_clusters),
                    'sub_clusters': []
                }
                
                for sub_label in range(n_sub_clusters):
                    sub_orders = [orders[i] for i in range(len(orders)) if sub_labels[i] == sub_label]
                    clusters[cluster_id] = sub_orders
                    print(f"    子群組 {cluster_id}: {len(sub_orders)} 個訂單")
                    
                    sub_center_lat = np.mean([o['lat'] for o in sub_orders])
                    sub_center_lon = np.mean([o['lon'] for o in sub_orders])
                    
                    split_info['sub_clusters'].append({
                        'final_cluster_id': int(cluster_id),
                        'size': int(len(sub_orders)),
                        'center': {
                            'lat': float(sub_center_lat),
                            'lon': float(sub_center_lon)
                        }
                    })
                    cluster_id += 1
                
                kmeans_operations.append(split_info)
        
        print(f"[INFO] 最終分成 {len(clusters)} 組")
        
        # 記錄步驟 3：K-means 細分
        # 生成細分操作摘要
        split_ops = [op for op in kmeans_operations if op['action'] == 'split']
        split_summary = []
        for op in split_ops[:2]:  # 只顯示前2個
            orig_center = op['original_center']
            sub_centers_text = ", ".join([
                f"({sc['center']['lat']:.5f}, {sc['center']['lon']:.5f})"
                for sc in op['sub_clusters'][:2]
            ])
            if len(op['sub_clusters']) > 2:
                sub_centers_text += f" ...共{len(op['sub_clusters'])}個"
            split_summary.append(f"群組{op['original_label']}({orig_center['lat']:.5f}, {orig_center['lon']:.5f}) → {sub_centers_text}")
        
        summary_desc = " | ".join(split_summary)
        if len(split_ops) > 2:
            summary_desc += f" | ...共細分{len(split_ops)}組"
        elif len(split_ops) == 0:
            summary_desc = f"所有群組都在 {max_group_size} 個訂單內，無需細分"
        
        algorithm_steps.append({
            'step': step_counter,
            'name': 'K-means 細分大群組',
            'description': summary_desc,
            'timestamp': float(time.time()),
            'affected_by': ['max_group_size', 'random_state', 'n_init'],
            'data': {
                'max_group_size': int(max_group_size),
                'operations': kmeans_operations,
                'final_clusters': {
                    str(int(cid)): [{'lat': float(o['lat']), 'lon': float(o['lon']), 'tracking_number': o['tracking_number']} for o in orders]
                    for cid, orders in clusters.items()
                },
                'stats': {
                    'initial_groups': int(len(initial_clusters)),
                    'final_groups': int(len(clusters)),
                    'kept_groups': int(len([op for op in kmeans_operations if op['action'] == 'keep'])),
                    'split_groups': int(len([op for op in kmeans_operations if op['action'] == 'split']))
                }
            }
        })
        
        # 計算每個群組的中心點
        cluster_centers = {}
        for label, orders in clusters.items():
            avg_lat = sum(o['lat'] for o in orders) / len(orders)
            avg_lon = sum(o['lon'] for o in orders) / len(orders)
            cluster_centers[label] = (avg_lat, avg_lon)
        
        # 步驟 3: 確定群組訪問順序（根據用戶選擇的方法）
        cluster_order = []
        start_pos = (start['lat'], start['lon'])
        print(f"[INFO] 起點座標: ({start_pos[0]:.6f}, {start_pos[1]:.6f})")
        print(f"[INFO] 群組中心點:")
        for label, center in cluster_centers.items():
            dist = calculate_distance(start_pos[0], start_pos[1], center[0], center[1])
            print(f"  Cluster {label}: ({center[0]:.6f}, {center[1]:.6f}), 距起點: {dist:.4f}°")
        
        # 初始化河流檢測器（如果需要在群組排序時考慮跨河）
        river_detector_for_groups = None
        use_api_for_groups = False
        
        if verification == 'geometry':
            river_detector_for_groups = RiverDetector.get_instance()
            print(f"[INFO] 群組排序將考慮跨河（幾何檢測），懲罰係數: {group_penalty}")
        elif verification == 'api':
            use_api_for_groups = True
            river_detector_for_groups = RiverDetector.get_instance()  # API 模式下組內仍用幾何
            print(f"[INFO] 群組排序將考慮跨河（API 檢測），懲罰係數: {group_penalty}")
        
        print(f"[INFO] 使用 {group_order_method} 方法計算群組訪問順序...")
        
        # === 方法 1: Sweep Algorithm（智能方向掃描）===
        if group_order_method == 'sweep':
            print(f"[INFO] Sweep Algorithm: 智能選擇掃描方向...")
            import math
            
            # 步驟 1: 計算每個群組相對起點的極角和距離
            cluster_angles = {}
            cluster_distances = {}
            for label, center in cluster_centers.items():
                dx = center[1] - start_pos[1]  # 經度差
                dy = center[0] - start_pos[0]  # 緯度差
                angle = math.atan2(dy, dx)  # 極角（-π 到 π）
                dist = calculate_distance(start_pos[0], start_pos[1], center[0], center[1])
                cluster_angles[label] = angle
                cluster_distances[label] = dist
            
            # 步驟 2: 找到距離起點最近的群組
            nearest_cluster = min(clusters.keys(), key=lambda x: cluster_distances[x])
            nearest_center = cluster_centers[nearest_cluster]
            start_angle = cluster_angles[nearest_cluster]
            
            print(f"[INFO] 最近群組: {nearest_cluster} (距離: {cluster_distances[nearest_cluster]:.2f} km, 極角: {math.degrees(start_angle):.1f}°)")
            
            # 步驟 3: 判斷其他群組在基準線（起點→最近群組）的左側/右側
            # 使用叉積判斷：cross = (B-A) × (C-A)
            # cross > 0: C在AB左側；cross < 0: C在AB右側
            left_orders = 0
            right_orders = 0
            
            for label, center in cluster_centers.items():
                if label == nearest_cluster:
                    continue
                
                # 向量: 起點 → 最近群組
                vec_base_x = nearest_center[1] - start_pos[1]
                vec_base_y = nearest_center[0] - start_pos[0]
                
                # 向量: 起點 → 當前群組
                vec_current_x = center[1] - start_pos[1]
                vec_current_y = center[0] - start_pos[0]
                
                # 叉積
                cross_product = vec_base_x * vec_current_y - vec_base_y * vec_current_x
                
                # 統計兩側訂單數
                order_count = len(clusters[label])
                if cross_product > 0:
                    left_orders += order_count
                else:
                    right_orders += order_count
            
            # 步驟 4: 決定掃描方向
            # 右側訂單多 → 順時針（先處理右側）
            # 左側訂單多 → 逆時針（先處理左側）
            clockwise = (right_orders >= left_orders)
            direction_text = "順時針" if clockwise else "逆時針"
            
            print(f"[INFO] 訂單分布: 左側 {left_orders} 個, 右側 {right_orders} 個")
            print(f"[INFO] 選擇掃描方向: {direction_text} ({direction_text}先處理較多訂單側)")
            
            # 步驟 5: 將所有極角調整為相對於最近群組的角度
            adjusted_angles = {}
            for label in clusters.keys():
                angle_diff = cluster_angles[label] - start_angle
                # 標準化到 [0, 2π) 範圍
                if angle_diff < 0:
                    angle_diff += 2 * math.pi
                adjusted_angles[label] = angle_diff
            
            # 步驟 6: 按調整後的極角排序
            if clockwise:
                # 順時針: 極角從小到大
                cluster_order = sorted(clusters.keys(), key=lambda x: adjusted_angles[x])
            else:
                # 逆時針: 極角從大到小
                cluster_order = sorted(clusters.keys(), key=lambda x: -adjusted_angles[x])
            
            print(f"[INFO] Sweep 完成，從最近群組 {nearest_cluster} 開始{direction_text}掃描")
            print(f"[INFO] 群組順序: {cluster_order}")
        
        # === 方法 2: Greedy + 2-opt 優化 ===
        elif group_order_method == '2opt':
            # 先用貪心算法生成初始順序
            print(f"[INFO] 步驟 1/2: 貪心算法生成初始順序...")
            visited_clusters = set()
            cluster_order = []
            current_pos = start_pos
            
            while len(visited_clusters) < len(clusters):
                best_cluster = None
                best_cost = float('inf')
                
                for label in clusters.keys():
                    if label in visited_clusters:
                        continue
                    
                    cluster_center = cluster_centers[label]
                    straight_dist = calculate_distance(
                        current_pos[0], current_pos[1],
                        cluster_center[0], cluster_center[1]
                    )
                    
                    cost = straight_dist
                    
                    # 考慮跨河懲罰
                    if use_api_for_groups:
                        crosses = river_detector_for_groups.check_crossing_api(
                            current_pos[0], current_pos[1],
                            cluster_center[0], cluster_center[1]
                        )
                        if crosses:
                            cost *= group_penalty
                    elif river_detector_for_groups:
                        result = river_detector_for_groups.check_obstacle_crossing(
                            current_pos[0], current_pos[1],
                            cluster_center[0], cluster_center[1],
                            check_rivers=True,
                            check_highways=check_highways
                        )
                        if result['crosses_any']:
                            cost *= group_penalty
                    
                    if cost < best_cost:
                        best_cost = cost
                        best_cluster = label
                
                if best_cluster is not None:
                    cluster_order.append(best_cluster)
                    visited_clusters.add(best_cluster)
                    current_pos = cluster_centers[best_cluster]
            
            print(f"[INFO] 初始順序: {cluster_order}")
            
            # 2-opt 優化
            print(f"[INFO] 步驟 2/2: 2-opt 優化...")
            
            def calculate_route_cost(order, include_return=False):
                """計算路線總成本"""
                total = 0
                pos = start_pos
                for label in order:
                    center = cluster_centers[label]
                    total += calculate_distance(pos[0], pos[1], center[0], center[1])
                    pos = center
                # 是否考慮回到起點
                if include_return:
                    total += calculate_distance(pos[0], pos[1], start_pos[0], start_pos[1])
                return total
            
            improved = True
            iteration = 0
            max_iterations = 100
            
            while improved and iteration < max_iterations:
                improved = False
                iteration += 1
                
                for i in range(len(cluster_order) - 1):
                    for j in range(i + 2, len(cluster_order)):
                        # 嘗試反轉 [i+1, j] 區間
                        new_order = cluster_order[:i+1] + cluster_order[i+1:j+1][::-1] + cluster_order[j+1:]
                        
                        old_cost = calculate_route_cost(cluster_order)
                        new_cost = calculate_route_cost(new_order)
                        
                        if new_cost < old_cost:
                            cluster_order = new_order
                            improved = True
                            print(f"  [2-opt] Iteration {iteration}: 改善 {old_cost:.2f} → {new_cost:.2f}")
                            break
                    
                    if improved:
                        break
            
            print(f"[INFO] 2-opt 完成（{iteration} 次迭代），優化後順序: {cluster_order}")
        
        # === 方法 3: 貪心算法（默認）===
        else:
            print(f"[INFO] 使用貪心最近鄰算法...")
            visited_clusters = set()
            cluster_order = []
            current_pos = start_pos
            
            while len(visited_clusters) < len(clusters):
                best_cluster = None
                best_cost = float('inf')
                
                for label in clusters.keys():
                    if label in visited_clusters:
                        continue
                    
                    cluster_center = cluster_centers[label]
                    straight_dist = calculate_distance(
                        current_pos[0], current_pos[1],
                        cluster_center[0], cluster_center[1]
                    )
                    
                    cost = straight_dist
                    
                    # 考慮跨河懲罰
                    if use_api_for_groups:
                        crosses = river_detector_for_groups.check_crossing_api(
                            current_pos[0], current_pos[1],
                            cluster_center[0], cluster_center[1]
                        )
                        if crosses:
                            cost *= group_penalty
                    elif river_detector_for_groups:
                        result = river_detector_for_groups.check_obstacle_crossing(
                            current_pos[0], current_pos[1],
                            cluster_center[0], cluster_center[1],
                            check_rivers=True,
                            check_highways=check_highways
                        )
                        if result['crosses_any']:
                            cost *= group_penalty
                    
                    if cost < best_cost:
                        best_cost = cost
                        best_cluster = label
                
                if best_cluster is not None:
                    cluster_order.append(best_cluster)
                    visited_clusters.add(best_cluster)
                    current_pos = cluster_centers[best_cluster]
                    print(f"[INFO] 群組 {len(cluster_order)}: 選擇 cluster {best_cluster}, 成本: {best_cost:.4f}")
        
        # 步驟 4: 為每個群組生成訂單順序
        group_names = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J',
                       'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T',
                       'U', 'V', 'W', 'X', 'Y', 'Z']
        optimized_orders = []
        current_pos = start_pos

        print(f"[INFO] 最終群組訪問順序（將決定 A, B, C... 的分配）:")
        for idx, label in enumerate(cluster_order):
            group_name = group_names[idx] if idx < len(group_names) else f"Z{idx-25}"
            print(f"  {group_name} = Cluster {label} ({len(clusters[label])} 個訂單)")
        
        # 初始化河流檢測器（如果需要）
        # 注意：API 模式下，組內仍使用幾何檢測（避免太多 API 調用）
        river_detector = None
        if verification in ['geometry', 'api']:
            river_detector = RiverDetector.get_instance()
            print(f"[INFO] 啟用組內跨河優化（幾何檢測），懲罰係數: {inner_penalty}")
        
        print(f"[INFO] 開始生成訂單順序...")
        
        for group_idx, cluster_label in enumerate(cluster_order):
            group_name = group_names[group_idx] if group_idx < len(group_names) else f"Z{group_idx-25}"
            group_orders = clusters[cluster_label].copy()
            
            print(f"[INFO] 處理群組 {group_name} ({len(group_orders)} 個訂單)，使用 {inner_order_method} 方法")
            
            # 根據 inner_order_method 選擇排序方式
            if inner_order_method == 'nearest':
                # 方法 1: 最近鄰算法（考慮跨河懲罰）- 原有方法
                remaining = group_orders.copy()
                group_sequence = []
                
                while remaining:
                    # 找最近的訂單（考慮障礙懲罰：河流 + 高速公路）
                    def calculate_cost(o):
                        dist = calculate_distance(current_pos[0], current_pos[1], o['lat'], o['lon'])
                        
                        # 如果啟用了障礙檢測，檢查是否穿越並增加懲罰
                        if river_detector:
                            result = river_detector.check_obstacle_crossing(
                                current_pos[0], current_pos[1], o['lat'], o['lon'],
                                check_rivers=True,
                                check_highways=check_highways
                            )
                            if result['crosses_any']:
                                dist *= inner_penalty
                        
                        return dist
                    
                    nearest = min(remaining, key=calculate_cost)
                    
                    group_sequence.append(nearest)
                    current_pos = (nearest['lat'], nearest['lon'])
                    remaining.remove(nearest)
            
            elif inner_order_method in ['ortools', '2opt-inner', 'lkh']:
                # 方法 2/3/4: 使用 TSP 求解器（考慮障礙物懲罰）
                # 準備座標（加上當前位置作為起點）
                coords_with_start = [current_pos] + [(o['lat'], o['lon']) for o in group_orders]
                
                # 定義考慮障礙物的距離函數
                def obstacle_aware_distance(i, j, coords):
                    """計算兩點間距離，考慮障礙物懲罰"""
                    lat1, lon1 = coords[i]
                    lat2, lon2 = coords[j]
                    
                    # 基礎直線距離
                    dist = calculate_distance(lat1, lon1, lat2, lon2)
                    
                    # 如果啟用障礙檢測，檢查並應用懲罰
                    if river_detector:
                        result = river_detector.check_obstacle_crossing(
                            lat1, lon1, lat2, lon2,
                            check_rivers=True,
                            check_highways=check_highways
                        )
                        if result['crosses_any']:
                            dist *= inner_penalty  # 應用懲罰係數
                    
                    return dist
                
                try:
                    # 求解 TSP（起點索引 = 0），使用障礙物感知的距離函數
                    route_indices = solve_tsp(
                        coords_with_start, 
                        method=inner_order_method, 
                        start_index=0,
                        distance_func=obstacle_aware_distance if river_detector else None
                    )
                    
                    # 移除起點索引，調整為訂單索引
                    route_indices = [i - 1 for i in route_indices if i > 0]
                    
                    # 按 TSP 順序排列
                    group_sequence = [group_orders[i] for i in route_indices]
                    
                    # 更新當前位置為最後一個訂單
                    if group_sequence:
                        current_pos = (group_sequence[-1]['lat'], group_sequence[-1]['lon'])
                
                except Exception as e:
                    print(f"[ERROR] TSP 求解失敗: {e}，回退到 nearest neighbor")
                    # 回退到最近鄰
                    remaining = group_orders.copy()
                    group_sequence = []
                    
                    while remaining:
                        def calculate_cost(o):
                            dist = calculate_distance(current_pos[0], current_pos[1], o['lat'], o['lon'])
                            if river_detector:
                                result = river_detector.check_obstacle_crossing(
                                    current_pos[0], current_pos[1], o['lat'], o['lon'],
                                    check_rivers=True,
                                    check_highways=check_highways
                                )
                                if result['crosses_any']:
                                    dist *= inner_penalty
                            return dist
                        
                        nearest = min(remaining, key=calculate_cost)
                        group_sequence.append(nearest)
                        current_pos = (nearest['lat'], nearest['lon'])
                        remaining.remove(nearest)
            
            else:
                print(f"[WARN] 未知的組內排序方法: {inner_order_method}，使用 nearest neighbor")
                # 默認：最近鄰
                remaining = group_orders.copy()
                group_sequence = []
                
                while remaining:
                    def calculate_cost(o):
                        dist = calculate_distance(current_pos[0], current_pos[1], o['lat'], o['lon'])
                        if river_detector:
                            result = river_detector.check_obstacle_crossing(
                                current_pos[0], current_pos[1], o['lat'], o['lon'],
                                check_rivers=True,
                                check_highways=check_highways
                            )
                            if result['crosses_any']:
                                dist *= inner_penalty
                        return dist
                    
                    nearest = min(remaining, key=calculate_cost)
                    group_sequence.append(nearest)
                    current_pos = (nearest['lat'], nearest['lon'])
                    remaining.remove(nearest)
            
            # 添加到結果，格式：A-01, A-02...
            for seq_num, order in enumerate(group_sequence, 1):
                optimized_orders.append({
                    'sequence': len(optimized_orders) + 1,
                    'group': group_name,
                    'group_sequence': f"{group_name}-{seq_num:02d}",
                    'tracking_number': order['tracking_number'],
                    'lat': order['lat'],
                    'lon': order['lon']
                })
        
        # 記錄步驟：群組排序完成
        step_counter += 1
        group_order_info = []
        for idx, label in enumerate(cluster_order):
            group_name = group_names[idx] if idx < len(group_names) else f"Z{idx-25}"
            center = cluster_centers[label]
            group_order_info.append({
                'group': group_name,
                'cluster_id': int(label),
                'size': int(len(clusters[label])),
                'center': {
                    'lat': float(center[0]),
                    'lon': float(center[1])
                }
            })
        
        # 生成群組順序描述
        group_desc = " → ".join([f"{g['group']}({g['size']})" for g in group_order_info[:5]])
        if len(group_order_info) > 5:
            group_desc += f" → ...共{len(group_order_info)}組"
        
        algorithm_steps.append({
            'step': step_counter,
            'name': '群組排序',
            'description': f'使用 {group_order_method} 方法排序 {len(cluster_order)} 個群組 | {group_desc}',
            'timestamp': float(time.time()),
            'affected_by': ['group_order_method', 'verification', 'group_penalty', 'check_highways'],
            'data': {
                'method': group_order_method,
                'total_groups': int(len(cluster_order)),
                'group_order': group_order_info,
                'cluster_centers': {str(int(label)): {'lat': float(center[0]), 'lon': float(center[1])} 
                                   for label, center in cluster_centers.items()}
            }
        })
        
        print(f"[INFO] 路線計算完成，共 {len(optimized_orders)} 個訂單，分成 {len(cluster_order)} 組")
        
        # 記錄最終步驟：完成所有排序
        step_counter += 1
        algorithm_steps.append({
            'step': step_counter,
            'name': '完成訂單排序',
            'description': f'所有 {len(optimized_orders)} 個訂單已排序完成',
            'timestamp': float(time.time()),
            'affected_by': ['inner_order_method', 'verification', 'inner_penalty', 'check_highways'],
            'data': {
                'total_orders': int(len(optimized_orders)),
                'total_groups': int(len(cluster_order)),
                'final_sequence': optimized_orders,  # 已經是純 Python dict，不需轉換
                'group_order': [{'group': group_names[idx] if idx < len(group_names) else f"Z{idx-25}", 
                                'cluster_id': int(label), 
                                'size': int(len(clusters[label]))} 
                               for idx, label in enumerate(cluster_order)]
            }
        })
        
        # 步驟 4.5: 處理終點設置
        print(f"[DEBUG] 終點模式: {end_point_mode}, 終點座標: {end_point}")
        
        if end_point_mode == 'manual' and end_point:
            # 手動終點：在路徑末端加入終點標記
            print(f"[INFO] 加入手動終點: ({end_point['lat']}, {end_point['lon']})")
            optimized_orders.append({
                'sequence': len(optimized_orders) + 1,
                'group': 'End',
                'group_sequence': 'END',
                'tracking_number': 'ENDPOINT',
                'lat': end_point['lat'],
                'lon': end_point['lon']
            })
        elif end_point_mode == 'farthest':
            # 使用最遠訂單：重新排序確保最遠的在最後
            print(f"[INFO] 調整順序確保最遠訂單在最後...")
            
            # 計算每個訂單距離起點的距離
            import math
            def distance_from_start(order):
                return math.sqrt(
                    (order['lat'] - start['lat'])**2 + 
                    (order['lon'] - start['lon'])**2
                )
            
            # 找出最遠訂單
            farthest_order = max(optimized_orders, key=distance_from_start)
            farthest_idx = optimized_orders.index(farthest_order)
            
            print(f"[INFO] 最遠訂單: {farthest_order['tracking_number']} (距離起點 {distance_from_start(farthest_order):.4f})")
            
            # 如果最遠訂單不在最後，移到最後
            if farthest_idx != len(optimized_orders) - 1:
                optimized_orders.remove(farthest_order)
                optimized_orders.append(farthest_order)
                
                # 重新編號
                for i, order in enumerate(optimized_orders, 1):
                    order['sequence'] = i
                
                print(f"[INFO] 已將最遠訂單移至最後")
        
        # 步驟 5: 障礙檢測（如果啟用）
        crossings = []
        if verification != 'none':
            obstacle_type = "障礙（河流 + 高速公路）" if check_highways else "河流"
            print(f"[INFO] 開始{obstacle_type}檢測（方法: {verification}）...")
            crossings = verify_route_crossings(optimized_orders, verification, check_highways)
            print(f"[INFO] 檢測完成，發現 {len(crossings)} 處穿越{obstacle_type}")
        
        return jsonify({
            'success': True,
            'orders': optimized_orders,
            'shape': '',
            'total_orders': len(optimized_orders),
            'total_groups': len(cluster_order),
            'crossings': crossings,
            'verification_method': verification,
            'algorithm_steps': algorithm_steps  # 新增：演算法步驟記錄
        })
        
        
    except Exception as e:
        print(f"[ERROR] 計算路徑錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'計算路徑錯誤: {str(e)}'}), 500


@app.route('/api/orders-sequence', methods=['GET'])
def get_orders_by_sequence():
    """取得指定 order_group 的訂單，按 delivery_sequence 排序"""
    order_group = request.args.get('order_group')
    
    if not order_group:
        return jsonify({'error': 'order_group 參數必填'}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # 查詢該 order_group 的所有訂單，按 delivery_sequence 排序
        query = """
            SELECT tracking_number, latitude, longitude, delivery_sequence
            FROM ordersjb 
            WHERE order_group = %s 
            AND latitude IS NOT NULL 
            AND longitude IS NOT NULL
            AND delivery_sequence IS NOT NULL
            ORDER BY delivery_sequence
        """
        
        cursor.execute(query, (order_group,))
        orders = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if not orders:
            return jsonify({'error': f'找不到 order_group: {order_group} 的訂單'}), 404
        
        # 轉換格式：資料庫整數除以 10^10
        result = []
        for order in orders:
            try:
                lat_raw = float(order['latitude'])
                lon_raw = float(order['longitude'])
                
                # 轉換格式
                lat = lat_raw / 10000000000.0 if abs(lat_raw) > 1000 else lat_raw
                lon = lon_raw / 10000000000.0 if abs(lon_raw) > 1000 else lon_raw
                
                # 驗證有效性
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    if abs(lat) > 0.001 and abs(lon) > 0.001:
                        result.append({
                            'tracking_number': order['tracking_number'],
                            'lat': lat,
                            'lon': lon,
                            'delivery_sequence_original': order['delivery_sequence']
                        })
            except (ValueError, TypeError):
                continue
        
        # 重新編號 delivery_sequence，從 1 開始，保持原本順序
        for idx, order in enumerate(result, 1):
            order['delivery_sequence'] = idx
        
        return jsonify({
            'order_group': order_group,
            'count': len(result),
            'orders': result
        })
        
    except Exception as e:
        return jsonify({'error': f'資料庫錯誤: {str(e)}'}), 500


@app.route('/api/valhalla-route', methods=['POST'])
def valhalla_route_proxy():
    """代理 Valhalla API 請求，避免 CORS 問題"""
    try:
        data = request.json
        
        # 調用 Valhalla API
        response = requests.post(
            'https://valhalla1.openstreetmap.de/route',
            json=data,
            timeout=10
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        elif response.status_code == 429:
            print(f"[WARN] Valhalla API 限流 (429)")
            return jsonify({'error': 'API 限流，請稍後重試'}), 429
        elif response.status_code == 400:
            print(f"[ERROR] Valhalla API 400: {response.text}")
            return jsonify({'error': 'API 請求格式錯誤'}), 400
        else:
            print(f"[ERROR] Valhalla API {response.status_code}: {response.text}")
            return jsonify({'error': f'Valhalla API 錯誤: {response.status_code}'}), response.status_code
            
    except requests.exceptions.Timeout:
        print(f"[ERROR] Valhalla API 超時")
        return jsonify({'error': 'API 請求超時'}), 504
    except Exception as e:
        print(f"[ERROR] Valhalla 代理錯誤: {str(e)}")
        return jsonify({'error': f'代理錯誤: {str(e)}'}), 500


@app.route('/api/analyze-distribution', methods=['POST'])
def analyze_distribution():
    """分析訂單分佈並提供智能建議"""
    data = request.json
    order_group = data.get('order_group')
    
    if not order_group:
        return jsonify({'error': 'order_group 必填'}), 400
    
    try:
        # 從資料庫取得訂單座標
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        query = """
            SELECT latitude, longitude 
            FROM ordersjb 
            WHERE order_group = %s 
            AND latitude IS NOT NULL 
            AND longitude IS NOT NULL
        """
        
        cursor.execute(query, (order_group,))
        orders = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if not orders or len(orders) < 3:
            return jsonify({'error': '訂單數量不足（至少需要 3 個）'}), 400
        
        # 轉換座標格式
        coords = []
        for order in orders:
            lat_raw = float(order['latitude'])
            lon_raw = float(order['longitude'])
            
            lat = lat_raw / 10000000000.0 if abs(lat_raw) > 1000 else lat_raw
            lon = lon_raw / 10000000000.0 if abs(lon_raw) > 1000 else lon_raw
            
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                if abs(lat) > 0.001 and abs(lon) > 0.001:
                    coords.append([lat, lon])
        
        if len(coords) < 3:
            return jsonify({'error': '有效座標不足'}), 400
        
        import numpy as np
        from scipy.spatial import ConvexHull
        from sklearn.decomposition import PCA
        
        coords_array = np.array(coords)
        total_orders = len(coords_array)
        
        # === 1. PCA 分析（長寬比）===
        pca = PCA(n_components=2)
        pca.fit(coords_array)
        
        # 主成分的變異數（代表長軸和短軸的長度平方）
        explained_variance = pca.explained_variance_
        aspect_ratio = np.sqrt(explained_variance[0] / explained_variance[1]) if explained_variance[1] > 0 else 1.0
        
        # 主軸方向（主成分向量）
        principal_axis = pca.components_[0]
        angle = np.arctan2(principal_axis[1], principal_axis[0]) * 180 / np.pi
        
        # 判斷方向性
        if -45 <= angle <= 45 or angle > 135 or angle < -135:
            orientation = 'east-west'
        else:
            orientation = 'north-south'
        
        # 計算主軸端點（用於視覺化）
        mean_point = np.mean(coords_array, axis=0)
        axis_length = np.sqrt(explained_variance[0]) * 3  # 3倍標準差
        axis_start = mean_point - principal_axis * axis_length
        axis_end = mean_point + principal_axis * axis_length
        
        # === 2. 凸包分析（密度）===
        try:
            hull = ConvexHull(coords_array)
            hull_area_deg = hull.volume  # 平方度
            
            # 轉換為 km²（1度緯度 ≈ 111 km）
            avg_lat = np.mean(coords_array[:, 0])
            lat_to_km = 111.0
            lon_to_km = 111.0 * np.cos(np.radians(avg_lat))
            hull_area_km = hull_area_deg * lat_to_km * lon_to_km
            
            # 密度（訂單/km²）
            density = total_orders / hull_area_km if hull_area_km > 0 else 0
            
            # 凸包頂點（用於視覺化）
            hull_vertices = coords_array[hull.vertices].tolist()
        except Exception as e:
            print(f"[WARN] 凸包計算失敗: {e}")
            hull_area_km = 0
            density = 0
            hull_vertices = []
        
        # === 3. 檢測是否可能跨河 ===
        # 簡單判斷：如果凸包跨越較大距離，可能跨河
        lat_range = np.max(coords_array[:, 0]) - np.min(coords_array[:, 0])
        lon_range = np.max(coords_array[:, 1]) - np.min(coords_array[:, 1])
        max_range_km = max(lat_range * 111.0, lon_range * 111.0 * np.cos(np.radians(avg_lat)))
        
        likely_crosses_river = max_range_km > 5.0  # 跨度 > 5km 可能跨河
        
        # === 4. 生成建議 ===
        suggestions = {}
        reasoning_parts = []
        
        # 建議 1: 群組排序方法
        if aspect_ratio > 3.0:
            # 長且扁 - 線性分佈
            suggestions['group_order_method'] = 'greedy'
            reasoning_parts.append(f"訂單呈線性分佈（長寬比 {aspect_ratio:.1f}），建議使用 Greedy 快速排序")
        elif aspect_ratio > 2.0:
            suggestions['group_order_method'] = 'sweep'
            reasoning_parts.append(f"訂單呈橢圓分佈（長寬比 {aspect_ratio:.1f}），建議使用 Sweep 避免繞回")
        else:
            suggestions['group_order_method'] = '2opt'
            reasoning_parts.append(f"訂單呈集中分佈（長寬比 {aspect_ratio:.1f}），建議使用 2-opt 最佳化")
        
        # 建議 2: max_group_size
        if total_orders < 50:
            suggestions['max_group_size'] = 20
        elif total_orders < 150:
            if density > 100:
                suggestions['max_group_size'] = 25
            elif density > 50:
                suggestions['max_group_size'] = 30
            else:
                suggestions['max_group_size'] = 35
        elif total_orders < 300:
            if density > 100:
                suggestions['max_group_size'] = 30
            elif density > 50:
                suggestions['max_group_size'] = 35
            else:
                suggestions['max_group_size'] = 40
        else:
            if density > 100:
                suggestions['max_group_size'] = 35
            else:
                suggestions['max_group_size'] = 45
        
        if density > 100:
            reasoning_parts.append(f"訂單密度高（{density:.0f} 訂單/km²），建議較小群組")
        elif density > 50:
            reasoning_parts.append(f"訂單密度中等（{density:.0f} 訂單/km²）")
        else:
            reasoning_parts.append(f"訂單密度低（{density:.0f} 訂單/km²），建議較大群組")
        
        # 建議 3: cluster_radius
        if density > 100:
            suggestions['cluster_radius'] = 0.8
        elif density > 50:
            suggestions['cluster_radius'] = 1.0
        else:
            suggestions['cluster_radius'] = 1.5
        
        if aspect_ratio > 3.0 and likely_crosses_river:
            suggestions['cluster_radius'] = max(0.6, suggestions['cluster_radius'] - 0.3)
            reasoning_parts.append("訂單分散且可能跨河，建議較小的聚類半徑")
        
        # 建議 4: 河流檢測
        if likely_crosses_river:
            suggestions['verification'] = 'geometry'
            suggestions['group_penalty'] = 2.5
            suggestions['inner_penalty'] = 1.8
            reasoning_parts.append(f"訂單跨度 {max_range_km:.1f}km，建議啟用河流檢測")
        else:
            suggestions['verification'] = 'none'
            suggestions['group_penalty'] = 2.0
            suggestions['inner_penalty'] = 1.5
        
        # 建議 5: 其他參數
        if density > 80:
            suggestions['min_samples'] = 4
        else:
            suggestions['min_samples'] = 3
        
        suggestions['metric'] = 'euclidean'
        suggestions['random_state'] = 42
        suggestions['n_init'] = 10
        suggestions['check_highways'] = likely_crosses_river
        
        reasoning = " | ".join(reasoning_parts)
        
        return jsonify({
            'success': True,
            'total_orders': int(total_orders),
            'aspect_ratio': round(float(aspect_ratio), 2),
            'density': round(float(density), 1),
            'orientation': str(orientation),
            'hull_area_km': round(float(hull_area_km), 2),
            'likely_crosses_river': bool(likely_crosses_river),
            'max_range_km': round(float(max_range_km), 1),
            'visualization': {
                'principal_axis': {
                    'start': [float(axis_start[0]), float(axis_start[1])],
                    'end': [float(axis_end[0]), float(axis_end[1])],
                    'angle': round(float(angle), 1)
                },
                'convex_hull': [[float(p[0]), float(p[1])] for p in hull_vertices],
                'center': [float(mean_point[0]), float(mean_point[1])]
            },
            'suggestions': {
                'group_order_method': str(suggestions['group_order_method']),
                'max_group_size': int(suggestions['max_group_size']),
                'cluster_radius': float(suggestions['cluster_radius']),
                'min_samples': int(suggestions['min_samples']),
                'verification': str(suggestions['verification']),
                'group_penalty': float(suggestions['group_penalty']),
                'inner_penalty': float(suggestions['inner_penalty']),
                'metric': str(suggestions['metric']),
                'random_state': int(suggestions['random_state']) if suggestions['random_state'] is not None else None,
                'n_init': int(suggestions['n_init']),
                'check_highways': bool(suggestions['check_highways'])
            },
            'reasoning': str(reasoning)
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'分析失敗: {str(e)}'}), 500


@app.route('/api/test-db', methods=['GET'])
def test_db():
    """測試資料庫連接"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'database': 'bonddb',
            'version': version[0]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/optimize-route-global', methods=['POST'])
def optimize_route_global():
    """全局 TSP 優化路徑（不分組）"""
    data = request.json
    
    # 驗證輸入
    if not data.get('start'):
        return jsonify({'error': '起點必填'}), 400
    if not data.get('order_group'):
        return jsonify({'error': 'order_group 必填'}), 400
    
    start = data['start']
    order_group = data['order_group']
    method = data.get('method', 'ortools')  # valhalla | ortools | lkh
    verification = data.get('verification', 'none')
    penalty = data.get('penalty', 1.5)
    check_highways = data.get('check_highways', False)
    end_point_mode = data.get('end_point_mode', 'last_order')  # 終點模式
    end_point = data.get('end_point')  # 終點座標（手動模式）
    
    print(f"[DEBUG] 全局優化請求: order_group={order_group}, method={method}, start={start}, end_point_mode={end_point_mode}")
    
    try:
        # 從資料庫取得訂單座標
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
        
        cursor.execute(query, (order_group,))
        orders = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if not orders:
            return jsonify({'error': f'找不到 order_group: {order_group} 的訂單'}), 404
        
        print(f"[DEBUG] 找到 {len(orders)} 個訂單")
        
        # 驗證並過濾有效的經緯度
        valid_orders = []
        for order in orders:
            try:
                lat_raw = float(order['latitude'])
                lon_raw = float(order['longitude'])
                
                # 轉換格式
                lat = lat_raw / 10000000000.0 if abs(lat_raw) > 1000 else lat_raw
                lon = lon_raw / 10000000000.0 if abs(lon_raw) > 1000 else lon_raw
                
                # 驗證經緯度範圍
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    if abs(lat) > 0.001 and abs(lon) > 0.001:
                        valid_orders.append({
                            'tracking_number': order['tracking_number'],
                            'lat': lat,
                            'lon': lon
                        })
            except (ValueError, TypeError) as e:
                print(f"[WARN] 跳過無效座標: {order.get('tracking_number')} - {e}")
                continue
        
        if not valid_orders:
            return jsonify({'error': '沒有有效的訂單座標'}), 404
        
        print(f"[DEBUG] 有效訂單: {len(valid_orders)} 個")
        
        # 限制數量
        if len(valid_orders) > 200:
            print(f"[WARN] 訂單數量 {len(valid_orders)} 超過限制，取前 200 個")
            valid_orders = valid_orders[:200]
        
        # 根據方法選擇優化策略
        if method == 'valhalla':
            # 使用 Valhalla Optimized Route API
            print(f"[INFO] 使用 Valhalla Optimized Route API 優化 {len(valid_orders)} 個訂單...")
            
            # 檢查是否有手動終點
            has_manual_endpoint = (end_point_mode == 'manual' and end_point)
            
            try:
                # 準備 locations（包含起點，如果有手動終點也包含）
                locations = [{"lat": start['lat'], "lon": start['lon']}]
                locations.extend([{"lat": o['lat'], "lon": o['lon']} for o in valid_orders])
                
                if has_manual_endpoint:
                    locations.append({"lat": end_point['lat'], "lon": end_point['lon']})
                    print(f"[INFO] 手動終點模式：將終點 ({end_point['lat']}, {end_point['lon']}) 納入 Valhalla 計算")
                
                # 調用 Valhalla optimized_route API
                response = requests.post(
                    'https://valhalla1.openstreetmap.de/optimized_route',
                    json={
                        "locations": locations,
                        "costing": "auto"
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # 提取優化後的順序
                    if 'trip' in result and 'locations' in result['trip']:
                        optimized_locations = result['trip']['locations']
                        # 移除起點（第一個），獲取訂單順序
                        order_indices = [loc.get('original_index', i) - 1 for i, loc in enumerate(optimized_locations) if i > 0]
                        
                        if has_manual_endpoint:
                            # 移除終點索引（最後一個）
                            end_idx = len(valid_orders)  # 終點在 valid_orders 之後
                            order_indices = [i for i in order_indices if i != end_idx]
                        
                        optimized_orders = [valid_orders[i] for i in order_indices if 0 <= i < len(valid_orders)]
                    else:
                        # API 返回格式不符，回退到貪心
                        print("[WARN] Valhalla API 返回格式不符，回退到貪心")
                        if has_manual_endpoint:
                            from tsp_solver import solve_tsp_with_end
                            coords_all = [(start['lat'], start['lon'])] + [(o['lat'], o['lon']) for o in valid_orders] + [(end_point['lat'], end_point['lon'])]
                            route_indices = solve_tsp_with_end(coords_all, method='nearest', start_index=0, end_index=len(coords_all)-1)
                            route_indices = [i - 1 for i in route_indices if 0 < i < len(coords_all) - 1]
                        else:
                            coords_with_start = [(start['lat'], start['lon'])] + [(o['lat'], o['lon']) for o in valid_orders]
                            route_indices = solve_tsp(coords_with_start, method='nearest', start_index=0)
                            route_indices = [i - 1 for i in route_indices if i > 0]
                        optimized_orders = [valid_orders[i] for i in route_indices]
                else:
                    print(f"[ERROR] Valhalla API 失敗: {response.status_code}，回退到貪心")
                    if has_manual_endpoint:
                        from tsp_solver import solve_tsp_with_end
                        coords_all = [(start['lat'], start['lon'])] + [(o['lat'], o['lon']) for o in valid_orders] + [(end_point['lat'], end_point['lon'])]
                        route_indices = solve_tsp_with_end(coords_all, method='nearest', start_index=0, end_index=len(coords_all)-1)
                        route_indices = [i - 1 for i in route_indices if 0 < i < len(coords_all) - 1]
                    else:
                        coords_with_start = [(start['lat'], start['lon'])] + [(o['lat'], o['lon']) for o in valid_orders]
                        route_indices = solve_tsp(coords_with_start, method='nearest', start_index=0)
                        route_indices = [i - 1 for i in route_indices if i > 0]
                    optimized_orders = [valid_orders[i] for i in route_indices]
            
            except Exception as e:
                print(f"[ERROR] Valhalla 優化失敗: {e}，回退到貪心")
                if has_manual_endpoint:
                    from tsp_solver import solve_tsp_with_end
                    coords_all = [(start['lat'], start['lon'])] + [(o['lat'], o['lon']) for o in valid_orders] + [(end_point['lat'], end_point['lon'])]
                    route_indices = solve_tsp_with_end(coords_all, method='nearest', start_index=0, end_index=len(coords_all)-1)
                    route_indices = [i - 1 for i in route_indices if 0 < i < len(coords_all) - 1]
                else:
                    coords_with_start = [(start['lat'], start['lon'])] + [(o['lat'], o['lon']) for o in valid_orders]
                    route_indices = solve_tsp(coords_with_start, method='nearest', start_index=0)
                    route_indices = [i - 1 for i in route_indices if i > 0]
                optimized_orders = [valid_orders[i] for i in route_indices]
        
        elif method in ['ortools', 'lkh']:
            # 使用 TSP 求解器
            print(f"[INFO] 使用 {method.upper()} 優化 {len(valid_orders)} 個訂單...")
            
            # 檢查是否有手動終點
            has_manual_endpoint = (end_point_mode == 'manual' and end_point)
            
            if has_manual_endpoint:
                # 手動終點模式：將終點加入 TSP 求解，並強制其為最後一個點
                print(f"[INFO] 手動終點模式：將終點 ({end_point['lat']}, {end_point['lon']}) 納入 TSP 計算")
                coords_with_start_and_end = [(start['lat'], start['lon'])] + \
                                            [(o['lat'], o['lon']) for o in valid_orders] + \
                                            [(end_point['lat'], end_point['lon'])]
                
                try:
                    from tsp_solver import solve_tsp_with_end
                    # 求解 TSP，強制終點為最後一個
                    end_index = len(coords_with_start_and_end) - 1  # 終點索引
                    route_indices = solve_tsp_with_end(coords_with_start_and_end, method=method, start_index=0, end_index=end_index)
                    
                    # 移除起點索引和終點索引，只保留訂單
                    route_indices = [i - 1 for i in route_indices if 0 < i < end_index]
                    
                    # 按順序排列
                    optimized_orders = [valid_orders[i] for i in route_indices]
                    
                    print(f"[INFO] TSP 求解完成，路徑確保以終點結束")
                
                except Exception as e:
                    print(f"[ERROR] {method.upper()} 求解失敗: {e}，回退到貪心")
                    coords_with_start = [(start['lat'], start['lon'])] + [(o['lat'], o['lon']) for o in valid_orders]
                    route_indices = solve_tsp(coords_with_start, method='nearest', start_index=0)
                    route_indices = [i - 1 for i in route_indices if i > 0]
                    optimized_orders = [valid_orders[i] for i in route_indices]
            else:
                # 普通模式：只包含起點和訂單
                coords_with_start = [(start['lat'], start['lon'])] + [(o['lat'], o['lon']) for o in valid_orders]
                
                try:
                    # 求解 TSP
                    route_indices = solve_tsp(coords_with_start, method=method, start_index=0)
                    
                    # 移除起點索引，調整為訂單索引
                    route_indices = [i - 1 for i in route_indices if i > 0]
                    
                    # 按順序排列
                    optimized_orders = [valid_orders[i] for i in route_indices]
                
                except Exception as e:
                    print(f"[ERROR] {method.upper()} 求解失敗: {e}，回退到貪心")
                    route_indices = solve_tsp(coords_with_start, method='nearest', start_index=0)
                    route_indices = [i - 1 for i in route_indices if i > 0]
                    optimized_orders = [valid_orders[i] for i in route_indices]
        
        else:
            return jsonify({'error': f'未知的優化方法: {method}'}), 400
        
        # 添加序號（全局優化不分組，統一編號）
        result_orders = []
        for seq, order in enumerate(optimized_orders, 1):
            result_orders.append({
                'sequence': seq,
                'group': 'Global',  # 全局優化標記
                'group_sequence': str(seq),  # 直接用數字
                'tracking_number': order['tracking_number'],
                'lat': order['lat'],
                'lon': order['lon']
            })
        
        print(f"[INFO] 全局優化完成，共 {len(result_orders)} 個訂單")
        
        # 處理終點設置
        if end_point_mode == 'manual' and end_point:
            # 手動終點：在路徑末端加入終點標記
            print(f"[INFO] 加入手動終點: ({end_point['lat']}, {end_point['lon']})")
            result_orders.append({
                'sequence': len(result_orders) + 1,
                'group': 'End',
                'group_sequence': str(len(result_orders) + 1),
                'tracking_number': 'ENDPOINT',
                'lat': end_point['lat'],
                'lon': end_point['lon']
            })
        elif end_point_mode == 'farthest':
            # 使用最遠訂單：重新排序確保最遠的在最後
            print(f"[INFO] 調整順序確保最遠訂單在最後...")
            
            # 計算每個訂單距離起點的距離
            import math
            def distance_from_start(order):
                return math.sqrt(
                    (order['lat'] - start['lat'])**2 + 
                    (order['lon'] - start['lon'])**2
                )
            
            # 找出最遠訂單
            farthest_order = max(result_orders, key=distance_from_start)
            farthest_idx = result_orders.index(farthest_order)
            
            print(f"[INFO] 最遠訂單: {farthest_order['tracking_number']} (距離起點 {distance_from_start(farthest_order):.4f})")
            
            # 如果最遠訂單不在最後，移到最後
            if farthest_idx != len(result_orders) - 1:
                result_orders.remove(farthest_order)
                result_orders.append(farthest_order)
                
                # 重新編號
                for i, order in enumerate(result_orders, 1):
                    order['sequence'] = i
                    order['group_sequence'] = str(i)
                
                print(f"[INFO] 已將最遠訂單移至最後")
        
        # 障礙檢測（如果啟用）
        crossings = []
        if verification != 'none':
            print(f"[INFO] 開始障礙檢測（方法: {verification}）...")
            crossings = verify_route_crossings(result_orders, verification, check_highways)
            print(f"[INFO] 檢測完成，發現 {len(crossings)} 處穿越障礙")
        
        return jsonify({
            'success': True,
            'orders': result_orders,
            'shape': '',
            'total_orders': len(result_orders),
            'total_groups': 1,  # 全局優化視為 1 組
            'crossings': crossings,
            'verification_method': verification,
            'optimization_method': method
        })
    
    except Exception as e:
        print(f"[ERROR] 全局優化錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'全局優化錯誤: {str(e)}'}), 500


if __name__ == '__main__':
    # 建立 static 目錄
    os.makedirs('static', exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=8080)


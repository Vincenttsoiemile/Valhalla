#!/usr/bin/env python3
"""
核心路径规划算法模块
包含混合聚类、群组排序、TSP 求解等核心函数

依赖包:
- numpy
- scikit-learn (sklearn)
- scipy
- ortools (可选，用于 OR-Tools TSP 求解器)
- python-tsp (可选，用于 LKH 算法)

安装命令:
pip install numpy scikit-learn scipy ortools python-tsp
"""

import math
import numpy as np
from typing import List, Tuple, Dict, Optional, Callable
from sklearn.cluster import DBSCAN, KMeans
from scipy.spatial import ConvexHull
from sklearn.decomposition import PCA


# ============================================================================
# 1. 距离计算函数
# ============================================================================

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    计算两点之间的欧几里得距离
    
    Args:
        lat1, lon1: 第一个点的经纬度
        lat2, lon2: 第二个点的经纬度
    
    Returns:
        距离（度数单位）
    """
    return math.sqrt((lat2 - lat1)**2 + (lon2 - lon1)**2)


def calculate_distance_matrix(coords: List[Tuple[float, float]], 
                              distance_func: Optional[Callable] = None) -> np.ndarray:
    """
    计算座标间的距离矩阵
    
    Args:
        coords: [(lat, lon), ...] 座标列表
        distance_func: 可选的自定义距离函数 distance_func(i, j, coords) -> float
                      如果提供，将使用此函数计算距离（可包含障碍物惩罚）
    
    Returns:
        距离矩阵 (n x n)
    """
    n = len(coords)
    matrix = np.zeros((n, n))
    
    if distance_func:
        # 使用自定义距离函数（例如考虑障碍物）
        for i in range(n):
            for j in range(i + 1, n):
                dist = distance_func(i, j, coords)
                matrix[i][j] = dist
                matrix[j][i] = dist
    else:
        # 默认：欧几里得距离
        for i in range(n):
            for j in range(i + 1, n):
                lat1, lon1 = coords[i]
                lat2, lon2 = coords[j]
                dist = math.sqrt((lat2 - lat1)**2 + (lon2 - lon1)**2)
                matrix[i][j] = dist
                matrix[j][i] = dist
    
    return matrix


# ============================================================================
# 2. TSP 求解器
# ============================================================================

def greedy_tsp(coords: List[Tuple[float, float]], 
               start_index: int = 0, 
               distance_func: Optional[Callable] = None) -> List[int]:
    """
    贪心最近邻算法求解 TSP
    
    Args:
        coords: [(lat, lon), ...] 座标列表
        start_index: 起点索引（默认 0）
        distance_func: 可选的自定义距离函数（考虑障碍物）
    
    Returns:
        访问顺序的索引列表 [0, 3, 1, 2, ...]
    """
    n = len(coords)
    distance_matrix = calculate_distance_matrix(coords, distance_func)
    
    visited = set([start_index])
    route = [start_index]
    current = start_index
    
    while len(visited) < n:
        best_next = None
        best_dist = float('inf')
        
        for i in range(n):
            if i not in visited:
                dist = distance_matrix[current][i]
                if dist < best_dist:
                    best_dist = dist
                    best_next = i
        
        if best_next is not None:
            route.append(best_next)
            visited.add(best_next)
            current = best_next
    
    return route


def solve_tsp_2opt(coords: List[Tuple[float, float]], 
                   start_index: int = 0, 
                   distance_func: Optional[Callable] = None) -> List[int]:
    """
    使用 2-opt 局部搜索求解 TSP
    
    Args:
        coords: [(lat, lon), ...] 座标列表
        start_index: 起点索引（默认 0）
        distance_func: 可选的自定义距离函数（考虑障碍物）
    
    Returns:
        访问顺序的索引列表
    """
    n = len(coords)
    
    # 先用贪心生成初始解
    route = greedy_tsp(coords, start_index, distance_func)
    distance_matrix = calculate_distance_matrix(coords, distance_func)
    
    def calculate_route_cost(route):
        cost = 0
        for i in range(len(route) - 1):
            cost += distance_matrix[route[i]][route[i+1]]
        return cost
    
    # 2-opt 优化
    improved = True
    max_iterations = 100
    iteration = 0
    
    while improved and iteration < max_iterations:
        improved = False
        iteration += 1
        
        for i in range(1, n - 1):
            for j in range(i + 2, n):
                # 尝试反转 [i, j] 区间
                new_route = route[:i] + route[i:j+1][::-1] + route[j+1:]
                
                old_cost = calculate_route_cost(route)
                new_cost = calculate_route_cost(new_route)
                
                if new_cost < old_cost:
                    route = new_route
                    improved = True
                    break
            
            if improved:
                break
    
    return route


def solve_tsp_ortools(coords: List[Tuple[float, float]], 
                      start_index: int = 0, 
                      distance_func: Optional[Callable] = None) -> List[int]:
    """
    使用 OR-Tools 求解 TSP
    
    Args:
        coords: [(lat, lon), ...] 座标列表
        start_index: 起点索引（默认 0）
        distance_func: 可选的自定义距离函数（考虑障碍物）
    
    Returns:
        访问顺序的索引列表 [0, 3, 1, 2, ...]
    """
    try:
        from ortools.constraint_solver import routing_enums_pb2
        from ortools.constraint_solver import pywrapcp
    except ImportError:
        print("[WARN] OR-Tools 未安装，回退到 2-opt")
        return solve_tsp_2opt(coords, start_index, distance_func)
    
    # 计算距离矩阵（转为整数，OR-Tools 需要整数）
    distance_matrix_float = calculate_distance_matrix(coords, distance_func)
    distance_matrix = (distance_matrix_float * 1000000).astype(int)  # 放大 10^6 倍
    
    n = len(coords)
    
    # 创建路径模型
    manager = pywrapcp.RoutingIndexManager(n, 1, start_index)
    routing = pywrapcp.RoutingModel(manager)
    
    # 定义距离回调
    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return distance_matrix[from_node][to_node]
    
    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
    
    # 设定搜索参数
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_parameters.time_limit.seconds = 5  # 限制 5 秒
    
    # 求解
    solution = routing.SolveWithParameters(search_parameters)
    
    if not solution:
        # 失败时返回贪心顺序
        print("[WARN] OR-Tools 求解失败，使用贪心顺序")
        return greedy_tsp(coords, start_index, distance_func)
    
    # 提取路径
    route = []
    index = routing.Start(0)
    while not routing.IsEnd(index):
        node = manager.IndexToNode(index)
        route.append(node)
        index = solution.Value(routing.NextVar(index))
    
    return route


def solve_tsp(coords: List[Tuple[float, float]], 
              method: str = 'ortools', 
              start_index: int = 0, 
              distance_func: Optional[Callable] = None) -> List[int]:
    """
    统一的 TSP 求解接口
    
    Args:
        coords: [(lat, lon), ...] 座标列表
        method: 'nearest' | 'ortools' | '2opt-inner' | 'lkh'
        start_index: 起点索引（默认 0）
        distance_func: 可选的自定义距离函数（考虑障碍物）
    
    Returns:
        访问顺序的索引列表
    """
    if len(coords) <= 1:
        return list(range(len(coords)))
    
    if method == 'nearest':
        return greedy_tsp(coords, start_index, distance_func)
    elif method == 'ortools':
        return solve_tsp_ortools(coords, start_index, distance_func)
    elif method == '2opt-inner':
        return solve_tsp_2opt(coords, start_index, distance_func)
    else:
        print(f"[WARN] 未知方法 {method}，使用 nearest neighbor")
        return greedy_tsp(coords, start_index, distance_func)


# ============================================================================
# 3. 混合聚类算法（DBSCAN + K-means）
# ============================================================================

def hybrid_clustering(orders: List[Dict], 
                     cluster_radius: float = 1.0,
                     min_samples: int = 3,
                     max_group_size: int = 30,
                     metric: str = 'euclidean',
                     random_state: int = 42,
                     n_init: int = 10) -> Dict[int, List[Dict]]:
    """
    混合聚类算法：DBSCAN（粗分）+ K-means（细分）
    
    Args:
        orders: 订单列表，每个订单包含 'lat', 'lon' 等字段
        cluster_radius: DBSCAN 聚类半径（单位: km）
        min_samples: DBSCAN 最小样本数
        max_group_size: 每组最大订单数（触发 K-means 细分）
        metric: 距离计算方式（'euclidean' | 'haversine' | 'manhattan'）
        random_state: K-means 随机种子
        n_init: K-means 初始化次数
    
    Returns:
        clusters: {cluster_id: [订单列表]}
    """
    # 准备数据
    coords = np.array([[o['lat'], o['lon']] for o in orders])
    n_orders = len(orders)
    
    print(f"[INFO] 开始混合聚类: {n_orders} 个订单")
    
    # === 步骤 1: DBSCAN 聚类（粗分）===
    if metric == 'haversine':
        # Haversine 需要弧度并使用地球半径
        coords_rad = np.radians(coords)
        eps_distance = cluster_radius / 6371.0  # 地球半径 6371 km
        dbscan = DBSCAN(eps=eps_distance, min_samples=min_samples, metric='haversine')
        cluster_labels = dbscan.fit_predict(coords_rad)
        print(f"[INFO] 使用 Haversine 距离，eps={eps_distance:.6f} 弧度")
    else:
        # Euclidean 或 Manhattan：1 度 ≈ 111 km
        eps_distance = cluster_radius / 111.0
        dbscan = DBSCAN(eps=eps_distance, min_samples=min_samples, metric=metric)
        cluster_labels = dbscan.fit_predict(coords)
        print(f"[INFO] 使用 {metric} 距离，eps={eps_distance:.6f} 度")
    
    # 统计结果
    unique_labels = set(cluster_labels)
    n_clusters = len(unique_labels) - (1 if -1 in unique_labels else 0)
    n_noise = list(cluster_labels).count(-1)
    print(f"[INFO] DBSCAN 完成: {n_clusters} 个簇, {n_noise} 个噪声点")
    
    # === 步骤 2: 处理噪声点（分配到最近的簇）===
    noise_indices = np.where(cluster_labels == -1)[0]
    if len(noise_indices) > 0:
        print(f"[INFO] 处理 {len(noise_indices)} 个噪声点...")
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
    
    # 将订单按群组分类
    initial_clusters = {}
    for idx, label in enumerate(cluster_labels):
        if label not in initial_clusters:
            initial_clusters[label] = []
        initial_clusters[label].append(orders[idx])
    
    # === 步骤 3: K-means 细分大群组 ===
    clusters = {}
    cluster_id = 0
    
    for label, group_orders in initial_clusters.items():
        if len(group_orders) <= max_group_size:
            # 群组够小，直接使用
            clusters[cluster_id] = group_orders
            print(f"  群组 {cluster_id}: {len(group_orders)} 个订单（保持）")
            cluster_id += 1
        else:
            # 群组太大，用 K-means 细分
            n_sub_clusters = (len(group_orders) + max_group_size - 1) // max_group_size
            print(f"  群组 {label} 有 {len(group_orders)} 个订单，细分成 {n_sub_clusters} 个子群组...")
            
            sub_coords = np.array([[o['lat'], o['lon']] for o in group_orders])
            kmeans = KMeans(n_clusters=n_sub_clusters, random_state=random_state, n_init=n_init)
            sub_labels = kmeans.fit_predict(sub_coords)
            
            for sub_label in range(n_sub_clusters):
                sub_orders = [group_orders[i] for i in range(len(group_orders)) if sub_labels[i] == sub_label]
                clusters[cluster_id] = sub_orders
                print(f"    子群组 {cluster_id}: {len(sub_orders)} 个订单")
                cluster_id += 1
    
    print(f"[INFO] 混合聚类完成: 最终 {len(clusters)} 个群组")
    return clusters


# ============================================================================
# 4. 群组排序算法
# ============================================================================

def calculate_cluster_centers(clusters: Dict[int, List[Dict]]) -> Dict[int, Tuple[float, float]]:
    """
    计算每个群组的中心点
    
    Args:
        clusters: {cluster_id: [订单列表]}
    
    Returns:
        {cluster_id: (center_lat, center_lon)}
    """
    centers = {}
    for cluster_id, orders in clusters.items():
        avg_lat = sum(o['lat'] for o in orders) / len(orders)
        avg_lon = sum(o['lon'] for o in orders) / len(orders)
        centers[cluster_id] = (avg_lat, avg_lon)
    return centers


def order_clusters_greedy(clusters: Dict[int, List[Dict]], 
                          start_pos: Tuple[float, float],
                          penalty_func: Optional[Callable] = None) -> List[int]:
    """
    贪心算法：从起点开始，每次选择最近的未访问群组
    
    Args:
        clusters: {cluster_id: [订单列表]}
        start_pos: 起点座标 (lat, lon)
        penalty_func: 可选的惩罚函数 penalty_func(from_pos, to_pos) -> float
                     返回额外的惩罚系数（例如跨河惩罚）
    
    Returns:
        群组访问顺序 [cluster_id1, cluster_id2, ...]
    """
    cluster_centers = calculate_cluster_centers(clusters)
    
    visited = set()
    order = []
    current_pos = start_pos
    
    while len(visited) < len(clusters):
        best_cluster = None
        best_cost = float('inf')
        
        for cluster_id in clusters.keys():
            if cluster_id in visited:
                continue
            
            center = cluster_centers[cluster_id]
            dist = calculate_distance(current_pos[0], current_pos[1], center[0], center[1])
            
            cost = dist
            
            # 应用惩罚（如果提供）
            if penalty_func:
                penalty = penalty_func(current_pos, center)
                cost *= penalty
            
            if cost < best_cost:
                best_cost = cost
                best_cluster = cluster_id
        
        if best_cluster is not None:
            order.append(best_cluster)
            visited.add(best_cluster)
            current_pos = cluster_centers[best_cluster]
    
    return order


def order_clusters_sweep(clusters: Dict[int, List[Dict]], 
                        start_pos: Tuple[float, float]) -> List[int]:
    """
    Sweep 算法：智能方向扫描
    
    算法步骤：
    1. 计算每个群组相对起点的极角和距离
    2. 找到距离起点最近的群组作为基准
    3. 判断其他群组在基准线左右两侧的分布
    4. 选择订单较多的一侧作为优先扫描方向
    5. 按极角顺序访问所有群组
    
    Args:
        clusters: {cluster_id: [订单列表]}
        start_pos: 起点座标 (lat, lon)
    
    Returns:
        群组访问顺序 [cluster_id1, cluster_id2, ...]
    """
    cluster_centers = calculate_cluster_centers(clusters)
    
    # 步骤 1: 计算极角和距离
    angles = {}
    distances = {}
    for cluster_id, center in cluster_centers.items():
        dx = center[1] - start_pos[1]
        dy = center[0] - start_pos[0]
        angle = math.atan2(dy, dx)
        dist = calculate_distance(start_pos[0], start_pos[1], center[0], center[1])
        angles[cluster_id] = angle
        distances[cluster_id] = dist
    
    # 步骤 2: 找最近群组
    nearest_cluster = min(clusters.keys(), key=lambda x: distances[x])
    nearest_center = cluster_centers[nearest_cluster]
    start_angle = angles[nearest_cluster]
    
    print(f"[INFO] 最近群组: {nearest_cluster} (距离: {distances[nearest_cluster]:.2f} km)")
    
    # 步骤 3: 判断左右两侧订单数
    left_orders = 0
    right_orders = 0
    
    for cluster_id, center in cluster_centers.items():
        if cluster_id == nearest_cluster:
            continue
        
        # 叉积判断左右
        vec_base_x = nearest_center[1] - start_pos[1]
        vec_base_y = nearest_center[0] - start_pos[0]
        vec_current_x = center[1] - start_pos[1]
        vec_current_y = center[0] - start_pos[0]
        
        cross_product = vec_base_x * vec_current_y - vec_base_y * vec_current_x
        
        order_count = len(clusters[cluster_id])
        if cross_product > 0:
            left_orders += order_count
        else:
            right_orders += order_count
    
    # 步骤 4: 选择扫描方向
    clockwise = (right_orders >= left_orders)
    direction = "顺时针" if clockwise else "逆时针"
    print(f"[INFO] 扫描方向: {direction} (左侧 {left_orders}, 右侧 {right_orders})")
    
    # 步骤 5: 按极角排序
    adjusted_angles = {}
    for cluster_id in clusters.keys():
        angle_diff = angles[cluster_id] - start_angle
        if angle_diff < 0:
            angle_diff += 2 * math.pi
        adjusted_angles[cluster_id] = angle_diff
    
    if clockwise:
        order = sorted(clusters.keys(), key=lambda x: adjusted_angles[x])
    else:
        order = sorted(clusters.keys(), key=lambda x: -adjusted_angles[x])
    
    return order


def order_clusters_2opt(clusters: Dict[int, List[Dict]], 
                       start_pos: Tuple[float, float]) -> List[int]:
    """
    2-opt 优化算法：先用贪心生成初始顺序，再用 2-opt 优化
    
    Args:
        clusters: {cluster_id: [订单列表]}
        start_pos: 起点座标 (lat, lon)
    
    Returns:
        群组访问顺序 [cluster_id1, cluster_id2, ...]
    """
    # 步骤 1: 贪心生成初始顺序
    order = order_clusters_greedy(clusters, start_pos)
    cluster_centers = calculate_cluster_centers(clusters)
    
    print(f"[INFO] 初始顺序: {order}")
    
    # 步骤 2: 2-opt 优化
    def calculate_route_cost(order):
        total = 0
        pos = start_pos
        for cluster_id in order:
            center = cluster_centers[cluster_id]
            total += calculate_distance(pos[0], pos[1], center[0], center[1])
            pos = center
        return total
    
    improved = True
    iteration = 0
    max_iterations = 100
    
    while improved and iteration < max_iterations:
        improved = False
        iteration += 1
        
        for i in range(len(order) - 1):
            for j in range(i + 2, len(order)):
                # 尝试反转 [i+1, j] 区间
                new_order = order[:i+1] + order[i+1:j+1][::-1] + order[j+1:]
                
                old_cost = calculate_route_cost(order)
                new_cost = calculate_route_cost(new_order)
                
                if new_cost < old_cost:
                    order = new_order
                    improved = True
                    print(f"  [2-opt] Iteration {iteration}: {old_cost:.2f} → {new_cost:.2f}")
                    break
            
            if improved:
                break
    
    print(f"[INFO] 2-opt 完成（{iteration} 次迭代）")
    return order


# ============================================================================
# 5. 组内订单排序
# ============================================================================

def order_within_cluster_nearest(orders: List[Dict], 
                                 start_pos: Tuple[float, float],
                                 penalty_func: Optional[Callable] = None) -> List[Dict]:
    """
    组内最近邻排序
    
    Args:
        orders: 订单列表
        start_pos: 当前位置 (lat, lon)
        penalty_func: 可选的惩罚函数 penalty_func(from_pos, to_pos) -> float
    
    Returns:
        排序后的订单列表
    """
    remaining = orders.copy()
    sequence = []
    current_pos = start_pos
    
    while remaining:
        def calculate_cost(o):
            dist = calculate_distance(current_pos[0], current_pos[1], o['lat'], o['lon'])
            
            if penalty_func:
                penalty = penalty_func(current_pos, (o['lat'], o['lon']))
                dist *= penalty
            
            return dist
        
        nearest = min(remaining, key=calculate_cost)
        sequence.append(nearest)
        current_pos = (nearest['lat'], nearest['lon'])
        remaining.remove(nearest)
    
    return sequence


def order_within_cluster_tsp(orders: List[Dict], 
                             start_pos: Tuple[float, float],
                             method: str = 'ortools',
                             distance_func: Optional[Callable] = None) -> List[Dict]:
    """
    组内 TSP 优化排序
    
    Args:
        orders: 订单列表
        start_pos: 当前位置 (lat, lon)
        method: TSP 求解方法 ('nearest' | 'ortools' | '2opt-inner')
        distance_func: 可选的自定义距离函数
    
    Returns:
        排序后的订单列表
    """
    # 准备坐标（加上当前位置作为起点）
    coords_with_start = [start_pos] + [(o['lat'], o['lon']) for o in orders]
    
    try:
        # 求解 TSP
        route_indices = solve_tsp(coords_with_start, method=method, start_index=0, distance_func=distance_func)
        
        # 移除起点索引，调整为订单索引
        route_indices = [i - 1 for i in route_indices if i > 0]
        
        # 按 TSP 顺序排列
        sequence = [orders[i] for i in route_indices]
        
        return sequence
    
    except Exception as e:
        print(f"[ERROR] TSP 求解失败: {e}，回退到最近邻")
        return order_within_cluster_nearest(orders, start_pos)


# ============================================================================
# 6. 完整路径规划流程
# ============================================================================

def plan_route(orders: List[Dict],
               start_pos: Tuple[float, float],
               cluster_params: Dict = None,
               group_order_method: str = 'greedy',
               inner_order_method: str = 'nearest',
               penalty_func: Optional[Callable] = None) -> List[Dict]:
    """
    完整的路径规划流程
    
    Args:
        orders: 订单列表，每个订单需包含 'lat', 'lon', 'tracking_number' 等字段
        start_pos: 起点座标 (lat, lon)
        cluster_params: 聚类参数字典，包含:
            - cluster_radius: float (默认 1.0)
            - min_samples: int (默认 3)
            - max_group_size: int (默认 30)
            - metric: str (默认 'euclidean')
            - random_state: int (默认 42)
            - n_init: int (默认 10)
        group_order_method: 群组排序方法 ('greedy' | 'sweep' | '2opt')
        inner_order_method: 组内排序方法 ('nearest' | 'ortools' | '2opt-inner')
        penalty_func: 可选的惩罚函数（用于障碍物检测）
    
    Returns:
        排序后的订单列表，每个订单增加了以下字段:
            - sequence: 全局序号 (1, 2, 3, ...)
            - group: 群组名称 ('A', 'B', 'C', ...)
            - group_sequence: 组内编号 ('A-01', 'A-02', ...)
    """
    # 默认聚类参数
    if cluster_params is None:
        cluster_params = {}
    
    cluster_radius = cluster_params.get('cluster_radius', 1.0)
    min_samples = cluster_params.get('min_samples', 3)
    max_group_size = cluster_params.get('max_group_size', 30)
    metric = cluster_params.get('metric', 'euclidean')
    random_state = cluster_params.get('random_state', 42)
    n_init = cluster_params.get('n_init', 10)
    
    print("="*80)
    print("开始路径规划")
    print("="*80)
    print(f"订单总数: {len(orders)}")
    print(f"起点: ({start_pos[0]:.6f}, {start_pos[1]:.6f})")
    print(f"聚类参数: radius={cluster_radius}km, min_samples={min_samples}, max_group_size={max_group_size}")
    print(f"群组排序: {group_order_method}, 组内排序: {inner_order_method}")
    print("="*80)
    
    # 步骤 1: 混合聚类
    clusters = hybrid_clustering(
        orders=orders,
        cluster_radius=cluster_radius,
        min_samples=min_samples,
        max_group_size=max_group_size,
        metric=metric,
        random_state=random_state,
        n_init=n_init
    )
    
    # 步骤 2: 群组排序
    if group_order_method == 'sweep':
        cluster_order = order_clusters_sweep(clusters, start_pos)
    elif group_order_method == '2opt':
        cluster_order = order_clusters_2opt(clusters, start_pos)
    else:
        cluster_order = order_clusters_greedy(clusters, start_pos, penalty_func)
    
    print(f"\n群组访问顺序: {cluster_order}")
    
    # 步骤 3: 组内排序
    group_names = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J',
                   'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T',
                   'U', 'V', 'W', 'X', 'Y', 'Z']
    
    result_orders = []
    current_pos = start_pos
    
    for group_idx, cluster_id in enumerate(cluster_order):
        group_name = group_names[group_idx] if group_idx < len(group_names) else f"Z{group_idx-25}"
        group_orders = clusters[cluster_id].copy()
        
        print(f"\n处理群组 {group_name} ({len(group_orders)} 个订单)...")
        
        # 组内排序
        if inner_order_method == 'nearest':
            sequence = order_within_cluster_nearest(group_orders, current_pos, penalty_func)
        else:
            sequence = order_within_cluster_tsp(group_orders, current_pos, inner_order_method)
        
        # 添加到结果，格式：A-01, A-02...
        for seq_num, order in enumerate(sequence, 1):
            result_orders.append({
                'sequence': len(result_orders) + 1,
                'group': group_name,
                'group_sequence': f"{group_name}-{seq_num:02d}",
                'tracking_number': order['tracking_number'],
                'lat': order['lat'],
                'lon': order['lon']
            })
        
        # 更新当前位置
        if sequence:
            current_pos = (sequence[-1]['lat'], sequence[-1]['lon'])
    
    print("\n" + "="*80)
    print(f"路径规划完成！共 {len(result_orders)} 个订单，{len(cluster_order)} 个群组")
    print("="*80)
    
    return result_orders


# ============================================================================
# 7. 智能参数分析
# ============================================================================

def analyze_order_distribution(orders: List[Dict]) -> Dict:
    """
    分析订单分布并提供智能参数建议
    
    Args:
        orders: 订单列表，每个订单包含 'lat', 'lon'
    
    Returns:
        分析结果字典，包含:
            - total_orders: 订单总数
            - aspect_ratio: 长宽比
            - density: 密度 (订单/km²)
            - orientation: 主轴方向 ('east-west' | 'north-south')
            - hull_area_km: 凸包面积 (km²)
            - likely_crosses_river: 是否可能跨河
            - max_range_km: 最大跨度 (km)
            - suggestions: 参数建议字典
            - reasoning: 建议理由
    """
    coords = np.array([[o['lat'], o['lon']] for o in orders])
    total_orders = len(coords)
    
    print(f"\n分析 {total_orders} 个订单的分布...")
    
    # 1. PCA 分析（长宽比）
    pca = PCA(n_components=2)
    pca.fit(coords)
    
    explained_variance = pca.explained_variance_
    aspect_ratio = np.sqrt(explained_variance[0] / explained_variance[1]) if explained_variance[1] > 0 else 1.0
    
    # 主轴方向
    principal_axis = pca.components_[0]
    angle = np.arctan2(principal_axis[1], principal_axis[0]) * 180 / np.pi
    
    if -45 <= angle <= 45 or angle > 135 or angle < -135:
        orientation = 'east-west'
    else:
        orientation = 'north-south'
    
    # 2. 凸包分析（密度）
    try:
        hull = ConvexHull(coords)
        hull_area_deg = hull.volume
        
        avg_lat = np.mean(coords[:, 0])
        lat_to_km = 111.0
        lon_to_km = 111.0 * np.cos(np.radians(avg_lat))
        hull_area_km = hull_area_deg * lat_to_km * lon_to_km
        
        density = total_orders / hull_area_km if hull_area_km > 0 else 0
    except Exception as e:
        print(f"[WARN] 凸包计算失败: {e}")
        hull_area_km = 0
        density = 0
    
    # 3. 检测是否可能跨河
    lat_range = np.max(coords[:, 0]) - np.min(coords[:, 0])
    lon_range = np.max(coords[:, 1]) - np.min(coords[:, 1])
    avg_lat = np.mean(coords[:, 0])
    max_range_km = max(lat_range * 111.0, lon_range * 111.0 * np.cos(np.radians(avg_lat)))
    
    likely_crosses_river = max_range_km > 5.0
    
    # 4. 生成建议
    suggestions = {}
    reasoning_parts = []
    
    # 群组排序方法
    if aspect_ratio > 3.0:
        suggestions['group_order_method'] = 'greedy'
        reasoning_parts.append(f"线性分布（长宽比 {aspect_ratio:.1f}）→ Greedy")
    elif aspect_ratio > 2.0:
        suggestions['group_order_method'] = 'sweep'
        reasoning_parts.append(f"椭圆分布（长宽比 {aspect_ratio:.1f}）→ Sweep")
    else:
        suggestions['group_order_method'] = '2opt'
        reasoning_parts.append(f"集中分布（长宽比 {aspect_ratio:.1f}）→ 2-opt")
    
    # max_group_size
    if total_orders < 50:
        suggestions['max_group_size'] = 20
    elif total_orders < 150:
        suggestions['max_group_size'] = 30 if density > 50 else 35
    else:
        suggestions['max_group_size'] = 35 if density > 100 else 45
    
    # cluster_radius
    if density > 100:
        suggestions['cluster_radius'] = 0.8
    elif density > 50:
        suggestions['cluster_radius'] = 1.0
    else:
        suggestions['cluster_radius'] = 1.5
    
    if aspect_ratio > 3.0 and likely_crosses_river:
        suggestions['cluster_radius'] = max(0.6, suggestions['cluster_radius'] - 0.3)
    
    # 其他参数
    suggestions['min_samples'] = 4 if density > 80 else 3
    suggestions['metric'] = 'euclidean'
    suggestions['random_state'] = 42
    suggestions['n_init'] = 10
    
    reasoning = " | ".join(reasoning_parts)
    
    result = {
        'total_orders': int(total_orders),
        'aspect_ratio': round(float(aspect_ratio), 2),
        'density': round(float(density), 1),
        'orientation': str(orientation),
        'hull_area_km': round(float(hull_area_km), 2),
        'likely_crosses_river': bool(likely_crosses_river),
        'max_range_km': round(float(max_range_km), 1),
        'suggestions': suggestions,
        'reasoning': reasoning
    }
    
    print(f"\n分析结果:")
    print(f"  长宽比: {result['aspect_ratio']}")
    print(f"  密度: {result['density']} 订单/km²")
    print(f"  方向: {result['orientation']}")
    print(f"  凸包面积: {result['hull_area_km']} km²")
    print(f"  最大跨度: {result['max_range_km']} km")
    print(f"  可能跨河: {'是' if result['likely_crosses_river'] else '否'}")
    print(f"\n建议: {result['reasoning']}")
    
    return result


# ============================================================================
# 8. 示例用法
# ============================================================================

if __name__ == '__main__':
    # 示例：创建一些测试订单
    test_orders = [
        {'tracking_number': 'T001', 'lat': 43.6532, 'lon': -79.3832},
        {'tracking_number': 'T002', 'lat': 43.6545, 'lon': -79.3850},
        {'tracking_number': 'T003', 'lat': 43.6520, 'lon': -79.3800},
        {'tracking_number': 'T004', 'lat': 43.6700, 'lon': -79.4000},
        {'tracking_number': 'T005', 'lat': 43.6710, 'lon': -79.4020},
        # ... 更多订单
    ]
    
    start_position = (43.6532, -79.3832)
    
    # 1. 分析订单分布
    analysis = analyze_order_distribution(test_orders)
    
    # 2. 使用建议参数规划路径
    result = plan_route(
        orders=test_orders,
        start_pos=start_position,
        cluster_params=analysis['suggestions'],
        group_order_method=analysis['suggestions']['group_order_method'],
        inner_order_method='nearest'
    )
    
    # 3. 输出结果
    print("\n最终路径:")
    for order in result:
        print(f"{order['sequence']:3d}. {order['group_sequence']:6s} - {order['tracking_number']}")



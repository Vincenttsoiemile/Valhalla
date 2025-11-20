# 核心算法函数汇总

生成时间: 2025-11-07

---

## 1. 混合聚类算法（DBSCAN + K-means）

### 核心函数位置
**文件**: `app.py`  
**函数**: `calculate_route()` (行 118-1078)

### 算法流程

#### 步骤 1: DBSCAN 密度聚类（粗分）

```python
# 准备数据
coords = np.array([[o['lat'], o['lon']] for o in valid_orders])

# 根据 metric 选择距离计算方式
if metric == 'haversine':
    coords_rad = np.radians(coords)
    eps_distance = cluster_radius / 6371.0  # 地球半径 6371 km
    dbscan = DBSCAN(eps=eps_distance, min_samples=min_samples, metric='haversine')
    cluster_labels = dbscan.fit_predict(coords_rad)
else:
    eps_distance = cluster_radius / 111.0  # 1 度 ≈ 111 km
    dbscan = DBSCAN(eps=eps_distance, min_samples=min_samples, metric=metric)
    cluster_labels = dbscan.fit_predict(coords)
```

**参数说明**:
- `cluster_radius`: 聚类半径（单位: km）
- `min_samples`: 最小样本数（形成簇的最小点数）
- `metric`: 距离计算方式（`euclidean` | `haversine` | `manhattan`）

**输出**: 每个订单的初步聚类标签

---

#### 步骤 2: 噪声点处理

```python
noise_indices = np.where(cluster_labels == -1)[0]

if len(noise_indices) > 0:
    for idx in noise_indices:
        point = coords[idx]
        # 找到最近的非噪声点
        valid_clusters = cluster_labels[cluster_labels != -1]
        if len(valid_clusters) > 0:
            distances = [calculate_distance(point[0], point[1], coords[i][0], coords[i][1]) 
                       for i in range(len(coords)) if cluster_labels[i] != -1]
            if distances:
                nearest_idx = [i for i in range(len(coords)) if cluster_labels[i] != -1][np.argmin(distances)]
                cluster_labels[idx] = cluster_labels[nearest_idx]
```

**功能**: 将孤立点（噪声点）分配到最近的聚类中心

---

#### 步骤 3: K-means 细分大群组

```python
for label, orders in initial_clusters.items():
    if len(orders) <= max_group_size:
        # 群组够小，直接使用
        clusters[cluster_id] = orders
        cluster_id += 1
    else:
        # 群组太大，用 K-means 细分
        n_sub_clusters = (len(orders) + max_group_size - 1) // max_group_size
        
        sub_coords = np.array([[o['lat'], o['lon']] for o in orders])
        kmeans = KMeans(n_clusters=n_sub_clusters, random_state=random_state, n_init=n_init)
        sub_labels = kmeans.fit_predict(sub_coords)
        
        for sub_label in range(n_sub_clusters):
            sub_orders = [orders[i] for i in range(len(orders)) if sub_labels[i] == sub_label]
            clusters[cluster_id] = sub_orders
            cluster_id += 1
```

**参数说明**:
- `max_group_size`: 每组最大订单数
- `random_state`: 随机种子（保证可重复性）
- `n_init`: K-means 初始化次数

---

## 2. 群组排序算法

### 2.1 Greedy（贪心最近邻）

**文件**: `app.py`  
**代码位置**: 行 744-792

```python
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
        
        # 考虑跨河惩罚
        if river_detector_for_groups:
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
```

**特点**: 简单快速，适合线性分布

---

### 2.2 Sweep Algorithm（扫描算法）

**文件**: `app.py`  
**代码位置**: 行 568-645

```python
# 步骤 1: 计算极角和距离
cluster_angles = {}
cluster_distances = {}
for label, center in cluster_centers.items():
    dx = center[1] - start_pos[1]
    dy = center[0] - start_pos[0]
    angle = math.atan2(dy, dx)  # 极角（-π 到 π）
    dist = calculate_distance(start_pos[0], start_pos[1], center[0], center[1])
    cluster_angles[label] = angle
    cluster_distances[label] = dist

# 步骤 2: 找最近群组
nearest_cluster = min(clusters.keys(), key=lambda x: cluster_distances[x])
start_angle = cluster_angles[nearest_cluster]

# 步骤 3: 判断左右两侧订单数
left_orders = 0
right_orders = 0

for label, center in cluster_centers.items():
    if label == nearest_cluster:
        continue
    
    # 叉积判断左右
    vec_base_x = nearest_center[1] - start_pos[1]
    vec_base_y = nearest_center[0] - start_pos[0]
    vec_current_x = center[1] - start_pos[1]
    vec_current_y = center[0] - start_pos[0]
    
    cross_product = vec_base_x * vec_current_y - vec_base_y * vec_current_x
    
    order_count = len(clusters[label])
    if cross_product > 0:
        left_orders += order_count
    else:
        right_orders += order_count

# 步骤 4: 选择扫描方向（顺时针 vs 逆时针）
clockwise = (right_orders >= left_orders)

# 步骤 5: 按极角排序
adjusted_angles = {}
for label in clusters.keys():
    angle_diff = cluster_angles[label] - start_angle
    if angle_diff < 0:
        angle_diff += 2 * math.pi
    adjusted_angles[label] = angle_diff

if clockwise:
    cluster_order = sorted(clusters.keys(), key=lambda x: adjusted_angles[x])
else:
    cluster_order = sorted(clusters.keys(), key=lambda x: -adjusted_angles[x])
```

**特点**: 智能方向选择，避免绕回，适合椭圆分布

---

### 2.3 2-opt 优化

**文件**: `app.py`  
**代码位置**: 行 648-741

```python
# 步骤 1: 贪心生成初始顺序
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
        cost = calculate_distance(current_pos[0], current_pos[1], 
                                  cluster_center[0], cluster_center[1])
        
        if cost < best_cost:
            best_cost = cost
            best_cluster = label
    
    if best_cluster is not None:
        cluster_order.append(best_cluster)
        visited_clusters.add(best_cluster)
        current_pos = cluster_centers[best_cluster]

# 步骤 2: 2-opt 局部优化
def calculate_route_cost(order):
    total = 0
    pos = start_pos
    for label in order:
        center = cluster_centers[label]
        total += calculate_distance(pos[0], pos[1], center[0], center[1])
        pos = center
    return total

improved = True
iteration = 0
max_iterations = 100

while improved and iteration < max_iterations:
    improved = False
    iteration += 1
    
    for i in range(len(cluster_order) - 1):
        for j in range(i + 2, len(cluster_order)):
            # 尝试反转 [i+1, j] 区间
            new_order = cluster_order[:i+1] + cluster_order[i+1:j+1][::-1] + cluster_order[j+1:]
            
            old_cost = calculate_route_cost(cluster_order)
            new_cost = calculate_route_cost(new_order)
            
            if new_cost < old_cost:
                cluster_order = new_order
                improved = True
                break
        
        if improved:
            break
```

**特点**: 最佳化路径，适合集中分布

---

## 3. 组内订单排序算法

### 3.1 Nearest Neighbor（最近邻）

**文件**: `app.py`  
**代码位置**: 行 822-848

```python
remaining = group_orders.copy()
group_sequence = []

while remaining:
    # 找最近的订单（考虑障碍惩罚）
    def calculate_cost(o):
        dist = calculate_distance(current_pos[0], current_pos[1], o['lat'], o['lon'])
        
        # 如果启用了障碍检测，检查是否穿越并增加惩罚
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
```

**特点**: 快速，考虑障碍物惩罚

---

### 3.2 TSP 求解器（OR-Tools / 2-opt / LKH）

**文件**: `app.py`  
**代码位置**: 行 850-917

```python
# 准备坐标（加上当前位置作为起点）
coords_with_start = [current_pos] + [(o['lat'], o['lon']) for o in group_orders]

# 定义考虑障碍物的距离函数
def obstacle_aware_distance(i, j, coords):
    lat1, lon1 = coords[i]
    lat2, lon2 = coords[j]
    
    # 基础直线距离
    dist = calculate_distance(lat1, lon1, lat2, lon2)
    
    # 如果启用障碍检测，检查并应用惩罚
    if river_detector:
        result = river_detector.check_obstacle_crossing(
            lat1, lon1, lat2, lon2,
            check_rivers=True,
            check_highways=check_highways
        )
        if result['crosses_any']:
            dist *= inner_penalty
    
    return dist

# 求解 TSP（起点索引 = 0）
route_indices = solve_tsp(
    coords_with_start, 
    method=inner_order_method,  # 'ortools' | '2opt-inner' | 'lkh'
    start_index=0,
    distance_func=obstacle_aware_distance if river_detector else None
)

# 移除起点索引，调整为订单索引
route_indices = [i - 1 for i in route_indices if i > 0]

# 按 TSP 顺序排列
group_sequence = [group_orders[i] for i in route_indices]
```

**特点**: 最优化路径，适合复杂场景

---

## 4. TSP 求解器模块

### 4.1 OR-Tools 求解器

**文件**: `tsp_solver.py`  
**函数**: `solve_tsp_ortools()` (行 46-109)

```python
def solve_tsp_ortools(coords: List[Tuple[float, float]], start_index: int = 0, distance_func: Optional[Callable] = None) -> List[int]:
    from ortools.constraint_solver import routing_enums_pb2
    from ortools.constraint_solver import pywrapcp
    
    # 计算距离矩阵（转为整数，OR-Tools 需要整数）
    distance_matrix_float = calculate_distance_matrix(coords, distance_func)
    distance_matrix = (distance_matrix_float * 1000000).astype(int)
    
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
    search_parameters.time_limit.seconds = 5
    
    # 求解
    solution = routing.SolveWithParameters(search_parameters)
    
    # 提取路径
    route = []
    index = routing.Start(0)
    while not routing.IsEnd(index):
        node = manager.IndexToNode(index)
        route.append(node)
        index = solution.Value(routing.NextVar(index))
    
    return route
```

---

### 4.2 2-opt 局部搜索

**文件**: `tsp_solver.py`  
**函数**: `solve_tsp_2opt()` (行 112-161)

```python
def solve_tsp_2opt(coords: List[Tuple[float, float]], start_index: int = 0, distance_func: Optional[Callable] = None) -> List[int]:
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
```

---

### 4.3 贪心算法

**文件**: `tsp_solver.py`  
**函数**: `greedy_tsp()` (行 164-199)

```python
def greedy_tsp(coords: List[Tuple[float, float]], start_index: int = 0, distance_func: Optional[Callable] = None) -> List[int]:
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
```

---

### 4.4 固定起点和终点的 TSP

**文件**: `tsp_solver.py`  
**函数**: `solve_tsp_with_end()` (行 236-319)

```python
def solve_tsp_with_end(coords: List[Tuple[float, float]], method: str = 'ortools', start_index: int = 0, end_index: int = None) -> List[int]:
    if end_index is None:
        return solve_tsp(coords, method, start_index)
    
    if method == 'ortools':
        from ortools.constraint_solver import pywrapcp
        
        n = len(coords)
        distance_matrix = calculate_distance_matrix(coords)
        distance_matrix_int = [[int(d * 10000) for d in row] for row in distance_matrix]
        
        # 创建路由模型（固定起点和终点）
        manager = pywrapcp.RoutingIndexManager(n, 1, [start_index], [end_index])
        routing = pywrapcp.RoutingModel(manager)
        
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return distance_matrix_int[from_node][to_node]
        
        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        
        # 设置求解参数
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.seconds = 30
        
        # 求解
        solution = routing.SolveWithParameters(search_parameters)
        
        if solution:
            route = []
            index = routing.Start(0)
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                route.append(node)
                index = solution.Value(routing.NextVar(index))
            # 添加终点
            route.append(manager.IndexToNode(index))
            return route
    
    # 回退方案
    return solve_tsp_greedy_with_end(coords, start_index, end_index)
```

---

## 5. 距离计算

### 5.1 欧几里得距离

```python
def calculate_distance(lat1, lon1, lat2, lon2):
    return math.sqrt((lat2 - lat1)**2 + (lon2 - lon1)**2)
```

### 5.2 距离矩阵计算

**文件**: `tsp_solver.py`  
**函数**: `calculate_distance_matrix()` (行 9-43)

```python
def calculate_distance_matrix(coords: List[Tuple[float, float]], 
                              distance_func: Optional[Callable] = None) -> np.ndarray:
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
```

---

## 6. 智能参数建议

### 分析订单分布并提供建议

**文件**: `app.py`  
**函数**: `analyze_distribution()` (行 1183-1410)

```python
# 1. PCA 分析（长宽比）
pca = PCA(n_components=2)
pca.fit(coords_array)

explained_variance = pca.explained_variance_
aspect_ratio = np.sqrt(explained_variance[0] / explained_variance[1])

# 主轴方向
principal_axis = pca.components_[0]
angle = np.arctan2(principal_axis[1], principal_axis[0]) * 180 / np.pi

# 判断方向性
if -45 <= angle <= 45 or angle > 135 or angle < -135:
    orientation = 'east-west'
else:
    orientation = 'north-south'

# 2. 凸包分析（密度）
hull = ConvexHull(coords_array)
hull_area_deg = hull.volume

# 转换为 km²
avg_lat = np.mean(coords_array[:, 0])
lat_to_km = 111.0
lon_to_km = 111.0 * np.cos(np.radians(avg_lat))
hull_area_km = hull_area_deg * lat_to_km * lon_to_km

# 密度（订单/km²）
density = total_orders / hull_area_km

# 3. 检测是否可能跨河
lat_range = np.max(coords_array[:, 0]) - np.min(coords_array[:, 0])
lon_range = np.max(coords_array[:, 1]) - np.min(coords_array[:, 1])
max_range_km = max(lat_range * 111.0, lon_range * 111.0 * np.cos(np.radians(avg_lat)))

likely_crosses_river = max_range_km > 5.0

# 4. 生成建议
if aspect_ratio > 3.0:
    suggestions['group_order_method'] = 'greedy'
elif aspect_ratio > 2.0:
    suggestions['group_order_method'] = 'sweep'
else:
    suggestions['group_order_method'] = '2opt'

if density > 100:
    suggestions['cluster_radius'] = 0.8
elif density > 50:
    suggestions['cluster_radius'] = 1.0
else:
    suggestions['cluster_radius'] = 1.5

if likely_crosses_river:
    suggestions['verification'] = 'geometry'
    suggestions['group_penalty'] = 2.5
    suggestions['inner_penalty'] = 1.8
```

---

## 7. 关键参数说明

### 聚类参数
- `cluster_radius`: 聚类半径（km），控制 DBSCAN 的邻域范围
- `min_samples`: 最小样本数，控制簇的紧密度
- `max_group_size`: 每组最大订单数，触发 K-means 细分
- `metric`: 距离度量（`euclidean` | `haversine` | `manhattan`）
- `random_state`: 随机种子，保证可重复性
- `n_init`: K-means 初始化次数

### 排序参数
- `group_order_method`: 群组排序方法（`greedy` | `sweep` | `2opt`）
- `inner_order_method`: 组内排序方法（`nearest` | `ortools` | `2opt-inner` | `lkh`）

### 障碍物检测参数
- `verification`: 检测方式（`none` | `geometry` | `api`）
- `group_penalty`: 群组间跨河惩罚系数（默认 2.0）
- `inner_penalty`: 组内跨河惩罚系数（默认 1.5）
- `check_highways`: 是否检测高速公路穿越

### 终点模式
- `end_point_mode`: 终点模式（`last_order` | `farthest` | `manual`）
- `end_point`: 手动终点坐标（仅在 `manual` 模式下使用）

---

## 总结

本算法系统采用**分层优化**策略：

1. **第一层（聚类）**: DBSCAN + K-means 混合聚类，将大量订单分成合理大小的群组
2. **第二层（群组排序）**: Greedy/Sweep/2-opt 确定群组访问顺序
3. **第三层（组内排序）**: Nearest/OR-Tools/2-opt 优化每组内的订单顺序
4. **第四层（障碍物优化）**: 考虑河流和高速公路穿越，应用惩罚系数

这种分层方法在保证计算效率的同时，能够处理大规模订单（5000+）并生成高质量的配送路径。



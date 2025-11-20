# 核心算法使用指南

## 文件说明

- **core_routing_algorithms.py**: 核心算法 Python 文件（独立模块）
- **core_algorithms_requirements.txt**: 依赖包列表
- **CORE_ALGORITHMS.md**: 详细算法文档（简体中文）

---

## 安装依赖

```bash
pip install -r core_algorithms_requirements.txt
```

### 必需的包
- `numpy`: 数值计算
- `scikit-learn`: DBSCAN、K-means 聚类算法
- `scipy`: 凸包、PCA 分析

### 可选的包
- `ortools`: Google OR-Tools TSP 求解器（更优化的结果）
- `python-tsp`: TSP 启发式算法库

---

## 快速开始

### 1. 基础使用

```python
from core_routing_algorithms import plan_route, analyze_order_distribution

# 准备订单数据
orders = [
    {'tracking_number': 'T001', 'lat': 43.6532, 'lon': -79.3832},
    {'tracking_number': 'T002', 'lat': 43.6545, 'lon': -79.3850},
    # ... 更多订单
]

# 起点位置
start_pos = (43.6532, -79.3832)

# 规划路径（使用默认参数）
result = plan_route(
    orders=orders,
    start_pos=start_pos
)

# 输出结果
for order in result:
    print(f"{order['sequence']}. {order['group_sequence']} - {order['tracking_number']}")
```

### 2. 使用智能参数建议

```python
from core_routing_algorithms import analyze_order_distribution, plan_route

# 1. 分析订单分布
analysis = analyze_order_distribution(orders)

print(f"建议使用群组排序方法: {analysis['suggestions']['group_order_method']}")
print(f"建议聚类半径: {analysis['suggestions']['cluster_radius']} km")

# 2. 使用建议参数规划路径
result = plan_route(
    orders=orders,
    start_pos=start_pos,
    cluster_params=analysis['suggestions'],
    group_order_method=analysis['suggestions']['group_order_method'],
    inner_order_method='ortools'  # 或 'nearest', '2opt-inner'
)
```

### 3. 自定义参数

```python
result = plan_route(
    orders=orders,
    start_pos=start_pos,
    cluster_params={
        'cluster_radius': 1.5,      # 聚类半径 (km)
        'min_samples': 3,            # DBSCAN 最小样本数
        'max_group_size': 30,        # 每组最大订单数
        'metric': 'euclidean',       # 距离度量
        'random_state': 42,          # 随机种子
        'n_init': 10                 # K-means 初始化次数
    },
    group_order_method='sweep',      # 'greedy' | 'sweep' | '2opt'
    inner_order_method='ortools'     # 'nearest' | 'ortools' | '2opt-inner'
)
```

---

## 核心函数说明

### 1. `plan_route()`
完整的路径规划流程（推荐使用）

**参数**:
- `orders`: 订单列表，每个订单需包含 `'lat'`, `'lon'`, `'tracking_number'`
- `start_pos`: 起点坐标 `(lat, lon)`
- `cluster_params`: 聚类参数字典（可选）
- `group_order_method`: 群组排序方法 `'greedy'` | `'sweep'` | `'2opt'`
- `inner_order_method`: 组内排序方法 `'nearest'` | `'ortools'` | `'2opt-inner'`
- `penalty_func`: 惩罚函数（可选，用于障碍物检测）

**返回**:
排序后的订单列表，每个订单增加:
- `sequence`: 全局序号 (1, 2, 3, ...)
- `group`: 群组名称 ('A', 'B', 'C', ...)
- `group_sequence`: 组内编号 ('A-01', 'A-02', ...)

### 2. `analyze_order_distribution()`
分析订单分布并提供参数建议

**参数**:
- `orders`: 订单列表

**返回**:
分析结果字典，包含:
- `total_orders`: 订单总数
- `aspect_ratio`: 长宽比
- `density`: 密度 (订单/km²)
- `suggestions`: 参数建议字典

### 3. `hybrid_clustering()`
混合聚类算法（DBSCAN + K-means）

**参数**:
- `orders`: 订单列表
- `cluster_radius`: 聚类半径 (km)
- `min_samples`: 最小样本数
- `max_group_size`: 每组最大订单数
- `metric`: 距离度量
- `random_state`: 随机种子
- `n_init`: K-means 初始化次数

**返回**:
`{cluster_id: [订单列表]}`

### 4. `order_clusters_greedy()` / `order_clusters_sweep()` / `order_clusters_2opt()`
群组排序算法

**参数**:
- `clusters`: 聚类结果字典
- `start_pos`: 起点坐标
- `penalty_func`: 惩罚函数（可选）

**返回**:
群组访问顺序 `[cluster_id1, cluster_id2, ...]`

### 5. `solve_tsp()` / `solve_tsp_ortools()` / `solve_tsp_2opt()` / `greedy_tsp()`
TSP 求解器

**参数**:
- `coords`: 坐标列表 `[(lat, lon), ...]`
- `start_index`: 起点索引
- `method`: 求解方法
- `distance_func`: 自定义距离函数（可选）

**返回**:
访问顺序索引列表 `[0, 3, 1, 2, ...]`

---

## 创建 API 示例

### Flask API 示例

```python
from flask import Flask, request, jsonify
from core_routing_algorithms import plan_route, analyze_order_distribution

app = Flask(__name__)

@app.route('/api/plan-route', methods=['POST'])
def api_plan_route():
    data = request.json
    
    # 解析输入
    orders = data.get('orders')  # [{'tracking_number': '...', 'lat': ..., 'lon': ...}, ...]
    start_pos = tuple(data.get('start_pos'))  # [lat, lon]
    
    # 可选参数
    cluster_params = data.get('cluster_params')
    group_order_method = data.get('group_order_method', 'greedy')
    inner_order_method = data.get('inner_order_method', 'nearest')
    
    # 规划路径
    result = plan_route(
        orders=orders,
        start_pos=start_pos,
        cluster_params=cluster_params,
        group_order_method=group_order_method,
        inner_order_method=inner_order_method
    )
    
    return jsonify({
        'success': True,
        'total_orders': len(result),
        'orders': result
    })

@app.route('/api/analyze-distribution', methods=['POST'])
def api_analyze():
    data = request.json
    orders = data.get('orders')
    
    analysis = analyze_order_distribution(orders)
    
    return jsonify(analysis)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

### FastAPI 示例

```python
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Optional
from core_routing_algorithms import plan_route, analyze_order_distribution

app = FastAPI()

class Order(BaseModel):
    tracking_number: str
    lat: float
    lon: float

class RouteRequest(BaseModel):
    orders: List[Order]
    start_pos: List[float]
    cluster_params: Optional[Dict] = None
    group_order_method: str = 'greedy'
    inner_order_method: str = 'nearest'

@app.post('/api/plan-route')
def api_plan_route(req: RouteRequest):
    # 转换为字典
    orders_dict = [o.dict() for o in req.orders]
    start_pos = tuple(req.start_pos)
    
    # 规划路径
    result = plan_route(
        orders=orders_dict,
        start_pos=start_pos,
        cluster_params=req.cluster_params,
        group_order_method=req.group_order_method,
        inner_order_method=req.inner_order_method
    )
    
    return {
        'success': True,
        'total_orders': len(result),
        'orders': result
    }

@app.post('/api/analyze-distribution')
def api_analyze(orders: List[Order]):
    orders_dict = [o.dict() for o in orders]
    analysis = analyze_order_distribution(orders_dict)
    return analysis
```

---

## 参数选择指南

### 群组排序方法 (`group_order_method`)

| 方法 | 特点 | 适用场景 |
|------|------|----------|
| `greedy` | 简单快速 | 线性分布（长宽比 > 3） |
| `sweep` | 智能扫描，避免绕回 | 椭圆分布（长宽比 2-3） |
| `2opt` | 最优化路径 | 集中分布（长宽比 < 2） |

### 组内排序方法 (`inner_order_method`)

| 方法 | 特点 | 计算时间 | 路径质量 |
|------|------|----------|----------|
| `nearest` | 最近邻，简单快速 | 快 | 中等 |
| `ortools` | OR-Tools 求解器 | 中等 | 优秀 |
| `2opt-inner` | 2-opt 局部搜索 | 中等 | 良好 |

### 聚类参数

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| `cluster_radius` | 0.8-1.5 km | 密度高用小值，密度低用大值 |
| `min_samples` | 3-4 | 密度高用 4，密度低用 3 |
| `max_group_size` | 20-45 | 订单少用小值，订单多用大值 |
| `metric` | `'euclidean'` | 通常使用欧几里得距离 |

---

## 性能建议

1. **小规模订单（< 100）**: 
   - 可以使用 `ortools` 或 `2opt-inner` 获得最优路径
   - 建议使用 `2opt` 群组排序

2. **中规模订单（100-1000）**:
   - 建议使用 `ortools` 组内排序 + `sweep` 群组排序
   - 或使用 `nearest` + `greedy` 平衡速度和质量

3. **大规模订单（> 1000）**:
   - 建议使用 `nearest` + `greedy` 保证计算速度
   - 适当减小 `max_group_size` 提高分组效率

---

## 故障排除

### 1. OR-Tools 安装失败
```bash
# 如果 ortools 安装失败，算法会自动回退到 2-opt
# 可以只安装必需的包
pip install numpy scikit-learn scipy
```

### 2. 内存不足
```bash
# 对于超大规模订单（> 5000），建议：
# 1. 增大 max_group_size 减少群组数
# 2. 使用 nearest 而非 ortools
# 3. 分批处理订单
```

### 3. 计算速度慢
```bash
# 优化建议：
# 1. 使用 greedy + nearest 组合
# 2. 减小 max_iterations（2-opt）
# 3. 减小 n_init（K-means）
```

---

## 联系与支持

如有问题，请查看：
- **详细文档**: CORE_ALGORITHMS.md
- **源代码**: core_routing_algorithms.py
- **原始系统**: app.py, tsp_solver.py



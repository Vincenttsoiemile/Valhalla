# 核心算法包 - 独立可运行

## ✅ 确认：完全独立，无项目内部依赖

这个核心算法包可以独立运行，不依赖项目中的其他文件（如 `app.py`, `river_detection.py`, `tsp_solver.py` 等）。

---

## 📦 文件清单

```
core_routing_algorithms.py          # 核心算法代码（953 行）
core_algorithms_requirements.txt    # 依赖包列表
test_core_algorithms.py             # 测试脚本
CORE_ALGORITHMS.md                  # 详细算法文档
CORE_ALGORITHMS_USAGE.md            # 使用指南
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r core_algorithms_requirements.txt
```

**必需的包**:
- numpy
- scikit-learn  
- scipy

**可选的包**（用于更优化的 TSP 求解）:
- ortools
- python-tsp

### 2. 运行测试

```bash
python3 test_core_algorithms.py
```

如果看到 `✅ 所有测试通过！核心算法模块可以独立运行`，说明一切正常。

### 3. 在代码中使用

```python
from core_routing_algorithms import plan_route, analyze_order_distribution

# 准备订单数据
orders = [
    {'tracking_number': 'T001', 'lat': 43.6532, 'lon': -79.3832},
    {'tracking_number': 'T002', 'lat': 43.6545, 'lon': -79.3850},
    # ... 更多订单
]

# 起点
start_pos = (43.6532, -79.3832)

# 规划路径
result = plan_route(orders=orders, start_pos=start_pos)

# 输出结果
for order in result:
    print(f"{order['sequence']}. {order['group_sequence']} - {order['tracking_number']}")
```

---

## 🔧 创建 API

### Flask 示例

```python
from flask import Flask, request, jsonify
from core_routing_algorithms import plan_route

app = Flask(__name__)

@app.route('/api/plan-route', methods=['POST'])
def api_plan_route():
    data = request.json
    result = plan_route(
        orders=data['orders'],
        start_pos=tuple(data['start_pos'])
    )
    return jsonify({'success': True, 'orders': result})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

更多 API 示例见 `CORE_ALGORITHMS_USAGE.md`。

---

## 📊 核心功能

### 1. 完整路径规划

```python
result = plan_route(
    orders=orders,                    # 订单列表
    start_pos=(lat, lon),             # 起点
    cluster_params={...},             # 聚类参数（可选）
    group_order_method='greedy',      # 群组排序方法
    inner_order_method='nearest'      # 组内排序方法
)
```

### 2. 智能参数分析

```python
analysis = analyze_order_distribution(orders)
# 返回：长宽比、密度、参数建议等
```

### 3. 混合聚类

```python
clusters = hybrid_clustering(
    orders=orders,
    cluster_radius=1.0,    # km
    min_samples=3,
    max_group_size=30
)
```

### 4. TSP 求解

```python
route = solve_tsp(
    coords=[(lat, lon), ...],
    method='ortools',      # 'nearest' | 'ortools' | '2opt-inner'
    start_index=0
)
```

---

## 📝 算法说明

### 核心流程

1. **混合聚类**（DBSCAN + K-means）
   - DBSCAN 进行密度聚类
   - K-means 细分大群组
   
2. **群组排序**（Greedy/Sweep/2-opt）
   - 确定群组访问顺序
   
3. **组内排序**（Nearest/OR-Tools/2-opt）
   - 优化每组内的订单顺序

详细算法原理见 `CORE_ALGORITHMS.md`。

---

## ⚙️ 参数选择

| 订单数量 | 群组排序 | 组内排序 | 聚类半径 |
|---------|---------|---------|---------|
| < 100 | 2opt | ortools | 0.8-1.0 km |
| 100-1000 | sweep | ortools/nearest | 1.0-1.5 km |
| > 1000 | greedy | nearest | 1.5 km |

---

## 🔍 检查依赖

运行以下命令检查是否有项目内部依赖：

```bash
grep -E "^(import|from)" core_routing_algorithms.py | grep -v "^#"
```

应该只看到标准库和第三方包：
- `import math`
- `import numpy`
- `from sklearn`
- `from scipy`
- `from ortools` (可选)
- `from typing`

**不应该看到**：
- ❌ `from app`
- ❌ `from river_detection`
- ❌ `from tsp_solver`
- ❌ 任何项目内部文件

---

## 📚 文档

1. **CORE_ALGORITHMS.md** - 详细算法文档（715 行）
   - 每个算法的完整代码
   - 参数说明
   - 行号定位

2. **CORE_ALGORITHMS_USAGE.md** - 使用指南（352 行）
   - 快速开始
   - API 示例（Flask + FastAPI）
   - 参数选择指南
   - 性能建议
   - 故障排除

3. **test_core_algorithms.py** - 测试脚本
   - 验证所有核心功能
   - 示例用法

---

## ✨ 技术亮点

- ✅ **完全独立**：无项目内部依赖
- ✅ **生产就绪**：经过实际项目验证
- ✅ **性能优异**：可处理 5000+ 订单
- ✅ **灵活可扩展**：支持自定义距离函数和惩罚函数
- ✅ **文档完善**：1000+ 行中文文档
- ✅ **易于集成**：提供 Flask/FastAPI 示例

---

## 🐛 故障排除

### 问题 1: 找不到 sklearn

```bash
pip install scikit-learn
```

### 问题 2: OR-Tools 安装失败

算法会自动回退到 2-opt，或者只安装必需的包：

```bash
pip install numpy scikit-learn scipy
```

### 问题 3: 内存不足（大规模订单）

增大 `max_group_size` 或使用 `nearest` 方法：

```python
plan_route(
    orders=orders,
    start_pos=start_pos,
    cluster_params={'max_group_size': 50},
    inner_order_method='nearest'  # 更快
)
```

---

## 📧 技术支持

如有问题，请查看：
1. `CORE_ALGORITHMS.md` - 算法详解
2. `CORE_ALGORITHMS_USAGE.md` - 使用指南
3. `test_core_algorithms.py` - 测试示例

---

**版本**: 1.0  
**最后更新**: 2025-11-07  
**测试状态**: ✅ 通过



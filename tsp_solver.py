#!/usr/bin/env python3
"""TSP 求解器模組 - 支援 OR-Tools 和 python-tsp"""

import math
import numpy as np
from typing import List, Tuple, Dict


def calculate_distance_matrix(coords: List[Tuple[float, float]]) -> np.ndarray:
    """
    計算座標間的距離矩陣（歐幾里得距離）
    
    Args:
        coords: [(lat, lon), ...] 座標列表
    
    Returns:
        距離矩陣 (n x n)
    """
    n = len(coords)
    matrix = np.zeros((n, n))
    
    for i in range(n):
        for j in range(i + 1, n):
            lat1, lon1 = coords[i]
            lat2, lon2 = coords[j]
            # 簡化：使用歐幾里得距離
            dist = math.sqrt((lat2 - lat1)**2 + (lon2 - lon1)**2)
            matrix[i][j] = dist
            matrix[j][i] = dist
    
    return matrix


def solve_tsp_ortools(coords: List[Tuple[float, float]], start_index: int = 0) -> List[int]:
    """
    使用 OR-Tools 求解 TSP
    
    Args:
        coords: [(lat, lon), ...] 座標列表
        start_index: 起點索引（默認 0）
    
    Returns:
        訪問順序的索引列表 [0, 3, 1, 2, ...]
    """
    try:
        from ortools.constraint_solver import routing_enums_pb2
        from ortools.constraint_solver import pywrapcp
    except ImportError:
        raise ImportError("OR-Tools 未安裝，請執行：pip install ortools")
    
    # 計算距離矩陣（轉為整數，OR-Tools 需要整數）
    distance_matrix_float = calculate_distance_matrix(coords)
    distance_matrix = (distance_matrix_float * 1000000).astype(int)  # 放大 10^6 倍
    
    n = len(coords)
    
    # 創建路徑模型
    manager = pywrapcp.RoutingIndexManager(n, 1, start_index)
    routing = pywrapcp.RoutingModel(manager)
    
    # 定義距離回調
    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return distance_matrix[from_node][to_node]
    
    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
    
    # 設定搜尋參數
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
        # 失敗時返回貪心順序
        print("[WARN] OR-Tools 求解失敗，使用貪心順序")
        return list(range(n))
    
    # 提取路徑
    route = []
    index = routing.Start(0)
    while not routing.IsEnd(index):
        node = manager.IndexToNode(index)
        route.append(node)
        index = solution.Value(routing.NextVar(index))
    
    return route


def solve_tsp_2opt(coords: List[Tuple[float, float]], start_index: int = 0) -> List[int]:
    """
    使用 2-opt 局部搜索求解 TSP
    
    Args:
        coords: [(lat, lon), ...] 座標列表
        start_index: 起點索引（默認 0）
    
    Returns:
        訪問順序的索引列表
    """
    n = len(coords)
    
    # 先用貪心生成初始解
    route = greedy_tsp(coords, start_index)
    distance_matrix = calculate_distance_matrix(coords)
    
    def calculate_route_cost(route):
        cost = 0
        for i in range(len(route) - 1):
            cost += distance_matrix[route[i]][route[i+1]]
        return cost
    
    # 2-opt 優化
    improved = True
    max_iterations = 100
    iteration = 0
    
    while improved and iteration < max_iterations:
        improved = False
        iteration += 1
        
        for i in range(1, n - 1):
            for j in range(i + 2, n):
                # 嘗試反轉 [i, j] 區間
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


def greedy_tsp(coords: List[Tuple[float, float]], start_index: int = 0) -> List[int]:
    """
    貪心最近鄰算法
    
    Args:
        coords: [(lat, lon), ...] 座標列表
        start_index: 起點索引（默認 0）
    
    Returns:
        訪問順序的索引列表
    """
    n = len(coords)
    distance_matrix = calculate_distance_matrix(coords)
    
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


def solve_tsp_lkh(coords: List[Tuple[float, float]], start_index: int = 0) -> List[int]:
    """
    使用 python-tsp 的 LKH 近似算法求解 TSP
    
    Args:
        coords: [(lat, lon), ...] 座標列表
        start_index: 起點索引（默認 0）
    
    Returns:
        訪問順序的索引列表
    """
    try:
        from python_tsp.heuristics import solve_tsp_simulated_annealing
    except ImportError:
        print("[WARN] python-tsp 未安裝，回退到 2-opt")
        return solve_tsp_2opt(coords, start_index)
    
    # 計算距離矩陣
    distance_matrix = calculate_distance_matrix(coords)
    
    # 使用模擬退火算法（python-tsp 的 LKH 實現較複雜，這裡用 SA 代替）
    try:
        permutation, distance = solve_tsp_simulated_annealing(distance_matrix)
        
        # 調整順序使其從 start_index 開始
        start_pos = permutation.index(start_index)
        route = permutation[start_pos:] + permutation[:start_pos]
        
        return route
    except Exception as e:
        print(f"[WARN] python-tsp 求解失敗: {e}，回退到 2-opt")
        return solve_tsp_2opt(coords, start_index)


def solve_tsp_with_end(coords: List[Tuple[float, float]], method: str = 'ortools', start_index: int = 0, end_index: int = None) -> List[int]:
    """
    TSP 求解（支援指定終點）- 固定起點和終點的開放式路徑
    
    Args:
        coords: [(lat, lon), ...] 座標列表
        method: 'nearest' | 'ortools' | '2opt-inner' | 'lkh'
        start_index: 起點索引
        end_index: 終點索引（可選）
    
    Returns:
        訪問順序的索引列表（確保從 start_index 開始，end_index 結束）
    """
    if len(coords) <= 1:
        return list(range(len(coords)))
    
    # 如果沒有指定終點，使用原有邏輯
    if end_index is None:
        return solve_tsp(coords, method, start_index)
    
    print(f"[INFO] solve_tsp_with_end: 固定起點 {start_index}，終點 {end_index}")
    
    # 使用 OR-Tools 求解固定起點和終點的路徑
    if method == 'ortools':
        try:
            from ortools.constraint_solver import routing_enums_pb2
            from ortools.constraint_solver import pywrapcp
            
            n = len(coords)
            distance_matrix = calculate_distance_matrix(coords)
            
            # 將浮點距離轉換為整數（乘以 10000）
            distance_matrix_int = [[int(d * 10000) for d in row] for row in distance_matrix]
            
            # 創建路由模型
            manager = pywrapcp.RoutingIndexManager(n, 1, [start_index], [end_index])
            routing = pywrapcp.RoutingModel(manager)
            
            def distance_callback(from_index, to_index):
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                return distance_matrix_int[from_node][to_node]
            
            transit_callback_index = routing.RegisterTransitCallback(distance_callback)
            routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
            
            # 設置求解參數
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
                # 添加終點
                route.append(manager.IndexToNode(index))
                
                print(f"[INFO] OR-Tools 求解成功，路徑長度: {len(route)}")
                print(f"[INFO] 路徑: {route[:10]}...{route[-10:] if len(route) > 10 else ''}")
                return route
            else:
                print("[WARN] OR-Tools 無解，回退到貪心")
                return solve_tsp_greedy_with_end(coords, start_index, end_index)
        
        except Exception as e:
            print(f"[ERROR] OR-Tools 求解失敗: {e}")
            return solve_tsp_greedy_with_end(coords, start_index, end_index)
    
    else:
        # 其他方法：先求解完整 TSP，再調整終點位置
        return solve_tsp_greedy_with_end(coords, start_index, end_index)


def solve_tsp_greedy_with_end(coords: List[Tuple[float, float]], start_index: int, end_index: int) -> List[int]:
    """
    貪心算法求解固定起點和終點的路徑
    """
    n = len(coords)
    distance_matrix = calculate_distance_matrix(coords)
    
    # 從起點開始，貪心訪問所有點（除了終點），最後到終點
    visited = set([start_index, end_index])
    route = [start_index]
    current = start_index
    
    # 訪問除起點和終點外的所有點
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
    
    # 最後到終點
    route.append(end_index)
    
    return route


def solve_tsp(coords: List[Tuple[float, float]], method: str = 'ortools', start_index: int = 0) -> List[int]:
    """
    統一的 TSP 求解接口
    
    Args:
        coords: [(lat, lon), ...] 座標列表
        method: 'nearest' | 'ortools' | '2opt-inner' | 'lkh'
        start_index: 起點索引（默認 0）
    
    Returns:
        訪問順序的索引列表
    """
    if len(coords) <= 1:
        return list(range(len(coords)))
    
    if method == 'nearest':
        return greedy_tsp(coords, start_index)
    elif method == 'ortools':
        return solve_tsp_ortools(coords, start_index)
    elif method == '2opt-inner':
        return solve_tsp_2opt(coords, start_index)
    elif method == 'lkh':
        return solve_tsp_lkh(coords, start_index)
    else:
        print(f"[WARN] 未知方法 {method}，使用 nearest neighbor")
        return greedy_tsp(coords, start_index)


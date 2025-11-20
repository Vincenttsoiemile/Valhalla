"""
Smart Route Planner - 智能路徑規劃演算法
使用開放式 2-opt 和動態 K-means 分組

演算法流程：
Stage 1: 智能分組（動態調整 K-means）
Stage 2: 組別排序與重新命名（2-opt 或嚴格由近到遠）
Stage 3: 預先確定組別起點（減少組間銜接距離）
Stage 4: 組內路徑優化（開放式 2-opt + 可選方向性約束）

作者：Vincent
建立日期：2025-11-19
最後更新：2025-11-20
"""

import numpy as np
from sklearn.cluster import KMeans
from scipy.spatial.distance import cdist
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SmartRoutePlanner:
    """智能路徑規劃器"""

    def __init__(self, max_group_size=15, initial_cluster_radius=0.8, min_cluster_radius=0.3,
                 strict_group_order=False, directional_constraint=False,
                 next_group_linkage='none', linkage_weight=0.5):
        """
        初始化

        Args:
            max_group_size: 每組最大訂單數（嚴格小於此值）
            initial_cluster_radius: 初始群聚半徑
            min_cluster_radius: 最小群聚半徑下限
            strict_group_order: 是否啟用嚴格組別順序（由近到遠，不繞回）
            directional_constraint: 是否啟用單向性約束（組內路徑朝向下一組中心）
            next_group_linkage: 組間銜接策略 ('none', 'weighted', 'virtual_endpoint')
            linkage_weight: 權重式銜接的權重（0.0-1.0）
        """
        self.max_group_size = max_group_size
        self.initial_cluster_radius = initial_cluster_radius
        self.min_cluster_radius = min_cluster_radius
        self.cluster_radius = initial_cluster_radius
        self.strict_group_order = strict_group_order
        self.directional_constraint = directional_constraint
        self.next_group_linkage = next_group_linkage
        self.linkage_weight = linkage_weight

    def calculate_distance(self, point1, point2):
        """計算兩點之間的歐幾里得距離"""
        return np.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

    def calculate_total_distance(self, points, route):
        """計算路徑總距離（開放式）"""
        total = 0
        for i in range(len(route) - 1):
            total += self.calculate_distance(points[route[i]], points[route[i+1]])
        return total

    # ============================================================
    # Stage 1: 智能 K-means 分組（動態調整）
    # ============================================================

    def smart_kmeans_clustering(self, orders):
        """
        智能 K-means 分組，自動調整直到所有組 < max_group_size

        Args:
            orders: 訂單列表，每個訂單包含 {lat, lon, ...}

        Returns:
            groups: 分組結果 {group_id: [order_indices]}
        """
        if len(orders) == 0:
            return {}

        # 提取座標
        coords = np.array([[order['lat'], order['lon']] for order in orders])

        # 初始 K 值
        n_orders = len(orders)
        k = max(1, int(np.ceil(n_orders / self.max_group_size)))

        self.cluster_radius = self.initial_cluster_radius
        iteration = 0
        max_iterations = 20  # 防止無限循環

        logger.info(f"開始智能分組：{n_orders} 個訂單，初始 K={k}")

        while iteration < max_iterations:
            iteration += 1

            # 執行 K-means
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(coords)

            # 統計每組訂單數
            group_sizes = {}
            for i, label in enumerate(labels):
                if label not in group_sizes:
                    group_sizes[label] = []
                group_sizes[label].append(i)

            # 檢查是否所有組都 < max_group_size
            max_size = max(len(indices) for indices in group_sizes.values())

            logger.info(f"迭代 {iteration}: K={k}, cluster_radius={self.cluster_radius:.3f}, "
                       f"最大組大小={max_size}, 組數={len(group_sizes)}")

            if max_size < self.max_group_size:
                # 成功！所有組都符合要求
                logger.info(f"✓ 分組成功！共 {len(group_sizes)} 組")
                return group_sizes

            # 需要調整：降低 cluster_radius 並增加 K
            self.cluster_radius *= 0.85  # 降低 15%

            if self.cluster_radius < self.min_cluster_radius:
                logger.warning(f"cluster_radius 已達下限 {self.min_cluster_radius}")
                self.cluster_radius = self.min_cluster_radius

            k += 1  # 增加組數
            logger.info(f"→ 調整參數：K={k}, cluster_radius={self.cluster_radius:.3f}")

        # 達到最大迭代次數，返回當前結果
        logger.warning(f"達到最大迭代次數 {max_iterations}，使用當前分組結果")
        return group_sizes

    # ============================================================
    # 開放式 2-opt 演算法
    # ============================================================

    def calculate_directional_score(self, points, route, target_point):
        """
        計算路徑的方向性得分（平均距離趨勢）

        方向性定義：路徑上越後面的點，應該離目標點越近

        Args:
            points: 點座標列表
            route: 路徑順序
            target_point: 目標點（下一組中心）

        Returns:
            score: 方向性得分（後半段平均距離 - 前半段平均距離）
                   負數表示有朝向目標的趨勢（越負越好）
        """
        if target_point is None or len(route) < 2:
            return 0.0

        # 計算每個點到目標的距離
        distances = [self.calculate_distance(points[idx], target_point) for idx in route]

        # 分成前半段和後半段
        mid = len(distances) // 2
        first_half_avg = np.mean(distances[:mid]) if mid > 0 else 0
        second_half_avg = np.mean(distances[mid:])

        # 後半段應該更近（距離更小），所以這個值應該是負數
        score = second_half_avg - first_half_avg

        return score

    def open_2opt(self, points, start_point=None, target_point=None, enable_directional=False):
        """
        開放式 2-opt 優化（不形成封閉迴路）

        Args:
            points: 點座標列表 [[lat1, lon1], [lat2, lon2], ...]
            start_point: 起始點座標 [lat, lon]，如果為 None 則使用 points[0]
            target_point: 目標點座標 [lat, lon]（下一組中心點）
            enable_directional: 是否啟用方向性約束

        Returns:
            route: 優化後的訪問順序（索引列表）
        """
        n = len(points)
        if n <= 2:
            return list(range(n))

        # 如果有指定起始點，找出最近的點作為起點
        if start_point is not None:
            distances = [self.calculate_distance(start_point, p) for p in points]
            start_idx = np.argmin(distances)
        else:
            start_idx = 0

        # 建立初始路徑：從起點開始的 Nearest Neighbor
        route = [start_idx]
        remaining = set(range(n)) - {start_idx}

        current = start_idx
        while remaining:
            nearest = min(remaining, key=lambda x: self.calculate_distance(points[current], points[x]))
            route.append(nearest)
            remaining.remove(nearest)
            current = nearest

        # 定義評估函數
        def evaluate_route(r):
            """計算路徑的總成本（距離 + 方向性）"""
            dist = self.calculate_total_distance(points, r)

            if enable_directional and target_point is not None:
                # 加入方向性得分（權重 1.0）
                directional_score = self.calculate_directional_score(points, r, target_point)
                # directional_score = second_half_avg - first_half_avg
                # 如果是負數表示好的方向性（後半段更靠近下一組）
                # 將負數加到成本上會降低總成本
                return dist + directional_score * 1.0
            else:
                return dist

        # 2-opt 優化（開放式）
        improved = True
        max_iterations = 100
        iteration = 0

        while improved and iteration < max_iterations:
            improved = False
            iteration += 1

            for i in range(1, n - 1):  # 起點固定（index 0），從 1 開始優化到倒數第二個
                for j in range(i + 1, n):  # j 可以到最後一個元素
                    # 嘗試反轉 route[i:j+1]
                    new_route = route[:i] + route[i:j+1][::-1] + route[j+1:]

                    # 計算成本（距離 + 方向性）
                    old_cost = evaluate_route(route)
                    new_cost = evaluate_route(new_route)

                    if new_cost < old_cost:
                        route = new_route
                        improved = True

        if enable_directional and target_point is not None:
            logger.info(f"開放式 2-opt (方向性約束) 完成：{iteration} 次迭代")
        else:
            logger.info(f"開放式 2-opt 完成：{iteration} 次迭代")
        return route

    def open_2opt_with_target(self, points, start_point=None, target_point=None, method='weighted', weight=0.5):
        """
        開放式 2-opt 優化（考慮目標終點）

        Args:
            points: 點座標列表 [[lat1, lon1], [lat2, lon2], ...]
            start_point: 起始點座標 [lat, lon]
            target_point: 目標終點座標 [lat, lon]（下一組中心點）
            method: 'weighted' 或 'virtual_endpoint'
            weight: weighted 方法的權重（0.0-1.0）

        Returns:
            route: 優化後的訪問順序（索引列表）
        """
        n = len(points)
        if n <= 2:
            return list(range(n))

        # 如果沒有目標點，使用標準 2-opt
        if target_point is None:
            return self.open_2opt(points, start_point)

        # 方案 2：虛擬終點法
        if method == 'virtual_endpoint':
            # 將目標點作為虛擬點添加到列表末尾
            extended_points = points + [target_point]

            # 找出最靠近起點的點作為起點
            if start_point is not None:
                distances = [self.calculate_distance(start_point, p) for p in points]
                start_idx = np.argmin(distances)
            else:
                start_idx = 0

            # 建立初始路徑：從起點到虛擬終點的 Nearest Neighbor
            route = [start_idx]
            remaining = set(range(n)) - {start_idx}  # 不包含虛擬點

            current = start_idx
            while remaining:
                nearest = min(remaining, key=lambda x: self.calculate_distance(extended_points[current], extended_points[x]))
                route.append(nearest)
                remaining.remove(nearest)
                current = nearest

            # 添加虛擬終點（索引 n）
            route.append(n)

            # 2-opt 優化（包含虛擬終點）
            improved = True
            max_iterations = 100
            iteration = 0

            while improved and iteration < max_iterations:
                improved = False
                iteration += 1

                # 虛擬終點固定在最後，不參與交換
                for i in range(1, n - 1):  # 起點固定
                    for j in range(i + 1, n):  # 只優化到倒數第二個真實點
                        new_route = route[:i] + route[i:j+1][::-1] + route[j+1:]

                        old_dist = self.calculate_total_distance(extended_points, route)
                        new_dist = self.calculate_total_distance(extended_points, new_route)

                        if new_dist < old_dist:
                            route = new_route
                            improved = True

            # 移除虛擬終點，返回實際路徑
            final_route = [idx for idx in route if idx < n]
            logger.info(f"虛擬終點法 2-opt 完成：{iteration} 次迭代")
            return final_route

        # 方案 1：權重法
        elif method == 'weighted':
            # 找出最靠近起點的點作為起點
            if start_point is not None:
                distances = [self.calculate_distance(start_point, p) for p in points]
                start_idx = np.argmin(distances)
            else:
                start_idx = 0

            # 建立初始路徑：Nearest Neighbor
            route = [start_idx]
            remaining = set(range(n)) - {start_idx}

            current = start_idx
            while remaining:
                nearest = min(remaining, key=lambda x: self.calculate_distance(points[current], points[x]))
                route.append(nearest)
                remaining.remove(nearest)
                current = nearest

            # 定義加權距離計算函數
            def calculate_weighted_distance(route_seq):
                # 組內總距離
                internal_dist = self.calculate_total_distance(points, route_seq)
                # 最後一個點到目標點的距離
                last_to_target = self.calculate_distance(points[route_seq[-1]], target_point)
                # 加權總距離
                return internal_dist + weight * last_to_target

            # 2-opt 優化（使用加權距離）
            improved = True
            max_iterations = 100
            iteration = 0

            while improved and iteration < max_iterations:
                improved = False
                iteration += 1

                for i in range(1, n - 1):
                    for j in range(i + 1, n):
                        new_route = route[:i] + route[i:j+1][::-1] + route[j+1:]

                        old_dist = calculate_weighted_distance(route)
                        new_dist = calculate_weighted_distance(new_route)

                        if new_dist < old_dist:
                            route = new_route
                            improved = True

            logger.info(f"權重法 2-opt 完成：{iteration} 次迭代, weight={weight}")
            return route

        else:
            # 未知方法，使用標準 2-opt
            logger.warning(f"未知的組間銜接方法: {method}，使用標準 2-opt")
            return self.open_2opt(points, start_point)

    # ============================================================
    # Stage 2: 組別排序與重新命名
    # ============================================================

    def sort_and_rename_groups(self, groups, orders, start_point):
        """
        排序組別並重新命名為 A, B, C, ...
        根據 strict_group_order 選擇排序策略

        Args:
            groups: 分組結果 {group_id: [order_indices]}
            orders: 訂單列表
            start_point: 用戶起始點 [lat, lon]

        Returns:
            sorted_groups: 排序後的組別 {'A': [order_indices], 'B': [...], ...}
        """
        # 計算各組中心點
        group_centers = {}
        for group_id, order_indices in groups.items():
            lats = [orders[i]['lat'] for i in order_indices]
            lons = [orders[i]['lon'] for i in order_indices]
            center = [np.mean(lats), np.mean(lons)]
            group_centers[group_id] = center

        # 準備中心點列表
        group_ids = list(groups.keys())
        centers = [group_centers[gid] for gid in group_ids]

        logger.info(f"Stage 2: 排序 {len(group_ids)} 個組別的中心點")

        # 根據 strict_group_order 選擇排序策略
        if self.strict_group_order:
            # 嚴格組別順序：按照距離起點由近到遠排序（不繞回）
            logger.info("  使用嚴格組別順序（由近到遠，不繞回）")

            # 計算每組中心點到起點的距離
            distances_to_start = []
            for i, gid in enumerate(group_ids):
                center = centers[i]
                dist = self.calculate_distance(start_point, center)
                distances_to_start.append((i, dist))

            # 按距離排序（由近到遠）
            distances_to_start.sort(key=lambda x: x[1])
            optimal_route = [idx for idx, dist in distances_to_start]

            # 記錄排序結果
            for i, (idx, dist) in enumerate(distances_to_start):
                logger.info(f"  第 {i+1} 組: 距起點 {dist:.6f}")
        else:
            # 使用開放式 2-opt 排序組別（優化總距離）
            logger.info("  使用 2-opt 優化（總距離最小）")
            optimal_route = self.open_2opt(centers, start_point)

        # 根據優化結果重新命名組別
        group_labels = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        sorted_groups = {}

        for i, route_idx in enumerate(optimal_route):
            original_group_id = group_ids[route_idx]
            # A-Z 用字母，超過 Z 後用 Z1, Z2, Z3...
            if i < len(group_labels):
                new_label = group_labels[i]
            else:
                new_label = f"Z{i - len(group_labels) + 1}"
            sorted_groups[new_label] = groups[original_group_id]
            logger.info(f"  組別 {original_group_id} → {new_label} ({len(groups[original_group_id])} 個訂單)")

        return sorted_groups

    # ============================================================
    # Stage 3: 預先確定組別起點
    # ============================================================

    def determine_group_entry_points(self, sorted_groups, orders, start_point):
        """
        預先確定每個組的起點（進入點）

        邏輯：
        - A組起點：離用戶起點最近的訂單
        - B組起點：離 A組中心點最近的訂單
        - C組起點：離 B組中心點最近的訂單
        - ...

        Args:
            sorted_groups: 排序後的組別 {'A': [order_indices], 'B': [...], ...}
            orders: 訂單列表
            start_point: 用戶起始點 [lat, lon]

        Returns:
            group_entry_points: 每組的起點 {'A': entry_point, 'B': entry_point, ...}
                               entry_point = [lat, lon] 座標
            group_entry_indices: 每組起點在該組內的索引 {'A': local_idx, 'B': local_idx, ...}
        """
        group_labels = sorted(sorted_groups.keys())

        # 計算所有組的中心點
        group_centers = {}
        for group_label in group_labels:
            order_indices = sorted_groups[group_label]
            if len(order_indices) > 0:
                lats = [orders[i]['lat'] for i in order_indices]
                lons = [orders[i]['lon'] for i in order_indices]
                group_centers[group_label] = [np.mean(lats), np.mean(lons)]

        group_entry_points = {}
        group_entry_indices = {}
        reference_point = start_point

        for group_label in group_labels:
            order_indices = sorted_groups[group_label]

            if len(order_indices) == 0:
                continue

            # 提取該組所有訂單的座標
            group_coords = [[orders[i]['lat'], orders[i]['lon']] for i in order_indices]

            # 找出離參考點最近的訂單
            distances = [self.calculate_distance(reference_point, coord) for coord in group_coords]
            closest_idx = np.argmin(distances)

            # 記錄起點
            group_entry_points[group_label] = group_coords[closest_idx]
            group_entry_indices[group_label] = closest_idx

            logger.info(f"  {group_label} 組起點: 局部索引 {closest_idx}, 距參考點 {distances[closest_idx]:.6f}")

            # 下一組的參考點 = 當前組的中心點
            reference_point = group_centers[group_label]

        return group_entry_points, group_entry_indices

    # ============================================================
    # Stage 4: 組內路徑優化
    # ============================================================

    def optimize_within_groups(self, sorted_groups, orders, start_point, group_entry_indices=None, group_entry_points=None):
        """
        使用開放式 2-opt 優化每組內的訂單順序

        Args:
            sorted_groups: 排序後的組別 {'A': [order_indices], 'B': [...], ...}
            orders: 訂單列表
            start_point: 用戶起始點 [lat, lon]
            group_entry_indices: 每組的起點索引（局部） {'A': idx, 'B': idx, ...}
            group_entry_points: 每組的起點座標 {'A': [lat, lon], 'B': [lat, lon], ...}

        Returns:
            final_route: 最終的全局訂單序列 [order_idx1, order_idx2, ...]
        """
        final_route = []
        current_point = start_point

        group_labels = sorted(sorted_groups.keys())

        # 計算所有組的中心點（用於 linkage）
        group_centers = {}
        if self.next_group_linkage != 'none':
            for group_label in group_labels:
                order_indices = sorted_groups[group_label]
                if len(order_indices) > 0:
                    lats = [orders[i]['lat'] for i in order_indices]
                    lons = [orders[i]['lon'] for i in order_indices]
                    group_centers[group_label] = [np.mean(lats), np.mean(lons)]

        for idx, group_label in enumerate(group_labels):
            order_indices = sorted_groups[group_label]

            if len(order_indices) == 0:
                continue

            # 提取該組的座標
            group_coords = [[orders[i]['lat'], orders[i]['lon']] for i in order_indices]

            # 確定起點（如果有預先確定的起點）
            fixed_start_idx = None
            if group_entry_indices and group_label in group_entry_indices:
                fixed_start_idx = group_entry_indices[group_label]
                # 使用固定起點的座標
                if group_entry_points and group_label in group_entry_points:
                    current_point = group_entry_points[group_label]

            # 確定目標點
            target_point = None
            if idx < len(group_labels) - 1:
                next_group_label = group_labels[idx + 1]

                # directionalConstraint: 目標點 = 下一組的起點（如果有）
                if self.directional_constraint and group_entry_points and next_group_label in group_entry_points:
                    target_point = group_entry_points[next_group_label]
                    logger.info(f"  方向性目標: 下一組({next_group_label})的起點")
                # linkage: 目標點 = 下一組的中心點
                elif self.next_group_linkage != 'none' and next_group_label in group_centers:
                    target_point = group_centers[next_group_label]
                    logger.info(f"  銜接目標: 下一組({next_group_label})的中心點")

            # 如果有固定起點，使用該點座標作為 start_point
            # 這樣 open_2opt 會自動選擇它作為起點
            optimization_start_point = current_point
            if fixed_start_idx is not None:
                optimization_start_point = group_coords[fixed_start_idx]
                logger.info(f"  使用固定起點: 局部索引 {fixed_start_idx}")

            # 選擇優化方法
            if self.next_group_linkage != 'none' and target_point is not None:
                # 使用組間銜接優化（weighted 或 virtual_endpoint）
                logger.info(f"Stage 4: 優化 {group_label} 組（{len(order_indices)} 個訂單）- {self.next_group_linkage} 銜接")
                local_route = self.open_2opt_with_target(
                    points=group_coords,
                    start_point=optimization_start_point,
                    target_point=target_point,
                    method=self.next_group_linkage,
                    weight=self.linkage_weight
                )
            else:
                # 使用標準 2-opt（可能帶方向性約束）
                if self.directional_constraint and target_point is not None:
                    logger.info(f"Stage 4: 優化 {group_label} 組（{len(order_indices)} 個訂單）- 方向性約束")
                else:
                    logger.info(f"Stage 4: 優化 {group_label} 組（{len(order_indices)} 個訂單）- 標準 2-opt")

                local_route = self.open_2opt(
                    points=group_coords,
                    start_point=optimization_start_point,
                    target_point=target_point,
                    enable_directional=self.directional_constraint
                )

            # 轉換為全局索引
            global_indices = [order_indices[i] for i in local_route]
            final_route.extend(global_indices)

            # 更新下一組的起始點為當前組的最後一個訂單
            last_order_idx = global_indices[-1]
            current_point = [orders[last_order_idx]['lat'], orders[last_order_idx]['lon']]

        logger.info(f"Stage 3 完成：共 {len(final_route)} 個訂單")
        return final_route

    # ============================================================
    # 主函數：整合所有 Stage
    # ============================================================

    def plan_route(self, orders, start_point):
        """
        智能路徑規劃主函數

        Args:
            orders: 訂單列表 [{lat, lon, ...}, ...]
            start_point: 用戶起始點 {lat, lon} 或 [lat, lon]

        Returns:
            result: {
                'route': [order_idx1, order_idx2, ...],  # 最終路徑
                'groups': {'A': [indices], 'B': [...], ...},  # 分組結果
                'total_distance': float,  # 總距離
                'metadata': {...}  # 其他資訊
            }
        """
        logger.info("=" * 60)
        logger.info("開始智能路徑規劃")
        logger.info("=" * 60)

        # 處理起始點格式
        if isinstance(start_point, dict):
            start_pt = [start_point['lat'], start_point['lon']]
        else:
            start_pt = start_point

        # Stage 1: 智能分組
        logger.info("\n[Stage 1] 智能 K-means 分組")
        groups = self.smart_kmeans_clustering(orders)

        # Stage 2: 組別排序與重新命名
        logger.info("\n[Stage 2] 組別排序與重新命名")
        sorted_groups = self.sort_and_rename_groups(groups, orders, start_pt)

        # Stage 3: 預先確定組別起點
        logger.info("\n[Stage 3] 預先確定組別起點")
        group_entry_points, group_entry_indices = self.determine_group_entry_points(sorted_groups, orders, start_pt)

        # Stage 4: 組內路徑優化
        logger.info("\n[Stage 4] 組內路徑優化")
        final_route = self.optimize_within_groups(sorted_groups, orders, start_pt,
                                                  group_entry_indices=group_entry_indices,
                                                  group_entry_points=group_entry_points)

        # 計算總距離
        total_distance = 0
        current = start_pt
        for order_idx in final_route:
            order_point = [orders[order_idx]['lat'], orders[order_idx]['lon']]
            total_distance += self.calculate_distance(current, order_point)
            current = order_point

        logger.info("=" * 60)
        logger.info(f"路徑規劃完成！總距離：{total_distance:.2f}")
        logger.info("=" * 60)

        return {
            'route': final_route,
            'groups': sorted_groups,
            'total_distance': total_distance,
            'metadata': {
                'n_orders': len(orders),
                'n_groups': len(sorted_groups),
                'max_group_size': self.max_group_size,
                'final_cluster_radius': self.cluster_radius
            }
        }


# ============================================================
# 測試函數
# ============================================================

if __name__ == "__main__":
    # 測試資料
    test_orders = [
        {'lat': 24.1 + i*0.01, 'lon': 120.6 + i*0.01, 'id': f'order_{i}'}
        for i in range(50)
    ]

    test_start = {'lat': 24.1, 'lon': 120.6}

    # 建立規劃器
    planner = SmartRoutePlanner(max_group_size=15, initial_cluster_radius=0.8)

    # 執行規劃
    result = planner.plan_route(test_orders, test_start)

    print("\n最終結果：")
    print(f"  路徑長度：{len(result['route'])} 個訂單")
    print(f"  組數：{len(result['groups'])}")
    print(f"  總距離：{result['total_distance']:.2f}")
    print(f"\n各組訂單數：")
    for label, indices in result['groups'].items():
        print(f"    {label} 組：{len(indices)} 個訂單")

#!/usr/bin/env python3
"""地理障礙檢測模組（河流 + 高速公路）"""

import json
import requests
from shapely.geometry import LineString, Point
from shapely import geometry
from shapely.strtree import STRtree
import time

class ObstacleDetector:
    def __init__(self, rivers_data_file='rivers_data.json', highways_data_file='highways_data.json'):
        """初始化障礙檢測器"""
        self.rivers = []
        self.highways = []
        self.rivers_tree = None  # 空間索引
        self.highways_tree = None  # 空間索引
        self.load_rivers(rivers_data_file)
        self.load_highways(highways_data_file)
    
    @staticmethod
    def get_instance(rivers_data_file='rivers_data.json', highways_data_file='highways_data.json'):
        """獲取單例實例（避免重複載入）"""
        if not hasattr(ObstacleDetector, '_instance'):
            ObstacleDetector._instance = ObstacleDetector(rivers_data_file, highways_data_file)
        return ObstacleDetector._instance
    
    def load_rivers(self, filename):
        """載入河流幾何數據"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 建立節點字典
            nodes = {}
            for element in data['elements']:
                if element['type'] == 'node':
                    nodes[element['id']] = (element['lon'], element['lat'])
            
            # 建立河流線段
            for element in data['elements']:
                if element['type'] == 'way' and 'nodes' in element:
                    coords = []
                    for node_id in element['nodes']:
                        if node_id in nodes:
                            coords.append(nodes[node_id])
                    
                    if len(coords) >= 2:
                        self.rivers.append(LineString(coords))
            
            print(f"[INFO] 載入 {len(self.rivers)} 條河流線段")

            # 建立空間索引（大幅提升查詢性能）
            if self.rivers:
                print(f"[INFO] 建立河流空間索引...")
                self.rivers_tree = STRtree(self.rivers)
                print(f"[INFO] 空間索引建立完成")

        except FileNotFoundError:
            print(f"[WARN] 找不到河流數據檔案: {filename}")
            self.rivers = []
        except Exception as e:
            print(f"[ERROR] 載入河流數據失敗: {e}")
            self.rivers = []
    
    def load_highways(self, filename):
        """載入高速公路幾何數據"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 建立節點字典
            nodes = {}
            for element in data['elements']:
                if element['type'] == 'node':
                    nodes[element['id']] = (element['lon'], element['lat'])
            
            # 建立高速公路線段
            for element in data['elements']:
                if element['type'] == 'way' and 'nodes' in element:
                    coords = []
                    for node_id in element['nodes']:
                        if node_id in nodes:
                            coords.append(nodes[node_id])
                    
                    if len(coords) >= 2:
                        self.highways.append(LineString(coords))
            
            print(f"[INFO] 載入 {len(self.highways)} 條高速公路線段")

            # 建立空間索引（大幅提升查詢性能）
            if self.highways:
                print(f"[INFO] 建立高速公路空間索引...")
                self.highways_tree = STRtree(self.highways)
                print(f"[INFO] 空間索引建立完成")

        except FileNotFoundError:
            print(f"[WARN] 找不到高速公路數據檔案: {filename}")
            self.highways = []
        except Exception as e:
            print(f"[ERROR] 載入高速公路數據失敗: {e}")
            self.highways = []
    
    def check_crossing_geometry(self, lat1, lon1, lat2, lon2):
        """方法 2：使用河流幾何數據檢查是否跨河（空間索引優化版）"""
        if not self.rivers or not self.rivers_tree:
            return False

        # 建立訂單間的直線
        line = LineString([(lon1, lat1), (lon2, lat2)])

        # 使用空間索引快速查詢可能相交的河流索引（性能提升 100-1000 倍）
        possible_indices = self.rivers_tree.query(line)

        # 精確檢查是否真的相交
        for idx in possible_indices:
            if line.intersects(self.rivers[idx]):
                return True

        return False
    
    def check_highway_crossing(self, lat1, lon1, lat2, lon2):
        """檢查是否跨越高速公路（空間索引優化版）"""
        if not self.highways or not self.highways_tree:
            return False

        # 建立訂單間的直線
        line = LineString([(lon1, lat1), (lon2, lat2)])

        # 使用空間索引快速查詢可能相交的高速公路索引（性能提升 100-1000 倍）
        possible_indices = self.highways_tree.query(line)

        # 精確檢查是否真的相交
        for idx in possible_indices:
            if line.intersects(self.highways[idx]):
                return True

        return False
    
    def check_obstacle_crossing(self, lat1, lon1, lat2, lon2, check_rivers=True, check_highways=True):
        """檢查是否跨越障礙（河流 + 高速公路）"""
        crosses_river = False
        crosses_highway = False
        
        if check_rivers:
            crosses_river = self.check_crossing_geometry(lat1, lon1, lat2, lon2)
        
        if check_highways:
            crosses_highway = self.check_highway_crossing(lat1, lon1, lat2, lon2)
        
        return {
            'crosses_river': crosses_river,
            'crosses_highway': crosses_highway,
            'crosses_any': crosses_river or crosses_highway
        }
    
    def check_crossing_api(self, lat1, lon1, lat2, lon2):
        """方法 3：使用 Valhalla API 檢查實際路線是否跨河"""
        try:
            # 調用 Valhalla route API
            url = "https://valhalla1.openstreetmap.de/route"
            
            payload = {
                "locations": [
                    {"lat": lat1, "lon": lon1},
                    {"lat": lat2, "lon": lon2}
                ],
                "costing": "auto",
                "directions_options": {
                    "units": "kilometers"
                }
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # 檢查 maneuvers 中是否有橋樑標記
                if 'trip' in data and 'legs' in data['trip']:
                    for leg in data['trip']['legs']:
                        if 'maneuvers' in leg:
                            for maneuver in leg['maneuvers']:
                                # 檢查是否提到橋樑或跨河關鍵字
                                instruction = maneuver.get('instruction', '').lower()
                                if any(keyword in instruction for keyword in ['bridge', 'cross', 'river']):
                                    return True
                                
                                # 檢查道路屬性
                                if maneuver.get('type') == 8:  # type 8 = bridge
                                    return True
                
                return False
            else:
                print(f"[WARN] Valhalla API 返回錯誤: {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            print(f"[WARN] Valhalla API 超時")
            return None
        except Exception as e:
            print(f"[ERROR] API 調用失敗: {e}")
            return None


def verify_route_crossings(orders, verification_method='none', check_highways=False):
    """驗證路線中的障礙穿越情況（河流 + 高速公路）"""
    if verification_method == 'none':
        return []

    detector = ObstacleDetector.get_instance()
    crossings = []

    if verification_method == 'geometry':
        # 方法 2：幾何檢測（河流 + 高速公路）使用空間索引優化
        print(f"[INFO] 使用空間索引進行幾何檢測 ({len(orders) - 1} 對連接)")

        for i in range(len(orders) - 1):
            order1 = orders[i]
            order2 = orders[i + 1]

            result = detector.check_obstacle_crossing(
                order1['lat'], order1['lon'],
                order2['lat'], order2['lon'],
                check_rivers=True,
                check_highways=check_highways
            )

            if result['crosses_any']:
                crossing_info = {
                    'from': order1['tracking_number'],
                    'to': order2['tracking_number'],
                    'method': 'geometry',
                    'crosses_river': result['crosses_river'],
                    'crosses_highway': result['crosses_highway']
                }
                crossings.append(crossing_info)
    
    elif verification_method == 'api':
        # 方法 3：API 實際路線檢測（限制數量以避免太慢）
        max_checks = min(100, len(orders) - 1)  # 最多檢查 100 對
        
        print(f"[INFO] API 檢測模式：將檢查前 {max_checks} 對訂單")
        
        for i in range(max_checks):
            order1 = orders[i]
            order2 = orders[i + 1]
            
            result = detector.check_crossing_api(
                order1['lat'], order1['lon'],
                order2['lat'], order2['lon']
            )
            
            if result:
                crossings.append({
                    'from': order1['tracking_number'],
                    'to': order2['tracking_number'],
                    'method': 'api',
                    'crosses_river': True,
                    'crosses_highway': False  # API 模式主要檢測河流
                })
            
            # 避免 API 限流
            time.sleep(0.1)
    
    return crossings


# 向後兼容：RiverDetector 別名
RiverDetector = ObstacleDetector


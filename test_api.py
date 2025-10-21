#!/usr/bin/env python3
"""使用 Valhalla Demo Server API 進行測試"""

import json
import requests

# Valhalla Demo Server
BASE_URL = "https://valhalla1.openstreetmap.de"


def test_route():
    """測試路徑規劃"""
    print("=" * 50)
    print("測試 Route（路徑規劃）")
    print("=" * 50)
    
    url = f"{BASE_URL}/route"
    
    # 路徑請求：柏林兩點之間
    payload = {
        "locations": [
            {"lat": 52.5200, "lon": 13.4050},  # 柏林布蘭登堡門
            {"lat": 52.5162, "lon": 13.3777}   # 柏林勝利紀念柱
        ],
        "costing": "auto",
        "directions_options": {"language": "zh-TW"}
    }
    
    response = requests.post(url, json=payload)
    data = response.json()
    
    if "trip" in data:
        trip = data["trip"]
        print(f"距離: {trip['summary']['length']:.2f} km")
        print(f"時間: {trip['summary']['time'] / 60:.1f} 分鐘")
        print(f"\n路線指引:")
        for leg in trip["legs"]:
            for i, maneuver in enumerate(leg["maneuvers"], 1):
                instruction = maneuver.get('instruction', 'N/A')
                if instruction != 'N/A':
                    print(f"  {i}. {instruction}")
    
    return data


def test_isochrone():
    """測試等時線圖"""
    print("\n" + "=" * 50)
    print("測試 Isochrone（等時線圖）")
    print("=" * 50)
    
    url = f"{BASE_URL}/isochrone"
    
    # 等時線請求：從柏林布蘭登堡門出發
    payload = {
        "locations": [
            {"lat": 52.5200, "lon": 13.4050}
        ],
        "costing": "auto",
        "contours": [
            {"time": 5, "color": "ff0000"},   # 5 分鐘
            {"time": 10, "color": "00ff00"},  # 10 分鐘
            {"time": 15, "color": "0000ff"}   # 15 分鐘
        ],
        "polygons": True
    }
    
    response = requests.post(url, json=payload)
    data = response.json()
    
    if "features" in data:
        print(f"生成 {len(data['features'])} 個等時線區域")
        for feature in data["features"]:
            props = feature.get("properties", {})
            contour = props.get("contour", "N/A")
            print(f"  - {contour} 分鐘範圍")
    
    return data


def test_matrix():
    """測試距離矩陣"""
    print("\n" + "=" * 50)
    print("測試 Matrix（距離/時間矩陣）")
    print("=" * 50)
    
    url = f"{BASE_URL}/sources_to_targets"
    
    # 矩陣請求：柏林多個景點之間
    locations = [
        {"lat": 52.5200, "lon": 13.4050},  # 布蘭登堡門
        {"lat": 52.5162, "lon": 13.3777},  # 勝利紀念柱
        {"lat": 52.5186, "lon": 13.3761},  # 柏林動物園
        {"lat": 52.5244, "lon": 13.4105}   # 柏林電視塔
    ]
    
    payload = {
        "sources": locations,
        "targets": locations,
        "costing": "auto"
    }
    
    response = requests.post(url, json=payload)
    data = response.json()
    
    if "sources_to_targets" in data:
        matrix = data["sources_to_targets"]
        print(f"矩陣大小: {len(matrix)} x {len(matrix[0]) if matrix else 0}")
        print("\n時間矩陣 (分鐘):")
        for i, row in enumerate(matrix):
            times = [f"{item.get('time', -1) / 60:.1f}" for item in row]
            print(f"  點 {i}: {' | '.join(times)}")
        
        print("\n距離矩陣 (km):")
        for i, row in enumerate(matrix):
            distances = [f"{item.get('distance', -1):.1f}" for item in row]
            print(f"  點 {i}: {' | '.join(distances)}")
    
    return data


def test_optimized_route():
    """測試優化路徑（TSP）"""
    print("\n" + "=" * 50)
    print("測試 Optimized Route（優化路徑/TSP）")
    print("=" * 50)
    
    url = f"{BASE_URL}/optimized_route"
    
    # 優化路徑請求：訪問柏林多個景點的最佳順序
    payload = {
        "locations": [
            {"lat": 52.5200, "lon": 13.4050},  # 起點：布蘭登堡門
            {"lat": 52.5162, "lon": 13.3777},  # 勝利紀念柱
            {"lat": 52.5186, "lon": 13.3761},  # 柏林動物園
            {"lat": 52.5244, "lon": 13.4105},  # 柏林電視塔
            {"lat": 52.5200, "lon": 13.4050}   # 終點：布蘭登堡門
        ],
        "costing": "auto"
    }
    
    response = requests.post(url, json=payload)
    data = response.json()
    
    if "trip" in data:
        trip = data["trip"]
        print(f"總距離: {trip['summary']['length']:.2f} km")
        print(f"總時間: {trip['summary']['time'] / 60:.1f} 分鐘")
        print(f"訪問順序:")
        for i, location in enumerate(trip["locations"], 1):
            print(f"  {i}. ({location['lat']:.4f}, {location['lon']:.4f})")
    
    return data


def test_map_matching():
    """測試地圖匹配"""
    print("\n" + "=" * 50)
    print("測試 Map Matching（軌跡匹配）")
    print("=" * 50)
    
    url = f"{BASE_URL}/trace_attributes"
    
    # GPS 軌跡匹配：將 GPS 點匹配到道路
    payload = {
        "shape": [
            {"lat": 52.5200, "lon": 13.4050},
            {"lat": 52.5210, "lon": 13.4060},
            {"lat": 52.5220, "lon": 13.4070},
            {"lat": 52.5230, "lon": 13.4080}
        ],
        "costing": "auto",
        "shape_match": "map_snap",
        "filters": {
            "attributes": ["edge.length", "edge.speed"],
            "action": "include"
        }
    }
    
    response = requests.post(url, json=payload)
    data = response.json()
    
    if "edges" in data:
        print(f"匹配到 {len(data['edges'])} 條道路邊")
        print("道路資訊:")
        for edge in data["edges"][:5]:  # 只顯示前5條
            length = edge.get('length', 0)
            speed = edge.get('speed', 0)
            print(f"  - 道路長度: {length:.0f}m, 速度: {speed}km/h")
    
    return data


def main():
    """主測試函數"""
    print("\n🚀 開始 Valhalla 路由功能測試")
    print(f"使用 Demo Server: {BASE_URL}\n")
    
    tests = [
        ("Route", test_route),
        ("Isochrone", test_isochrone),
        ("Matrix", test_matrix),
        ("Optimized Route", test_optimized_route),
        ("Map Matching", test_map_matching)
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
            print(f"✅ {name} 測試完成")
        except Exception as e:
            print(f"❌ {name} 測試失敗: {e}")
            results[name] = None
    
    # 儲存結果
    with open("test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 50)
    print("所有測試完成！結果已儲存至 test_results.json")
    print("=" * 50)


if __name__ == "__main__":
    main()


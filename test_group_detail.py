#!/usr/bin/env python3
"""
詳細測試 Group202510172101060201 的分組和序列號生成過程
"""

import requests
import json
from datetime import datetime
import pymysql

# 資料庫配置
DB_CONFIG = {
    'host': '15.156.112.57',
    'port': 33306,
    'user': 'select-user',
    'password': 'emile2024',
    'database': 'bonddb',
    'charset': 'utf8mb4'
}

# API 配置
BASE_URL = "http://localhost:8080"
ORDER_GROUP = "Group202510172101060201"

def get_db_connection():
    """建立資料庫連接"""
    return pymysql.connect(**DB_CONFIG)


def fetch_raw_orders():
    """從資料庫直接獲取原始訂單資料"""
    print("\n" + "="*80)
    print("步驟 1：從資料庫獲取原始訂單")
    print("="*80)
    
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    query = """
        SELECT tracking_number, latitude, longitude, delivery_sequence
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
    
    print(f"\n✅ 找到 {len(orders)} 個訂單")
    print(f"\n前 5 個訂單範例：")
    for i, order in enumerate(orders[:5], 1):
        lat_raw = float(order['latitude'])
        lon_raw = float(order['longitude'])
        lat = lat_raw / 10000000000.0 if abs(lat_raw) > 1000 else lat_raw
        lon = lon_raw / 10000000000.0 if abs(lon_raw) > 1000 else lon_raw
        print(f"  {i}. {order['tracking_number']}")
        print(f"     原始座標: ({lat_raw}, {lon_raw})")
        print(f"     轉換後座標: ({lat:.6f}, {lon:.6f})")
        if order['delivery_sequence']:
            print(f"     資料庫序列號: {order['delivery_sequence']}")
    
    return orders


def analyze_distribution():
    """分析訂單分佈並獲取建議參數"""
    print("\n" + "="*80)
    print("步驟 2：分析訂單分佈")
    print("="*80)
    
    response = requests.post(
        f"{BASE_URL}/api/analyze-distribution",
        json={"order_group": ORDER_GROUP}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ 分析完成")
        print(f"\n訂單統計：")
        print(f"  - 總數: {data['total_orders']}")
        print(f"  - 長寬比: {data['aspect_ratio']}")
        print(f"  - 密度: {data['density']} 訂單/km²")
        print(f"  - 方向: {data['orientation']}")
        print(f"  - 凸包面積: {data['hull_area_km']} km²")
        print(f"  - 可能跨河: {'是' if data['likely_crosses_river'] else '否'}")
        print(f"  - 最大跨度: {data['max_range_km']} km")
        
        print(f"\n智能建議參數：")
        suggestions = data['suggestions']
        for key, value in suggestions.items():
            print(f"  - {key}: {value}")
        
        print(f"\n建議理由: {data['reasoning']}")
        
        return suggestions
    else:
        print(f"❌ 分析失敗: {response.text}")
        return None


def calculate_route(suggestions=None):
    """計算路徑並記錄分組過程"""
    print("\n" + "="*80)
    print("步驟 3：計算路徑與分組")
    print("="*80)
    
    # 使用建議參數或默認參數
    params = {
        "order_group": ORDER_GROUP,
        "start": {
            "lat": 43.6532,
            "lon": -79.3832
        },
        "costing": "auto",
        "max_orders": 5000,
        "max_group_size": suggestions.get('max_group_size', 30) if suggestions else 30,
        "cluster_radius": suggestions.get('cluster_radius', 1.0) if suggestions else 1.0,
        "min_samples": suggestions.get('min_samples', 3) if suggestions else 3,
        "metric": suggestions.get('metric', 'euclidean') if suggestions else 'euclidean',
        "random_state": 42,
        "n_init": 10,
        "verification": suggestions.get('verification', 'none') if suggestions else 'none',
        "group_penalty": suggestions.get('group_penalty', 2.0) if suggestions else 2.0,
        "inner_penalty": suggestions.get('inner_penalty', 1.5) if suggestions else 1.5,
        "check_highways": suggestions.get('check_highways', False) if suggestions else False,
        "group_order_method": suggestions.get('group_order_method', 'greedy') if suggestions else 'greedy',
        "inner_order_method": "nearest",
        "end_point_mode": "last_order"
    }
    
    print(f"\n使用參數：")
    for key, value in params.items():
        if key != 'start':
            print(f"  - {key}: {value}")
    print(f"  - start: ({params['start']['lat']}, {params['start']['lon']})")
    
    response = requests.post(
        f"{BASE_URL}/api/route",
        json=params
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ 路徑計算完成")
        print(f"\n結果統計：")
        print(f"  - 處理訂單數: {data['total_orders']}")
        print(f"  - 分組數: {data['total_groups']}")
        
        return data
    else:
        print(f"❌ 路徑計算失敗: {response.text}")
        return None


def analyze_grouping(result_data):
    """分析分組結果"""
    print("\n" + "="*80)
    print("步驟 4：分析分組結果")
    print("="*80)
    
    orders = result_data['orders']
    
    # 按群組分類
    groups = {}
    for order in orders:
        group = order['group']
        if group not in groups:
            groups[group] = []
        groups[group].append(order)
    
    print(f"\n共分成 {len(groups)} 個群組：")
    for group_name in sorted(groups.keys()):
        group_orders = groups[group_name]
        print(f"\n群組 {group_name}: {len(group_orders)} 個訂單")
        print(f"  序列範圍: {group_orders[0]['sequence']} - {group_orders[-1]['sequence']}")
        print(f"  組內編號: {group_orders[0]['group_sequence']} - {group_orders[-1]['group_sequence']}")
        
        # 顯示前 3 個訂單
        print(f"  前 3 個訂單:")
        for order in group_orders[:3]:
            print(f"    - {order['tracking_number']}")
            print(f"      全局序號: {order['sequence']}")
            print(f"      組內編號: {order['group_sequence']}")
            print(f"      座標: ({order['lat']:.6f}, {order['lon']:.6f})")
    
    return groups


def generate_detailed_report(raw_orders, suggestions, result_data, groups):
    """生成詳細報告"""
    print("\n" + "="*80)
    print("步驟 5：生成詳細報告")
    print("="*80)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"GROUP_ANALYSIS_{ORDER_GROUP}_{timestamp}.md"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# {ORDER_GROUP} 分組與序列號生成詳細報告\n\n")
        f.write(f"生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")
        
        # 原始資料
        f.write("## 1. 原始訂單資料\n\n")
        f.write(f"- 訂單總數: {len(raw_orders)}\n")
        f.write(f"- Order Group: `{ORDER_GROUP}`\n\n")
        
        f.write("### 前 10 個訂單範例\n\n")
        f.write("| # | Tracking Number | 緯度 | 經度 | 資料庫序列號 |\n")
        f.write("|---|-----------------|------|------|-------------|\n")
        for i, order in enumerate(raw_orders[:10], 1):
            lat_raw = float(order['latitude'])
            lon_raw = float(order['longitude'])
            lat = lat_raw / 10000000000.0 if abs(lat_raw) > 1000 else lat_raw
            lon = lon_raw / 10000000000.0 if abs(lon_raw) > 1000 else lon_raw
            seq = order.get('delivery_sequence', 'NULL')
            f.write(f"| {i} | {order['tracking_number']} | {lat:.6f} | {lon:.6f} | {seq} |\n")
        
        f.write("\n---\n\n")
        
        # 智能分析建議
        if suggestions:
            f.write("## 2. 智能分析建議\n\n")
            f.write("| 參數 | 建議值 | 說明 |\n")
            f.write("|------|--------|------|\n")
            f.write(f"| group_order_method | {suggestions['group_order_method']} | 群組排序方法 |\n")
            f.write(f"| max_group_size | {suggestions['max_group_size']} | 每組最大訂單數 |\n")
            f.write(f"| cluster_radius | {suggestions['cluster_radius']} km | DBSCAN 鄰域半徑 |\n")
            f.write(f"| min_samples | {suggestions['min_samples']} | DBSCAN 最小樣本數 |\n")
            f.write(f"| verification | {suggestions['verification']} | 跨河檢測方式 |\n")
            f.write(f"| group_penalty | {suggestions['group_penalty']} | 群組間跨河懲罰 |\n")
            f.write(f"| inner_penalty | {suggestions['inner_penalty']} | 組內跨河懲罰 |\n")
            f.write("\n---\n\n")
        
        # 分組結果
        f.write("## 3. 分組結果\n\n")
        f.write(f"- 總群組數: {len(groups)}\n")
        f.write(f"- 總訂單數: {result_data['total_orders']}\n\n")
        
        for group_name in sorted(groups.keys()):
            group_orders = groups[group_name]
            f.write(f"### 群組 {group_name}\n\n")
            f.write(f"- 訂單數: {len(group_orders)}\n")
            f.write(f"- 全局序列號範圍: {group_orders[0]['sequence']} - {group_orders[-1]['sequence']}\n")
            f.write(f"- 組內編號範圍: {group_orders[0]['group_sequence']} - {group_orders[-1]['group_sequence']}\n\n")
            
            f.write("#### 所有訂單列表\n\n")
            f.write("| 全局序號 | 組內編號 | Tracking Number | 緯度 | 經度 |\n")
            f.write("|----------|----------|-----------------|------|------|\n")
            for order in group_orders:
                f.write(f"| {order['sequence']} | {order['group_sequence']} | {order['tracking_number']} | {order['lat']:.6f} | {order['lon']:.6f} |\n")
            f.write("\n")
        
        f.write("---\n\n")
        
        # 序列號生成邏輯
        f.write("## 4. 序列號生成邏輯\n\n")
        f.write("### 全局序號（sequence）\n\n")
        f.write("- 從 1 開始遞增\n")
        f.write("- 按照分組順序和組內順序連續編號\n")
        f.write("- 範圍: 1 到 {}\n\n".format(result_data['total_orders']))
        
        f.write("### 組內編號（group_sequence）\n\n")
        f.write("- 格式: `{群組字母}-{組內序號}`\n")
        f.write("- 組內序號從 01 開始，補零到 2 位數\n")
        f.write("- 範例: A-01, A-02, ..., B-01, B-02, ...\n\n")
        
        f.write("### 群組字母分配\n\n")
        f.write("- 按照群組訪問順序分配字母：A, B, C, ..., Z\n")
        f.write("- 如果超過 26 組，使用 Z1, Z2, Z3, ...\n\n")
        
        f.write("---\n\n")
        
        # 完整序列映射
        f.write("## 5. 完整訂單序列映射表\n\n")
        f.write("| 全局序號 | 組內編號 | 群組 | Tracking Number |\n")
        f.write("|----------|----------|------|------------------|\n")
        for order in result_data['orders']:
            f.write(f"| {order['sequence']} | {order['group_sequence']} | {order['group']} | {order['tracking_number']} |\n")
        
        f.write("\n---\n\n")
        f.write("## 總結\n\n")
        f.write(f"本次測試使用混合聚類算法（DBSCAN + K-means）對 {len(raw_orders)} 個訂單進行智能分組，\n")
        f.write(f"最終生成 {len(groups)} 個群組，每個群組包含不同數量的訂單。\n\n")
        f.write("序列號生成遵循以下規則：\n")
        f.write("1. **全局序號**：按訪問順序從 1 遞增\n")
        f.write("2. **組內編號**：格式為 `{群組}-{序號}`，例如 A-01, A-02\n")
        f.write("3. **群組字母**：按訪問順序分配 A, B, C...\n\n")
    
    print(f"\n✅ 報告已生成: {filename}")
    return filename


def main():
    """主函數"""
    print("\n" + "="*80)
    print(f"開始測試: {ORDER_GROUP}")
    print("="*80)
    
    # 步驟 1: 獲取原始訂單
    raw_orders = fetch_raw_orders()
    
    # 步驟 2: 分析分佈並獲取建議
    suggestions = analyze_distribution()
    
    # 步驟 3: 計算路徑
    result_data = calculate_route(suggestions)
    
    if result_data:
        # 步驟 4: 分析分組
        groups = analyze_grouping(result_data)
        
        # 步驟 5: 生成報告
        report_file = generate_detailed_report(raw_orders, suggestions, result_data, groups)
        
        print("\n" + "="*80)
        print("測試完成！")
        print("="*80)
        print(f"\n詳細報告: {report_file}")
        print(f"總訂單數: {len(raw_orders)}")
        print(f"總群組數: {len(groups)}")
    else:
        print("\n❌ 測試失敗")


if __name__ == '__main__':
    main()


